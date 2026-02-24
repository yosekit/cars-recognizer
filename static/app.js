const API = '';

// --- Log ---
const logEl = document.getElementById('log');
const logToggle = document.getElementById('logToggle');
const logHeader = document.getElementById('logHeader');
let logCollapsed = false;

function toggleLog() {
  logCollapsed = !logCollapsed;
  logEl.classList.toggle('collapsed', logCollapsed);
  logToggle.innerHTML = logCollapsed ? '&#x25BC;' : '&#x25B2;';
}
logHeader.addEventListener('click', toggleLog);

function log(msg, type = 'info') {
  const ts = new Date().toLocaleTimeString();
  const tag = type === 'ok' ? '[OK]' : type === 'err' ? '[ERR]' : '[...]';
  const span = document.createElement('div');
  span.className = type;
  span.textContent = `${ts} ${tag} ${msg}`;
  logEl.appendChild(span);
  logEl.scrollTop = logEl.scrollHeight;
  // Auto-expand on new message
  if (logCollapsed) toggleLog();
}

// --- Tabs ---
document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    if (btn.dataset.tab === 'workspace') loadFiles();
    if (btn.dataset.tab === 'results') loadStats();
  });
});

// --- Upload ---
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');

dropzone.addEventListener('click', () => fileInput.click());
dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('dragover'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
dropzone.addEventListener('drop', e => {
  e.preventDefault();
  dropzone.classList.remove('dragover');
  handleFiles(e.dataTransfer.files);
});
fileInput.addEventListener('change', () => handleFiles(fileInput.files));

async function handleFiles(fileList) {
  if (!fileList.length) return;
  const files = Array.from(fileList);
  log(`Uploading ${files.length} file(s)...`);

  try {
    if (files.length === 1) {
      const fd = new FormData();
      fd.append('file', files[0]);
      const res = await fetch(API + '/upload/', { method: 'POST', body: fd });
      if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
      const data = await res.json();
      log(`Uploaded: ${data.files.map(f => f.filename).join(', ')}`, 'ok');
    } else {
      const fd = new FormData();
      files.forEach(f => fd.append('files', f));
      const res = await fetch(API + '/upload/batch', { method: 'POST', body: fd });
      if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
      const data = await res.json();
      log(`Batch uploaded: ${data.files.map(f => f.filename).join(', ')}`, 'ok');
    }
    loadFiles();
  } catch (e) {
    log(`Upload failed: ${e.message}`, 'err');
  }
  fileInput.value = '';
}

// --- Files ---
async function loadFiles() {
  try {
    const res = await fetch(API + '/files/');
    if (!res.ok) throw new Error(res.statusText);
    const files = await res.json();
    const tbody = document.getElementById('filesBody');

    // Update unprocessed hint
    const unproc = files.filter(f => !f.processed).length;
    document.getElementById('unprocessedHint').textContent =
      files.length ? `${files.length} file(s), ${unproc} unprocessed` : '';

    if (!files.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="muted">No files uploaded yet.</td></tr>';
      return;
    }
    tbody.innerHTML = files.map(f => {
      const size = f.size_bytes < 1024*1024
        ? (f.size_bytes / 1024).toFixed(1) + ' KB'
        : (f.size_bytes / (1024*1024)).toFixed(2) + ' MB';
      const date = new Date(f.upload_date).toLocaleString();
      const status = f.processed
        ? '<span style="color:#00ff41;">processed</span>'
        : '<span style="color:#777;">pending</span>';
      const top = f.results && f.results.length
        ? `${f.results[0].label} (${((f.results[0].confidence || f.results[0].score) * 100).toFixed(1)}%)`
        : '-';
      return `<tr>
        <td>${f.id}</td>
        <td>${esc(f.filename)}</td>
        <td>${size}</td>
        <td>${date}</td>
        <td>${status}</td>
        <td>${esc(top)}</td>
        <td class="actions">
          <button class="btn btn-sm" onclick="recognizeSingleById(${f.id})" title="Recognize">run</button>
          <button class="btn btn-sm" onclick="reprocessFile(${f.id})" title="Reprocess">re</button>
          <button class="btn btn-sm btn-red" onclick="deleteFile(${f.id})" title="Delete">rm</button>
        </td>
      </tr>`;
    }).join('');
  } catch (e) {
    log('Failed to load files: ' + e.message, 'err');
  }
}

async function deleteFile(id) {
  if (!confirm('Delete file #' + id + '?')) return;
  try {
    const res = await fetch(API + '/files/' + id, { method: 'DELETE' });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    log(`File #${id} deleted.`, 'ok');
    loadFiles();
  } catch (e) {
    log('Delete failed: ' + e.message, 'err');
  }
}

async function reprocessFile(id) {
  try {
    const res = await fetch(API + '/files/' + id + '/reprocess', { method: 'POST' });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    log(`File #${id} marked for reprocessing.`, 'ok');
    loadFiles();
  } catch (e) {
    log('Reprocess failed: ' + e.message, 'err');
  }
}

// --- Inference ---
async function recognizeSingleById(id) {
  log(`Recognizing file #${id}...`);
  try {
    const res = await fetch(API + '/inference/' + id, { method: 'POST' });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    const data = await res.json();
    log(`File #${id}: ${data.predictions[0].label} (${(data.predictions[0].confidence * 100).toFixed(1)}%)`, 'ok');
    renderInferenceResults([data]);
    loadFiles();
  } catch (e) {
    log('Inference failed: ' + e.message, 'err');
  }
}

async function recognizeSingle() {
  const id = parseInt(document.getElementById('inferIdInput').value);
  if (!id) { log('Enter a valid file ID.', 'err'); return; }
  recognizeSingleById(id);
}

async function recognizeBatch() {
  log('Loading unprocessed files...');
  try {
    const filesRes = await fetch(API + '/files/');
    if (!filesRes.ok) throw new Error(filesRes.statusText);
    const files = await filesRes.json();
    const ids = files.filter(f => !f.processed).map(f => f.id);
    if (!ids.length) { log('No unprocessed files.', 'info'); return; }
    log(`Recognizing ${ids.length} file(s)...`);
    const res = await fetch(API + '/inference/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(ids)
    });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    const data = await res.json();
    log(`Batch inference complete: ${data.length} result(s).`, 'ok');
    renderInferenceResults(data);
    loadFiles();
  } catch (e) {
    log('Batch inference failed: ' + e.message, 'err');
  }
}

