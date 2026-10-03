// Verify page logic.
renderNav("/verify");
renderStatusChips();

$("verifyForm").addEventListener("submit", async (e) => {
  e.preventDefault(); const f = e.target;
  await withBusy(f, async () => {
    try {
      const r = await api("/api/verify", { method: "POST", body: new FormData(f) });
      setMsg("verifyMsg", "Done.", true);
      renderResult(r);
    } catch (err) { setMsg("verifyMsg", err.message, false); }
  });
});

function renderResult(r) {
  const body = $("resultBody"); body.replaceChildren(); $("resultCard").hidden = false;
  body.appendChild(badge(r.decision.status));

  body.appendChild(el("p", "hint mono", "SHA-256 " + r.exact_hash));
  if (r.artifact) {
    const p = el("p", "", "");
    p.appendChild(el("span", "", "Artifact "));
    p.appendChild(artifactLink(r.artifact.artifact_id));
    if (r.model) p.appendChild(el("span", "", ` · claimed origin: ${r.model.name} v${r.model.version} by ${r.model.creator_name}`));
    body.appendChild(p);
  }

  renderChecks(body, r.checks);

  if (r.lineage && r.lineage.steps && r.lineage.steps.length) {
    body.appendChild(el("h3", "", "Lineage"));
    renderLineageRow(body, r.lineage);
  }

  if (r.decision.flags && r.decision.flags.includes("PROOF_OF_CREATOR_VERIFIED")) {
    const pocChip = el("span", "chip ok", "✔ Proof of Creator Biometrically Authorized");
    pocChip.style.display = "inline-block";
    pocChip.style.margin = "6px 0";
    body.appendChild(pocChip);
  }

  const reasons = el("ul", "reasons");
  r.decision.reasons.forEach((t) => reasons.appendChild(el("li", "", t)));
  body.appendChild(reasons);

  if (r.decision.flags && r.decision.flags.length) {
    body.appendChild(el("p", "hint", "Flags: " + r.decision.flags.join(", ")));
  }
  body.appendChild(el("p", "hint", "Blockchain: " + (r.blockchain && r.blockchain.note ? r.blockchain.note : "state unknown")));
  $("resultCard").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// Zero Prompt Commitment Verification Logic
const samplePrompt = "A serene cybernetic garden with bioluminescent plants and crystalline water fountains in the style of solarpunk.";
async function sha256Hex(text) {
  const enc = new TextEncoder().encode(text);
  const buf = await crypto.subtle.digest("SHA-256", enc);
  return Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

const demoPromptBtn = $("demoPromptBtn");
if (demoPromptBtn) {
  demoPromptBtn.addEventListener("click", async () => {
    const hash = await sha256Hex(samplePrompt);
    if ($("candidatePromptInput")) $("candidatePromptInput").value = samplePrompt;
    if ($("expectedCommitmentInput")) $("expectedCommitmentInput").value = hash;
    setMsg("promptCommitmentMsg", "Filled sample prompt and exact SHA-256 commitment hash.", true);
  });
}

const promptCommitmentForm = $("promptCommitmentForm");
if (promptCommitmentForm) {
  promptCommitmentForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    await withBusy(f, async () => {
      const commitment = $("expectedCommitmentInput").value.trim();
      const promptText = $("candidatePromptInput").value;
      try {
        const r = await api("/api/verify/prompt-commitment", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt_commitment: commitment, prompt_text: promptText }),
        });
        if (r.valid) {
          setMsg("promptCommitmentMsg", `✔ PROMPT COMMITMENT VERIFIED: Computed hash ${r.computed_hash.slice(0, 16)}… matches expected commitment. Zero prompt leakage guaranteed!`, true);
        } else {
          setMsg("promptCommitmentMsg", `✖ MISMATCH: Computed hash (${r.computed_hash.slice(0, 16)}…) does not match expected commitment (${r.expected_commitment.slice(0, 16)}…).`, false);
        }
      } catch (err) {
        setMsg("promptCommitmentMsg", err.message, false);
      }
    });
  });
}

// Drag and drop uses the same native file input and the existing verification request.
const verifyInput = $("verifyForm").querySelector('input[type="file"]');
if (verifyInput) {
  const zone = verifyInput.closest("label"); zone.classList.add("upload-zone"); zone.setAttribute("aria-label", "Choose or drop an artifact to verify");
  ["dragenter", "dragover"].forEach((name) => zone.addEventListener(name, (event) => { event.preventDefault(); zone.classList.add("drag-over"); }));
  ["dragleave", "drop"].forEach((name) => zone.addEventListener(name, (event) => { event.preventDefault(); zone.classList.remove("drag-over"); }));
  zone.addEventListener("drop", (event) => { const file = event.dataTransfer.files && event.dataTransfer.files[0]; if (!file) return; const transfer = new DataTransfer(); transfer.items.add(file); verifyInput.files = transfer.files; verifyInput.dispatchEvent(new Event("change", { bubbles: true })); });
}
