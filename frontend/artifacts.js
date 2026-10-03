// Artifacts page logic.
renderNav("/artifacts");
renderStatusChips();

function fillSelect(sel, opts, firstLabel) {
  const keep = sel.value; sel.replaceChildren();
  const f = el("option", "", firstLabel); f.value = ""; sel.appendChild(f);
  opts.forEach(([v, l]) => { const o = el("option", "", l); o.value = v; sel.appendChild(o); });
  sel.value = keep;
}

async function refreshArtifacts() {
  const [models, artifacts] = await Promise.all([api("/api/models"), api("/api/artifacts")]);
  $("artifactCount").textContent = `(${artifacts.length})`;
  table("artifactTable", ["ID", "SHA-256", "Model", "Robust FP", "Size", "Registered"],
    artifacts.map((a) => [
      { node: artifactLink(a.artifact_id) }, short(a.exact_hash), a.model_id || "—",
      short(a.robust_fingerprint), a.size_bytes + " B", fmt(a.created_at),
    ]));
  fillSelect($("modelSelect"), models.map((m) => [m.model_id, `${m.name} v${m.version} (${m.model_id})`]), "— none —");
  fillSelect($("parentSelect"), artifacts.map((a) => [a.artifact_id, `${a.artifact_id} · ${short(a.exact_hash)}`]), "— none (GENERATED) —");
}

$("artifactForm").addEventListener("submit", async (e) => {
  e.preventDefault(); const f = e.target;
  await withBusy(f, async () => {
    const fd = new FormData(f);
    for (const k of [...fd.keys()]) if (fd.get(k) === "") fd.delete(k);
    try {
      const r = await api("/api/artifacts", { method: "POST", body: fd });
      const msg = `Registered ${r.artifact.artifact_id}` + (r.event ? ` · ${r.event.action} · event ${r.event.event_id}` : "");
      setMsg("artifactMsg", msg, true);
      await refreshArtifacts();
    } catch (err) { setMsg("artifactMsg", err.message, false); }
  });
});

refreshArtifacts().catch((e) => setMsg("artifactMsg", "Could not reach the API: " + e.message, false));
