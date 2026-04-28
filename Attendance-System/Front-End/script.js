/* ═══════════════════════════════════════════════════
   CONFIG
═══════════════════════════════════════════════════ */
const API = 'http://127.0.0.1:5000/api';
let token = localStorage.getItem('att_token');
let user  = JSON.parse(localStorage.getItem('att_user') || 'null');

/* ═══════════════════════════════════════════════════
   UTILS
═══════════════════════════════════════════════════ */
const $ = id => document.getElementById(id);

async function api(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (token) opts.headers['Authorization'] = 'Bearer ' + token;
  if (body)  opts.body = JSON.stringify(body);
  try {
    const res = await fetch(API + path, opts);
    const data = await res.json().catch(() => ({}));
    
    // If token is invalid or expired, redirect to login
    if (res.status === 401 && data.error && data.error.includes('Invalid token')) {
      console.warn('Token invalid, clearing and redirecting to login');
      localStorage.removeItem('att_token');
      localStorage.removeItem('att_user');
      token = null;
      user = null;
      window.location.href = 'index.html';
      return;
    }
    
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  } catch (err) {
    console.error('API Error:', method, path, err);
    throw err;
  }
}

function showAlert(id, msg, type='error') {
  const el = $(id);
  if (!el) return;
  el.className = `alert alert-${type} show`;
  const span = el.querySelector('span');
  if (span) span.textContent = msg;
  else el.textContent = msg;
}
function hideAlert(id) { const el=$(id); if(el) el.classList.remove('show'); }

function fmtDate(d) {
  if (!d) return '—';
  const dt = new Date(d);
  return dt.toLocaleDateString('en-PH',{month:'short',day:'numeric',year:'numeric'});
}
function fmtTime(t) {
  if (!t) return '—';
  const [h,m] = t.split(':');
  const hr = +h, suffix = hr >= 12 ? 'PM' : 'AM';
  return `${hr%12||12}:${m} ${suffix}`;
}
function fmtDateTime(dt) {
  if (!dt) return '—';
  return new Date(dt).toLocaleString('en-PH',{
    month:'short',day:'numeric',hour:'numeric',minute:'2-digit',hour12:true
  });
}

function openModal(id) { const el = $(id); if (el) el.classList.add('open'); }
function closeModal(id) { const el = $(id); if (el) el.classList.remove('open'); }

/* ═══════════════════════════════════════════════════
   AUTH TABS / ROLE
═══════════════════════════════════════════════════ */
function switchAuthTab(tab) {
  document.querySelectorAll('.auth-tab').forEach((el,i)=>{
    el.classList.toggle('active', i === (tab==='login'?0:1));
  });
  $('login-form').classList.toggle('active', tab==='login');
  $('register-form').classList.toggle('active', tab==='register');
}

function setRole(role) {
  $('reg-role').value = role;
  $('role-student').classList.toggle('active', role==='student');
  $('role-teacher').classList.toggle('active', role==='teacher');
  $('student-fields').style.display = role==='student' ? 'grid' : 'none';
}

/* ═══════════════════════════════════════════════════
   AUTH — LOGIN
═══════════════════════════════════════════════════ */
async function doLogin() {
  hideAlert('login-alert');
  const email = $('login-email').value.trim();
  const pass  = $('login-password').value;
  if (!email || !pass) return showAlert('login-alert','Please fill in all fields.');

  $('login-spinner').classList.add('show');
  $('login-btn-text').textContent = 'Signing in…';
  try {
    const data = await api('POST','/auth/login',{email,password:pass});
    token = data.token; user = data.user;
    localStorage.setItem('att_token', token);
    localStorage.setItem('att_user', JSON.stringify(user));
    if (document.getElementById('app-page')) {
      launchApp();
    } else {
      window.location.href = user.role === 'teacher' ? 'teacher.html' : 'student.html';
    }
  } catch(e) {
    showAlert('login-alert', e.message);
  } finally {
    $('login-spinner').classList.remove('show');
    $('login-btn-text').textContent = 'Sign In';
  }
}

