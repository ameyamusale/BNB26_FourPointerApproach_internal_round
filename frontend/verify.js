// Verify page logic.
renderNav("/verify");
renderStatusChips();

$("verifyForm").addEventListener("submit", async (e) => {
  e.preventDefault(); const f = e.target;
  await withBusy(f, async () => {
    try {
      const r = await api("/api/verify", { method: "POST", body: new FormData(f) });
      setMsg("verifyMsg", "Done.", true);
      renderResult(r);
    } catch (err) { setMsg("verifyMsg", err.message, false); }
  });
});

function renderResult(r) {
  const body = $("resultBody"); body.replaceChildren(); $("resultCard").hidden = false;
  body.appendChild(badge(r.decision.status));

  body.appendChild(el("p", "hint mono", "SHA-256 " + r.exact_hash));
  if (r.artifact) {
    const p = el("p", "", "");
    p.appendChild(el("span", "", "Artifact "));
    p.appendChild(artifactLink(r.artifact.artifact_id));
    if (r.model) p.appendChild(el("span", "", ` · claimed origin: ${r.model.name} v${r.model.version} by ${r.model.creator_name}`));
    body.appendChild(p);
  }

  renderChecks(body, r.checks);

  if (r.lineage && r.lineage.steps && r.lineage.steps.length) {
    body.appendChild(el("h3", "", "Lineage"));
    renderLineageRow(body, r.lineage);
  }

  const reasons = el("ul", "reasons");
  r.decision.reasons.forEach((t) => reasons.appendChild(el("li", "", t)));
  body.appendChild(reasons);

  if (r.decision.flags && r.decision.flags.length) {
    body.appendChild(el("p", "hint", "Flags: " + r.decision.flags.join(", ")));
  }
  body.appendChild(el("p", "hint", "Blockchain: " + (r.blockchain && r.blockchain.note ? r.blockchain.note : "state unknown")));
  $("resultCard").scrollIntoView({ behavior: "smooth", block: "nearest" });
}
