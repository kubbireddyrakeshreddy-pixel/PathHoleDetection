/**
 * api.js — centralised API client for RoadSafe Portal.
 *
 * All fetch requests go through this module.
 * JWT token is stored in localStorage and automatically attached.
 */

const API = (() => {
  const BASE = '/api';

  // ── Token helpers ──────────────────────────────────────────────────────
  const getToken  = ()     => localStorage.getItem('rs_token');
  const setToken  = (tok)  => localStorage.setItem('rs_token', tok);
  const clearToken= ()     => { localStorage.removeItem('rs_token'); localStorage.removeItem('rs_user'); };
  const getUser   = ()     => { try { return JSON.parse(localStorage.getItem('rs_user')); } catch { return null; } };
  const setUser   = (usr)  => localStorage.setItem('rs_user', JSON.stringify(usr));
  const getRole   = ()     => localStorage.getItem('rs_role');
  const setRole   = (r)    => localStorage.setItem('rs_role', r);

  // ── Core fetch ─────────────────────────────────────────────────────────
  async function req(method, path, body = null, isFormData = false) {
    const headers = {};
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (!isFormData) headers['Content-Type'] = 'application/json';

    const opts = { method, headers };
    if (body) opts.body = isFormData ? body : JSON.stringify(body);

    const res  = await fetch(`${BASE}${path}`, opts);
    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      const err = new Error(data.error || `HTTP ${res.status}`);
      err.status = res.status;
      err.data   = data;
      throw err;
    }
    return data;
  }

  // ── Auth ───────────────────────────────────────────────────────────────
  const Auth = {
    async registerUser(payload) {
      const data = await req('POST', '/auth/register/user', payload);
      setToken(data.token); setUser(data.user); setRole('user');
      return data;
    },
    async registerAdmin(payload) {
      const data = await req('POST', '/auth/register/admin', payload);
      setToken(data.token); setUser(data.admin); setRole('admin');
      return data;
    },
    async loginUser(payload) {
      const data = await req('POST', '/auth/login/user', payload);
      setToken(data.token); setUser(data.user); setRole('user');
      return data;
    },
    async loginAdmin(payload) {
      const data = await req('POST', '/auth/login/admin', payload);
      setToken(data.token); setUser(data.admin); setRole('admin');
      return data;
    },
    async me() {
      return req('GET', '/auth/me');
    },
    logout() {
      clearToken();
      localStorage.removeItem('rs_role');
      window.location.href = '/';
    },
    isLoggedIn() { return !!getToken(); },
  };

  // ── Reports ────────────────────────────────────────────────────────────
  const Reports = {
    async submit(formData) {
      return req('POST', '/reports', formData, true);
    },
    async list() {
      return req('GET', '/reports');
    },
    async get(id) {
      return req('GET', `/reports/${id}`);
    },
    async updateStatus(id, status, notes = '') {
      return req('PUT', `/reports/${id}/status`, { status, notes });
    },
  };

  // ── Admin ──────────────────────────────────────────────────────────────
  const AdminAPI = {
    async stats() {
      return req('GET', '/admin/stats');
    },
    async deleteReport(id) {
      return req('DELETE', `/reports/${id}`);
    }
  };

  // ── Images ────────────────────────────────────────────────────────────
  function imageUrl(filename) {
    if (!filename) return '';
    if (filename.startsWith('http')) return filename;
    return `${BASE}/images/${filename}`;
  }

  // ── Expose ────────────────────────────────────────────────────────────
  return {
    Auth, Reports, Admin: AdminAPI, AdminAPI, imageUrl,
    getUser, getRole,
  };
})();

// ── Toast notifications ────────────────────────────────────────────────────
const Toast = (() => {
  let container;
  function init() {
    if (!document.getElementById('toast-container')) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    } else {
      container = document.getElementById('toast-container');
    }
  }

  function show(message, type = 'info', duration = 4000) {
    init();
    const icons = { success:'✅', error:'❌', info:'ℹ️', warning:'⚠️' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('removing');
      toast.addEventListener('animationend', () => toast.remove());
    }, duration);
  }

  return {
    success: (msg, dur) => show(msg, 'success', dur),
    error:   (msg, dur) => show(msg, 'error',   dur),
    info:    (msg, dur) => show(msg, 'info',     dur),
    warning: (msg, dur) => show(msg, 'warning',  dur),
  };
})();

// ── Status helpers ─────────────────────────────────────────────────────────
const StatusHelper = {
  labels: {
    reported:    '🔴 Reported',
    reviewed:    '🟡 Reviewed',
    in_progress: '🔵 Work in Progress',
    repaired:    '🟢 Road Repaired',
  },
  badgeClass(status) {
    return `badge badge-${status}`;
  },
  label(status) {
    return this.labels[status] || status;
  },
  gmapsUrl(lat, lng) {
    return `https://www.google.com/maps?q=${lat},${lng}`;
  },
  timeAgo(isoStr) {
    const diff = Date.now() - new Date(isoStr).getTime();
    const mins  = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days  = Math.floor(diff / 86400000);
    if (days  > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (mins  > 0) return `${mins}m ago`;
    return 'Just now';
  },
  formatDate(isoStr) {
    return new Date(isoStr).toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata',
      day:'2-digit', month:'short', year:'numeric',
      hour:'2-digit', minute:'2-digit',
    });
  },

  // ── Clock ───────────────────────────────────────────────────────────
  startClock() {
    const clockEl = document.getElementById('liveClock');
    if (!clockEl) return;
    
    function updateTime() {
      const now = new Date();
      clockEl.textContent = now.toLocaleTimeString('en-IN', {
        timeZone: 'Asia/Kolkata',
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true
      }) + ' (IST)';
    }
    
    updateTime();
    setInterval(updateTime, 1000);
  }
};
