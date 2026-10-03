// Shared graph rendering for ModelLedger pages (Phase 5+).
// Renders a node/edge graph as a horizontal flow of linked chips.

function nodeHref(node) {
  if (node.kind === "ARTIFACT") return "/artifacts/" + encodeURIComponent(node.artifact_id || node.label);
  if (node.kind === "MODEL") return "/models/" + encodeURIComponent(node.model_id || node.label);
  return null;
}

function flowNode(node) {
  const span = el("span", "node mono" + (node.missing ? " missing" : ""), "");
  const href = nodeHref(node);
  if (href && !node.missing) {
    const a = el("a", "", node.label); a.href = href; span.appendChild(a);
  } else {
    span.appendChild(el("span", "", node.label + (node.missing ? " (missing)" : "")));
  }
  span.title = node.kind + (node.exact_hash ? " · " + node.exact_hash.slice(0, 16) + "…" : "");
  return span;
}

function renderFlow(container, nodes, edges) {
  container.replaceChildren();
  if (!nodes || !nodes.length) { container.appendChild(el("p", "empty", "No graph data yet.")); return; }
  const byId = {}; nodes.forEach((n) => { byId[n.id] = n; });
  const flow = el("div", "flow");
  if (!edges || !edges.length) {
    nodes.forEach((n) => flow.appendChild(flowNode(n)));
  } else {
    // Order edges by creation where available so the flow reads root -> final.
    const ordered = edges.slice().sort((a, b) => String(a.created_at || a.order || "").localeCompare(String(b.created_at || b.order || "")));
    const visited = new Set();
    ordered.forEach((edge, i) => {
      const src = byId[edge.source];
      if (src && !visited.has(edge.source)) { if (i) flow.appendChild(el("span", "arrow", "→")); flow.appendChild(flowNode(src)); visited.add(edge.source); }
      const dst = byId[edge.target];
      if (dst && !visited.has(edge.target)) {
        flow.appendChild(el("span", "arrow", "— " + edge.label + " →"));
        flow.appendChild(flowNode(dst)); visited.add(edge.target);
      }
    });
    nodes.forEach((n) => { if (!visited.has(n.id)) flow.appendChild(flowNode(n)); });
  }
  container.appendChild(flow);
}

function renderLineageRow(container, lineage) {
  container.replaceChildren();
  if (!lineage || !lineage.steps || !lineage.steps.length) { container.appendChild(el("p", "empty", "No lineage recorded.")); return; }
  const row = el("div", "lineage");
  lineage.steps.forEach((s, i) => {
    if (i) row.appendChild(el("span", "arrow", "→ " + (s.event ? s.event.action : "?") + " →"));
    const node = el("span", "node mono");
    const a = el("a", "", s.artifact_id); a.href = "/artifacts/" + encodeURIComponent(s.artifact_id);
    node.appendChild(a); row.appendChild(node);
  });
  container.appendChild(row);
  if (lineage.issues && lineage.issues.length) {
    const ul = el("ul", "reasons");
    lineage.issues.forEach((t) => ul.appendChild(el("li", "", t)));
    container.appendChild(ul);
  }
  const meta = el("p", "hint", "Depth: " + lineage.depth + " · root reached: " + (lineage.root_reached ? "yes" : "NO"));
  container.appendChild(meta);
}

function renderChecks(container, checks) {
  container.replaceChildren();
  const ul = el("ul", "checks");
  (checks || []).forEach((c) => {
    const li = el("li", c.state);
    li.appendChild(el("span", "ico", c.state === "pass" ? "✔" : c.state === "fail" ? "✖" : "–"));
    li.appendChild(el("span", "", c.label + (c.state === "not_checked" ? " — not checked" : "")));
    li.appendChild(el("span", "detail", c.state === "not_checked" ? "" : c.detail));
    ul.appendChild(li);
  });
  container.appendChild(ul);
}

function artifactLink(id) { return link(id, "/artifacts/" + encodeURIComponent(id)); }
function modelLink(id) { return link(id, "/models/" + encodeURIComponent(id)); }
