// Model & Artifact passport page logic. The HTML page tells us which kind via <body data-kind>.
renderNav(document.body.dataset.kind === "model" ? "/models" : "/artifacts");
renderStatusChips();

const PASSPORT_KIND = document.body.dataset.kind;
const RESOURCE_ID = decodeURIComponent(location.pathname.split("/").pop());

async function loadPassport() {
  $("passportId").textContent = RESOURCE_ID;
  let p;
  try {
    p = await api(`/api/graph/${PASSPORT_KIND}s/${encodeURIComponent(RESOURCE_ID)}/passport`);
  } catch (err) {
    setMsg("passportMsg", err.message, false); return;
  }
  setMsg("passportMsg", "", true);

  const body = $("passportBody"); body.replaceChildren();

  if (PASSPORT_KIND === "model") {
    const m = p.model;
    body.appendChild(badge(m.status));
    const kv = el("div", "kv");
    [["Model ID", m.model_id], ["Name", `${m.name} v${m.version}`], ["Type", m.model_type],
     ["Creator", `${m.creator_name} (${m.creator_id})`], ["Model hash", m.model_hash],
     ["Metadata hash", m.metadata_hash], ["Registered", fmt(m.created_at)],
     ["On-chain tx", p.blockchain.tx || "— (not configured)"]].forEach(([k, v]) => {
      const kd = el("div", "k", k), vd = el("div", "mono", String(v));
      vd.style.wordBreak = "break-all";
      kv.appendChild(kd); kv.appendChild(vd);
    });
    body.appendChild(kv);
    body.appendChild(el("p", "hint", `Artifacts produced: ${p.artifacts_count} · Provenance events: ${p.events_count}`));

    if (p.events.length) {
      body.appendChild(el("h3", "", "Provenance events"));
      const wrap = el("div"); wrap.id = "modelEvents"; ensureTable("modelEvents");
      table("modelEvents", ["Event", "Action", "Child artifact", "Signed", "On-chain"],
        p.events.map((ev) => [ev.event_id, ev.action, { node: artifactLink(ev.child_artifact_id) },
          ev.signature ? "yes" : "no", ev.blockchain_tx ? ev.blockchain_tx.slice(0, 14) + "…" : "—"]));
      body.appendChild(wrap);
    }
  } else {
    const a = p.artifact;
    body.appendChild(badge(p.trust.status));
    const kv = el("div", "kv");
    [["Artifact ID", a.artifact_id], ["Type", a.artifact_type], ["SHA-256", a.exact_hash],
     ["Robust fingerprint", a.robust_fingerprint || "—"], ["Size", a.size_bytes + " bytes"],
     ["Claimed origin", p.model ? `${p.model.name} v${p.model.version} (${p.model.model_id})` : a.model_id || "—"],
     ["Registered", fmt(a.created_at)], ["Transformations", String(p.transformation_count)],
     ["On-chain tx", p.blockchain.artifact_tx || "— (not configured)"]].forEach(([k, v]) => {
      const kd = el("div", "k", k), vd = el("div", "mono", String(v));
      vd.style.wordBreak = "break-all";
      kv.appendChild(kd); kv.appendChild(vd);
    });
    body.appendChild(kv);

    body.appendChild(el("h3", "", "Lineage"));
    renderLineageRow(body, p.lineage);

    body.appendChild(el("h3", "", "Provenance graph"));
    const gh = el("div"); renderFlow(gh, p.graph.nodes, p.graph.edges); body.appendChild(gh);

    if (p.claims && p.claims.length) {
      body.appendChild(el("h3", "", "Registered claims"));
      const ul = el("ul", "reasons");
      p.claims.forEach((c) => ul.appendChild(el("li", "", `${c.claim_id} · ${c.claim_type} · issuer ${c.issuer_id || "—"} · ${c.status}`)));
      body.appendChild(ul);
    }

    body.appendChild(el("p", "hint", p.trust.note));
  }
}

loadPassport();
