// ModelLedger console (Phase 4). Plain JS, no build step. All server text is inserted with textContent.
const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
const short = (h) => (h ? h.slice(0, 10) + "…" : "—");
const fmt = (t) => new Date(t).toLocaleString();

async function api(path, opts) {
  const res = await fetch(path, opts);
  let body = null;
  try { body = await res.json(); } catch (_) { /* non-JSON */ }
  if (!res.ok) {
    let d = body && body.detail;
    if (d && typeof d === "object" && !Array.isArray(d)) d = d.message || JSON.stringify(d);
    if (Array.isArray(d)) d = d.map((x) => x.msg).join("; ");
    throw new Error(d || `Request failed (${res.status})`);
  }
  return body;
}

function setMsg(id, text, good) { const m = $(id); m.textContent = text; m.className = "msg " + (good ? "good" : "err"); }

function table(id, headers, rows) {
  const t = $(id); t.replaceChildren();
  if (!rows.length) { const d = el("div", "empty", "Nothing yet."); t.replaceWith(Object.assign(d, { id })); return; }
  const thead = el("thead"), hr = el("tr");
  headers.forEach((h) => hr.appendChild(el("th", "", h))); thead.appendChild(hr); t.appendChild(thead);
  const tb = el("tbody");
  rows.forEach((r) => { const tr = el("tr"); r.forEach((c, i) => tr.appendChild(el("td", i === 0 ? "mono" : "", c))); tb.appendChild(tr); });
  t.appendChild(tb);
}
function ensureTable(id) { const n = $(id); if (n.tagName !== "TABLE") { const t = el("table"); t.id = id; n.replaceWith(t); } }

async function refreshStatus() {
  const s = await api("/api/status");
  const chips = $("statusChips"); chips.replaceChildren();
  const add = (text, cls) => chips.appendChild(el("span", "chip " + (cls || ""), text));
  add(`Phase ${s.implemented_phase} build`, "ok");
  add(`Blockchain: ${s.blockchain.mode}${s.blockchain.connected ? "" : " (not connected)"}`, "warn");
  add(`Storage: ${s.storage.mode}`, "warn");
  add(`Signatures: ${s.signatures.implemented ? (s.signatures.configured ? "ready" : "implemented / key not configured") : "not available"}`, s.signatures.configured ? "ok" : "warn");
  add(`Robust FP: ${s.robust_fingerprint.implemented ? "on" : "not yet"}`, s.robust_fingerprint.implemented ? "ok" : "warn");
}

let models = [], artifacts = [];
async function refreshLists() {
  [models, artifacts] = await Promise.all([api("/api/models"), api("/api/artifacts")]);
  const events = await api("/api/provenance/events");
  ["modelTable", "artifactTable", "eventTable"].forEach(ensureTable);
  $("modelCount").textContent = `(${models.length})`; $("artifactCount").textContent = `(${artifacts.length})`; $("eventCount").textContent = `(${events.length})`;
  table("modelTable", ["ID", "Name", "Version", "Creator", "Status"], models.map((m) => [m.model_id, m.name, m.version, m.creator_name, m.status]));
  table("artifactTable", ["ID", "SHA-256", "Model", "Size", "Registered"], artifacts.map((a) => [a.artifact_id, short(a.exact_hash), a.model_id || "—", a.size_bytes + " B", fmt(a.created_at)]));
  ensureTable("eventTable");
  table("eventTable", ["Event", "Action", "Parent", "Child", "Model / App", "Metadata hash"], events.map((e) => [e.event_id, e.action, e.parent_artifact_id || "—", e.child_artifact_id, e.model_id || e.application_id || "—", short(e.metadata_hash)]));
  fillSelect($("modelSelect"), models.map((m) => [m.model_id, `${m.name} v${m.version} (${m.model_id})`]), "— none —");
  fillSelect($("parentSelect"), artifacts.map((a) => [a.artifact_id, `${a.artifact_id} · ${short(a.exact_hash)}`]), "— none (GENERATED) —");
}
function fillSelect(sel, opts, firstLabel) {
  const keep = sel.value; sel.replaceChildren();
  const f = el("option", "", firstLabel); f.value = ""; sel.appendChild(f);
  opts.forEach(([v, l]) => { const o = el("option", "", l); o.value = v; sel.appendChild(o); });
  sel.value = keep;
}

