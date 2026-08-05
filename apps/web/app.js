/**
 * AEGIS-X Enterprise Cyber-Physical Security Dashboard Logic
 */

const API_BASE = '/api/v1';

// Application State
const state = {
  activeTab: 'dashboard',
  incidents: [],
  cases: [],
  responsePlans: [],
  telemetryStats: null,
  benchmarkResults: null,
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  loadDashboardData();
  initAttackGraphCanvas();
  setInterval(loadDashboardData, 5000); // Live poll every 5s
});

// Setup Navigation Tabs
function setupNavigation() {
  const links = document.querySelectorAll('.nav-link');
  links.forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const targetTab = link.getAttribute('data-tab');
      if (!targetTab) return;

      links.forEach(l => l.classList.remove('active'));
      link.classList.add('active');

      document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));
      const targetSection = document.getElementById(`${targetTab}-view`);
      if (targetSection) targetSection.classList.add('active');

      state.activeTab = targetTab;
      if (targetTab === 'incidents') fetchIncidents();
      if (targetTab === 'cases') fetchCases();
      if (targetTab === 'response') fetchResponsePlans();
      if (targetTab === 'benchmarks') fetchBenchmarks();
    });
  });
}

// Fetch Overview Dashboard Data
async function loadDashboardData() {
  try {
    const res = await fetch(`${API_BASE}/status`);
    if (res.ok) {
      const statusData = await res.json();
      document.getElementById('platform-phase').textContent = statusData.phase;
    }

    const telRes = await fetch(`${API_BASE}/telemetry/health`);
    if (telRes.ok) {
      state.telemetryStats = await telRes.json();
      updateTelemetryUI();
    }

    fetchIncidents();
  } catch (err) {
    console.warn('Backend API connection offline, using fallback state:', err);
  }
}

function updateTelemetryUI() {
  if (!state.telemetryStats) return;
  const storage = state.telemetryStats.storage || {};
  document.getElementById('metric-events').textContent = storage.total_records || '14,820';
  document.getElementById('metric-anomalies').textContent = storage.total_alerts || '42';
}

// Fetch Incidents
async function fetchIncidents() {
  try {
    const res = await fetch(`${API_BASE}/incidents`);
    if (res.ok) {
      const data = await res.json();
      state.incidents = data.incidents || [];
      renderIncidentsTable();
      document.getElementById('metric-incidents').textContent = state.incidents.length;
    }
  } catch (err) {
    console.error('Failed to fetch incidents:', err);
  }
}

function renderIncidentsTable() {
  const tbody = document.getElementById('incidents-tbody');
  if (!tbody) return;

  if (state.incidents.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">No active incidents reported.</td></tr>';
    return;
  }

  tbody.innerHTML = state.incidents.map(inc => `
    <tr>
      <td><span class="badge badge-critical">${inc.incident_id}</span></td>
      <td>${inc.title || 'PLC Operational Anomaly Cluster'}</td>
      <td><span class="badge badge-${inc.risk_score >= 0.8 ? 'critical' : 'high'}">${(inc.risk_score * 100).toFixed(0)}%</span></td>
      <td>${inc.affected_assets ? inc.affected_assets.join(', ') : 'plc-01, hmi-01'}</td>
      <td><span class="badge badge-low">${inc.status}</span></td>
      <td>
        <button class="btn btn-secondary" onclick="viewIncidentDetails('${inc.incident_id}')">Investigate</button>
      </td>
    </tr>
  `).join('');
}

// Fetch Cases
async function fetchCases() {
  try {
    const res = await fetch(`${API_BASE}/cases`);
    if (res.ok) {
      const data = await res.json();
      state.cases = data.cases || [];
      renderCasesTable();
    }
  } catch (err) {
    console.error('Failed to fetch cases:', err);
  }
}

function renderCasesTable() {
  const tbody = document.getElementById('cases-tbody');
  if (!tbody) return;

  if (state.cases.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">No investigation cases created yet.</td></tr>';
    return;
  }

  tbody.innerHTML = state.cases.map(c => `
    <tr>
      <td><span class="badge badge-info">${c.case_id}</span></td>
      <td>${c.title || 'Case Investigation'}</td>
      <td>${c.assigned_analyst || 'soc_lead_01'}</td>
      <td><span class="badge badge-medium">${c.status}</span></td>
      <td>
        <button class="btn btn-primary" onclick="viewCaseDossier('${c.case_id}')">View Dossier</button>
      </td>
    </tr>
  `).join('');
}

// Fetch Response Plans
async function fetchResponsePlans() {
  // Demo plan trigger
  const tbody = document.getElementById('response-tbody');
  if (!tbody) return;

  tbody.innerHTML = `
    <tr>
      <td><span class="badge badge-high">resp-c7a912</span></td>
      <td>ISOLATE_ASSET & SET_SAFE_STATE</td>
      <td>plc-01, pump-01</td>
      <td><span class="badge badge-medium">PENDING APPROVAL</span></td>
      <td>
        <button class="btn btn-primary" onclick="grantApprovalDemo('req-991')">Approve Action</button>
      </td>
    </tr>
  `;
}

function grantApprovalDemo(reqId) {
  alert(`Human Approval Granted for Request ${reqId}! Executing containment playbook...`);
  fetchResponsePlans();
}

// Canvas Attack Graph Visualizer
function initAttackGraphCanvas() {
  const canvas = document.getElementById('attackGraphCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  function resize() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight;
    drawGraph();
  }

  window.addEventListener('resize', resize);
  resize();

  function drawGraph() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const nodes = [
      { id: 'Attacker IP', x: canvas.width * 0.15, y: canvas.height * 0.5, color: '#ef4444' },
      { id: 'HMI Subnet (T0831)', x: canvas.width * 0.45, y: canvas.height * 0.3, color: '#f97316' },
      { id: 'PLC-01 Command Injection', x: canvas.width * 0.45, y: canvas.height * 0.7, color: '#eab308' },
      { id: 'Water Pump Safe Stop', x: canvas.width * 0.80, y: canvas.height * 0.5, color: '#00f0ff' }
    ];

    // Draw Edges
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.4)';
    ctx.lineWidth = 2;

    ctx.beginPath();
    ctx.moveTo(nodes[0].x, nodes[0].y);
    ctx.lineTo(nodes[1].x, nodes[1].y);
    ctx.lineTo(nodes[3].x, nodes[3].y);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(nodes[0].x, nodes[0].y);
    ctx.lineTo(nodes[2].x, nodes[2].y);
    ctx.lineTo(nodes[3].x, nodes[3].y);
    ctx.stroke();

    // Draw Nodes
    nodes.forEach(node => {
      ctx.beginPath();
      ctx.arc(node.x, node.y, 16, 0, Math.PI * 2);
      ctx.fillStyle = node.color;
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.fillStyle = '#f0f4f8';
      ctx.font = '12px JetBrains Mono';
      ctx.fillText(node.id, node.x - 40, node.y + 32);
    });
  }
}

function viewIncidentDetails(id) {
  alert(`Loading grounded AI investigation narrative for incident ${id}...`);
}

function viewCaseDossier(caseId) {
  alert(`Loading unified case dossier and SHA-256 chain-of-custody for case ${caseId}...`);
}
