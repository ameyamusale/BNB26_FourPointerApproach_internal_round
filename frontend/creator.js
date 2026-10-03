// Proof of Creator client logic (Phases 8 & 10). Plain JS, no build step.
renderNav("/proof-of-creator");
renderStatusChips();

let currentImageBase64 = null;
let mediaStream = null;

const video = $("webcam");
const overlay = $("overlay");
const placeholder = $("cameraPlaceholder");
const btnStartCam = $("btnStartCam");
const btnSnapPhoto = $("btnSnapPhoto");
const btnStopCam = $("btnStopCam");
const fileInput = $("fileInput");
const capturePreview = $("capturePreview");
const capturePreviewContainer = $("capturePreviewContainer");

// --- Webcam Handling ---
btnStartCam.addEventListener("click", async () => {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
    });
    video.srcObject = mediaStream;
    video.style.display = "block";
    placeholder.style.display = "none";
    btnStartCam.disabled = true;
    btnSnapPhoto.disabled = false;
    btnStopCam.disabled = false;
  } catch (err) {
    alert("Camera access denied or unavailable: " + err.message + "\nYou can still use the file upload option below.");
  }
});

btnStopCam.addEventListener("click", () => {
  stopWebcam();
});

function stopWebcam() {
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop());
    mediaStream = null;
  }
  video.style.display = "none";
  placeholder.style.display = "block";
  btnStartCam.disabled = false;
  btnSnapPhoto.disabled = true;
  btnStopCam.disabled = true;
}

btnSnapPhoto.addEventListener("click", () => {
  if (!video.videoWidth) return;
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  currentImageBase64 = canvas.toDataURL("image/png");
  showCapturePreview(currentImageBase64);
});

fileInput.addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (evt) => {
    currentImageBase64 = evt.target.result;
    showCapturePreview(currentImageBase64);
  };
  reader.readAsDataURL(file);
});

function showCapturePreview(dataUrl) {
  ["authFaceStep", "authLiveStep", "authIdentityStep", "authSignStep"].forEach((id) => setAuthStage(id, "waiting"));
  setAuthStage("authImageStep", "verified");
  capturePreview.src = dataUrl;
  capturePreviewContainer.style.display = "block";
}

// --- Load Creator Directory & Select Options ---
async function loadCreators() {
  const creators = await api("/api/creator/identities");
  const select = $("creatorSelect");
  select.replaceChildren();

  const enrolled = creators.filter((c) => c.has_biometric);
  if (!enrolled.length) {
    select.appendChild(el("option", "", "— No creators enrolled yet — enroll below"));
  } else {
    enrolled.forEach((c) => {
      const opt = el("option", "", `${c.name} (${c.identity_id})`);
      opt.value = c.identity_id;
      select.appendChild(opt);
    });
  }

  $("identitiesCount").textContent = `(${creators.length})`;
  table("creatorTable", ["ID", "Name", "Role", "Wallet", "Biometric Enrolled", "Created"],
    creators.map((c) => [
      c.identity_id,
      c.name,
      c.role,
      c.wallet_address ? short(c.wallet_address) : "—",
      c.has_biometric ? "✔ Enrolled" : "– Self-asserted",
      fmt(c.created_at),
    ])
  );
}

// --- Liveness Check Only ---
$("btnCheckLiveness").addEventListener("click", async () => {
  if (!currentImageBase64) {
    setMsg("verifyMsg", "Please capture a camera frame or upload a photo first.", false);
    return;
  }
  setMsg("verifyMsg", "Analyzing anti-spoof liveness…", true);
  try {
    const fd = new FormData();
    fd.append("image_base64", currentImageBase64);
    const r = await api("/api/creator/liveness-check", { method: "POST", body: fd });
    renderLivenessResult(r);
    setMsg("verifyMsg", "Liveness analysis complete.", true);
  } catch (err) {
    setMsg("verifyMsg", err.message, false);
  }
});

// --- Verify & Authorize ---
$("verifyForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const creatorId = $("creatorSelect").value;
  if (!creatorId || creatorId.startsWith("—")) {
    setMsg("verifyMsg", "Please select an enrolled creator identity.", false);
    return;
  }
  if (!currentImageBase64) {
    setMsg("verifyMsg", "Please capture a camera frame or upload a photo first.", false);
    return;
  }

  setMsg("verifyMsg", "Verifying face match and anti-spoof liveness…", true);
  try {
    const fd = new FormData();
    fd.append("creator_id", creatorId);
    fd.append("image_base64", currentImageBase64);
    const r = await api("/api/creator/authorize", { method: "POST", body: fd });
    renderAuthReceipt(r);
    setMsg("verifyMsg", "Identity authorized! Proof of Creator token issued.", true);
  } catch (err) {
    setMsg("verifyMsg", err.message, false);
  }
});

