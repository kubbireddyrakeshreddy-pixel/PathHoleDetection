/**
 * admin-dashboard.js — Logic for the government officer admin dashboard.
 */
document.addEventListener('DOMContentLoaded', async () => {
  StatusHelper.startClock();

  // ── Auth guard ─────────────────────────────────────────────────────────
  if (!API.Auth.isLoggedIn() || API.getRole() !== 'admin') {
    window.location.href = 'admin-login.html'; return;
  }

  const admin = API.getUser();
  document.getElementById('adminName').textContent    = admin?.name    || 'Officer';
  document.getElementById('adminInitial').textContent = (admin?.name   || 'A')[0].toUpperCase();
  document.getElementById('adminDept').textContent    = admin?.department || '';

  // ── Tab navigation ─────────────────────────────────────────────────────
  document.querySelectorAll('[data-nav]').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      const target = link.dataset.nav;
      document.querySelectorAll('[data-nav]').forEach(l => l.classList.remove('active'));
      document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
      link.classList.add('active');
      document.getElementById(`sec-${target}`)?.classList.add('active');
      if (target === 'dashboard') { loadStats(); loadReports(); }
      if (target === 'map')       { loadMap(); }
      if (target === 'reports')   { loadReports(true); }
    });
  });

  // ── Load Dashboard Stats ───────────────────────────────────────────────
  async function loadStats() {
    try {
      const stats = await API.AdminAPI.stats();
      document.getElementById('statTotal').textContent    = stats.total;
      document.getElementById('statPending').textContent  = stats.reported;
      document.getElementById('statProgress').textContent = stats.in_progress;
      document.getElementById('statFixed').textContent    = stats.repaired;
    } catch (err) { console.error('Stats error:', err); }
  }

  // ── Load Reports ───────────────────────────────────────────────────────
  let allReports = [];
  async function loadReports(tableView = false) {
    try {
      allReports = await API.Reports.list();
      renderReportsTable(allReports);
      if (!tableView) renderRecentReports(allReports.slice(0, 5));
    } catch (err) { console.error('Reports error:', err); }
  }

  function renderRecentReports(reports) {
    const el = document.getElementById('recentReports');
    if (!reports.length) {
      el.innerHTML = `<div style="text-align:center;padding:40px;color:var(--text-muted)">
        <div style="font-size:2.5rem;margin-bottom:12px">📭</div>
        No reports in your zone yet.
      </div>`; return;
    }
    el.innerHTML = reports.map(r => renderReportRow(r)).join('');
    attachStatusButtons();
  }

  function renderReportsTable(reports) {
    const el = document.getElementById('allReportsTable');
    if (!el) return;
    if (!reports.length) {
      el.innerHTML = `<div style="text-align:center;padding:60px;color:var(--text-muted)">No reports found.</div>`;
      return;
    }
    el.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th>#ID</th><th>Date</th><th>Location</th><th>Image</th>
            <th>Confidence</th><th>Status</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${reports.map(r => `
            <tr>
              <td><strong>#${r.id}</strong></td>
              <td style="white-space:nowrap">${StatusHelper.formatDate(r.created_at)}</td>
              <td>
                <a href="${StatusHelper.gmapsUrl(r.latitude, r.longitude)}" target="_blank"
                   style="color:var(--secondary);font-size:13px">
                  📍 ${r.latitude.toFixed(4)}, ${r.longitude.toFixed(4)}
                </a><br>
                <span style="font-size:12px;color:var(--text-muted)">${r.address || ''}</span>
              </td>
              <td>
                ${r.annotated_image
                  ? `<img src="${API.imageUrl(r.annotated_image)}" style="width:80px;height:55px;object-fit:cover;border-radius:6px;cursor:pointer;border:1px solid var(--border)" onclick="openImageModal('${API.imageUrl(r.annotated_image)}')">`
                  : '<span style="color:var(--text-muted)">–</span>'}
              </td>
              <td>
                ${r.confidence_score
                  ? `<span style="font-weight:700;color:${r.confidence_score > 0.7 ? 'var(--danger)' : 'var(--warning)'}">${(r.confidence_score*100).toFixed(1)}%</span>`
                  : '–'}
              </td>
              <td><span class="${StatusHelper.badgeClass(r.status)}">${StatusHelper.label(r.status)}</span></td>
              <td><button class="btn btn-secondary btn-sm" onclick="openStatusModal(${r.id},'${r.status}','${(r.admin_notes||'').replace(/'/g,"\\'")}')">Update Status</button></td>
            </tr>`).join('')}
        </tbody>
      </table>`;
  }

  function renderReportRow(r) {
    const mapsUrl = StatusHelper.gmapsUrl(r.latitude, r.longitude);
    return `
    <div class="glass-card" style="padding:20px;margin-bottom:16px" id="report-${r.id}">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
        <div style="flex:1">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px">
            <span style="font-weight:800;font-family:var(--font-display)">#${r.id}</span>
            <span class="${StatusHelper.badgeClass(r.status)}">${StatusHelper.label(r.status)}</span>
            ${r.pothole_detected ? '<span class="badge badge-reported">⚠️ Pothole</span>' : '<span class="badge badge-repaired">✅ Clear</span>'}
          </div>
          <div style="font-size:13px;color:var(--text-secondary)">
            👤 ${r.user_name || 'Anonymous'} · 📅 ${StatusHelper.timeAgo(r.created_at)}
          </div>
          <div style="font-size:13px;margin-top:6px">
            📍 <a href="${mapsUrl}" target="_blank" style="color:var(--secondary)">Lat ${r.latitude.toFixed(4)}, Lng ${r.longitude.toFixed(4)}</a>
            ${r.confidence_score ? ` · 🎯 ${(r.confidence_score*100).toFixed(1)}%` : ''}
          </div>
          ${r.damage_percentage > 0 ? `<div style="font-size:13px;color:var(--danger);margin-top:4px;font-weight:600">🚨 ${r.damage_percentage}% of road in uploaded image is damaged</div>` : ''}
          ${r.address ? `<div style="font-size:13px;color:var(--text-muted);margin-top:4px">📌 ${r.address}</div>` : ''}
        </div>
        ${r.annotated_image
          ? `<img src="${API.imageUrl(r.annotated_image)}" style="width:110px;height:75px;object-fit:cover;border-radius:8px;border:1px solid var(--border);cursor:pointer" onclick="openImageModal('${API.imageUrl(r.annotated_image)}')">`
          : ''}
      </div>

      <!-- Status Action Buttons -->
      <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:16px">
        ${r.status === 'reported'
          ? `<button class="btn btn-warning btn-sm status-btn" data-id="${r.id}" data-status="reviewed">👁️ Mark Reviewed</button>` : ''}
        ${r.status === 'reviewed'
          ? `<button class="btn btn-info btn-sm status-btn" data-id="${r.id}" data-status="in_progress">🔧 Work in Progress</button>` : ''}
        ${r.status === 'in_progress'
          ? `<button class="btn btn-success btn-sm status-btn" data-id="${r.id}" data-status="repaired">✅ Mark Repaired</button>` : ''}
        ${r.status !== 'repaired'
          ? `<button class="btn btn-ghost btn-sm" onclick="openStatusModal(${r.id},'${r.status}','${(r.admin_notes||'').replace(/'/g,"\\'")}')">💬 Add Notes</button>` : ''}
        <a href="${mapsUrl}" target="_blank" class="btn btn-ghost btn-sm">🗺️ View on Map</a>
      </div>
    </div>`;
  }

  function attachStatusButtons() {
    document.querySelectorAll('.status-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id     = btn.dataset.id;
        const status = btn.dataset.status;
        btn.disabled = true; btn.textContent = 'Updating…';
        try {
          await API.Reports.updateStatus(id, status);
          Toast.success(`Status updated to: ${StatusHelper.label(status)}`);
          loadStats(); loadReports();
        } catch (err) {
          Toast.error(err.message || 'Update failed.');
          btn.disabled = false;
        }
      });
    });
  }

  // ── Status Modal ───────────────────────────────────────────────────────
  window.openStatusModal = function(id, currentStatus, notes) {
    document.getElementById('modalReportId').textContent = id;
    document.getElementById('modalCurrentStatus').className = StatusHelper.badgeClass(currentStatus);
    document.getElementById('modalCurrentStatus').textContent = StatusHelper.label(currentStatus);
    document.getElementById('modalNotes').value = notes || '';

    const sel = document.getElementById('modalStatusSelect');
    const options = [
      { value:'reviewed',    label:'🟡 Reviewed' },
      { value:'in_progress', label:'🔵 Work in Progress' },
      { value:'repaired',    label:'🟢 Road Repaired' },
    ];
    sel.innerHTML = options.filter(o => o.value !== currentStatus)
      .map(o => `<option value="${o.value}">${o.label}</option>`).join('');

    document.getElementById('modalSubmitBtn').onclick = async () => {
      const newStatus = sel.value;
      const notes_val = document.getElementById('modalNotes').value;
      const btn = document.getElementById('modalSubmitBtn');
      btn.disabled = true; btn.textContent = 'Updating…';
      try {
        await API.Reports.updateStatus(id, newStatus, notes_val);
        Toast.success('Status updated! User notified by email.');
        closeStatusModal();
        loadStats(); loadReports();
      } catch (err) {
        Toast.error(err.message || 'Update failed.');
      } finally {
        btn.disabled = false; btn.textContent = 'Update Status';
      }
    };
    document.getElementById('statusModal').classList.add('active');
  };

  window.closeStatusModal = () => {
    document.getElementById('statusModal').classList.remove('active');
  };

  // ── Image Modal ────────────────────────────────────────────────────────
  window.openImageModal = function(src) {
    document.getElementById('modalFullImg').src = src;
    document.getElementById('imageModal').classList.add('active');
  };
  window.closeImageModal = () => {
    document.getElementById('imageModal').classList.remove('active');
  };

  // ── Map ────────────────────────────────────────────────────────────────
  let map = null;
  let mapMarkers = [];      // track all circle markers for easy removal
  let mapAutoRefresh = null; // interval handle

  async function loadMap() {
    // Initialise Leaflet map once
    if (!map) {
      await new Promise(r => setTimeout(r, 120));
      map = L.map('leafletMap').setView([17.0, 79.3], 9); // centre on pincode 508001 zone
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(map);
    }

    await refreshMapPins();

    // Auto-refresh every 30 seconds while map tab is active
    if (!mapAutoRefresh) {
      mapAutoRefresh = setInterval(refreshMapPins, 30000);
      updateMapTimer(30);
    }
  }

  async function refreshMapPins() {
    // Remove old markers
    mapMarkers.forEach(m => m.remove());
    mapMarkers = [];

    const allReports    = await API.Reports.list();
    // Only show ACTIVE potholes — hide repaired roads
    const reports = allReports.filter(r => r.status !== 'repaired');
    const bounds  = [];

    // Update counter badge
    const counter = document.getElementById('mapReportCount');
    if (counter) counter.textContent = `${reports.length} active pothole${reports.length !== 1 ? 's' : ''} pinned`;

    const colorMap = {
      reported:    '#ef4444',
      reviewed:    '#f59e0b',
      in_progress: '#3b82f6',
      repaired:    '#22c55e',
    };
    const pulseMap = {
      reported:    '0 0 0 4px rgba(239,68,68,0.3)',
      reviewed:    '0 0 0 4px rgba(245,158,11,0.3)',
      in_progress: '0 0 0 4px rgba(59,130,246,0.3)',
      repaired:    '0 0 0 4px rgba(34,197,94,0.3)',
    };

    reports.forEach(r => {
      const color = colorMap[r.status] || '#ef4444';
      // Use larger radius for unreviewed reports to draw attention
      const radius = r.status === 'reported' ? 11 : 9;

      const marker = L.circleMarker([r.latitude, r.longitude], {
        radius,
        fillColor:   color,
        color:       'white',
        weight:      2.5,
        fillOpacity: 0.92,
      }).addTo(map);

      // Rich popup with image thumbnail
      const imgHtml = r.annotated_image
        ? `<img src="${API.imageUrl(r.annotated_image)}"
               style="width:100%;max-height:120px;object-fit:cover;border-radius:6px;
                      margin:8px 0;border:2px solid ${color}">`
        : '';

      marker.bindPopup(`
        <div style="font-family:'Segoe UI',Arial,sans-serif;min-width:220px;max-width:260px">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
            <strong style="font-size:14px">#${r.id}</strong>
            <span style="background:${color};color:white;padding:2px 8px;border-radius:999px;
                         font-size:11px;font-weight:700">${StatusHelper.label(r.status)}</span>
          </div>
          ${imgHtml}
          <div style="font-size:12px;line-height:1.8">
            👤 <b>${r.user_name || 'Anonymous'}</b><br>
            📅 ${StatusHelper.formatDate(r.created_at)}<br>
            📍 Lat ${r.latitude.toFixed(5)}, Lng ${r.longitude.toFixed(5)}<br>
            ${r.confidence_score ? `🎯 Confidence: <b>${(r.confidence_score*100).toFixed(1)}%</b><br>` : ''}
            ${r.num_potholes ? `🕳️ Potholes found: <b>${r.num_potholes}</b><br>` : ''}
            ${r.damage_percentage > 0 ? `🚨 <span style="color:#ef4444;font-weight:700">${r.damage_percentage}% of road in uploaded image is damaged</span><br>` : ''}
            ${r.address ? `📌 ${r.address}<br>` : ''}
          </div>
          <a href="${StatusHelper.gmapsUrl(r.latitude, r.longitude)}" target="_blank"
             style="display:inline-block;margin-top:8px;background:#f97316;color:white;
                    padding:5px 12px;border-radius:6px;font-size:12px;font-weight:700;
                    text-decoration:none">📍 Open in Google Maps</a>
        </div>`, { maxWidth: 280 });

      mapMarkers.push(marker);
      bounds.push([r.latitude, r.longitude]);
    });

    if (bounds.length) {
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 });
    }

    // Update last-refreshed time
    const ts = document.getElementById('mapLastRefresh');
    if (ts) ts.textContent = `Last updated: ${new Date().toLocaleTimeString('en-IN')}`;
  }

  function stopMapAutoRefresh() {
    if (mapAutoRefresh) { clearInterval(mapAutoRefresh); mapAutoRefresh = null; }
  }

  // Countdown timer shown on the map tab
  let timerInterval = null;
  function updateMapTimer(seconds) {
    const el = document.getElementById('mapCountdown');
    if (!el) return;
    let remaining = seconds;
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(() => {
      remaining--;
      if (remaining <= 0) { remaining = 30; }
      el.textContent = `Auto-refresh in ${remaining}s`;
    }, 1000);
  }

  // ── Filters ────────────────────────────────────────────────────────────
  document.getElementById('filterStatus')?.addEventListener('change', e => {
    const val = e.target.value;
    const filtered = val ? allReports.filter(r => r.status === val) : allReports;
    renderReportsTable(filtered);
  });

  // ── Logout ─────────────────────────────────────────────────────────────
  document.getElementById('logoutBtn').addEventListener('click', () => {
    if (confirm('Logout of Admin Panel?')) API.Auth.logout();
  });

  // ── Tab nav: stop map refresh when leaving map tab ─────────────────────
  document.querySelectorAll('[data-nav]').forEach(link => {
    link.addEventListener('click', () => {
      if (link.dataset.nav !== 'map') stopMapAutoRefresh();
    });
  });

  // Manual refresh button on map tab
  document.getElementById('refreshMapBtn')?.addEventListener('click', async () => {
    const btn = document.getElementById('refreshMapBtn');
    btn.disabled = true; btn.textContent = '⏳ Refreshing…';
    await refreshMapPins();
    btn.disabled = false; btn.textContent = '🔄 Refresh Now';
    Toast.info('Map updated!');
  });

  // ── Initial load ───────────────────────────────────────────────────────
  loadStats();
  loadReports();
  // Also auto-refresh dashboard stats every 60s
  setInterval(() => { loadStats(); loadReports(); }, 60000);
});
