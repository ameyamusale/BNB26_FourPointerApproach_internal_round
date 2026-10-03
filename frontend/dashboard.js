// Dashboard page logic.
renderNav("/dashboard");
renderStatusChips();

async function loadDashboard() {
  const [status, models, artifacts, events] = await Promise.all([
    api("/api/status"), api("/api/models"), api("/api/artifacts"), api("/api/provenance/events"),
  ]);

  $("statModels").textContent = models.length;
  $("statArtifacts").textContent = artifacts.length;
  $("statEvents").textContent = events.length;
  $("statSigned").textContent = events.filter((e) => e.signature).length;
  $("statOnchain").textContent =
    models.filter((m) => m.blockchain_tx).length +
    artifacts.filter((a) => a.blockchain_tx).length +
    events.filter((e) => e.blockchain_tx).length;

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