async function withBusy(form, fn) {
  const btn = form.querySelector("button"); btn.disabled = true;
  try { await fn(); } finally { btn.disabled = false; }
}

$("modelForm").addEventListener("submit", async (e) => {
  e.preventDefault(); const f = e.target;
  await withBusy(f, async () => {
    const body = Object.fromEntries(new FormData(f).entries());
    Object.keys(body).forEach((k) => { if (body[k] === "") delete body[k]; });
    try {
      const m = await api("/api/models", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      setMsg("modelMsg", `Registered ${m.model_id}`, true); f.reset(); f.model_type.value = "image-generator";
      await Promise.all([refreshLists(), refreshStatus()]);
    } catch (err) { setMsg("modelMsg", err.message, false); }
  });
});

$("artifactForm").addEventListener("submit", async (e) => {
  e.preventDefault(); const f = e.target;
  await withBusy(f, async () => {
    const fd = new FormData(f);
    for (const k of [...fd.keys()]) if (fd.get(k) === "") fd.delete(k);
    try {
      const r = await api("/api/artifacts", { method: "POST", body: fd });
      setMsg("artifactMsg", `Registered ${r.artifact.artifact_id}` + (r.event ? ` · ${r.event.action}` : ""), true); f.reset();
      await Promise.all([refreshLists(), refreshStatus()]);
    } catch (err) { setMsg("artifactMsg", err.message, false); }
  });
});

$("verifyForm").addEventListener("submit", async (e) => {
  e.preventDefault(); const f = e.target;
  await withBusy(f, async () => {
    try {
      const r = await api("/api/verify", { method: "POST", body: new FormData(f) });
      setMsg("verifyMsg", "Done.", true); renderResult(r);
    } catch (err) { setMsg("verifyMsg", err.message, false); }
  });
});

function renderResult(r) {
  const body = $("resultBody"); body.replaceChildren(); $("resultCard").hidden = false;
  body.appendChild(el("div", "badge " + r.decision.status, r.decision.status.replace("_", "-")));
  const hashLine = el("p", "hint mono", "SHA-256 " + r.exact_hash); body.appendChild(hashLine);
  if (r.artifact) body.appendChild(el("p", "", `Artifact ${r.artifact.artifact_id}` + (r.model ? ` · claimed origin: ${r.model.name} v${r.model.version} by ${r.model.creator_name}` : "")));
  const ul = el("ul", "checks");
  r.checks.forEach((c) => {
    const li = el("li", c.state); li.appendChild(el("span", "ico", c.state === "pass" ? "✔" : c.state === "fail" ? "✖" : "–"));
    li.appendChild(el("span", "", c.label + (c.state === "not_checked" ? " — not checked" : "")));
    li.appendChild(el("span", "detail", c.state === "not_checked" ? "" : c.detail)); ul.appendChild(li);
  });
  body.appendChild(ul);
  if (r.lineage && r.lineage.steps.length) {
    body.appendChild(el("h3", "", "Lineage"));
    const row = el("div", "lineage");
    r.lineage.steps.forEach((s, i) => {
      if (i) row.appendChild(el("span", "arrow", "→ " + (s.event ? s.event.action : "") + " →"));
      row.appendChild(el("span", "node mono", s.artifact_id));
    });
    body.appendChild(row);
  }
  const reasons = el("ul", "reasons"); r.decision.reasons.forEach((t) => reasons.appendChild(el("li", "", t))); body.appendChild(reasons);
  body.appendChild(el("p", "hint", "Blockchain: " + r.blockchain.note));
  $("resultCard").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

Promise.all([refreshStatus(), refreshLists()]).catch((e) => setMsg("verifyMsg", "Could not reach the API: " + e.message, false));