/* ═══════════════════════════════════════════════════
   AUTH — REGISTER
═══════════════════════════════════════════════════ */
async function doRegister() {
  hideAlert('reg-alert');
  const payload = {
    full_name:  $('reg-name').value.trim(),
    email:      $('reg-email').value.trim(),
    password:   $('reg-pass').value,
    role:       $('reg-role').value,
    student_id: $('reg-sid').value.trim(),
    section:    $('reg-section').value.trim(),
  };
  if (!payload.full_name||!payload.email||!payload.password)
    return showAlert('reg-alert','Please fill required fields.');

  $('reg-spinner').classList.add('show');
  $('reg-btn-text').textContent = 'Creating…';
  try {
    const data = await api('POST','/auth/register',payload);
    token = data.token; user = data.user;
    localStorage.setItem('att_token', token);
    localStorage.setItem('att_user', JSON.stringify(user));
    if (document.getElementById('app-page')) {
      launchApp();
    } else {
      window.location.href = user.role === 'teacher' ? 'teacher.html' : 'student.html';
    }
  } catch(e) {
    showAlert('reg-alert', e.message);
  } finally {
    $('reg-spinner').classList.remove('show');
    $('reg-btn-text').textContent = 'Create Account';
  }
}

function logout() {
  localStorage.removeItem('att_token');
  localStorage.removeItem('att_user');
  token = null; user = null;

  const authPage = document.getElementById('auth-page');
  const appPage = document.getElementById('app-page');

  if (authPage && appPage) {
    authPage.classList.add('active');
    appPage.classList.remove('active');
  } else {
    window.location.href = 'index.html';
  }
}

/* ═══════════════════════════════════════════════════
   APP LAUNCH
═══════════════════════════════════════════════════ */
function launchApp() {
  const authPage = $('auth-page');
  const appPage = $('app-page');
  if (authPage) authPage.classList.remove('active');
  if (appPage) appPage.classList.add('active');

  const navName = $('nav-name');
  if (navName && user && user.full_name) {
    navName.textContent = user.full_name.split(' ')[0];
  }

  buildSidebar();
  navigateTo(user.role === 'teacher' ? 'create' : 'confirm');
}

function buildSidebar() {
  const nav = $('sidebar');
  const items = user.role === 'teacher'
    ? [
        { id:'create',   icon: plusIcon(),  label: 'Create Session' },
        { id:'sessions', icon: calIcon(),   label: 'Sessions'       },
        { id:'t-records', icon: listIcon(),  label: 'Records'        },
      ]
    : [
        { id:'confirm',   icon: checkIcon(), label: 'Confirm'    },
        { id:'s-history', icon: listIcon(),  label: 'My History' },
      ];

  nav.innerHTML = items.map(it=>`
    <button class="nav-item" id="nav-${it.id}" onclick="navigateTo('${it.id}')">
      ${it.icon} ${it.label}
    </button>`).join('');
}

function navigateTo(panel) {
  document.querySelectorAll('.nav-item').forEach(el=>el.classList.remove('active'));
  const btn = $('nav-'+panel);
  if (btn) btn.classList.add('active');

  // render
  const area = $('content-area');
  area.innerHTML = '';
  const div = document.createElement('div');
  div.id = 'panel-'+panel;
  div.className = 'panel active';
  area.appendChild(div);

  switch(panel) {
    case 'create':    renderTeacherCreate(div);  break;
    case 'sessions':  renderTeacherSessions(div); break;
    case 't-records': renderTeacherRecords(div);  break;
    case 'confirm':   renderStudentConfirm(div);  break;
    case 's-history': renderStudentHistory(div);  break;
  }
}

