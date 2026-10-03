// Audit page logic.
renderNav("/audit");
renderStatusChips();

async function loadAudit() {
  const [events, status] = await Promise.all([api("/api/provenance/events"), api("/api/status")]);
  $("eventCount").textContent = `(${events.length})`;
  table("eventTable", ["Event", "Action", "Parent", "Child", "Model / App", "Signed", "On-chain tx", "When"],
    events.map((e) => [
      e.event_id, e.action,
      e.parent_artifact_id || "—", { node: artifactLink(e.child_artifact_id) },
      e.model_id || e.application_id || "—",
      e.signature ? "✔" : "–",
      e.blockchain_tx ? e.blockchain_tx.slice(0, 14) + "…" : "—",
      fmt(e.created_at),
    ]));

  const cs = $("chainState"); cs.replaceChildren();
  const kv = el("div", "kv");
  [["Mode", status.blockchain.mode], ["Connected", String(status.blockchain.connected)],
   ["Contract", status.blockchain.contract_address || "—"],
   ["Note", status.blockchain.note]].forEach(([k, v]) => {
    const kd = el("div", "k", k), vd = el("div", "mono", String(v));
    vd.style.wordBreak = "break-all";
    kv.appendChild(kd); kv.appendChild(vd);
  });
  cs.appendChild(kv);
}

loadAudit().catch((e) => setMsg("eventCount", "Could not reach the API: " + e.message, false));
