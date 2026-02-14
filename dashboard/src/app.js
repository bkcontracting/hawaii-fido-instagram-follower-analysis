/**
 * Hawaii Fi-Do Dashboard Application
 *
 * Main application logic for the follower analysis dashboard.
 * Handles tab navigation, table rendering, search, filters, sorting, and modal views.
 */

class Dashboard {
    constructor() {
        // Ensure data is loaded
        if (typeof DASHBOARD_CONFIG === 'undefined' || typeof DASHBOARD_DATA === 'undefined') {
            console.error('Dashboard data not loaded!');
            document.body.innerHTML = '<div style="padding: 2rem; text-align: center;"><h2>Error: Dashboard data not found</h2><p>Please rebuild the dashboard.</p></div>';
            return;
        }

        // State
        this.config = DASHBOARD_CONFIG;
        this.data = DASHBOARD_DATA;
        this.currentTab = this.config.tabs[0].id;
        this.currentPage = 1;
        this.recordsPerPage = this.config.features.recordsPerPage || 25;
        this.filters = {
            search: '',
            category: '',
            entity: '',
            hawaiiOnly: false
        };
        this.sorting = {
            column: null,
            direction: 'asc'
        };
        this.currentDetailIndex = -1;

        // Initialize
        this.init();
    }

    init() {
        console.log('Initializing dashboard...', this.config.dashboardTitle);
        this.renderTabNavigation();
        this.attachEventListeners();
        this.switchTab(this.currentTab);
    }