function renderLivenessResult(r) {
  const resCard = $("pocResult");
  const body = $("pocResultBody");
  body.replaceChildren();
  resCard.style.display = "block";

  setAuthStage("authFaceStep", r.face_detected ? "verified" : "failed");
  if (!r.face_detected) {
    body.appendChild(badge("UNVERIFIABLE"));
    body.appendChild(el("p", "msg err", "No face detected in the frame. Ensure clear lighting."));
    return;
  }

  const lv = r.liveness || {};
  setAuthStage("authLiveStep", lv.liveness_passed ? "verified" : "failed");
  body.appendChild(badge(lv.liveness_passed ? "TRUSTED" : "CONFLICT"));
  body.appendChild(el("h4", "", `Verdict: ${lv.verdict} (Score: ${(lv.liveness_score * 100).toFixed(1)}%)`));

  const kv = el("div", "kv");
  [
    ["Texture Focus Score", `${(lv.texture_score * 100).toFixed(1)}%`],
    ["Spectral Moiré Score", `${(lv.frequency_score * 100).toFixed(1)}%`],
    ["Chroma Dispersion", `${(lv.chroma_score * 100).toFixed(1)}%`],
    ["Face Box", JSON.stringify(r.face_box)],
  ].forEach(([k, v]) => {
    kv.appendChild(el("div", "k", k));
    kv.appendChild(el("div", "mono", v));
  });
  body.appendChild(kv);
}

function renderAuthReceipt(r) {
  const resCard = $("pocResult");
  const body = $("pocResultBody");
  body.replaceChildren();
  resCard.style.display = "block";

  ["authFaceStep", "authLiveStep", "authIdentityStep", "authSignStep"].forEach((id) => setAuthStage(id, "verified"));
  body.appendChild(badge("TRUSTED"));
  body.appendChild(el("h4", "", `Proof of Creator Verified: ${r.creator_name}`));

  const kv = el("div", "kv");
  [
    ["Creator ID", r.creator_id],
    ["Biometric Commitment", r.biometric_commitment],
    ["Identity Similarity", `${(r.similarity * 100).toFixed(1)}% (Matched)`],
    ["Liveness Score", `${(r.liveness_score * 100).toFixed(1)}% (Live)`],
    ["Token Expiry", fmt(r.expires_at)],
  ].forEach(([k, v]) => {
    kv.appendChild(el("div", "k", k));
    const vd = el("div", "mono", v);
    vd.style.wordBreak = "break-all";
    kv.appendChild(vd);
  });
  body.appendChild(kv);

  // Token Box
  const tokenBox = el("div", "hint", "Active Authorization Token (Attach when registering models or artifacts):");
  tokenBox.style.marginTop = "12px";
  const code = el("pre", "mono", r.authorization_token);
  code.style.padding = "8px";
  code.style.background = "#1e293b";
  code.style.borderRadius = "4px";
  code.style.wordBreak = "break-all";
  code.style.whiteSpace = "pre-wrap";
  tokenBox.appendChild(code);

  if (r.authorization_token) {
    sessionStorage.setItem("modelledger_creator_token", r.authorization_token);
    sessionStorage.setItem("modelledger_creator_name", r.creator_name);
    sessionStorage.setItem("modelledger_creator_id", r.creator_id);
  }

  const copyBtn = el("button", "ghost-btn", "Copy Token");
  copyBtn.style.marginTop = "6px";
  copyBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(r.authorization_token);
    copyBtn.textContent = "Copied! ✔";
    setTimeout(() => { copyBtn.textContent = "Copy Token"; }, 2000);
  });
  tokenBox.appendChild(copyBtn);

  const regLink = el("a", "primary-btn", "Register Model with this Token →");
  regLink.href = "/models";
  regLink.style.display = "inline-block";
  regLink.style.marginLeft = "8px";
  regLink.style.textDecoration = "none";
  regLink.style.fontSize = "0.85rem";
  regLink.style.padding = "6px 12px";
  tokenBox.appendChild(regLink);

  body.appendChild(tokenBox);
}

// --- Enroll Form ---
$("enrollForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!currentImageBase64) {
    setMsg("enrollMsg", "Please capture a camera frame or upload a photo first.", false);
    return;
  }
  const name = $("enrollName").value;
  const cid = $("enrollId").value;
  const wallet = $("enrollWallet").value;

  setMsg("enrollMsg", "Processing facial biometrics & generating commitment…", true);
  try {
    const fd = new FormData();
    fd.append("name", name);
    if (cid) fd.append("identity_id", cid);
    if (wallet) fd.append("wallet_address", wallet);
    fd.append("image_base64", currentImageBase64);

    const r = await api("/api/creator/enroll", { method: "POST", body: fd });
    setMsg("enrollMsg", `Enrolled successfully! Commitment: ${r.biometric_commitment.slice(0, 16)}…`, true);
    $("enrollName").value = "";
    $("enrollId").value = "";
    $("enrollWallet").value = "";
    await loadCreators();
  } catch (err) {
    setMsg("enrollMsg", err.message, false);
  }
});

loadCreators().catch((err) => setMsg("verifyMsg", "Failed to load creators: " + err.message, false));

function setAuthStage(id, state) { const stage = $(id); if (stage) stage.dataset.state = state; }