function renderInferenceResults(results) {
  const el = document.getElementById('inferResults');
  if (!results.length) { el.innerHTML = '<p class="muted">No results.</p>'; return; }
  el.innerHTML = '<table><thead><tr><th>id</th><th>filename</th><th>#1</th><th>#2</th><th>#3</th></tr></thead><tbody>' +
    results.map(r => {
      const preds = (r.predictions || []).slice(0, 3);
      const cells = [0,1,2].map(i => {
        if (!preds[i]) return '<td>-</td>';
        return `<td>${esc(preds[i].label)} <span class="muted">(${(preds[i].confidence * 100).toFixed(1)}%)</span></td>`;
      }).join('');
      return `<tr><td>${r.id}</td><td>${esc(r.filename)}</td>${cells}</tr>`;
    }).join('') + '</tbody></table>';
}

// --- Stats ---
async function loadStats() {
  try {
    const res = await fetch(API + '/visualization/stats');
    if (!res.ok) throw new Error(res.statusText);
    const s = await res.json();
    document.getElementById('statsGrid').innerHTML = `
      <div class="stat-card"><div class="label">total files</div><div class="value">${s.total_files}</div></div>
      <div class="stat-card"><div class="label">processed</div><div class="value">${s.processed_files}</div></div>
      <div class="stat-card"><div class="label">unprocessed</div><div class="value">${s.unprocessed_files}</div></div>
    `;
    if (s.top_brands && s.top_brands.length) {
      document.getElementById('topBrands').innerHTML =
        '<h2>top brands</h2><table><thead><tr><th>brand / model</th><th>count</th></tr></thead><tbody>' +
        s.top_brands.map(b => `<tr><td>${esc(b.label)}</td><td>${b.count}</td></tr>`).join('') +
        '</tbody></table>';
    } else {
      document.getElementById('topBrands').innerHTML = '<p class="muted mt">No predictions yet.</p>';
    }
  } catch (e) {
    log('Failed to load stats: ' + e.message, 'err');
  }
}

function downloadCSV() {
  window.open(API + '/visualization/export/csv', '_blank');
}

// --- Report ---
function loadReport() {
  const frame = document.getElementById('reportFrame');
  frame.style.display = 'block';
  frame.src = API + '/visualization/report';
  log('Loading report...', 'info');
}

// --- Util ---
function esc(s) {
  if (!s) return '';
  const d = document.createElement('div');
  d.textContent = String(s);
  return d.innerHTML;
}

// Init
log('Cars Recognizer frontend loaded.', 'ok');
loadFiles();
