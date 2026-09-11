/**
 * public-dashboard.js — Logic for the citizen portal dashboard.
 */
document.addEventListener('DOMContentLoaded', async () => {
  StatusHelper.startClock();

  // ── Auth guard ─────────────────────────────────────────────────────────
  if (!API.Auth.isLoggedIn() || API.getRole() !== 'user') {
    window.location.href = 'public-login.html'; return;
  }

  const user = API.getUser();
  document.getElementById('userName').textContent    = user?.name    || 'Citizen';
  document.getElementById('userInitial').textContent = (user?.name   || 'U')[0].toUpperCase();

  // ── Tab navigation ─────────────────────────────────────────────────────
  document.querySelectorAll('[data-nav]').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      const target = link.dataset.nav;
      document.querySelectorAll('[data-nav]').forEach(l => l.classList.remove('active'));
      document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
      link.classList.add('active');
      document.getElementById(`sec-${target}`)?.classList.add('active');
      if (target === 'my-reports') loadMyReports();
    });
  });

  // ── Upload zone ────────────────────────────────────────────────────────
  const uploadZone  = document.getElementById('uploadZone');
  const fileInput   = document.getElementById('fileInput');
  const preview     = document.getElementById('previewImg');
  const previewWrap = document.getElementById('previewWrap');

  uploadZone.addEventListener('click', () => fileInput.click());
  uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('drag-over'); });
  uploadZone.addEventListener('dragleave', ()=> uploadZone.classList.remove('drag-over'));
  uploadZone.addEventListener('drop', e => {
    e.preventDefault(); uploadZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  });
  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) handleFileSelect(fileInput.files[0]);
  });

  let selectedFile = null;
  function handleFileSelect(file) {
    if (!file.type.startsWith('image/')) { Toast.error('Please select an image file.'); return; }
    if (file.size > 16 * 1024 * 1024)   { Toast.error('Image must be under 16 MB.'); return; }
    selectedFile = file;
    const url = URL.createObjectURL(file);
    preview.src = url;
    previewWrap.style.display = '';
    uploadZone.style.display  = 'none';
    document.getElementById('detectBtn').disabled = false;
    document.getElementById('resultArea').style.display = 'none';
  }

  document.getElementById('clearImageBtn').addEventListener('click', () => {
    selectedFile = null;
    fileInput.value = '';
    previewWrap.style.display = 'none';
    uploadZone.style.display  = '';
    document.getElementById('detectBtn').disabled = true;
    document.getElementById('resultArea').style.display = 'none';
  });

  // ── Geolocation ────────────────────────────────────────────────────────
  let currentLat = null, currentLng = null;

  document.getElementById('getLocationBtn').addEventListener('click', () => {
    const btn = document.getElementById('getLocationBtn');
    btn.textContent = '⏳ Getting location…'; btn.disabled = true;
    if (!navigator.geolocation) {
      Toast.warning('Geolocation not supported by your browser.');
      btn.textContent = '📍 Get My Location'; btn.disabled = false; return;
    }
    navigator.geolocation.getCurrentPosition(
      pos => {
        currentLat = pos.coords.latitude;
        currentLng = pos.coords.longitude;
        document.getElementById('latInput').value = currentLat.toFixed(6);
        document.getElementById('lngInput').value = currentLng.toFixed(6);
        btn.textContent = '✅ Location captured'; btn.disabled = false;
        Toast.success(`Location: ${currentLat.toFixed(4)}, ${currentLng.toFixed(4)}`);
      },
      err => {
        Toast.error('Could not get location: ' + err.message);
        btn.textContent = '📍 Get My Location'; btn.disabled = false;
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  });

  // Manual lat/lng inputs
  document.getElementById('latInput').addEventListener('input', e => {
    currentLat = parseFloat(e.target.value) || null;
  });
  document.getElementById('lngInput').addEventListener('input', e => {
    currentLng = parseFloat(e.target.value) || null;
  });

  // ── Detection submit ───────────────────────────────────────────────────
  document.getElementById('detectBtn').addEventListener('click', async () => {
    if (!selectedFile)   { Toast.error('Please select an image first.');      return; }
    if (!currentLat || !currentLng) { Toast.error('Please capture or enter your GPS location.'); return; }

    const btn = document.getElementById('detectBtn');
    btn.disabled = true; btn.textContent = '🔄 Analysing…';
    document.getElementById('loadingOverlay').style.display = 'flex';

    try {
      const formData = new FormData();
      formData.append('image',     selectedFile);
      formData.append('latitude',  currentLat);
      formData.append('longitude', currentLng);
      formData.append('address',   document.getElementById('addressInput').value || '');

      const data = await API.Reports.submit(formData);
      showDetectionResult(data);
    } catch (err) {
      Toast.error(err.message || 'Detection failed. Please try again.');
    } finally {
      btn.disabled = false; btn.textContent = '🔍 Detect & Report';
      document.getElementById('loadingOverlay').style.display = 'none';
    }
  });

  function showDetectionResult(data) {
    const dr  = data.detection_result;
    const rep = data.report;
    const area = document.getElementById('resultArea');
    area.style.display = '';

    // Annotated image
    if (rep.annotated_image) {
      document.getElementById('annotatedImg').src = API.imageUrl(rep.annotated_image);
      document.getElementById('annotatedImg').style.display = '';
    }

    // Detection summary
    const summaryBox = document.getElementById('detectionSummary');
    if (dr.pothole_detected) {
      summaryBox.className = 'detection-result detected';
      summaryBox.innerHTML = `
        <span style="font-size:2.5rem">🚧</span>
        <div>
          <div style="font-size:1.1rem;font-weight:800;color:#ef4444">⚠️ Pothole Detected!</div>
          <div style="font-size:13px;color:var(--text-secondary);margin-top:4px">
            ${dr.num_potholes} pothole${dr.num_potholes > 1 ? 's' : ''} found · Confidence: ${(dr.max_confidence * 100).toFixed(1)}%
          </div>
          ${dr.damage_percentage > 0 ? `<div style="font-size:13px;color:var(--danger);margin-top:4px;font-weight:600">🚨 ${dr.damage_percentage}% of road in uploaded image is damaged</div>` : ''}
          <div style="font-size:13px;color:#4ade80;margin-top:6px">✅ Report #${rep.id} submitted · Admin notified by email</div>
        </div>`;
    } else {
      summaryBox.className = 'detection-result not-detected';
      summaryBox.innerHTML = `
        <span style="font-size:2.5rem">✅</span>
        <div>
          <div style="font-size:1.1rem;font-weight:800;color:#4ade80">No Pothole Detected</div>
          <div style="font-size:13px;color:var(--text-secondary);margin-top:4px">
            The road appears to be in good condition.
          </div>
          <div style="font-size:13px;color:var(--text-muted);margin-top:6px">Report #${rep.id} saved for your records.</div>
        </div>`;
    }

    area.scrollIntoView({ behavior:'smooth', block:'nearest' });
    Toast.success(dr.pothole_detected ? 'Pothole reported! Admin has been alerted.' : 'No pothole detected. Road looks good!');
  }

  // ── Load My Reports ────────────────────────────────────────────────────
  async function loadMyReports() {
    const container = document.getElementById('reportsContainer');
    container.innerHTML = `<div style="text-align:center;padding:40px"><div class="spinner"></div></div>`;
    try {
      const reports = await API.Reports.list();
      if (reports.length === 0) {
        container.innerHTML = `<div style="text-align:center;padding:60px;color:var(--text-muted)">
          <div style="font-size:3rem;margin-bottom:16px">📭</div>
          <div style="font-size:16px;font-weight:600">No reports yet</div>
          <p>Submit your first pothole report to see it here.</p>
        </div>`;
        return;
      }
      container.innerHTML = reports.map(r => renderReportCard(r)).join('');
      // Click expand
      container.querySelectorAll('.report-card').forEach(card => {
        card.querySelector('.expand-btn')?.addEventListener('click', async () => {
          const id   = card.dataset.id;
          const logs = card.querySelector('.status-logs');
          if (logs.style.display === 'none') {
            const full = await API.Reports.get(id);
            logs.innerHTML = renderStatusLogs(full.status_logs);
            logs.style.display = '';
          } else { logs.style.display = 'none'; }
        });
      });
    } catch (err) {
      container.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
    }
  }

  function renderReportCard(r) {
    const mapsUrl = StatusHelper.gmapsUrl(r.latitude, r.longitude);
    const conf    = r.confidence_score ? `${(r.confidence_score*100).toFixed(1)}%` : 'N/A';
    return `
    <div class="report-card glass-card" data-id="${r.id}" style="padding:24px;margin-bottom:16px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
        <div>
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
            <span style="font-family:var(--font-display);font-size:1.1rem;font-weight:800">Report #${r.id}</span>
            <span class="${StatusHelper.badgeClass(r.status)}">${StatusHelper.label(r.status)}</span>
            ${r.pothole_detected ? '<span class="badge badge-reported">Pothole</span>' : '<span class="badge badge-repaired">No Pothole</span>'}
          </div>
          <div style="font-size:13px;color:var(--text-secondary)">
            📅 ${StatusHelper.formatDate(r.created_at)} · 
            📍 <a href="${mapsUrl}" target="_blank" style="color:var(--secondary)">Lat ${r.latitude.toFixed(4)}, Lng ${r.longitude.toFixed(4)}</a>
            ${r.confidence_score ? ` · 🎯 Confidence: ${conf}` : ''}
          </div>
          ${r.damage_percentage > 0 ? `<div style="font-size:13px;color:var(--danger);margin-top:4px;font-weight:600">🚨 ${r.damage_percentage}% of road in uploaded image is damaged</div>` : ''}
        </div>
        ${r.annotated_image
          ? `<img src="${API.imageUrl(r.annotated_image)}" style="width:100px;height:70px;object-fit:cover;border-radius:8px;border:1px solid var(--border)">`
          : ''}
      </div>

      <!-- Progress Steps -->
      <div class="progress-steps" style="margin:20px 0 8px">
        ${renderProgressSteps(r.status)}
      </div>

      ${r.admin_notes ? `<div style="margin-top:12px;padding:10px 14px;background:rgba(56,189,248,0.08);border-radius:8px;border:1px solid rgba(56,189,248,0.2);font-size:13px;color:var(--secondary)">💬 Admin note: ${r.admin_notes}</div>` : ''}

      <div style="display:flex;gap:10px;margin-top:16px">
        <button class="btn btn-ghost btn-sm expand-btn">📋 View Status History</button>
        <a href="${mapsUrl}" target="_blank" class="btn btn-ghost btn-sm">🗺️ View on Map</a>
      </div>
      <div class="status-logs" style="display:none;margin-top:16px"></div>
    </div>`;
  }

  function renderProgressSteps(status) {
    const steps = [
      { key:'reported',    label:'Reported',    icon:'📌' },
      { key:'reviewed',    label:'Reviewed',    icon:'👁️' },
      { key:'in_progress', label:'In Progress', icon:'🔧' },
      { key:'repaired',    label:'Repaired',    icon:'✅' },
    ];
    const order = steps.map(s => s.key);
    const idx   = order.indexOf(status);
    return steps.map((s, i) => {
      const cls = i < idx ? 'done' : i === idx ? 'active' : '';
      return `
        <div class="progress-step ${cls}">
          <div class="step-dot">${i < idx ? '✓' : s.icon}</div>
          <div class="step-label">${s.label}</div>
        </div>`;
    }).join('');
  }

  function renderStatusLogs(logs) {
    if (!logs || !logs.length) return '<p style="color:var(--text-muted);font-size:13px">No status history yet.</p>';
    return `<div style="border-top:1px solid var(--border);padding-top:14px">
      <div style="font-size:12px;font-weight:700;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">Status History</div>
      ${logs.map(l => `
        <div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:10px">
          <div style="width:8px;height:8px;border-radius:50%;background:var(--primary);margin-top:5px;flex-shrink:0"></div>
          <div>
            <span class="${StatusHelper.badgeClass(l.status)}" style="font-size:11px">${StatusHelper.label(l.status)}</span>
            <span style="font-size:12px;color:var(--text-muted);margin-left:8px">${StatusHelper.formatDate(l.timestamp)}</span>
            ${l.changed_by ? `<span style="font-size:12px;color:var(--text-muted)"> · by ${l.changed_by}</span>` : ''}
            ${l.notes ? `<div style="font-size:12px;color:var(--text-secondary);margin-top:3px">${l.notes}</div>` : ''}
          </div>
        </div>`).join('')}
    </div>`;
  }

  // Load reports on first open if on that section
  if (window.location.hash === '#reports') {
    document.querySelector('[data-nav="my-reports"]')?.click();
  }

  // Logout
  document.getElementById('logoutBtn').addEventListener('click', () => {
    if (confirm('Logout of RoadSafe?')) API.Auth.logout();
  });
});
