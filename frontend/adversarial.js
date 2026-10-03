// Adversarial Lab page logic.
renderNav("/adversarial");
renderStatusChips();

async function loadScenarios() {
  const scenarios = await api("/api/adversarial/scenarios");
  const host = $("attackList"); host.replaceChildren();
  scenarios.forEach((s) => {
    const card = el("div", "attack"); card.id = "attack-" + s.id;
    card.appendChild(el("h3", "", s.title));
    card.appendChild(el("p", "expected", "Expected: " + s.expected));
    const btn = el("button", "danger-btn", "Run attack");
    btn.addEventListener("click", () => runAttack(s.id, card));
    card.appendChild(btn);
    const result = el("div", "result"); result.hidden = true; card.appendChild(result);
    host.appendChild(card);
  });
}

async function runAttack(id, card) {
  const btn = card.querySelector("button");
  const result = card.querySelector(".result");
  btn.disabled = true;
  const original = btn.textContent;
  btn.textContent = "Running…";
  result.hidden = true;
  try {
    const r = await api("/api/adversarial/run/" + id, { method: "POST" });
    renderAttackResult(result, r);
    result.hidden = false;
  } catch (err) {
    result.replaceChildren(el("p", "msg err", "Attack failed to run: " + err.message));
    result.hidden = false;
  } finally {
    btn.disabled = false; btn.textContent = original;
  }
}

function renderAttackResult(result, r) {
  result.replaceChildren();
  const v = r.verification || {};
  const decision = v.decision || {};
  result.appendChild(badge(decision.status || "UNKNOWN"));
  result.appendChild(el("p", "", r.attack_description || ""));

  const kv = el("div", "kv");
  const rs = r.registry_state || {};
  Object.entries(rs).forEach(([k, val]) => {
    const kd = el("div", "k", k.replace(/_/g, " ")), vd = el("div", "mono", String(val));
    vd.style.wordBreak = "break-all";
    kv.appendChild(kd); kv.appendChild(vd);
  });
  result.appendChild(kv);

  if (r.claims && r.claims.length) {
    result.appendChild(el("h3", "", "Competing claims"));
    const ul = el("ul", "reasons");
    r.claims.forEach((c) => ul.appendChild(el("li", "", `${c.claim_id} · issuer ${c.issuer_id || "—"} · ${c.status}`)));
    result.appendChild(ul);
  }

  result.appendChild(el("h3", "", "Evidence checks"));
  renderChecks(result, v.checks || []);

  const reasons = el("ul", "reasons");
  (decision.reasons || []).forEach((t) => reasons.appendChild(el("li", "", t)));
  if (reasons.childNodes.length) {
    result.appendChild(el("h3", "", "Why"));
    result.appendChild(reasons);
  }

  if (r.note) result.appendChild(el("p", "hint", r.note));
}

loadScenarios().catch((e) => setMsg("attackList", "Could not reach the API: " + e.message, false));
