function getStorage() {
  const storage = {};

  try {
    storage.local = window.localStorage;
  } catch (e) {
    storage.local = null;
  }

  try {
    storage.session = window.sessionStorage;
  } catch (e) {
    storage.session = null;
  }

  return storage;
}

function persistResult(result) {
  const storage = getStorage();
  const safeResult = JSON.stringify(result);
  window.__veritrust_last_result = result;

  try {
    if (storage.local) storage.local.setItem('veritrust_result', safeResult);
  } catch (e) {}

  try {
    if (storage.session) storage.session.setItem('veritrust_result', safeResult);
  } catch (e) {}

  try {
    const url = new URL(window.location.href);
    url.searchParams.set('result', encodeURIComponent(safeResult));
    window.history.replaceState({}, '', url);
  } catch (e) {}
}

function readStoredResult() {
  const storage = getStorage();

  try {
    const params = new URLSearchParams(window.location.search);
    const rawResult = params.get('result');
    if (rawResult) {
      const parsed = JSON.parse(decodeURIComponent(rawResult));
      if (parsed && (parsed.document || parsed.name)) {
        window.__veritrust_last_result = parsed;
        return parsed;
      }
    }
  } catch (e) {}

  if (window.__veritrust_last_result && (window.__veritrust_last_result.document || window.__veritrust_last_result.name)) {
    return window.__veritrust_last_result;
  }

  for (const key of ['local', 'session']) {
    const store = storage[key];
    if (!store) continue;

    try {
      const raw = store.getItem('veritrust_result');
      if (!raw) continue;
      const parsed = JSON.parse(raw);
      if (parsed && parsed.document) return parsed;
      if (parsed && parsed.name) return parsed;
    } catch (e) {
      continue;
    }
  }

  return null;
}

function updateSelectedFileUI(fileInput) {
  const statusText = document.getElementById('file-status');
  const selectedBox = document.getElementById('selected-file-box');
  const selectedName = document.getElementById('selected-file-name');

  if (!fileInput || !statusText || !selectedBox || !selectedName) return;

  const file = fileInput.files && fileInput.files[0];
  if (!file) {
    statusText.textContent = 'Click to select your marksheet or result card';
    selectedBox.style.display = 'none';
    selectedName.textContent = 'None';
    return;
  }

  statusText.textContent = 'File loaded and ready to upload';
  selectedName.textContent = file.name;
  selectedBox.style.display = 'block';
}

function renderResultPage() {
  const result = readStoredResult();
  const resultBody = document.getElementById('result-body');
  if (!resultBody) return;

  if (!result) {
    resultBody.innerHTML = '<div class="status-box danger">No verification result found. Please upload a document first.</div>';
    return;
  }

  const checks = result.checks || [];
  const statusClass = result.status === 'VERIFIED' ? 'success' : result.status === 'SUSPICIOUS' ? 'warning' : 'danger';

  resultBody.innerHTML = `
    <div class="status-box ${statusClass}">
      <h3>DOCUMENT RESULT</h3>
      <p class="muted">Status: <strong>${result.status}</strong></p>
      <p class="muted">Trust Score: <strong>${result.trust_score || result.score || 0}%</strong></p>
    </div>

    <div class="result-grid">
      <div class="metric">
        <div class="label">Trust Score</div>
        <div class="value">${result.trust_score || result.score || 0}%</div>
      </div>
      <div class="metric">
        <div class="label">Status</div>
        <div class="value">${result.status}</div>
      </div>
      <div class="metric">
        <div class="label">Document Hash</div>
        <div class="value" style="font-size:0.82rem;word-break:break-all">${(result.hash || 'N/A').slice(0, 24)}...</div>
      </div>
    </div>

    <ul class="check-list">
      ${checks.map((item) => `
        <li>
          <span>${item.label}</span>
          <span class="${item.passed ? 'pass' : 'fail'}">${item.passed ? '✓' : '✗'}</span>
        </li>
      `).join('')}
    </ul>
  `;
}

function renderDetailsPage() {
  const result = readStoredResult();
  const detailsBody = document.getElementById('details-body');
  if (!detailsBody) return;

  if (!result) {
    detailsBody.innerHTML = `
      <div class="status-box danger">
        No student details are available yet. Please upload a document and verify it first.
      </div>
    `;
    return;
  }

  const doc = result.document || {};
  detailsBody.innerHTML = `
    <table class="info-table">
      <tr><th>Student</th><td>${doc.name || 'N/A'}</td></tr>
      <tr><th>Enrollment</th><td>${doc.roll_number || 'N/A'}</td></tr>
      <tr><th>University</th><td>${doc.university || 'N/A'}</td></tr>
      <tr><th>Semester</th><td>${doc.semester || 'N/A'}</td></tr>
      <tr><th>CGPA</th><td>${doc.cgpa ?? 'N/A'}</td></tr>
      <tr><th>Blockchain</th><td>${result.blockchain && result.blockchain.verified ? '✓ Registered and hash matched' : 'Not registered or hash mismatch'}</td></tr>
      <tr><th>Hash</th><td style="word-break:break-all;">${result.hash || 'N/A'}</td></tr>
    </table>
  `;
}

async function submitUpload(form) {
  const formData = new FormData(form);
  const fileInput = form.querySelector('input[type="file"]');

  if (!fileInput || !fileInput.files || !fileInput.files[0]) {
    alert('Please choose a PDF or image file to continue.');
    return;
  }

  const button = form.querySelector('button[type="submit"]');
  const originalText = button.textContent;
  button.textContent = 'Verifying...';
  button.disabled = true;

  try {
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Verification failed');
    }

    persistResult(data);
    const resultUrl = '/result?result=' + encodeURIComponent(JSON.stringify(data));
    window.location.href = resultUrl;
  } catch (error) {
    alert(error.message || 'Unable to verify this document right now.');
    button.textContent = originalText;
    button.disabled = false;
  }
}

window.addEventListener('DOMContentLoaded', () => {
  const uploadForm = document.getElementById('upload-form');
  const fileInput = document.getElementById('file-input');

  if (fileInput) {
    fileInput.addEventListener('change', () => updateSelectedFileUI(fileInput));
  }

  if (uploadForm) {
    uploadForm.addEventListener('submit', (event) => {
      event.preventDefault();
      submitUpload(uploadForm);
    });
  }

  const resultLink = document.getElementById('result-link');
  const detailsLink = document.getElementById('details-link');

  if (resultLink) {
    const params = new URLSearchParams(window.location.search);
    const currentResult = params.get('result');
    if (currentResult) {
      resultLink.href = '/result?result=' + currentResult;
    }
  }

  if (detailsLink) {
    const params = new URLSearchParams(window.location.search);
    const currentResult = params.get('result');
    if (currentResult) {
      detailsLink.href = '/details?result=' + currentResult;
    }
  }

  if (fileInput) updateSelectedFileUI(fileInput);
  renderResultPage();
  renderDetailsPage();
});
