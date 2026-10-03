// Audit page logic.
renderNav("/audit");
renderStatusChips();

async function loadAudit() {
  const [events, status, logs] = await Promise.all([
    api("/api/provenance/events"),
    api("/api/status"),
    api("/api/audit/logs").catch(() => []),
  ]);
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

  if ($("auditLogCount")) $("auditLogCount").textContent = `(${logs.length} entries)`;
  if ($("auditLogTable")) {
    table("auditLogTable", ["Log ID", "Action", "Actor", "Resource ID", "Details", "Log Hash", "Prev Hash", "Time"],
      logs.map((l) => [
        l.log_id || l.entry_id || "—",
        l.action,
        l.actor || "system",
        l.resource_id || l.target_id || "—",
        typeof l.details === "object" && l.details !== null ? JSON.stringify(l.details) : (l.details || "—"),
        short(l.log_hash || l.entry_hash),
        short(l.prev_hash),
        fmt(l.timestamp || l.created_at),
      ]));
  }

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

const verifyChainBtn = $("verifyChainBtn");
if (verifyChainBtn) {
  verifyChainBtn.addEventListener("click", async () => {
    verifyChainBtn.disabled = true;
    const orig = verifyChainBtn.textContent;
    verifyChainBtn.textContent = "Verifying cryptographic chain…";
    const resBox = $("chainIntegrityResult");
    resBox.replaceChildren();
    try {
      const r = await api("/api/audit/verify-chain");
      if (r.chain_intact) {
        const bd = el("span", "badge CHAIN_INTACT", "✔ HASH CHAIN INTEGRITY VERIFIED");
        resBox.appendChild(bd);
        const p = el("p", "hint good", `Intact SHA-256 chain verified across all ${r.verified_count} audit blocks. Genesis: ${short(r.genesis_hash)} · Latest: ${short(r.latest_hash)}.`);
        p.style.color = "var(--ok)";
        resBox.appendChild(p);
      } else {
        const bd = el("span", "badge CHAIN_BROKEN", "✖ HASH CHAIN TAMPER DETECTED");
        resBox.appendChild(bd);
        const p = el("p", "hint err", `Hash mismatch detected at block #${r.broken_at_entry_id}: ${r.message}`);
        resBox.appendChild(p);
      }
    } catch (err) {
      resBox.appendChild(el("p", "msg err", "Chain verification failed: " + err.message));
    } finally {
      verifyChainBtn.disabled = false;
      verifyChainBtn.textContent = orig;
    }
  });
}

loadAudit().catch((e) => setMsg("eventCount", "Could not reach the API: " + e.message, false));
