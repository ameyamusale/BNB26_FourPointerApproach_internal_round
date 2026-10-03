// Demo pipeline page logic.
renderNav("/demo");
renderStatusChips();

$("pipelineForm").addEventListener("submit", async (e) => {
  e.preventDefault(); const f = e.target;
  await withBusy(f, async () => {
    try {
      const r = await api("/api/demo/pipeline", { method: "POST", body: new FormData(f) });
      setMsg("pipelineMsg", "Pipeline complete — see the result below.", true);
      renderPipeline(r);
    } catch (err) { setMsg("pipelineMsg", err.message, false); }
  });
});

function renderPipeline(r) {
  const body = $("resultBody"); body.replaceChildren(); $("resultCard").hidden = false;

  const summary = el("div", "flow");
  summary.appendChild(el("span", "chip ok", "Multi-model: yes"));
  summary.appendChild(el("span", "chip", "Depth " + (r.summary ? r.summary.depth : r.lineage.depth)));
  summary.appendChild(el("span", "chip " + (r.summary && r.summary.root_reached ? "ok" : "warn"),
    r.summary && r.summary.root_reached ? "Root reached" : "Root NOT reached"));
  body.appendChild(summary);

  body.appendChild(el("h3", "", "Steps"));
  (r.steps || []).forEach((s) => {
    const step = el("div", "step");
    step.appendChild(el("div", "t", s.step.replace(/_/g, " ")));
    const parts = [];
    if (s.model_id) parts.push("model " + s.model_id);
    if (s.name) parts.push(`${s.name} v${s.version || ""}`);
    if (s.artifact_id) parts.push("artifact " + s.artifact_id);
    if (s.event_id) parts.push("event " + s.event_id + (s.action ? ` (${s.action})` : ""));
    if (s.sha256) parts.push("sha256 " + s.sha256.slice(0, 16) + "…");
    if (s.parent_artifact_id) parts.push("parent " + s.parent_artifact_id);
    if (s.blockchain_tx) parts.push("tx " + s.blockchain_tx.slice(0, 14) + "…");
    parts.push(s.signed === false ? "unsigned" : s.signed === true ? "signed ✔" : "");
    step.appendChild(el("div", "", parts.filter(Boolean).join(" · ")));
    body.appendChild(step);
  });

  body.appendChild(el("h3", "", "Provenance graph"));
  renderFlow(body, r.graph.nodes, r.graph.edges);

  body.appendChild(el("h3", "", "Lineage"));
  renderLineageRow(body, r.lineage);

  body.appendChild(el("p", "hint", `Final artifact: `));
  const p = body.lastChild; p.appendChild(artifactLink(r.artifacts.final));
  body.appendChild(el("p", "hint", "Now verify the final artifact on the Verify page — or open its artifact passport."));

  $("resultCard").scrollIntoView({ behavior: "smooth", block: "nearest" });
}