/* ═══════════════════════════════════════════════════
   TEACHER — SESSIONS PANEL
═══════════════════════════════════════════════════ */
/* ══════════════════════════════════════════════════════════════════════════
   TEACHER — CREATE SESSION PAGE
═══════════════════════════════════════════════════════════════════════════ */
function renderTeacherCreate(el) {
  const today = new Date().toISOString().slice(0,10);
  el.innerHTML = `
    <div class="panel-header">
      <div>
        <h1>Create Session</h1>
        <p>Start a new attendance session for your students.</p>
      </div>
    </div>
    <div class="card">
      <div id="create-result"></div>
      <div id="create-alert" class="alert alert-error"><span id="create-msg"></span></div>
      <div class="field">
        <label>Subject</label>
        <input type="text" id="s-subject" placeholder="e.g. Web Systems & Technologies"/>
      </div>
      <div class="field-row">
        <div class="field">
          <label>Section</label>
          <input type="text" id="s-section" placeholder="BSIT-3A"/>
        </div>
        <div class="field">
          <label>Date</label>
          <input type="date" id="s-date" value="${today}"/>
        </div>
      </div>
      <div class="field-row">
        <div class="field">
          <label>Start Time</label>
          <input type="time" id="s-start"/>
        </div>
        <div class="field">
          <label>End Time</label>
          <input type="time" id="s-end"/>
        </div>
      </div>
      <div class="field">
        <label>Max Students (optional)</label>
        <input type="number" id="s-max" placeholder="Leave empty for unlimited" min="1"/>
      </div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:4px;">
        <button class="btn btn-ghost" onclick="navigateTo('sessions')">Cancel</button>
        <button class="btn btn-primary" onclick="createSession()">
          <span id="create-btn-text">Create Session</span>
          <div class="spinner" id="create-spinner"></div>
        </button>
      </div>
    </div>`;
}

async function renderTeacherSessions(el) {
  el.innerHTML = `
    <div class="panel-header">
      <div>
        <h1>Sessions</h1>
        <p>Manage your attendance sessions</p>
      </div>
    </div>
    <div id="sessions-list"><div class="empty"><div class="empty-icon">📋</div><p>Loading sessions…</p></div></div>`;

  await loadSessions();
}

