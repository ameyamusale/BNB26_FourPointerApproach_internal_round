// ModelLedger shared UI helpers (Phase 5+). Plain JS, no build step.
// All dynamic text is inserted with textContent (never innerHTML).
const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
const short = (h) => (h ? h.slice(0, 12) + "…" : "—");
const fmt = (t) => { try { return new Date(t).toLocaleString(); } catch (_) { return String(t); } };

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

function setMsg(id, text, good) { const m = $(id); if (!m) return; m.textContent = text; m.className = "msg " + (good ? "good" : "err"); }

function table(id, headers, rows) {
  const host = $(id);
  let t = host.tagName === "TABLE" ? host : null;
  if (!t) { t = el("table"); t.id = id; host.replaceWith(t); }
  t.replaceChildren();
  if (!rows.length) { const d = el("div", "empty", "Nothing yet."); t.replaceWith(Object.assign(d, { id })); return; }
  const thead = el("thead"), hr = el("tr");
  headers.forEach((h) => hr.appendChild(el("th", "", h)));
  thead.appendChild(hr); t.appendChild(thead);
  const tb = el("tbody");
  rows.forEach((r) => {
    const tr = el("tr");
    r.forEach((c, i) => {
      const td = el("td", i === 0 ? "mono" : "");
      if (c && typeof c === "object" && c.node) { td.appendChild(c.node); } else { td.textContent = c === undefined || c === null ? "—" : String(c); }
      tr.appendChild(td);
    });
    tb.appendChild(tr);
  });
  t.appendChild(tb);
}
function ensureTable(id) { const n = $(id); if (n && n.tagName !== "TABLE") { const t = el("table"); t.id = id; n.replaceWith(t); } }

const STATUS_LABEL = { TRUSTED: "TRUSTED", SELF_ASSERTED: "SELF-ASSERTED", UNVERIFIABLE: "UNVERIFIABLE", CONFLICT: "CONFLICT" };
function badge(status) { return el("span", "badge " + status, STATUS_LABEL[status] || status); }

function link(text, href) { const a = el("a", "link", text); a.href = href; return a; }

const NAV = [
  ["/dashboard", "Dashboard"], ["/models", "Models"], ["/artifacts", "Artifacts"],
  ["/verify", "Verify"], ["/adversarial", "Adversarial Lab"], ["/audit", "Audit"], ["/demo", "Demo Pipeline"],
];
function renderNav(active) {
  const host = $("navLinks"); if (!host) return;
  host.replaceChildren();
  NAV.forEach(([href, label]) => {
    const a = el("a", "navlink" + (href === active ? " active" : ""), label);
    a.href = href; host.appendChild(a);
  });
}

async function renderStatusChips() {
  const chips = $("statusChips"); if (!chips) return;
  try {
    const s = await api("/api/status");
    chips.replaceChildren();
    const add = (text, cls) => chips.appendChild(el("span", "chip " + (cls || ""), text));
    add(`Phase ${s.implemented_phase} build`, "ok");
    add(`Blockchain: ${s.blockchain.mode}${s.blockchain.connected ? "" : " (no on-chain evidence)"}`, s.blockchain.connected ? "ok" : "warn");
    add(`Signatures: ${s.signatures.configured ? "ready" : "key not configured"}`, s.signatures.configured ? "ok" : "warn");
    add(`Robust FP: ${s.robust_fingerprint.implemented ? "on" : "off"}`, s.robust_fingerprint.implemented ? "ok" : "warn");
  } catch (_) {
    chips.replaceChildren(el("span", "chip warn", "API unreachable"));
  }
}

function withBusy(form, fn) {
  const btn = form.querySelector("button[type=submit], button:not([type])");
  if (btn) btn.disabled = true;
  return Promise.resolve(fn()).finally(() => { if (btn) btn.disabled = false; });
}
