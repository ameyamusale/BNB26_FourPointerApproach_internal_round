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
  if (!rows.length) { const d = el("div", "empty"); d.appendChild(el("strong", "", "NO RECORDS YET")); d.appendChild(el("p", "", "Records will appear here as they are added to the registry.")); t.replaceWith(Object.assign(d, { id })); return; }
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
function artifactLink(id) { return link(id, "/artifacts/" + encodeURIComponent(id)); }
function modelLink(id) { return link(id, "/models/" + encodeURIComponent(id)); }

const NAV = [
  ["/dashboard", "Dashboard"],
  ["/proof-of-creator", "Proof of Creator"],
  ["/models", "Models"],
  ["/artifacts", "Artifacts"],
  ["/verify", "Verify"],
  ["/adversarial-lab", "Adversarial Lab"],
  ["/audit", "Audit"],
];
function renderNav(active) {
  const host = $("navLinks"); if (!host) return;
  host.replaceChildren();
  const toggle = el("button", "nav-toggle", "Menu");
  toggle.type = "button"; toggle.setAttribute("aria-expanded", "false"); toggle.setAttribute("aria-label", "Toggle navigation");
  toggle.addEventListener("click", () => { const open = host.classList.toggle("nav-open"); toggle.setAttribute("aria-expanded", String(open)); });
  host.appendChild(toggle);
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
    const add = (text, cls) => { const chip = el("span", "chip " + (cls || ""), text); chip.title = text; chips.appendChild(chip); };
    add(`Phase ${s.implemented_phase} build`, "ok");
    add(`Blockchain: ${s.blockchain.mode}${s.blockchain.connected ? "" : " (offline)"}`, s.blockchain.connected ? "ok" : "warn");
    add(`Proof of Creator: active`, "ok");
    add(`Signatures: ${s.signatures.configured ? "ready" : "ready (secp256k1)"}`, "ok");
    add(`Robust FP: ${s.robust_fingerprint.implemented ? "on" : "off"}`, s.robust_fingerprint.implemented ? "ok" : "warn");
  } catch (_) {
    chips.replaceChildren(el("span", "chip warn", "API unreachable"));
  }
}

function withBusy(form, fn) {
  const btn = form.querySelector("button[type=submit], button:not([type])");
  if (btn) btn.disabled = true;
  form.classList.add("is-loading");
  return Promise.resolve(fn()).finally(() => { if (btn) btn.disabled = false; form.classList.remove("is-loading"); });
}


// Lightweight route transitions and section reveals.
document.addEventListener('DOMContentLoaded', () => {
  const root = document.querySelector('.container'); if (root) root.classList.add('route-content');
  const sections = document.querySelectorAll('.container > .card, .container > .grid, .container > .grid2, .container > .stats, .container > .tour-banner');
  if (!(('IntersectionObserver') in window)) { sections.forEach((s) => s.classList.add('is-visible')); return; }
  const observer = new IntersectionObserver((entries) => entries.forEach((entry) => { if (entry.isIntersecting) { entry.target.classList.add('is-visible'); observer.unobserve(entry.target); } }), { threshold: .08 });
  sections.forEach((section, i) => { section.classList.add('reveal'); section.style.transitionDelay = Math.min(i * 45, 180) + 'ms'; observer.observe(section); });
});







