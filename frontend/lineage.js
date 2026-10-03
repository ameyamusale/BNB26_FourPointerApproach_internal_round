// Lineage page logic.
renderNav(null);
renderStatusChips();

const LINEAGE_ID = decodeURIComponent(location.pathname.split("/").pop());

async function loadLineage() {
  $("lineageId").textContent = LINEAGE_ID;
  let g;
  try {
    g = await api("/api/graph/artifacts/" + encodeURIComponent(LINEAGE_ID));
  } catch (err) { setMsg("lineageMsg", err.message, false); return; }
  setMsg("lineageMsg", "", true);

  const body = $("lineageBody"); body.replaceChildren();

  const flagRow = el("div", "flow");
  flagRow.appendChild(el("span", "chip " + (g.root_reached ? "ok" : "warn"), g.root_reached ? "Root reached" : "Root NOT reached"));
  flagRow.appendChild(el("span", "chip", "Depth " + g.depth));
  if (g.issues.length) flagRow.appendChild(el("span", "chip warn", g.issues.length + " issue(s)"));
  body.appendChild(flagRow);

  body.appendChild(el("h3", "", "Provenance graph"));
  renderFlow(body, g.nodes, g.edges);

  body.appendChild(el("h3", "", "Lineage chain"));
  renderLineageRow(body, g.lineage);

  body.appendChild(el("h3", "", "Edges"));
  const wrap = el("div"); wrap.id = "edgeTable"; ensureTable("edgeTable");
  table("edgeTable", ["Event", "From", "Edge", "To", "Signed", "On-chain tx"],
    g.edges.map((e) => {
      const src = (e.source || "").split(":").pop();
      const dst = (e.target || "").split(":").pop();
      return [e.event_id, src, e.label, dst, e.signed ? "yes" : "no", e.blockchain_tx || "—"];
    }));
  body.appendChild(wrap);

  if (g.issues.length) {
    body.appendChild(el("h3", "", "Issues"));
    const ul = el("ul", "reasons");
    g.issues.forEach((t) => ul.appendChild(el("li", "", t)));
    body.appendChild(ul);
  }
}

loadLineage();
