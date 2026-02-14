/* tables.js — Table rendering, sorting, filtering, expand/collapse, pagination */

const Tables = (() => {
  const ROWS_PER_PAGE = 50;

  function formatNumber(n) {
    if (n == null) return '—';
    return Number(n).toLocaleString();
  }

  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function igLink(handle) {
    if (!handle) return '';
    const clean = handle.replace(/^@/, '');
    return `<a href="https://www.instagram.com/${encodeURIComponent(clean)}/" target="_blank" rel="noopener" class="handle-link">@${escapeHtml(clean)}</a>`;
  }

  function tierBadge(tier) {
    if (!tier) return '';
    const cls = tier.includes('High') ? 'badge-tier1'
      : tier.includes('Medium') ? 'badge-tier2'
      : tier.includes('Low') ? 'badge-tier3'
      : 'badge-tier4';
    const short = tier.replace(' - ', ': ').replace(' Priority', '');
    return `<span class="badge ${cls}">${escapeHtml(short)}</span>`;
  }

  function categoryBadge(cat) {
    if (!cat) return '';
    const label = cat.replace(/_/g, ' ');
    return `<span class="badge badge-category">${escapeHtml(label)}</span>`;
  }

  function outreachBadge(type) {
    if (!type) return '';
    const label = type.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
    return `<span class="badge badge-outreach">${escapeHtml(label)}</span>`;
  }

  function hawaiiIcon(isHawaii) {
    return isHawaii
      ? '<span class="badge-hawaii" title="Hawaii-based">&#10003;</span>'
      : '<span class="badge-not-hawaii">—</span>';
  }

  function scoreBar(financial, donor, dinner, hawaii) {
    const f = financial || 0, d = donor || 0, di = dinner || 0, h = hawaii || 0;
    const total = 100;
    return `<div class="score-bar" title="Financial: ${f}/40, Donor: ${d}/25, Dinner: ${di}/20, Hawaii: ${h}/15">
      <div class="score-bar-segment score-bar-financial" style="width:${(f/total)*100}%"></div>
      <div class="score-bar-segment score-bar-donor" style="width:${(d/total)*100}%"></div>
      <div class="score-bar-segment score-bar-dinner" style="width:${(di/total)*100}%"></div>
      <div class="score-bar-segment score-bar-hawaii-conn" style="width:${(h/total)*100}%"></div>
    </div>`;
  }

  /* ── Prospects Table ─────────────────────────────────────── */

  function renderProspectsTable(container, data) {
    const columns = [
      { key: '_expand', label: '', sortable: false },
      { key: 'Rank', label: 'Rank', sortable: true },
      { key: 'Handle', label: 'Handle', sortable: true },
      { key: 'Display Name', label: 'Name', sortable: true },
      { key: 'Entity Type', label: 'Entity Type', sortable: true },
      { key: 'Total Score', label: 'Score', sortable: true },
      { key: '_scorebar', label: 'Breakdown', sortable: false },
      { key: 'Outreach Type', label: 'Outreach', sortable: true },
      { key: 'Suggested Ask', label: 'Suggested Ask', sortable: false },
    ];

    let sortKey = 'Rank';
    let sortAsc = true;
    const expanded = new Set();

    function sortData() {
      const sorted = [...data];
      sorted.sort((a, b) => {
        let va = a[sortKey], vb = b[sortKey];
        if (typeof va === 'number' && typeof vb === 'number') return sortAsc ? va - vb : vb - va;
        va = (va || '').toString().toLowerCase();
        vb = (vb || '').toString().toLowerCase();
        return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
      });
      return sorted;
    }

    function render() {
      const sorted = sortData();
      let html = '<table class="data-table"><thead><tr>';
      columns.forEach(col => {
        const isSorted = col.key === sortKey;
        const arrow = col.sortable ? `<span class="sort-arrow">${isSorted ? (sortAsc ? '&#9650;' : '&#9660;') : '&#9650;'}</span>` : '';
        html += `<th class="${isSorted ? 'sorted' : ''}" data-key="${col.key}" ${col.sortable ? '' : 'style="cursor:default"'}>${col.label}${arrow}</th>`;
      });
      html += '</tr></thead><tbody>';

      sorted.forEach((row, i) => {
        const handle = row['Handle'] || '';
        const isExpanded = expanded.has(handle);
        html += `<tr class="expandable" data-handle="${escapeHtml(handle)}">`;
        html += `<td><span class="expand-icon ${isExpanded ? 'expanded' : ''}">&#9654;</span></td>`;
        html += `<td>${row['Rank'] || ''}</td>`;
        html += `<td>${igLink(handle)}</td>`;
        html += `<td>${escapeHtml(row['Display Name'])}</td>`;
        html += `<td>${categoryBadge(row['Entity Type'])}</td>`;
        html += `<td><strong>${row['Total Score'] || 0}</strong>/100</td>`;
        html += `<td>${scoreBar(row['Financial Capacity'], row['Donor Access'], row['Dinner Potential'], row['Hawaii Connection'])}</td>`;
        html += `<td>${outreachBadge(row['Outreach Type'])}</td>`;
        html += `<td>${escapeHtml(row['Suggested Ask'])}</td>`;
        html += '</tr>';

        if (isExpanded) {
          html += `<tr class="detail-row"><td colspan="${columns.length}"><div class="detail-content">`;
          html += '<div class="detail-grid">';
          html += '<div class="detail-section"><h4>Score Details</h4>';
          html += `<div class="detail-row-item"><span class="detail-label">Financial</span><span class="detail-value">${row['Financial Capacity'] || 0}/40</span></div>`;
          html += `<div class="detail-row-item"><span class="detail-label">Donor Access</span><span class="detail-value">${row['Donor Access'] || 0}/25</span></div>`;
          html += `<div class="detail-row-item"><span class="detail-label">Dinner</span><span class="detail-value">${row['Dinner Potential'] || 0}/20</span></div>`;
          html += `<div class="detail-row-item"><span class="detail-label">Hawaii</span><span class="detail-value">${row['Hawaii Connection'] || 0}/15</span></div>`;
          html += `<div class="detail-row-item"><span class="detail-label">Hawaii-Based</span><span class="detail-value">${row['Hawaii-Based'] || '—'}</span></div>`;
          if (row['Website']) html += `<div class="detail-row-item"><span class="detail-label">Website</span><span class="detail-value"><a href="${row['Website'].startsWith('http') ? '' : 'https://'}${escapeHtml(row['Website'])}" target="_blank" rel="noopener">${escapeHtml(row['Website'])}</a></span></div>`;
          html += '</div>';
          html += '<div class="detail-section"><h4>Bio</h4>';
          html += `<div class="detail-bio">${escapeHtml(row['Bio'])}</div>`;
          html += '</div>';
          html += '</div></div></td></tr>';
        }
      });
      html += '</tbody></table>';
      container.innerHTML = html;

      // Event listeners
      container.querySelectorAll('th[data-key]').forEach(th => {
        const key = th.dataset.key;
        const col = columns.find(c => c.key === key);
        if (!col || !col.sortable) return;
        th.addEventListener('click', () => {
          if (sortKey === key) { sortAsc = !sortAsc; }
          else { sortKey = key; sortAsc = true; }
          render();
        });
      });

      container.querySelectorAll('tr.expandable').forEach(tr => {
        tr.addEventListener('click', () => {
          const h = tr.dataset.handle;
          if (expanded.has(h)) expanded.delete(h); else expanded.add(h);
          render();
        });
      });
    }

    render();
  }

  /* ── Partners Table ──────────────────────────────────────── */

  function renderPartnersTable(container, data) {
    const columns = [
      { key: '_expand', label: '', sortable: false },
      { key: 'Rank', label: 'Rank', sortable: true },
      { key: 'Handle', label: 'Handle', sortable: true },
      { key: 'Display Name', label: 'Name', sortable: true },
      { key: 'Followers', label: 'Followers', sortable: true },
      { key: 'Entity Type', label: 'Entity Type', sortable: true },
      { key: 'Score', label: 'Score', sortable: true },
      { key: 'Website', label: 'Website', sortable: false },
    ];

    let sortKey = 'Rank';
    let sortAsc = true;
    const expanded = new Set();

    function sortData() {
      const sorted = [...data];
      sorted.sort((a, b) => {
        let va = a[sortKey], vb = b[sortKey];
        if (typeof va === 'number' && typeof vb === 'number') return sortAsc ? va - vb : vb - va;
        va = (va || '').toString().toLowerCase();
        vb = (vb || '').toString().toLowerCase();
        return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
      });
      return sorted;
    }

    function render() {
      const sorted = sortData();
      let html = '<table class="data-table"><thead><tr>';
      columns.forEach(col => {
        const isSorted = col.key === sortKey;
        const arrow = col.sortable ? `<span class="sort-arrow">${isSorted ? (sortAsc ? '&#9650;' : '&#9660;') : '&#9650;'}</span>` : '';
        html += `<th class="${isSorted ? 'sorted' : ''}" data-key="${col.key}" ${col.sortable ? '' : 'style="cursor:default"'}>${col.label}${arrow}</th>`;
      });
      html += '</tr></thead><tbody>';

      sorted.forEach(row => {
        const handle = row['Handle'] || '';
        const isExpanded = expanded.has(handle);
        html += `<tr class="expandable" data-handle="${escapeHtml(handle)}">`;
        html += `<td><span class="expand-icon ${isExpanded ? 'expanded' : ''}">&#9654;</span></td>`;
        html += `<td>${row['Rank'] || ''}</td>`;
        html += `<td>${igLink(handle)}</td>`;
        html += `<td>${escapeHtml(row['Display Name'])}</td>`;
        html += `<td>${formatNumber(row['Followers'])}</td>`;
        html += `<td>${categoryBadge(row['Entity Type'])}</td>`;
        html += `<td><strong>${row['Score'] || 0}</strong></td>`;
        const website = row['Website'];
        html += `<td>${website ? `<a href="${website.startsWith('http') ? '' : 'https://'}${escapeHtml(website)}" target="_blank" rel="noopener">${escapeHtml(website)}</a>` : '—'}</td>`;
        html += '</tr>';

        if (isExpanded) {
          html += `<tr class="detail-row"><td colspan="${columns.length}"><div class="detail-content">`;
          html += '<div class="detail-grid">';
          html += '<div class="detail-section"><h4>Profile</h4>';
          html += `<div class="detail-row-item"><span class="detail-label">Hawaii-Based</span><span class="detail-value">${row['Hawaii-Based'] || '—'}</span></div>`;
          html += `<div class="detail-row-item"><span class="detail-label">Instagram</span><span class="detail-value">${igLink(handle)}</span></div>`;
          html += '</div>';
          html += '<div class="detail-section"><h4>Bio</h4>';
          html += `<div class="detail-bio">${escapeHtml(row['Bio'])}</div>`;
          html += '</div>';
          html += '</div></div></td></tr>';
        }
      });
      html += '</tbody></table>';
      container.innerHTML = html;

      container.querySelectorAll('th[data-key]').forEach(th => {
        const key = th.dataset.key;
        const col = columns.find(c => c.key === key);
        if (!col || !col.sortable) return;
        th.addEventListener('click', () => {
          if (sortKey === key) sortAsc = !sortAsc;
          else { sortKey = key; sortAsc = true; }
          render();
        });
      });

      container.querySelectorAll('tr.expandable').forEach(tr => {
        tr.addEventListener('click', () => {
          const h = tr.dataset.handle;
          if (expanded.has(h)) expanded.delete(h); else expanded.add(h);
          render();
        });
      });
    }

    render();
  }

  /* ── All Followers Table ─────────────────────────────────── */

  function renderFollowersTable(container, paginationContainer, resultsEl, allData) {
    let currentPage = 1;
    let filteredData = [...allData];
    const expanded = new Set();

    const searchInput = document.getElementById('search-input');
    const filterCategory = document.getElementById('filter-category');
    const filterHawaii = document.getElementById('filter-hawaii');
    const filterTier = document.getElementById('filter-tier');
    const sortBy = document.getElementById('sort-by');

    // Populate category dropdown
    const categories = [...new Set(allData.map(f => f.category).filter(Boolean))].sort();
    categories.forEach(cat => {
      const opt = document.createElement('option');
      opt.value = cat;
      opt.textContent = cat.replace(/_/g, ' ');
      filterCategory.appendChild(opt);
    });

    function applyFilters() {
      const search = (searchInput.value || '').toLowerCase();
      const cat = filterCategory.value;
      const hawaii = filterHawaii.value;
      const tier = filterTier.value;

      filteredData = allData.filter(f => {
        if (search) {
          const haystack = [f.handle, f.display_name, f.bio].filter(Boolean).join(' ').toLowerCase();
          if (!haystack.includes(search)) return false;
        }
        if (cat && f.category !== cat) return false;
        if (hawaii === 'true' && !f.is_hawaii) return false;
        if (hawaii === 'false' && f.is_hawaii) return false;
        if (tier && f.tier !== tier) return false;
        return true;
      });

      // Sort
      const [sortField, sortDir] = (sortBy.value || 'priority_score-desc').split('-');
      const asc = sortDir === 'asc';
      filteredData.sort((a, b) => {
        let va = a[sortField], vb = b[sortField];
        if (typeof va === 'number' && typeof vb === 'number') {
          va = va || 0; vb = vb || 0;
          return asc ? va - vb : vb - va;
        }
        va = (va || '').toString().toLowerCase();
        vb = (vb || '').toString().toLowerCase();
        return asc ? va.localeCompare(vb) : vb.localeCompare(va);
      });

      currentPage = 1;
      render();
    }

    function render() {
      const totalPages = Math.max(1, Math.ceil(filteredData.length / ROWS_PER_PAGE));
      if (currentPage > totalPages) currentPage = totalPages;
      const start = (currentPage - 1) * ROWS_PER_PAGE;
      const page = filteredData.slice(start, start + ROWS_PER_PAGE);

      resultsEl.textContent = `Showing ${page.length} of ${filteredData.length} followers (page ${currentPage}/${totalPages})`;

      let html = `<table class="data-table"><thead><tr>
        <th style="cursor:default"></th>
        <th style="cursor:default">Handle</th>
        <th style="cursor:default">Name</th>
        <th style="cursor:default">Category</th>
        <th style="cursor:default">Hawaii</th>
        <th style="cursor:default">Score</th>
        <th style="cursor:default">Followers</th>
        <th style="cursor:default">Status</th>
      </tr></thead><tbody>`;

      page.forEach(f => {
        const handle = f.handle || '';
        const isExpanded = expanded.has(handle);
        html += `<tr class="expandable" data-handle="${escapeHtml(handle)}">`;
        html += `<td><span class="expand-icon ${isExpanded ? 'expanded' : ''}">&#9654;</span></td>`;
        html += `<td>${igLink(handle)}</td>`;
        html += `<td>${escapeHtml(f.display_name)}</td>`;
        html += `<td>${categoryBadge(f.category)}</td>`;
        html += `<td>${hawaiiIcon(f.is_hawaii)}</td>`;
        html += `<td>${tierBadge(f.tier)} <strong>${f.priority_score || 0}</strong></td>`;
        html += `<td>${formatNumber(f.follower_count)}</td>`;
        html += `<td>${escapeHtml(f.status)}</td>`;
        html += '</tr>';

        if (isExpanded) {
          html += '<tr class="detail-row"><td colspan="8"><div class="detail-content">';
          html += '<div class="detail-grid">';

          html += '<div class="detail-section"><h4>Profile</h4>';
          html += `<div class="detail-row-item"><span class="detail-label">Following</span><span class="detail-value">${formatNumber(f.following_count)}</span></div>`;
          html += `<div class="detail-row-item"><span class="detail-label">Posts</span><span class="detail-value">${formatNumber(f.post_count)}</span></div>`;
          html += `<div class="detail-row-item"><span class="detail-label">Verified</span><span class="detail-value">${f.is_verified ? 'Yes' : 'No'}</span></div>`;
          html += `<div class="detail-row-item"><span class="detail-label">Private</span><span class="detail-value">${f.is_private ? 'Yes' : 'No'}</span></div>`;
          html += `<div class="detail-row-item"><span class="detail-label">Business</span><span class="detail-value">${f.is_business ? 'Yes' : 'No'}</span></div>`;
          html += `<div class="detail-row-item"><span class="detail-label">Subcategory</span><span class="detail-value">${escapeHtml(f.subcategory) || '—'}</span></div>`;
          html += `<div class="detail-row-item"><span class="detail-label">Location</span><span class="detail-value">${escapeHtml(f.location) || '—'}</span></div>`;
          html += `<div class="detail-row-item"><span class="detail-label">Confidence</span><span class="detail-value">${f.confidence != null ? f.confidence.toFixed(2) : '—'}</span></div>`;
          if (f.website) {
            const url = f.website.startsWith('http') ? f.website : 'https://' + f.website;
            html += `<div class="detail-row-item"><span class="detail-label">Website</span><span class="detail-value"><a href="${escapeHtml(url)}" target="_blank" rel="noopener">${escapeHtml(f.website)}</a></span></div>`;
          }
          html += '</div>';

          html += '<div class="detail-section"><h4>Scoring</h4>';
          html += `<div class="detail-row-item"><span class="detail-label">Score</span><span class="detail-value">${f.priority_score || 0}/100</span></div>`;
          html += `<div class="detail-row-item"><span class="detail-label">Tier</span><span class="detail-value">${tierBadge(f.tier)}</span></div>`;
          html += `<div class="detail-row-item"><span class="detail-label">Reason</span><span class="detail-value">${escapeHtml(f.priority_reason) || '—'}</span></div>`;
          if (f.processed_at) html += `<div class="detail-row-item"><span class="detail-label">Processed</span><span class="detail-value">${escapeHtml(f.processed_at)}</span></div>`;
          html += '</div>';

          html += '<div class="detail-section"><h4>Bio</h4>';
          html += `<div class="detail-bio">${escapeHtml(f.bio) || 'No bio available'}</div>`;
          html += '</div>';

          html += '</div></div></td></tr>';
        }
      });

      html += '</tbody></table>';
      container.innerHTML = html;

      // Pagination
      let pagHtml = '';
      if (totalPages > 1) {
        pagHtml += `<button class="page-btn" ${currentPage === 1 ? 'disabled' : ''} data-page="${currentPage - 1}">&laquo; Prev</button>`;
        const maxVisible = 7;
        let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
        let endPage = Math.min(totalPages, startPage + maxVisible - 1);
        if (endPage - startPage < maxVisible - 1) startPage = Math.max(1, endPage - maxVisible + 1);

        if (startPage > 1) {
          pagHtml += `<button class="page-btn" data-page="1">1</button>`;
          if (startPage > 2) pagHtml += `<span style="padding:0.4rem;color:var(--ash)">...</span>`;
        }
        for (let p = startPage; p <= endPage; p++) {
          pagHtml += `<button class="page-btn ${p === currentPage ? 'active' : ''}" data-page="${p}">${p}</button>`;
        }
        if (endPage < totalPages) {
          if (endPage < totalPages - 1) pagHtml += `<span style="padding:0.4rem;color:var(--ash)">...</span>`;
          pagHtml += `<button class="page-btn" data-page="${totalPages}">${totalPages}</button>`;
        }
        pagHtml += `<button class="page-btn" ${currentPage === totalPages ? 'disabled' : ''} data-page="${currentPage + 1}">Next &raquo;</button>`;
      }
      paginationContainer.innerHTML = pagHtml;

      // Expand listeners
      container.querySelectorAll('tr.expandable').forEach(tr => {
        tr.addEventListener('click', () => {
          const h = tr.dataset.handle;
          if (expanded.has(h)) expanded.delete(h); else expanded.add(h);
          render();
        });
      });

      // Pagination listeners
      paginationContainer.querySelectorAll('.page-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          if (btn.disabled) return;
          currentPage = parseInt(btn.dataset.page);
          render();
          container.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
      });
    }

    // Debounced search
    let searchTimeout;
    searchInput.addEventListener('input', () => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(applyFilters, 300);
    });
    filterCategory.addEventListener('change', applyFilters);
    filterHawaii.addEventListener('change', applyFilters);
    filterTier.addEventListener('change', applyFilters);
    sortBy.addEventListener('change', applyFilters);

    applyFilters();
  }

  return { renderProspectsTable, renderPartnersTable, renderFollowersTable };
})();
