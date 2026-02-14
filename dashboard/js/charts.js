/* charts.js — Chart.js chart configurations for all tabs */

const Charts = (() => {
  const COLORS = {
    coral: '#D4785C',
    sand: '#D4A574',
    gold: '#C4A35A',
    sage: '#7A9B76',
    ocean: '#3B7A9E',
    slate: '#6B8F9E',
    plum: '#9B8EC4',
    rose: '#D47A8B',
    koa: '#8B6914',
    ash: '#B0A898',
    cream: '#F5EDE0',
    softGray: '#E8E0D5',
  };

  const CATEGORY_COLORS = [
    COLORS.coral, COLORS.sand, COLORS.gold, COLORS.sage,
    COLORS.ocean, COLORS.slate, COLORS.plum, COLORS.rose,
    COLORS.koa, COLORS.ash, '#7ECFC0', '#C49BD4',
    '#D4C47A', '#8B9DC4', '#C47A7A', '#7AC4A8',
  ];

  const TIER_COLORS = {
    'Tier 1 - High Priority': COLORS.coral,
    'Tier 2 - Medium Priority': COLORS.gold,
    'Tier 3 - Low Priority': COLORS.sage,
    'Tier 4 - Skip': COLORS.ash,
  };

  const chartInstances = {};

  function destroyChart(id) {
    if (chartInstances[id]) {
      chartInstances[id].destroy();
      delete chartInstances[id];
    }
  }

  const defaultTooltip = {
    backgroundColor: 'rgba(45,45,45,0.9)',
    titleFont: { family: "'Inter', system-ui", size: 13 },
    bodyFont: { family: "system-ui", size: 12 },
    cornerRadius: 6,
    padding: 10,
  };

  const defaultLegend = {
    labels: {
      font: { family: "'Inter', system-ui", size: 12 },
      padding: 16,
      usePointStyle: true,
      pointStyleWidth: 10,
    },
  };

  /* ── Overview Charts ─────────────────────────────────────── */

  function renderCategoryChart(summary, includePersonal) {
    const canvasId = 'chart-categories';
    destroyChart(canvasId);

    let entries = Object.entries(summary.categoryBreakdown);
    if (!includePersonal) {
      entries = entries.filter(([k]) => k !== 'personal_passive' && k !== 'personal_engaged');
    }
    entries.sort((a, b) => b[1] - a[1]);

    const labels = entries.map(([k]) => k.replace(/_/g, ' '));
    const values = entries.map(([, v]) => v);
    const colors = entries.map((_, i) => CATEGORY_COLORS[i % CATEGORY_COLORS.length]);

    const ctx = document.getElementById(canvasId);
    chartInstances[canvasId] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: colors,
          borderRadius: 4,
          barThickness: 20,
        }],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { ...defaultTooltip },
        },
        scales: {
          x: {
            grid: { color: COLORS.softGray },
            ticks: { font: { family: "system-ui", size: 11 } },
          },
          y: {
            grid: { display: false },
            ticks: {
              font: { family: "'Inter', system-ui", size: 11 },
              callback: function(value) {
                const label = this.getLabelForValue(value);
                return label.length > 20 ? label.substr(0, 18) + '...' : label;
              },
            },
          },
        },
      },
    });
  }

  function renderHawaiiChart(summary) {
    const canvasId = 'chart-hawaii';
    destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);

    chartInstances[canvasId] = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Hawaii-Based', 'Non-Hawaii'],
        datasets: [{
          data: [summary.hawaiiCount, summary.nonHawaiiCount],
          backgroundColor: [COLORS.ocean, COLORS.softGray],
          borderWidth: 2,
          borderColor: '#fff',
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        cutout: '55%',
        plugins: {
          legend: { ...defaultLegend, position: 'bottom' },
          tooltip: {
            ...defaultTooltip,
            callbacks: {
              label: ctx => {
                const total = summary.hawaiiCount + summary.nonHawaiiCount;
                const pct = ((ctx.raw / total) * 100).toFixed(1);
                return ` ${ctx.label}: ${ctx.raw} (${pct}%)`;
              },
            },
          },
        },
      },
    });
  }

  function renderTierChart(summary) {
    const canvasId = 'chart-tiers';
    destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);

    const tiers = summary.tierBreakdown;
    const labels = Object.keys(tiers).map(k => k.replace(' - ', ': ').replace(' Priority', ''));
    const values = Object.values(tiers);
    const colors = Object.keys(tiers).map(k => TIER_COLORS[k] || COLORS.ash);

    chartInstances[canvasId] = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: colors,
          borderWidth: 2,
          borderColor: '#fff',
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        cutout: '55%',
        plugins: {
          legend: { ...defaultLegend, position: 'bottom' },
          tooltip: {
            ...defaultTooltip,
            callbacks: {
              label: ctx => {
                const total = values.reduce((a, b) => a + b, 0);
                const pct = ((ctx.raw / total) * 100).toFixed(1);
                return ` ${ctx.label}: ${ctx.raw} (${pct}%)`;
              },
            },
          },
        },
      },
    });
  }

  function renderReachChart(summary) {
    const canvasId = 'chart-reach';
    destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);

    const order = ['<100', '100-1K', '1K-5K', '5K-10K', '10K-50K', '50K+'];
    const labels = order;
    const values = order.map(k => summary.followerRanges[k] || 0);
    const opacities = [0.3, 0.45, 0.6, 0.7, 0.85, 1.0];
    const colors = opacities.map(o => `rgba(212, 165, 116, ${o})`);

    chartInstances[canvasId] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: colors,
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { ...defaultTooltip },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { family: "'Inter', system-ui", size: 11 } },
          },
          y: {
            grid: { color: COLORS.softGray },
            ticks: { font: { family: "system-ui", size: 11 } },
          },
        },
      },
    });
  }

  function renderOverviewCharts(summary, includePersonal) {
    renderCategoryChart(summary, includePersonal);
    renderHawaiiChart(summary);
    renderTierChart(summary);
    renderReachChart(summary);
  }

  /* ── Prospects Chart ─────────────────────────────────────── */

  function renderProspectsChart(prospects) {
    const canvasId = 'chart-prospects';
    destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);

    const sorted = [...prospects].sort((a, b) => (b['Total Score'] || 0) - (a['Total Score'] || 0));
    const labels = sorted.map(p => p['Display Name'] || p['Handle'] || '');

    chartInstances[canvasId] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Financial Capacity (/40)',
            data: sorted.map(p => p['Financial Capacity'] || 0),
            backgroundColor: COLORS.coral,
          },
          {
            label: 'Donor Access (/25)',
            data: sorted.map(p => p['Donor Access'] || 0),
            backgroundColor: COLORS.ocean,
          },
          {
            label: 'Dinner Potential (/20)',
            data: sorted.map(p => p['Dinner Potential'] || 0),
            backgroundColor: COLORS.gold,
          },
          {
            label: 'Hawaii Connection (/15)',
            data: sorted.map(p => p['Hawaii Connection'] || 0),
            backgroundColor: COLORS.sage,
          },
        ],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { ...defaultLegend, position: 'top' },
          tooltip: {
            ...defaultTooltip,
            mode: 'index',
            intersect: false,
            callbacks: {
              afterBody: items => {
                const total = items.reduce((s, i) => s + i.raw, 0);
                return `\nTotal: ${total}/100`;
              },
            },
          },
        },
        scales: {
          x: {
            stacked: true,
            max: 100,
            grid: { color: COLORS.softGray },
            ticks: { font: { size: 11 } },
          },
          y: {
            stacked: true,
            grid: { display: false },
            ticks: {
              font: { family: "'Inter', system-ui", size: 10 },
              callback: function(value) {
                const label = this.getLabelForValue(value);
                return label.length > 25 ? label.substr(0, 23) + '...' : label;
              },
            },
          },
        },
      },
    });
  }

  /* ── Partners Chart ──────────────────────────────────────── */

  function renderPartnersChart(partners) {
    const canvasId = 'chart-partners';
    destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);

    const sorted = [...partners].sort((a, b) => (b['Score'] || 0) - (a['Score'] || 0));
    const labels = sorted.map(p => p['Display Name'] || p['Handle'] || '');
    const values = sorted.map(p => p['Score'] || 0);

    const entityTypes = [...new Set(sorted.map(p => p['Entity Type']))];
    const entityColorMap = {};
    entityTypes.forEach((t, i) => { entityColorMap[t] = CATEGORY_COLORS[i % CATEGORY_COLORS.length]; });
    const colors = sorted.map(p => entityColorMap[p['Entity Type']] || COLORS.ash);

    chartInstances[canvasId] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: colors,
          borderRadius: 4,
          barThickness: 20,
        }],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            ...defaultTooltip,
            callbacks: {
              afterLabel: ctx => `Entity: ${sorted[ctx.dataIndex]['Entity Type'] || 'unknown'}`,
            },
          },
        },
        scales: {
          x: {
            grid: { color: COLORS.softGray },
            ticks: { font: { size: 11 } },
          },
          y: {
            grid: { display: false },
            ticks: {
              font: { family: "'Inter', system-ui", size: 10 },
              callback: function(value) {
                const label = this.getLabelForValue(value);
                return label.length > 25 ? label.substr(0, 23) + '...' : label;
              },
            },
          },
        },
      },
    });
  }

  return { renderOverviewCharts, renderProspectsChart, renderPartnersChart };
})();
