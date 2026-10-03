// Dashboard page logic.
renderNav("/dashboard");
renderStatusChips();

async function loadDashboard() {
  const [status, models, artifacts, events, creators, auditLogs] = await Promise.all([
    api("/api/status"),
    api("/api/models"),
    api("/api/artifacts"),
    api("/api/provenance/events"),
    api("/api/creator/identities").catch(() => []),
    api("/api/audit/logs").catch(() => []),
  ]);

  animateMetric("statModels", models.length);
  animateMetric("statArtifacts", artifacts.length);
  animateMetric("statEvents", events.length);
  if ($("statCreators")) animateMetric("statCreators", creators.length);
  if ($("statAuditLogs")) animateMetric("statAuditLogs", auditLogs.length);
  animateMetric("statOnchain",
    models.filter((m) => m.blockchain_tx).length +
    artifacts.filter((a) => a.blockchain_tx).length +
    events.filter((e) => e.blockchain_tx).length);

  table("modelTable", ["ID", "Name", "Version", "Creator", "Status"],
    models.slice(0, 5).map((m) => [
      { node: modelLink(m.model_id) }, m.name, m.version, m.creator_name, m.status,
    ]));
  table("artifactTable", ["ID", "SHA-256", "Model", "Size", "Registered"],
    artifacts.slice(0, 5).map((a) => [
      { node: artifactLink(a.artifact_id) }, short(a.exact_hash), a.model_id || "—",
      a.size_bytes + " B", fmt(a.created_at),
    ]));

  const g = await api("/api/graph/full");
  $("graphCount").textContent = `(${g.nodes.length} nodes · ${g.edges.length} edges)`;
  renderFlow($("fullGraph"), g.nodes, g.edges);
}

loadDashboard().catch((e) => setMsg("statGrid", "Could not reach the API: " + e.message, false));

function animateMetric(id, value) {
  const target = $(id); if (!target) return;
  const end = Number(value) || 0; const start = performance.now(); const duration = 520;
  function frame(now) { const t = Math.min(1, (now - start) / duration); target.textContent = String(Math.round(end * (1 - Math.pow(1 - t, 3)))); if (t < 1) requestAnimationFrame(frame); }
  requestAnimationFrame(frame);
}

const inspector = $("graphInspector");
if (inspector) {
  const close = inspector.querySelector("[data-close-inspector]");
  close.addEventListener("click", () => inspector.close());
  $("fullGraph").addEventListener("click", (event) => {
    const node = event.target.closest(".node"); if (!node) return;
    event.preventDefault();
    let data; try { data = JSON.parse(node.dataset.nodePayload || "{}"); } catch (_) { return; }
    showNodeInspector(data);
  });
  $("fullGraph").addEventListener("keydown", (event) => { if ((event.key === "Enter" || event.key === " ") && event.target.matches(".node")) { event.preventDefault(); event.target.click(); } });
}
function showNodeInspector(node) {
  $("inspectorTitle").textContent = node.label || node.id || "Evidence node";
  const body = $("inspectorBody"); body.replaceChildren();
  const fields = [["ID", node.model_id || node.artifact_id || node.application_id || node.id], ["Type", node.kind], ["Hash", node.exact_hash || "Not available"], ["Creator", node.creator || "Not available"], ["Status", node.status || (node.missing ? "MISSING RECORD" : "Recorded in registry")]];
  const grid = el("div", "inspector-meta");
  fields.forEach(([key, value]) => { grid.appendChild(el("div", "k", key)); const val = el("div", "mono", String(value)); val.style.wordBreak = "break-all"; grid.appendChild(val); });
  body.appendChild(grid);
  const href = node.kind === "MODEL" ? "/models/" + encodeURIComponent(node.model_id || "") : node.kind === "ARTIFACT" ? "/artifacts/" + encodeURIComponent(node.artifact_id || "") : null;
  if (href && !node.missing) { const link = el("a", "primary-btn", "Open passport"); link.href = href; body.appendChild(link); }
  if (inspector.showModal) inspector.showModal();
}


