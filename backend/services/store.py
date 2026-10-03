"""Thread-safe SQLite persistent store for Phase 2 data models and Phase 9 Audit Logs.

Replaces the in-memory maps from Phase 1 with a real local SQLite database.
Schema tables:
- identities
- models
- artifacts
- provenance_events
- claims
- audit_logs (tamper-evident SHA-256 hash-chained log)
"""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.artifact import ArtifactRecord, ArtifactStatus, ArtifactType
from models.claims import VerificationEvidence
from models.model import ModelRecord, ModelStatus
from models.provenance import ProvenanceAction, ProvenanceEvent


class SQLiteStore:
    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        p = Path(self.db_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    def _initialize(self) -> None:
        with self.lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS identities (
                    identity_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    wallet_address TEXT,
                    role TEXT NOT NULL DEFAULT 'CREATOR',
                    biometric_enrollment_reference TEXT,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS models (
                    model_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    creator_id TEXT NOT NULL,
                    creator_name TEXT NOT NULL,
                    description TEXT,
                    model_hash TEXT NOT NULL,
                    metadata_hash TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    created_at TEXT NOT NULL,
                    blockchain_tx TEXT,
                    creator_verified INTEGER NOT NULL DEFAULT 0,
                    biometric_commitment TEXT,
                    private_prompt_commitment TEXT,
                    FOREIGN KEY (creator_id) REFERENCES identities(identity_id)
                );

                CREATE UNIQUE INDEX IF NOT EXISTS uq_models_metadata_hash
                    ON models(metadata_hash);

                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    artifact_type TEXT NOT NULL,
                    exact_hash TEXT NOT NULL UNIQUE,
                    robust_fingerprint TEXT,
                    size_bytes INTEGER NOT NULL,
                    storage_uri TEXT,
                    model_id TEXT,
                    status TEXT NOT NULL DEFAULT 'REGISTERED',
                    created_at TEXT NOT NULL,
                    blockchain_tx TEXT,
                    FOREIGN KEY (model_id) REFERENCES models(model_id)
                );

                CREATE INDEX IF NOT EXISTS idx_artifacts_model_id ON artifacts(model_id);
                CREATE INDEX IF NOT EXISTS idx_artifacts_robust_fp ON artifacts(robust_fingerprint);

                CREATE TABLE IF NOT EXISTS provenance_events (
                    event_id TEXT PRIMARY KEY,
                    parent_artifact_id TEXT,
                    child_artifact_id TEXT NOT NULL,
                    model_id TEXT,
                    application_id TEXT,
                    action TEXT NOT NULL,
                    metadata_hash TEXT NOT NULL,
                    signature TEXT,
                    signature_public_key TEXT,
                    blockchain_tx TEXT,
                    created_at TEXT NOT NULL,
                    creator_verified INTEGER NOT NULL DEFAULT 0,
                    biometric_commitment TEXT,
                    FOREIGN KEY (parent_artifact_id) REFERENCES artifacts(artifact_id),
                    FOREIGN KEY (child_artifact_id) REFERENCES artifacts(artifact_id),
                    FOREIGN KEY (model_id) REFERENCES models(model_id)
                );

                CREATE UNIQUE INDEX IF NOT EXISTS uq_event_child ON provenance_events(child_artifact_id);
                CREATE INDEX IF NOT EXISTS idx_events_parent ON provenance_events(parent_artifact_id);
                CREATE INDEX IF NOT EXISTS idx_events_child ON provenance_events(child_artifact_id);

                CREATE TABLE IF NOT EXISTS claims (
                    claim_id TEXT PRIMARY KEY,
                    artifact_id TEXT NOT NULL,
                    claim_type TEXT NOT NULL,
                    issuer_id TEXT,
                    evidence_type TEXT,
                    signature TEXT,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    evidence_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (artifact_id) REFERENCES artifacts(artifact_id),
                    FOREIGN KEY (issuer_id) REFERENCES identities(identity_id)
                );

                CREATE INDEX IF NOT EXISTS idx_claims_artifact_id ON claims(artifact_id);
                CREATE INDEX IF NOT EXISTS idx_claims_issuer_id ON claims(issuer_id);

                CREATE TABLE IF NOT EXISTS audit_logs (
                    log_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    resource_id TEXT,
                    details_json TEXT NOT NULL DEFAULT '{}',
                    prev_hash TEXT NOT NULL,
                    log_hash TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
                """
            )
            existing_models = {row[1] for row in conn.execute("PRAGMA table_info(models)").fetchall()}
            existing_artifacts = {row[1] for row in conn.execute("PRAGMA table_info(artifacts)").fetchall()}
            existing_events = {row[1] for row in conn.execute("PRAGMA table_info(provenance_events)").fetchall()}
            if "blockchain_tx" not in existing_models:
                conn.execute("ALTER TABLE models ADD COLUMN blockchain_tx TEXT")
            if "creator_verified" not in existing_models:
                conn.execute("ALTER TABLE models ADD COLUMN creator_verified INTEGER DEFAULT 0")
            if "biometric_commitment" not in existing_models:
                conn.execute("ALTER TABLE models ADD COLUMN biometric_commitment TEXT")
            if "private_prompt_commitment" not in existing_models:
                conn.execute("ALTER TABLE models ADD COLUMN private_prompt_commitment TEXT")
            if "blockchain_tx" not in existing_artifacts:
                conn.execute("ALTER TABLE artifacts ADD COLUMN blockchain_tx TEXT")
            if "signature_public_key" not in existing_events:
                conn.execute("ALTER TABLE provenance_events ADD COLUMN signature_public_key TEXT")
            if "creator_verified" not in existing_events:
                conn.execute("ALTER TABLE provenance_events ADD COLUMN creator_verified INTEGER DEFAULT 0")
            if "biometric_commitment" not in existing_events:
                conn.execute("ALTER TABLE provenance_events ADD COLUMN biometric_commitment TEXT")

    @staticmethod
    def _dt(value: str):
        return datetime.fromisoformat(value)

    @staticmethod
    def _model(row: sqlite3.Row) -> ModelRecord:
        keys = row.keys()
        return ModelRecord(
            model_id=row["model_id"],
            name=row["name"],
            version=row["version"],
            model_type=row["model_type"],
            creator_id=row["creator_id"],
            creator_name=row["creator_name"],
            description=row["description"],
            model_hash=row["model_hash"],
            metadata_hash=row["metadata_hash"],
            status=row["status"],
            created_at=SQLiteStore._dt(row["created_at"]),
            blockchain_tx=row["blockchain_tx"],
            creator_verified=bool(row["creator_verified"]) if "creator_verified" in keys else False,
            biometric_commitment=row["biometric_commitment"] if "biometric_commitment" in keys else None,
            private_prompt_commitment=row["private_prompt_commitment"] if "private_prompt_commitment" in keys else None,
        )

    @staticmethod
    def _artifact(row: sqlite3.Row) -> ArtifactRecord:
        return ArtifactRecord(
            artifact_id=row["artifact_id"],
            artifact_type=row["artifact_type"],
            exact_hash=row["exact_hash"],
            robust_fingerprint=row["robust_fingerprint"],
            size_bytes=row["size_bytes"],
            storage_uri=row["storage_uri"],
            model_id=row["model_id"],
            status=row["status"],
            created_at=SQLiteStore._dt(row["created_at"]),
            blockchain_tx=row["blockchain_tx"],
        )

    @staticmethod
    def _event(row: sqlite3.Row) -> ProvenanceEvent:
        keys = row.keys()
        return ProvenanceEvent(
            event_id=row["event_id"],
            parent_artifact_id=row["parent_artifact_id"],
            child_artifact_id=row["child_artifact_id"],
            action=row["action"],
            model_id=row["model_id"],
            application_id=row["application_id"],
            metadata_hash=row["metadata_hash"],
            signature=row["signature"],
            blockchain_tx=row["blockchain_tx"],
            signature_public_key=row["signature_public_key"],
            created_at=SQLiteStore._dt(row["created_at"]),
            creator_verified=bool(row["creator_verified"]) if "creator_verified" in keys else False,
            biometric_commitment=row["biometric_commitment"] if "biometric_commitment" in keys else None,
        )

    # Compatibility views used by the existing Phase 1 code and status endpoint.
    @property
    def models(self) -> Dict[str, ModelRecord]:
        with self.lock, self._connect() as conn:
            rows = conn.execute("SELECT * FROM models").fetchall()
        return {r["model_id"]: self._model(r) for r in rows}

    @property
    def artifacts(self) -> Dict[str, ArtifactRecord]:
        with self.lock, self._connect() as conn:
            rows = conn.execute("SELECT * FROM artifacts").fetchall()
        return {r["artifact_id"]: self._artifact(r) for r in rows}

    @property
    def events(self) -> Dict[str, ProvenanceEvent]:
        with self.lock, self._connect() as conn:
            rows = conn.execute("SELECT * FROM provenance_events").fetchall()
        return {r["event_id"]: self._event(r) for r in rows}

    def reset(self) -> None:
        """Clear application data while retaining the database schema."""
        with self.lock, self._connect() as conn:
            conn.execute("DELETE FROM audit_logs")
            conn.execute("DELETE FROM claims")
            conn.execute("DELETE FROM provenance_events")
            conn.execute("DELETE FROM artifacts")
            conn.execute("DELETE FROM models")
            conn.execute("DELETE FROM identities")
            conn.commit()

    def log_audit(
        self,
        action: str,
        actor: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record an immutable, hash-chained audit log entry."""
        import hashlib
        log_id = f"AUD-{uuid.uuid4().hex[:10].upper()}"
        ts = datetime.now(timezone.utc).isoformat()
        details_str = json.dumps(details or {}, sort_keys=True)
        with self.lock, self._connect() as conn:
            last_row = conn.execute("SELECT log_hash FROM audit_logs ORDER BY rowid DESC LIMIT 1").fetchone()
            prev_hash = last_row[0] if last_row else "0" * 64
            h_payload = f"{prev_hash}:{log_id}:{ts}:{action}:{actor}:{resource_id or ''}:{details_str}"
            log_hash = hashlib.sha256(h_payload.encode()).hexdigest()
            conn.execute(
                """INSERT INTO audit_logs(log_id, timestamp, action, actor, resource_id, details_json, prev_hash, log_hash)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (log_id, ts, action, actor, resource_id, details_str, prev_hash, log_hash),
            )
            conn.commit()
        return {
            "log_id": log_id,
            "timestamp": ts,
            "action": action,
            "actor": actor,
            "resource_id": resource_id,
            "details": details or {},
            "prev_hash": prev_hash,
            "log_hash": log_hash,
        }

    def list_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self.lock, self._connect() as conn:
            rows = conn.execute("SELECT * FROM audit_logs ORDER BY rowid DESC LIMIT ?", (limit,)).fetchall()
        res = []
        for r in rows:
            d = dict(r)
            try:
                d["details"] = json.loads(d["details_json"])
            except Exception:
                d["details"] = {}
            res.append(d)
        return res

    def verify_audit_log_chain(self) -> Dict[str, Any]:
        """Verify the cryptographic integrity of the entire audit log chain."""
        import hashlib
        with self.lock, self._connect() as conn:
            rows = conn.execute("SELECT * FROM audit_logs ORDER BY rowid ASC").fetchall()
        if not rows:
            return {
                "valid": True,
                "chain_intact": True,
                "count": 0,
                "verified_count": 0,
                "genesis_hash": "0" * 64,
                "latest_hash": "0" * 64,
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "chain_status": "INTACT",
                "details": "No audit records",
            }
        prev_hash = "0" * 64
        genesis_hash = rows[0]["prev_hash"] if rows else "0" * 64
        for idx, r in enumerate(rows):
            if r["prev_hash"] != prev_hash:
                return {
                    "valid": False,
                    "chain_intact": False,
                    "broken_at_index": idx,
                    "broken_at_entry_id": r["log_id"],
                    "log_id": r["log_id"],
                    "message": "Previous hash link mismatch (chain corruption/tampering)",
                    "reason": "Previous hash link mismatch (chain corruption/tampering)",
                }
            h_payload = f"{r['prev_hash']}:{r['log_id']}:{r['timestamp']}:{r['action']}:{r['actor']}:{r['resource_id'] or ''}:{r['details_json']}"
            expected_hash = hashlib.sha256(h_payload.encode()).hexdigest()
            if r["log_hash"] != expected_hash:
                return {
                    "valid": False,
                    "chain_intact": False,
                    "broken_at_index": idx,
                    "broken_at_entry_id": r["log_id"],
                    "log_id": r["log_id"],
                    "message": "Log hash tampering detected",
                    "reason": "Log hash tampering detected",
                }
            prev_hash = r["log_hash"]
        return {
            "valid": True,
            "chain_intact": True,
            "count": len(rows),
            "verified_count": len(rows),
            "genesis_hash": genesis_hash,
            "latest_hash": prev_hash,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "chain_status": "INTACT",
        }

    def upsert_identity(
        self,
        identity_id: str,
        name: str,
        role: str = "CREATOR",
        wallet_address: Optional[str] = None
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.lock, self._connect() as conn:
            conn.execute(
                """INSERT INTO identities(identity_id,name,wallet_address,role,status,created_at)
                   VALUES(?,?,?,?,?,?)
                   ON CONFLICT(identity_id) DO UPDATE SET name=excluded.name,
                   wallet_address=COALESCE(excluded.wallet_address, identities.wallet_address)""",
                (identity_id, name, wallet_address, role, "ACTIVE", now),
            )
            conn.commit()

    def insert_model(self, record: ModelRecord) -> None:
        with self.lock, self._connect() as conn:
            conn.execute(
                """INSERT INTO identities(identity_id,name,role,status,created_at)
                   VALUES(?,?,?,?,?)
                   ON CONFLICT(identity_id) DO UPDATE SET name=excluded.name""",
                (record.creator_id, record.creator_name, "CREATOR", "ACTIVE", record.created_at.isoformat()),
            )
            conn.execute(
                """INSERT INTO models(model_id,name,version,model_type,creator_id,creator_name,
                   description,model_hash,metadata_hash,status,created_at,blockchain_tx,
                   creator_verified,biometric_commitment,private_prompt_commitment)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    record.model_id, record.name, record.version, record.model_type,
                    record.creator_id, record.creator_name, record.description, record.model_hash,
                    record.metadata_hash, record.status.value, record.created_at.isoformat(), record.blockchain_tx,
                    1 if record.creator_verified else 0, record.biometric_commitment, record.private_prompt_commitment,
                ),
            )
            conn.commit()

    def get_model(self, model_id: str) -> Optional[ModelRecord]:
        with self.lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM models WHERE model_id=?", (model_id,)).fetchone()
        return self._model(row) if row else None

    def insert_artifact(self, record: ArtifactRecord) -> None:
        with self.lock, self._connect() as conn:
            conn.execute(
                """INSERT INTO artifacts(artifact_id,artifact_type,exact_hash,robust_fingerprint,
                   size_bytes,storage_uri,model_id,status,created_at,blockchain_tx) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    record.artifact_id, record.artifact_type.value, record.exact_hash,
                    record.robust_fingerprint, record.size_bytes, record.storage_uri, record.model_id,
                    record.status.value, record.created_at.isoformat(), record.blockchain_tx,
                ),
            )
            conn.commit()

    def get_artifact(self, artifact_id: str) -> Optional[ArtifactRecord]:
        with self.lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM artifacts WHERE artifact_id=?", (artifact_id,)).fetchone()
        return self._artifact(row) if row else None

    def insert_event(self, event: ProvenanceEvent) -> None:
        with self.lock, self._connect() as conn:
            conn.execute(
                """INSERT INTO provenance_events(event_id,parent_artifact_id,child_artifact_id,
                   model_id,application_id,action,metadata_hash,signature,signature_public_key,blockchain_tx,created_at,
                   creator_verified,biometric_commitment)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    event.event_id, event.parent_artifact_id, event.child_artifact_id, event.model_id,
                    event.application_id, event.action.value, event.metadata_hash, event.signature,
                    event.signature_public_key, event.blockchain_tx, event.created_at.isoformat(),
                    1 if event.creator_verified else 0, event.biometric_commitment,
                ),
            )
            conn.commit()

    def update_model_blockchain_tx(self, model_id: str, tx_hash: str) -> None:
        with self.lock, self._connect() as conn:
            conn.execute("UPDATE models SET blockchain_tx=? WHERE model_id=?", (tx_hash, model_id))
            conn.commit()

    def update_artifact_blockchain_tx(self, artifact_id: str, tx_hash: str) -> None:
        with self.lock, self._connect() as conn:
            conn.execute("UPDATE artifacts SET blockchain_tx=? WHERE artifact_id=?", (tx_hash, artifact_id))
            conn.commit()

    def update_event_evidence(
        self,
        event_id: str,
        signature: Optional[str] = None,
        signature_public_key: Optional[str] = None,
        blockchain_tx: Optional[str] = None,
        creator_verified: Optional[bool] = None,
        biometric_commitment: Optional[str] = None
    ) -> None:
        with self.lock, self._connect() as conn:
            current = conn.execute(
                "SELECT signature,signature_public_key,blockchain_tx,creator_verified,biometric_commitment FROM provenance_events WHERE event_id=?",
                (event_id,),
            ).fetchone()
            if not current:
                return
            conn.execute(
                """UPDATE provenance_events SET signature=?, signature_public_key=?, blockchain_tx=?,
                   creator_verified=?, biometric_commitment=? WHERE event_id=?""",
                (
                    signature if signature is not None else current[0],
                    signature_public_key if signature_public_key is not None else current[1],
                    blockchain_tx if blockchain_tx is not None else current[2],
                    (1 if creator_verified else 0) if creator_verified is not None else current[3],
                    biometric_commitment if biometric_commitment is not None else current[4],
                    event_id,
                ),
            )
            conn.commit()

    def revoke_model(self, model_id: str) -> None:
        with self.lock, self._connect() as conn:
            conn.execute("UPDATE models SET status='REVOKED' WHERE model_id=?", (model_id,))
            conn.commit()

    def events_for_child(self, artifact_id: str) -> List[ProvenanceEvent]:
        with self.lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM provenance_events WHERE child_artifact_id=? ORDER BY created_at",
                (artifact_id,),
            ).fetchall()
        return [self._event(r) for r in rows]

    def events_for_artifact(self, artifact_id: str) -> List[ProvenanceEvent]:
        with self.lock, self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM provenance_events
                   WHERE child_artifact_id=? OR parent_artifact_id=? ORDER BY created_at""",
                (artifact_id, artifact_id),
            ).fetchall()
        return [self._event(r) for r in rows]

    def find_artifact_by_hash(self, exact_hash: str) -> Optional[ArtifactRecord]:
        with self.lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM artifacts WHERE lower(exact_hash)=lower(?) LIMIT 1", (exact_hash,)
            ).fetchone()
        return self._artifact(row) if row else None

    def list_models(self) -> List[ModelRecord]:
        with self.lock, self._connect() as conn:
            rows = conn.execute("SELECT * FROM models ORDER BY created_at DESC").fetchall()
        return [self._model(r) for r in rows]

    def list_artifacts(self) -> List[ArtifactRecord]:
        with self.lock, self._connect() as conn:
            rows = conn.execute("SELECT * FROM artifacts ORDER BY created_at DESC").fetchall()
        return [self._artifact(r) for r in rows]

    def list_events(self) -> List[ProvenanceEvent]:
        with self.lock, self._connect() as conn:
            rows = conn.execute("SELECT * FROM provenance_events ORDER BY created_at DESC").fetchall()
        return [self._event(r) for r in rows]

    def create_claim(
        self,
        claim_id: str,
        artifact_id: str,
        claim_type: str,
        issuer_id: Optional[str],
        evidence_type: Optional[str],
        signature: Optional[str],
        status: str,
        evidence: Optional[VerificationEvidence] = None
    ) -> None:
        evidence_json = evidence.model_dump_json() if evidence else "{}"
        with self.lock, self._connect() as conn:
            conn.execute(
                """INSERT INTO claims(claim_id,artifact_id,claim_type,issuer_id,evidence_type,
                   signature,status,evidence_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    claim_id, artifact_id, claim_type, issuer_id, evidence_type, signature,
                    status, evidence_json, datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()

    def get_claim(self, claim_id: str) -> Optional[Dict[str, Any]]:
        with self.lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM claims WHERE claim_id=?", (claim_id,)).fetchone()
        return dict(row) if row else None

    def list_claims(self, artifact_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.lock, self._connect() as conn:
            if artifact_id:
                rows = conn.execute("SELECT * FROM claims WHERE artifact_id=? ORDER BY created_at DESC", (artifact_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM claims ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def update_claim_status(self, claim_id: str, status: str) -> None:
        with self.lock, self._connect() as conn:
            conn.execute("UPDATE claims SET status=? WHERE claim_id=?", (status, claim_id))
            conn.commit()

    def get_identity(self, identity_id: str) -> Optional[Dict[str, Any]]:
        with self.lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM identities WHERE identity_id=?", (identity_id,)).fetchone()
        return dict(row) if row else None

    def list_identities(self) -> List[Dict[str, Any]]:
        with self.lock, self._connect() as conn:
            rows = conn.execute("SELECT * FROM identities ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def update_model_status(self, model_id: str, status: str) -> None:
        with self.lock, self._connect() as conn:
            conn.execute("UPDATE models SET status=? WHERE model_id=?", (status, model_id))
            conn.commit()

    def update_artifact_status(self, artifact_id: str, status: str) -> None:
        with self.lock, self._connect() as conn:
            conn.execute("UPDATE artifacts SET status=? WHERE artifact_id=?", (status, artifact_id))
            conn.commit()


# Keep the public `store` object used by services, but make it persistent.
import config
store = SQLiteStore(config.DATABASE_PATH)