async function loadSessions() {
  try {
    const rows = await api('GET','/sessions');
    const list = $('sessions-list');
    if (!rows.length) {
      list.innerHTML = `<div class="empty"><div class="empty-icon">📋</div><p>No sessions yet. Create one to get started.</p></div>`;
      return;
    }
    list.innerHTML = `
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Subject</th><th>Section</th><th>Date</th>
              <th>Time</th><th>Code</th><th>Max</th><th>Status</th><th></th>
            </tr>
          </thead>
          <tbody>
            ${rows.map(r=>`
            <tr>
              <td><strong>${r.subject}</strong></td>
              <td>${r.section}</td>
              <td>${fmtDate(r.session_date)}</td>
              <td style="white-space:nowrap">${fmtTime(r.start_time)} – ${fmtTime(r.end_time)}</td>
              <td><span style="font-family:var(--mono);font-weight:500;letter-spacing:2px;color:var(--accent)">${r.code}</span></td>
              <td>${r.max_students || '—'}</td>
              <td>
                ${r.is_open
                  ? `<span class="badge badge-green">● Open</span>`
                  : `<span class="badge badge-muted">Closed</span>`}
              </td>
              <td>
                <div style="display:flex;gap:6px">
                  <button class="btn btn-ghost btn-sm" onclick="viewAttendance(${r.id},'${r.subject}')">View</button>
                  <button class="btn btn-ghost btn-sm" onclick="editSessionMax(${r.id})">Edit</button>
                  <button class="btn btn-sm ${r.is_open?'btn-danger':'btn-ghost'}"
                    onclick="toggleSession(${r.id})">
                    ${r.is_open?'Close':'Open'}
                  </button>
                </div>
              </td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>`;
  } catch(e) {
    $('sessions-list').innerHTML = `<div class="alert alert-error show">${e.message}</div>`;
  }
}

function openNewSession() {
  // prefill today
  const today = new Date().toISOString().slice(0,10);
  $('s-date').value = today;
  hideAlert('session-modal-alert');
  openModal('session-modal');
}

async function createSession() {
  const alertTarget = $('create-result') ? 'create-alert' : 'session-modal-alert';
  hideAlert(alertTarget);
  const body = {
    subject:      $('s-subject').value.trim(),
    section:      $('s-section').value.trim(),
    session_date: $('s-date').value,
    start_time:   $('s-start').value,
    end_time:     $('s-end').value,
    max_students: $('s-max').value.trim() || null,
  };
  if (!body.subject||!body.section||!body.session_date||!body.start_time||!body.end_time)
    return showAlert(alertTarget,'Please fill in all fields.','error');

  const createSpinner = $('create-spinner');
  const createBtnText = $('create-btn-text');
  if (createSpinner) createSpinner.classList.add('show');
  if (createBtnText) createBtnText.textContent = 'Creating…';

  try {
    const data = await api('POST','/sessions',body);
    closeModal('session-modal');
    showCodeAlert(body.subject, data.code);
    if ($('sessions-list')) await loadSessions();
  } catch(e) {
    showAlert(alertTarget, e.message, 'error');
  } finally {
    if (createSpinner) createSpinner.classList.remove('show');
    if (createBtnText) createBtnText.textContent = 'Create Session';
  }
}

function showCodeAlert(subject, code) {
  const list = $('create-result') || $('sessions-list');
  if (!list) return;
  const div = document.createElement('div');
  div.className = 'alert alert-info show';
  div.style.cssText = 'margin-bottom:16px;flex-direction:column;align-items:flex-start;gap:8px';
  div.innerHTML = `
    <strong>Session created for "${subject}"</strong>
    <span>Share this code with students:</span>
    <span style="font-family:var(--mono);font-size:22px;letter-spacing:5px;color:var(--accent)">${code}</span>`;
  list.prepend(div);
  setTimeout(()=>div.remove(), 8000);
}

async function toggleSession(id) {
  try {
    await api('PATCH', `/sessions/${id}/toggle`);
    await loadSessions();
  } catch(e) { alert(e.message); }
}

async function editSessionMax(id) {
  try {
    const data = await api('GET', `/sessions/${id}`);
    const s = data;
    $('edit-session-body').innerHTML = `
      <div id="edit-alert" class="alert alert-error"><span id="edit-msg"></span></div>
      <div class="field-row">
        <div class="field">
          <label>Start Time</label>
          <input type="time" id="edit-start" value="${s.start_time.slice(0,5)}"/>
        </div>
        <div class="field">
          <label>End Time</label>
          <input type="time" id="edit-end" value="${s.end_time.slice(0,5)}"/>
        </div>
      </div>
      <div class="field">
        <label>Max Students (optional)</label>
        <input type="number" id="edit-max" placeholder="Leave empty for unlimited" min="1" value="${s.max_students || ''}"/>
      </div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:16px;">
        <button class="btn btn-ghost" onclick="closeModal('edit-session-modal')">Cancel</button>
        <button class="btn btn-primary" onclick="saveSessionEdit(${id})">
          <span id="edit-btn-text">Save Changes</span>
          <div class="spinner" id="edit-spinner"></div>
        </button>
      </div>`;
    openModal('edit-session-modal');
  } catch(e) {
    alert(e.message);
  }
}

async function saveSessionEdit(id) {
  hideAlert('edit-alert');
  const start_time = $('edit-start').value;
  const end_time = $('edit-end').value;
  const max = $('edit-max').value.trim();
  const max_students = max ? +max : null;
  if (!start_time || !end_time) {
    showAlert('edit-alert', 'Please fill in start and end times.');
    return;
  }
  if (max_students !== null && (isNaN(max_students) || max_students < 1)) {
    showAlert('edit-alert', 'Please enter a valid max students number.');
    return;
  }

  $('edit-spinner').classList.add('show');
  $('edit-btn-text').textContent = 'Saving…';
  try {
    await api('PATCH', `/sessions/${id}/max`, { start_time, end_time, max_students });
    closeModal('edit-session-modal');
    await loadSessions();
    // Also reload records if open
    if ($('records-content')) await renderTeacherRecords($('panel-t-records'));
  } catch(e) {
    showAlert('edit-alert', e.message);
  } finally {
    $('edit-spinner').classList.remove('show');
    $('edit-btn-text').textContent = 'Save Changes';
  }
}

async function viewAttendance(id, subject) {
  $('attend-modal-title').textContent = subject;
  $('attend-modal-body').innerHTML = '<p style="color:var(--muted);padding:8px 0">Loading…</p>';
  openModal('attend-modal');
  try {
    const data = await api('GET', `/sessions/${id}/attendance`);
    const s = data.session;
    const records = data.records;
    $('attend-modal-body').innerHTML = `
      <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px">
        <span class="badge badge-blue">${s.section}</span>
        <span class="badge badge-muted">${fmtDate(s.session_date)}</span>
        <span class="badge badge-muted">${fmtTime(s.start_time)} – ${fmtTime(s.end_time)}</span>
        ${s.max_students ? `<span class="badge badge-muted">Max: ${s.max_students}</span>` : ''}
        ${s.is_open
          ? `<span class="badge badge-green">● Open</span>`
          : `<span class="badge badge-muted">Closed</span>`}
      </div>
      <div style="margin-bottom:16px">
        <span style="font-size:13px;color:var(--muted)">Attendance Code</span><br/>
        <span style="font-family:var(--mono);font-size:20px;letter-spacing:4px;color:var(--accent)">${s.code}</span>
      </div>
      ${records.length === 0
        ? `<div class="empty" style="padding:24px"><div class="empty-icon">🙋</div><p>No students have confirmed attendance yet.</p></div>`
        : `<div class="stat-grid" style="margin-bottom:20px">
            <div class="stat-card"><div class="stat-label">Total Confirmed</div><div class="stat-value">${records.length}</div></div>
          </div>
          <div style="margin-bottom:16px">
            <input type="text" id="attendance-search" placeholder="Search students by name or ID..." style="width:100%;padding:8px;border:1px solid var(--border);border-radius:4px;"/>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Name</th><th>Student ID</th><th>Section</th><th>Time</th><th>Status</th></tr></thead>
              <tbody>
                ${records.map(r=>`
                <tr>
                  <td><strong>${r.full_name}</strong></td>
                  <td style="font-family:var(--mono);font-size:13px">${r.sid||'—'}</td>
                  <td>${r.section||'—'}</td>
                  <td style="font-size:13px;white-space:nowrap">${fmtDateTime(r.confirmed_at)}</td>
                  <td>${r.status==='present'
                    ? `<span class="badge badge-green">Present</span>`
                    : `<span class="badge badge-amber">Late</span>`}
                  </td>
                </tr>`).join('')}
              </tbody>
            </table>
          </div>`}`;
  } catch(e) {
    $('attend-modal-body').innerHTML = `<div class="alert alert-error show">${e.message}</div>`;
  }

  // Add search functionality
  const searchInput = $('attendance-search');
  if (searchInput) {
    searchInput.addEventListener('input', function() {
      const query = this.value.toLowerCase();
      const tbody = this.closest('.table-wrap').querySelector('tbody');
      if (!tbody) return;
      const rows = tbody.querySelectorAll('tr');
      rows.forEach(row => {
        const name = row.cells[0].textContent.toLowerCase();
        const sid = row.cells[1].textContent.toLowerCase();
        if (name.includes(query) || sid.includes(query)) {
          row.style.display = '';
        } else {
          row.style.display = 'none';
        }
      });
    });
  }
}

/* ═══════════════════════════════════════════════════
   TEACHER — RECORDS PANEL (all sessions summary)
═══════════════════════════════════════════════════ */
async function renderTeacherRecords(el) {
  el.innerHTML = `
    <div class="panel-header">
      <div><h1>All Records</h1><p>Overview of all your sessions</p></div>
    </div>
    <div id="records-content"><p style="color:var(--muted)">Loading…</p></div>`;

  try {
    const rows = await api('GET','/sessions');
    const total = rows.length;
    const open  = rows.filter(r=>r.is_open).length;
    $('records-content').innerHTML = `
      <div class="stat-grid">
        <div class="stat-card"><div class="stat-label">Total Sessions</div><div class="stat-value">${total}</div></div>
        <div class="stat-card"><div class="stat-label">Open Now</div><div class="stat-value" style="color:var(--green)">${open}</div></div>
        <div class="stat-card"><div class="stat-label">Closed</div><div class="stat-value">${total-open}</div></div>
      </div>
      ${total ? `
        <div class="table-wrap">
          <table>
            <thead><tr><th>Subject</th><th>Section</th><th>Date</th><th>Code</th><th>Max</th><th>Status</th><th></th></tr></thead>
            <tbody>
              ${rows.map(r=>`
              <tr>
                <td><strong>${r.subject}</strong></td>
                <td>${r.section}</td>
                <td>${fmtDate(r.session_date)}</td>
                <td style="font-family:var(--mono);letter-spacing:2px;color:var(--accent)">${r.code}</td>
                <td>${r.max_students || '—'}</td>
                <td>${r.is_open?`<span class="badge badge-green">Open</span>`:`<span class="badge badge-muted">Closed</span>`}</td>
                <td><div style="display:flex;gap:6px"><button class="btn btn-ghost btn-sm" onclick="viewAttendance(${r.id},'${r.subject}')">View</button><button class="btn btn-ghost btn-sm" onclick="editSessionMax(${r.id})">Edit</button></div></td>
              </tr>`).join('')}
            </tbody>
          </table>
        </div>` : `<div class="empty"><div class="empty-icon">📊</div><p>No records yet.</p></div>`}`;
  } catch(e) {
    $('records-content').innerHTML = `<div class="alert alert-error show">${e.message}</div>`;
  }
}

/* ═══════════════════════════════════════════════════
   STUDENT — CONFIRM ATTENDANCE
═══════════════════════════════════════════════════ */
function renderStudentConfirm(el) {
  el.innerHTML = `
    <div class="panel-header">
      <div><h1>Confirm Attendance</h1><p>Enter your class session code to mark present</p></div>
    </div>
    <div class="card confirm-box">
      <div id="confirm-alert" class="alert alert-error"><span id="confirm-msg"></span></div>
      <div id="confirm-success" class="alert alert-success"><span id="confirm-success-msg"></span></div>

      <div class="field">
        <label>Session Code</label>
        <input class="code-input-big" type="text" id="att-code"
          placeholder="ATT7X2" maxlength="6"
          oninput="this.value=this.value.toUpperCase()"
          onkeydown="if(event.key==='Enter')submitAttendance()"/>
        <p style="font-size:12px;color:var(--muted);margin-top:6px">Ask your teacher for the 6-character code</p>
      </div>
      <button class="btn btn-primary btn-full" onclick="submitAttendance()" style="margin-top:4px">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3"><polyline points="20 6 9 17 4 12"/></svg>
        <span id="att-btn-text">Confirm Attendance</span>
        <div class="spinner" id="att-spinner"></div>
      </button>
    </div>

    <div style="margin-top:28px">
      <h3 style="font-size:15px;font-weight:600;margin-bottom:14px">Recent Attendance</h3>
      <div id="recent-history"><p style="font-size:14px;color:var(--muted)">Loading…</p></div>
    </div>`;

  loadRecentHistory();
}

async function submitAttendance() {
  hideAlert('confirm-alert');
  const confirmSuccess = $('confirm-success');
  if (confirmSuccess) confirmSuccess.classList.remove('show');

  const attCode = $('att-code');
  const code = attCode ? attCode.value.trim().toUpperCase() : '';
  if (!code || code.length < 6) return showAlert('confirm-alert','Please enter a valid 6-character code.');

  const attSpinner = $('att-spinner');
  const attBtnText = $('att-btn-text');
  if (attSpinner) attSpinner.classList.add('show');
  if (attBtnText) attBtnText.textContent = 'Confirming…';
  try {
    const data = await api('POST','/attendance/confirm',{code});
    $('att-code').value = '';
    const msg = `Attendance confirmed for ${data.subject}! Status: ${data.status === 'late' ? '⚠️ Late' : '✅ Present'}`;
    $('confirm-success-msg').textContent = msg;
    $('confirm-success').classList.add('show');
    loadRecentHistory();
  } catch(e) {
    showAlert('confirm-alert', e.message);
  } finally {
    if (attSpinner) attSpinner.classList.remove('show');
    if (attBtnText) attBtnText.textContent = 'Confirm Attendance';
  }
}

async function loadRecentHistory() {
  try {
    const rows = await api('GET','/attendance/my');
    const recent = rows.slice(0,5);
    const el = $('recent-history');
    if (!recent.length) {
      el.innerHTML = `<p style="font-size:14px;color:var(--muted)">No attendance records yet.</p>`;
      return;
    }
    el.innerHTML = `
      <div class="table-wrap">
        <table>
          <thead><tr><th>Subject</th><th>Date</th><th>Confirmed At</th><th>Status</th></tr></thead>
          <tbody>
            ${recent.map(r=>`
            <tr>
              <td><strong>${r.subject}</strong></td>
              <td>${fmtDate(r.session_date)}</td>
              <td style="font-size:13px">${fmtDateTime(r.confirmed_at)}</td>
              <td>${r.status==='present'
                ? `<span class="badge badge-green">Present</span>`
                : `<span class="badge badge-amber">Late</span>`}
              </td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>`;
  } catch(e) {}
}

/* ═══════════════════════════════════════════════════
   STUDENT — FULL HISTORY
═══════════════════════════════════════════════════ */
async function renderStudentHistory(el) {
  el.innerHTML = `
    <div class="panel-header">
      <div><h1>My Attendance</h1><p>Your complete attendance history</p></div>
    </div>
    <div id="history-content"><p style="color:var(--muted)">Loading…</p></div>`;

  try {
    const rows = await api('GET','/attendance/my');
    const present = rows.filter(r=>r.status==='present').length;
    const late    = rows.filter(r=>r.status==='late').length;

    $('history-content').innerHTML = `
      <div class="stat-grid">
        <div class="stat-card"><div class="stat-label">Total</div><div class="stat-value">${rows.length}</div></div>
        <div class="stat-card"><div class="stat-label">Present</div><div class="stat-value" style="color:var(--green)">${present}</div></div>
        <div class="stat-card"><div class="stat-label">Late</div><div class="stat-value" style="color:var(--amber)">${late}</div></div>
      </div>
      ${rows.length ? `
        <div class="table-wrap">
          <table>
            <thead><tr><th>Subject</th><th>Section</th><th>Date</th><th>Time</th><th>Confirmed At</th><th>Status</th></tr></thead>
            <tbody>
              ${rows.map(r=>`
              <tr>
                <td><strong>${r.subject}</strong></td>
                <td>${r.section}</td>
                <td>${fmtDate(r.session_date)}</td>
                <td style="white-space:nowrap">${fmtTime(r.start_time)}</td>
                <td style="font-size:13px;white-space:nowrap">${fmtDateTime(r.confirmed_at)}</td>
                <td>${r.status==='present'
                  ? `<span class="badge badge-green">Present</span>`
                  : `<span class="badge badge-amber">Late</span>`}
                </td>
              </tr>`).join('')}
            </tbody>
          </table>
        </div>` : `<div class="empty"><div class="empty-icon">📅</div><p>No attendance records yet.</p></div>`}`;
  } catch(e) {
    $('history-content').innerHTML = `<div class="alert alert-error show">${e.message}</div>`;
  }
}

/* ═══════════════════════════════════════════════════
   SVG ICONS
═══════════════════════════════════════════════════ */
function plusIcon() {
  return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>`;
}
function calIcon() {
  return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`;
}
function listIcon() {
  return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>`;
}
function checkIcon() {
  return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`;
}

/* ═══════════════════════════════════════════════════
   THEME TOGGLE
═══════════════════════════════════════════════════ */
function toggleTheme() {
  const body = document.body;
  const isDark = body.classList.toggle('dark');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
  updateThemeIcon();
}

function updateThemeIcon() {
  const toggle = $('theme-toggle');
  if (toggle) {
    toggle.textContent = document.body.classList.contains('dark') ? '☀️' : '🌙';
  }
}

// Apply saved theme on load
const savedTheme = localStorage.getItem('theme');
if (savedTheme === 'dark') {
  document.body.classList.add('dark');
}
updateThemeIcon();

/* ═══════════════════════════════════════════════════
   INIT — auto-login if token exists
═══════════════════════════════════════════════════ */
if (token && user && document.getElementById('app-page')) {
  launchApp();
}