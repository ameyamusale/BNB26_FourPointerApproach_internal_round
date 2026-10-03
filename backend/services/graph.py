"""Provenance graph (Phase 5).

Builds the model / artifact / application node graph with typed edges from the
provenance events. This is the data source for the /lineage page and for the
graph section of each passport. Only registry metadata is exposed — never
private event metadata (that is committed as a hash only).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set

from models.provenance import LineageStep, ProvenanceAction
from services import provenance as provenance_service
from services.store import store


def _provenance_step_to_edge(step: LineageStep, index: int, origin_node_id: str) -> Optional[dict]:
    event = step.event
    if event is None:
        return None
    if event.action == ProvenanceAction.GENERATED:
        source = origin_node_id if event.model_id else ("app:" + (event.application_id or "unknown"))
        label = "GENERATED"
    else:
        source = ("model:" + event.model_id) if event.model_id else ("app:" + (event.application_id or "unknown"))
        label = event.action.value
    return {
        "source": source,
        "target": "artifact:" + step.artifact_id,
        "label": label,
        "event_id": event.event_id,
        "model_id": event.model_id,
        "application_id": event.application_id,
        "signed": bool(event.signature),
        "blockchain_tx": event.blockchain_tx,
        "order": index,
    }


def build_graph(artifact_id: str) -> dict:
    """Build the graph for one artifact: its ancestors, the producing models and apps."""
    lineage = provenance_service.build_lineage(artifact_id)
    nodes: Dict[str, dict] = {}
    edges: List[dict] = []
    seen_apps: Set[str] = set()

    steps = list(lineage.steps)
    for index, step in enumerate(steps):
        artifact = store.get_artifact(step.artifact_id)
        if artifact is None:
            nodes["artifact:" + step.artifact_id] = {
                "id": "artifact:" + step.artifact_id, "kind": "ARTIFACT", "label": step.artifact_id,
                "artifact_id": step.artifact_id, "missing": True,
            }
            continue
        nodes["artifact:" + artifact.artifact_id] = {
            "id": "artifact:" + artifact.artifact_id, "kind": "ARTIFACT",
            "label": artifact.artifact_id, "artifact_id": artifact.artifact_id,
            "exact_hash": artifact.exact_hash, "model_id": artifact.model_id,
        }
        event = step.event
        if event is None:
            continue
        if event.action == ProvenanceAction.GENERATED and event.model_id:
            model = store.get_model(event.model_id)
            node_id = "model:" + event.model_id
            nodes.setdefault(node_id, {
                "id": node_id, "kind": "MODEL", "label": f"{model.name} v{model.version}" if model else event.model_id,
                "model_id": event.model_id, "missing": model is None,
            })
        elif event.application_id:
            node_id = "app:" + event.application_id
            if node_id not in seen_apps:
                seen_apps.add(node_id)
                nodes.setdefault(node_id, {
                    "id": node_id, "kind": "APPLICATION", "label": event.application_id,
                    "application_id": event.application_id,
                })
        edge = _provenance_step_to_edge(step, index, "model:" + event.model_id if event.model_id else "app:" + (event.application_id or "unknown"))
        if edge is not None:
            edges.append(edge)

    # The topmost event is the origin; MODEL/APPLICATION source nodes for it are
    # added above. Any edge whose source node never got created means the
    # referenced model/application row vanished; emit an explicit missing node.
    for edge in edges:
        if edge["source"] not in nodes:
            nodes[edge["source"]] = {
                "id": edge["source"], "kind": edge["source"].split(":", 1)[0].upper(),
                "label": edge["source"].split(":", 1)[1], "missing": True,
            }

    return {
        "artifact_id": artifact_id,
        "lineage": lineage,
        "nodes": list(nodes.values()),
        "edges": edges,
        "depth": lineage.depth,
        "root_reached": lineage.root_reached,
        "issues": list(lineage.issues),
    }


def build_full_graph() -> dict:
    """Whole-registry graph (dashboard / audit page): every model, artifact, event."""
    nodes: Dict[str, dict] = {}
    edges: List[dict] = []

    for model in store.list_models():
        nodes["model:" + model.model_id] = {
            "id": "model:" + model.model_id, "kind": "MODEL",
            "label": f"{model.name} v{model.version}", "model_id": model.model_id,
            "status": model.status.value, "creator": model.creator_name,
        }
    for artifact in store.list_artifacts():
        nodes["artifact:" + artifact.artifact_id] = {
            "id": "artifact:" + artifact.artifact_id, "kind": "ARTIFACT",
            "label": artifact.artifact_id, "artifact_id": artifact.artifact_id,
            "exact_hash": artifact.exact_hash, "model_id": artifact.model_id,
        }
    for event in store.list_events():
        child_exists = store.get_artifact(event.child_artifact_id) is not None
        if event.action == ProvenanceAction.GENERATED:
            if event.model_id:
                source = "model:" + event.model_id
            else:
                source = "app:" + (event.application_id or "unknown")
                nodes.setdefault(source, {
                    "id": source, "kind": "APPLICATION",
                    "label": event.application_id or "unknown", "application_id": event.application_id,
                })
            label = "GENERATED"
        else:
            if event.model_id:
                source = "model:" + event.model_id
            else:
                source = "app:" + (event.application_id or "unknown")
                nodes.setdefault(source, {
                    "id": source, "kind": "APPLICATION",
                    "label": event.application_id or "unknown", "application_id": event.application_id,
                })
            label = event.action.value
        if event.parent_artifact_id and store.get_artifact(event.parent_artifact_id) is None:
            nodes.setdefault("artifact:" + event.parent_artifact_id, {
                "id": "artifact:" + event.parent_artifact_id, "kind": "ARTIFACT",
                "label": event.parent_artifact_id, "artifact_id": event.parent_artifact_id, "missing": True,
            })
        if not child_exists:
            nodes.setdefault("artifact:" + event.child_artifact_id, {
                "id": "artifact:" + event.child_artifact_id, "kind": "ARTIFACT",
                "label": event.child_artifact_id, "artifact_id": event.child_artifact_id, "missing": True,
            })
        edges.append({
            "source": source, "target": "artifact:" + event.child_artifact_id,
            "label": label, "event_id": event.event_id,
            "parent_artifact_id": event.parent_artifact_id,
            "signed": bool(event.signature), "blockchain_tx": event.blockchain_tx,
            "created_at": event.created_at.isoformat(),
        })

    for edge in edges:
        if edge["source"] not in nodes:
            kind, _, name = edge["source"].partition(":")
            nodes[edge["source"]] = {"id": edge["source"], "kind": kind.upper(), "label": name, "missing": True}

    return {"nodes": list(nodes.values()), "edges": edges}
