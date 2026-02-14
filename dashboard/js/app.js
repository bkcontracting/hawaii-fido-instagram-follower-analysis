/* app.js — Tab switching, Firebase Auth, dashboard initialization */

// ── Firebase Configuration ────────────────────────────────────
// TODO: Replace with your Firebase project config from Firebase Console
// 1. Go to https://console.firebase.google.com/
// 2. Create a new project (or use existing)
// 3. Go to Project Settings > General > Your apps > Add web app
// 4. Copy the firebaseConfig object here
// 5. Go to Authentication > Sign-in method > Enable Google
// 6. Uncomment the Firebase script tags in index.html
const FIREBASE_CONFIG = {
  apiKey: '',
  authDomain: '',
  projectId: '',
  storageBucket: '',
  messagingSenderId: '',
  appId: '',
};

// Add authorized board member email addresses here
const ALLOWED_EMAILS = [
  // 'boardmember1@gmail.com',
  // 'boardmember2@gmail.com',
];

// Set to true for local development (bypasses auth)
const DEV_MODE = true;

// ── Auth ──────────────────────────────────────────────────────

function initAuth() {
  const loginScreen = document.getElementById('login-screen');
  const dashboard = document.getElementById('dashboard');
  const loginBtn = document.getElementById('login-btn');
  const loginError = document.getElementById('login-error');
  const logoutBtn = document.getElementById('logout-btn');
  const userEmailEl = document.getElementById('user-email');

  if (DEV_MODE || typeof firebase === 'undefined') {
    loginScreen.style.display = 'none';
    dashboard.hidden = false;
    userEmailEl.textContent = 'Dev Mode';
    initDashboard();
    return;
  }

  firebase.initializeApp(FIREBASE_CONFIG);
  const auth = firebase.auth();
  const provider = new firebase.auth.GoogleAuthProvider();

  function showDashboard(user) {
    loginScreen.style.display = 'none';
    dashboard.hidden = false;
    userEmailEl.textContent = user.email;
    initDashboard();
  }

  function showLogin(message) {
    loginScreen.style.display = 'flex';
    dashboard.hidden = true;
    if (message) {
      loginError.textContent = message;
      loginError.hidden = false;
    }
  }

  auth.onAuthStateChanged(user => {
    if (user) {
      if (ALLOWED_EMAILS.length === 0 || ALLOWED_EMAILS.includes(user.email)) {
        showDashboard(user);
      } else {
        loginError.textContent = 'Access denied. Your account is not authorized. Contact the administrator.';
        loginError.hidden = false;
        auth.signOut();
      }
    } else {
      showLogin();
    }
  });

  loginBtn.addEventListener('click', () => {
    loginError.hidden = true;
    auth.signInWithPopup(provider).catch(err => {
      showLogin('Sign-in failed: ' + err.message);
    });
  });

  logoutBtn.addEventListener('click', () => {
    auth.signOut();
  });
}

// ── Tab Switching ─────────────────────────────────────────────

let tabInitialized = {};

function initTabs() {
  const tabs = document.querySelectorAll('.tab');
  const contents = document.querySelectorAll('.tab-content');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;
      tabs.forEach(t => t.classList.remove('active'));
      contents.forEach(c => c.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById('tab-' + target).classList.add('active');

      // Lazy-init tab content
      if (!tabInitialized[target]) {
        initTabContent(target);
        tabInitialized[target] = true;
      }
    });
  });
}

// ── Dashboard Init ────────────────────────────────────────────

function initDashboard() {
  const data = DASHBOARD_DATA;

  // Export date in footer
  const exportDate = document.getElementById('export-date');
  if (data.summary.exportedAt) {
    const d = new Date(data.summary.exportedAt);
    exportDate.textContent = '| Data exported ' + d.toLocaleDateString('en-US', {
      year: 'numeric', month: 'long', day: 'numeric',
    });
  }

  // Init tabs
  initTabs();

  // Render overview (always visible first)
  renderOverview(data);
  tabInitialized['overview'] = true;
}

function initTabContent(tabName) {
  const data = DASHBOARD_DATA;
  switch (tabName) {
    case 'prospects':
      Charts.renderProspectsChart(data.fundraisingProspects);
      Tables.renderProspectsTable(
        document.getElementById('prospects-table-container'),
        data.fundraisingProspects
      );
      break;
    case 'partners':
      Charts.renderPartnersChart(data.marketingPartners);
      Tables.renderPartnersTable(
        document.getElementById('partners-table-container'),
        data.marketingPartners
      );
      break;
    case 'followers':
      Tables.renderFollowersTable(
        document.getElementById('followers-table-container'),
        document.getElementById('pagination'),
        document.getElementById('results-count'),
        data.allFollowers
      );
      break;
  }
}

// ── Overview Tab ──────────────────────────────────────────────

function renderOverview(data) {
  const s = data.summary;
  const t1 = s.tierBreakdown['Tier 1 - High Priority'] || 0;
  const t2 = s.tierBreakdown['Tier 2 - Medium Priority'] || 0;

  const cards = [
    { value: s.totalFollowers, label: 'Total Followers', sub: 'Analyzed accounts' },
    {
      value: s.hawaiiCount,
      label: 'Hawaii-Based',
      sub: ((s.hawaiiCount / s.totalFollowers) * 100).toFixed(1) + '% of total',
    },
    { value: t1 + t2, label: 'High Priority', sub: 'Tier 1 + 2 (Score 60+)' },
    { value: s.fundraisingCount, label: 'Fundraising Prospects', sub: 'AI-analyzed' },
    { value: s.marketingCount, label: 'Marketing Partners', sub: 'Collaboration ready' },
  ];

  const cardsContainer = document.getElementById('stat-cards');
  cardsContainer.innerHTML = cards.map(c =>
    `<div class="stat-card">
      <div class="stat-card-value">${c.value.toLocaleString()}</div>
      <div class="stat-card-label">${c.label}</div>
      <div class="stat-card-sub">${c.sub}</div>
    </div>`
  ).join('');

  // Charts
  let includePersonal = false;
  Charts.renderOverviewCharts(s, includePersonal);

  // Toggle personal accounts
  const toggle = document.getElementById('toggle-personal');
  toggle.addEventListener('change', () => {
    includePersonal = toggle.checked;
    Charts.renderOverviewCharts(s, includePersonal);
  });
}

// ── Boot ──────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', initAuth);
