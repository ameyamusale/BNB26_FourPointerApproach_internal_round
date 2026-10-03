// Models page logic.
renderNav("/models");
renderStatusChips();

async function refreshModels() {
  const models = await api("/api/models");
  $("modelCount").textContent = `(${models.length})`;
  table("modelTable", ["ID", "Name", "Version", "Creator", "Status", "On-chain"],
    models.map((m) => [
      { node: modelLink(m.model_id) }, m.name, m.version, m.creator_name, m.status,
      m.blockchain_tx ? "committed" : "—",
    ]));
}

$("modelForm").addEventListener("submit", async (e) => {
  e.preventDefault(); const f = e.target;
  await withBusy(f, async () => {
    const body = Object.fromEntries(new FormData(f).entries());
    Object.keys(body).forEach((k) => { if (body[k] === "") delete body[k]; });
    try {
      const m = await api("/api/models", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      setMsg("modelMsg", `Registered ${m.model_id} — open its passport to inspect evidence.`, true);
      f.reset(); f.model_type.value = "image-generator";
      await refreshModels();
    } catch (err) { setMsg("modelMsg", err.message, false); }
  });
});

refreshModels().catch((e) => setMsg("modelMsg", "Could not reach the API: " + e.message, false));