    /**
     * Render tab navigation buttons
     */
    renderTabNavigation() {
        const navContainer = document.getElementById('tab-nav-buttons');
        const buttons = this.config.tabs.map(tab => `
            <button
                class="tab-btn ${tab.id === this.currentTab ? 'active' : ''}"
                data-tab="${tab.id}">
                ${tab.label}
            </button>
        `).join('');
        navContainer.innerHTML = buttons;
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Tab navigation
        document.getElementById('tab-nav-buttons').addEventListener('click', (e) => {
            if (e.target.classList.contains('tab-btn')) {
                this.switchTab(e.target.dataset.tab);
            }
        });

        // Search
        const searchInput = document.getElementById('search-input');
        searchInput.addEventListener('input', (e) => {
            this.filters.search = e.target.value;
            this.currentPage = 1;
            this.renderCurrentTab();
            this.toggleClearButton();
        });

        document.getElementById('clear-search').addEventListener('click', () => {
            searchInput.value = '';
            this.filters.search = '';
            this.currentPage = 1;
            this.renderCurrentTab();
            this.toggleClearButton();
        });

        // Filters
        document.getElementById('filter-category').addEventListener('change', (e) => {
            this.filters.category = e.target.value;
            this.currentPage = 1;
            this.renderCurrentTab();
        });

        document.getElementById('filter-entity').addEventListener('change', (e) => {
            this.filters.entity = e.target.value;
            this.currentPage = 1;
            this.renderCurrentTab();
        });

        document.getElementById('filter-hawaii').addEventListener('change', (e) => {
            this.filters.hawaiiOnly = e.target.checked;
            this.currentPage = 1;
            this.renderCurrentTab();
        });

        // Modal
        document.getElementById('modal-close').addEventListener('click', () => this.closeModal());
        document.querySelector('.modal-overlay').addEventListener('click', () => this.closeModal());
        document.getElementById('modal-prev').addEventListener('click', () => this.navigateDetail(-1));
        document.getElementById('modal-next').addEventListener('click', () => this.navigateDetail(1));

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            const modal = document.getElementById('detail-modal');
            if (modal.classList.contains('show')) {
                if (e.key === 'Escape') {
                    this.closeModal();
                } else if (e.key === 'ArrowLeft') {
                    this.navigateDetail(-1);
                } else if (e.key === 'ArrowRight') {
                    this.navigateDetail(1);
                }
            }
        });
    }

    /**
     * Toggle clear button visibility
     */
    toggleClearButton() {
        const btn = document.getElementById('clear-search');
        const searchInput = document.getElementById('search-input');
        btn.classList.toggle('visible', searchInput.value.length > 0);
    }

    /**
     * Switch to a different tab
     */
    switchTab(tabId) {
        this.currentTab = tabId;
        this.currentPage = 1;
        this.filters = { search: '', category: '', entity: '', hawaiiOnly: false };

        // Reset UI
        document.getElementById('search-input').value = '';
        this.toggleClearButton();

        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabId);
        });

        // Set default sorting from config
        const tabConfig = this.getTabConfig();
        if (tabConfig.defaultSort) {
            this.sorting.column = tabConfig.defaultSort.column;
            this.sorting.direction = tabConfig.defaultSort.direction;
        }

        this.renderCurrentTab();
    }

    /**
     * Get current tab configuration
     */
    getTabConfig() {
        return this.config.tabs.find(t => t.id === this.currentTab);
    }

    /**
     * Get current tab data
     */
    getTabData() {
        return this.data[this.currentTab] || [];
    }

    /**
     * Render current tab
     */
    renderCurrentTab() {
        const tabConfig = this.getTabConfig();
        const tabData = this.getTabData();

        // Update description
        document.getElementById('tab-description').textContent = tabConfig.description;

        // Update filter options
        this.updateFilterOptions(tabData, tabConfig);

        // Filter data
        const filteredData = this.filterData(tabData, tabConfig);

        // Sort data
        const sortedData = this.sortData(filteredData);

        // Paginate
        const paginatedData = this.paginateData(sortedData);

        // Render table
        this.renderTable(paginatedData, sortedData.length, tabConfig);

        // Render pagination
        this.renderPagination(sortedData.length);

        // Update record count
        document.getElementById('record-count').textContent =
            `${sortedData.length} of ${tabData.length} records`;
    }

    /**
     * Update filter dropdowns with unique values from data
     */
    updateFilterOptions(data, config) {
        // Category filter
        const categories = [...new Set(data.map(row => row.Category).filter(Boolean))].sort();
        const categorySelect = document.getElementById('filter-category');
        categorySelect.innerHTML = '<option value="">All Categories</option>' +
            categories.map(cat => `<option value="${cat}">${cat}</option>`).join('');
        categorySelect.value = this.filters.category;

        // Entity type filter
        const entities = [...new Set(data.map(row => row['Entity Type']).filter(Boolean))].sort();
        const entitySelect = document.getElementById('filter-entity');
        entitySelect.innerHTML = '<option value="">All Entity Types</option>' +
            entities.map(ent => `<option value="${ent}">${ent}</option>`).join('');
        entitySelect.value = this.filters.entity;

        // Hawaii checkbox
        document.getElementById('filter-hawaii').checked = this.filters.hawaiiOnly;
    }

    /**
     * Filter data based on current filters
     */
    filterData(data, config) {
        return data.filter(row => {
            // Search filter
            if (this.filters.search) {
                const searchText = config.columns.searchable
                    .map(col => row[col] || '')
                    .join(' ')
                    .toLowerCase();
                if (!searchText.includes(this.filters.search.toLowerCase())) {
                    return false;
                }
            }

            // Category filter
            if (this.filters.category && row.Category !== this.filters.category) {
                return false;
            }

            // Entity filter
            if (this.filters.entity && row['Entity Type'] !== this.filters.entity) {
                return false;
            }

            // Hawaii filter
            if (this.filters.hawaiiOnly && row['Hawaii-Based'] !== 'Yes') {
                return false;
            }

            return true;
        });
    }

    /**
     * Sort data
     */
    sortData(data) {
        if (!this.sorting.column) {
            return data;
        }

        return [...data].sort((a, b) => {
            let aVal = a[this.sorting.column];
            let bVal = b[this.sorting.column];

            // Handle numbers
            const aNum = parseFloat(aVal);
            const bNum = parseFloat(bVal);
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return this.sorting.direction === 'asc' ? aNum - bNum : bNum - aNum;
            }

            // Handle strings
            aVal = String(aVal || '').toLowerCase();
            bVal = String(bVal || '').toLowerCase();

            if (this.sorting.direction === 'asc') {
                return aVal.localeCompare(bVal);
            } else {
                return bVal.localeCompare(aVal);
            }
        });
    }

    /**
     * Paginate data
     */
    paginateData(data) {
        const start = (this.currentPage - 1) * this.recordsPerPage;
        const end = start + this.recordsPerPage;
        return data.slice(start, end);
    }

    /**
     * Render table
     */
    renderTable(data, totalRecords, config) {
        const container = document.getElementById('table-container');

        if (data.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <div class="empty-state-text">No records found</div>
                </div>
            `;
            return;
        }

        const columns = config.columns.display;
        const sortableColumns = config.columns.sortable || [];

        let html = '<table class="data-table"><thead><tr>';

        // Headers
        columns.forEach(col => {
            const isSortable = sortableColumns.includes(col);
            const sortClass = this.sorting.column === col
                ? (this.sorting.direction === 'asc' ? 'sort-asc' : 'sort-desc')
                : '';

            html += `<th class="${isSortable ? 'sortable' : ''} ${sortClass}" data-column="${col}">
                ${col}
            </th>`;
        });

        html += '</tr></thead><tbody>';

        // Rows
        data.forEach((row, index) => {
            html += '<tr data-index="' + index + '">';
            columns.forEach(col => {
                const value = row[col] || '';
                const isNumber = !isNaN(parseFloat(value)) && isFinite(value);
                const isHawaii = col === 'Hawaii-Based';

                let cellContent = this.formatValue(col, value);
                let cellClass = isNumber ? 'number' : '';

                html += `<td class="${cellClass}" data-label="${col}">${cellContent}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table>';
        container.innerHTML = html;

        // Attach row click handlers
        container.querySelectorAll('tbody tr').forEach((tr, index) => {
            tr.addEventListener('click', () => this.showDetailModal(index));
        });

        // Attach header click handlers
        container.querySelectorAll('th.sortable').forEach(th => {
            th.addEventListener('click', () => {
                const column = th.dataset.column;
                if (this.sorting.column === column) {
                    this.sorting.direction = this.sorting.direction === 'asc' ? 'desc' : 'asc';
                } else {
                    this.sorting.column = column;
                    this.sorting.direction = 'asc';
                }
                this.renderCurrentTab();
            });
        });
    }

    /**
     * Format cell value
     */
    formatValue(column, value) {
        if (!value && value !== 0) return '—';

        // Special formatting
        if (column === 'Hawaii-Based') {
            return value === 'Yes'
                ? '<span class="badge badge-success">Yes</span>'
                : '<span class="badge badge-neutral">No</span>';
        }

        if (column === 'Handle') {
            return `<strong>@${value.replace('@', '')}</strong>`;
        }

        if (column === 'Priority Score' || column === 'Total Score') {
            const score = parseInt(value);
            let badgeClass = 'badge-neutral';
            if (score >= 80) badgeClass = 'badge-success';
            else if (score >= 60) badgeClass = 'badge-warning';
            return `<span class="badge ${badgeClass}">${value}</span>`;
        }

        if (column === 'Followers') {
            return parseInt(value).toLocaleString();
        }

        return String(value);
    }

    /**
     * Render pagination
     */
    renderPagination(totalRecords) {
        const container = document.getElementById('pagination');
        const totalPages = Math.ceil(totalRecords / this.recordsPerPage);

        if (totalPages <= 1) {
            container.innerHTML = '';
            return;
        }

        const start = (this.currentPage - 1) * this.recordsPerPage + 1;
        const end = Math.min(this.currentPage * this.recordsPerPage, totalRecords);

        let html = `
            <div class="pagination-info">
                Showing ${start}-${end} of ${totalRecords}
            </div>
            <div class="pagination-buttons">
                <button class="btn-page" ${this.currentPage === 1 ? 'disabled' : ''} data-page="prev">
                    ← Previous
                </button>
        `;

        // Page numbers (show max 5)
        let startPage = Math.max(1, this.currentPage - 2);
        let endPage = Math.min(totalPages, startPage + 4);
        startPage = Math.max(1, endPage - 4);

        for (let i = startPage; i <= endPage; i++) {
            html += `
                <button class="btn-page ${i === this.currentPage ? 'active' : ''}" data-page="${i}">
                    ${i}
                </button>
            `;
        }

        html += `
                <button class="btn-page" ${this.currentPage === totalPages ? 'disabled' : ''} data-page="next">
                    Next →
                </button>
            </div>
        `;

        container.innerHTML = html;

        // Attach handlers
        container.querySelectorAll('.btn-page').forEach(btn => {
            btn.addEventListener('click', () => {
                const page = btn.dataset.page;
                if (page === 'prev') {
                    this.currentPage = Math.max(1, this.currentPage - 1);
                } else if (page === 'next') {
                    this.currentPage = Math.min(totalPages, this.currentPage + 1);
                } else {
                    this.currentPage = parseInt(page);
                }
                this.renderCurrentTab();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
        });
    }

    /**
     * Show detail modal
     */
    showDetailModal(pageIndex) {
        const tabConfig = this.getTabConfig();
        const tabData = this.getTabData();
        const filteredData = this.sortData(this.filterData(tabData, tabConfig));

        const globalIndex = (this.currentPage - 1) * this.recordsPerPage + pageIndex;
        this.currentDetailIndex = globalIndex;

        const row = filteredData[globalIndex];
        if (!row) return;

        const modalBody = document.getElementById('modal-body');
        let html = '<div class="detail-grid">';

        // Display all fields
        Object.entries(row).forEach(([key, value]) => {
            if (!value && value !== 0) return;

            html += `
                <div class="detail-row">
                    <div class="detail-label">${key}</div>
                    <div class="detail-value">${this.formatDetailValue(key, value)}</div>
                </div>
            `;
        });

        html += '</div>';

        // Add Instagram link
        if (row.Handle) {
            const handle = row.Handle.replace('@', '');
            html += `
                <a href="https://instagram.com/${handle}"
                   target="_blank"
                   class="instagram-link">
                    📸 Open Instagram Profile →
                </a>
            `;
        }

        modalBody.innerHTML = html;

        // Update navigation buttons
        document.getElementById('modal-prev').disabled = globalIndex === 0;
        document.getElementById('modal-next').disabled = globalIndex === filteredData.length - 1;

        // Show modal
        document.getElementById('detail-modal').classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    /**
     * Format detail view value
     */
    formatDetailValue(key, value) {
        if (key === 'Website' && value) {
            const url = value.startsWith('http') ? value : `https://${value}`;
            return `<a href="${url}" target="_blank">${value}</a>`;
        }

        if (key === 'Bio') {
            return value.replace(/\n/g, '<br>');
        }

        if (key === 'Followers') {
            return parseInt(value).toLocaleString();
        }

        return value;
    }

    /**
     * Close modal
     */
    closeModal() {
        document.getElementById('detail-modal').classList.remove('show');
        document.body.style.overflow = '';
    }

    /**
     * Navigate detail modal
     */
    navigateDetail(direction) {
        const tabConfig = this.getTabConfig();
        const tabData = this.getTabData();
        const filteredData = this.sortData(this.filterData(tabData, tabConfig));

        const newIndex = this.currentDetailIndex + direction;
        if (newIndex < 0 || newIndex >= filteredData.length) return;

        this.currentDetailIndex = newIndex;

        // Calculate page for this record
        const newPage = Math.floor(newIndex / this.recordsPerPage) + 1;
        if (newPage !== this.currentPage) {
            this.currentPage = newPage;
            this.renderCurrentTab();
        }

        const pageIndex = newIndex % this.recordsPerPage;
        this.showDetailModal(pageIndex);
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM ready, initializing dashboard...');
    window.dashboard = new Dashboard();
});
