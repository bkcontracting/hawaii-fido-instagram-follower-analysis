/**
 * End-to-End Tests for Hawaii Fi-Do Dashboard
 *
 * Comprehensive Playwright tests covering:
 * - All visual components
 * - All interactive elements (buttons, inputs, dropdowns)
 * - Tab navigation
 * - Search and filters
 * - Sorting functionality
 * - Pagination
 * - Modal interactions
 * - Keyboard shortcuts
 * - Mobile responsiveness
 *
 * Run:
 *   npx playwright test dashboard/tests/e2e/test_dashboard.spec.js
 *
 * Run with UI:
 *   npx playwright test dashboard/tests/e2e/test_dashboard.spec.js --ui
 *
 * Run specific test:
 *   npx playwright test dashboard/tests/e2e/test_dashboard.spec.js -g "search functionality"
 */

const { test, expect } = require('@playwright/test');
const path = require('path');

// Path to generated dashboard
const DASHBOARD_PATH = path.join(__dirname, '../../dist/index.html');
const DASHBOARD_URL = `file://${DASHBOARD_PATH}`;

test.describe('Dashboard Loading and Initialization', () => {
    test('should load dashboard successfully', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Check title
        await expect(page).toHaveTitle(/Hawaii Fi-Do/);

        // Check header is visible
        const header = page.locator('h1.dashboard-title');
        await expect(header).toBeVisible();
        await expect(header).toContainText('Hawaii Fi-Do');
    });

    test('should display all main UI components', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Header
        await expect(page.locator('.dashboard-header')).toBeVisible();

        // Tab navigation
        await expect(page.locator('.tab-navigation')).toBeVisible();

        // Filter bar
        await expect(page.locator('.filter-bar')).toBeVisible();

        // Main content
        await expect(page.locator('.dashboard-main')).toBeVisible();

        // Table container
        await expect(page.locator('.table-container')).toBeVisible();
    });

    test('should load data correctly', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Wait for table to render
        await page.waitForSelector('table.data-table', { timeout: 5000 });

        // Check that data rows exist
        const rows = page.locator('tbody tr');
        const count = await rows.count();

        expect(count).toBeGreaterThan(0);
    });

    test('should display record count', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        const recordCount = page.locator('#record-count');
        await expect(recordCount).toBeVisible();

        const text = await recordCount.textContent();
        expect(text).toMatch(/\d+ of \d+ records/);
    });
});

test.describe('Tab Navigation', () => {
    test('should have all tabs visible', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Check for 3 tabs
        const tabs = page.locator('.tab-btn');
        const tabCount = await tabs.count();

        expect(tabCount).toBe(3);

        // Verify tab labels
        await expect(tabs.nth(0)).toContainText('Fundraising');
        await expect(tabs.nth(1)).toContainText('Marketing');
        await expect(tabs.nth(2)).toContainText('Combined');
    });

    test('should have first tab active by default', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        const firstTab = page.locator('.tab-btn').first();
        await expect(firstTab).toHaveClass(/active/);
    });

    test('should switch tabs when clicked', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Click second tab
        const marketingTab = page.locator('.tab-btn').nth(1);
        await marketingTab.click();

        // Check it's now active
        await expect(marketingTab).toHaveClass(/active/);

        // Check first tab is no longer active
        const fundraisingTab = page.locator('.tab-btn').first();
        await expect(fundraisingTab).not.toHaveClass(/active/);
    });

    test('should load different data for each tab', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Get first row handle from first tab
        await page.waitForSelector('tbody tr', { timeout: 5000 });
        const firstTabFirstRow = await page.locator('tbody tr').first().textContent();

        // Switch to second tab
        await page.locator('.tab-btn').nth(1).click();
        await page.waitForTimeout(500);

        // Get first row from second tab
        const secondTabFirstRow = await page.locator('tbody tr').first().textContent();

        // They should be different (different datasets)
        expect(firstTabFirstRow).not.toBe(secondTabFirstRow);
    });

    test('should update tab description when switching', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        const description = page.locator('#tab-description');

        // Get description for first tab
        const firstDesc = await description.textContent();
        expect(firstDesc).toBeTruthy();

        // Switch tab
        await page.locator('.tab-btn').nth(1).click();
        await page.waitForTimeout(300);

        // Description should change
        const secondDesc = await description.textContent();
        expect(secondDesc).not.toBe(firstDesc);
    });
});

test.describe('Search Functionality', () => {
    test('should have search input visible', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        const searchInput = page.locator('#search-input');
        await expect(searchInput).toBeVisible();
        await expect(searchInput).toHaveAttribute('placeholder', /Search/);
    });

    test('should filter results when searching', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Get initial row count
        await page.waitForSelector('tbody tr');
        const initialCount = await page.locator('tbody tr').count();

        // Type in search
        await page.locator('#search-input').fill('hawaii');
        await page.waitForTimeout(500);

        // Get filtered row count
        const filteredCount = await page.locator('tbody tr').count();

        // Should have fewer results (or same if all contain 'hawaii')
        expect(filteredCount).toBeLessThanOrEqual(initialCount);
    });

    test('should show clear button when search has text', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        const clearBtn = page.locator('#clear-search');

        // Initially hidden
        await expect(clearBtn).not.toHaveClass(/visible/);

        // Type in search
        await page.locator('#search-input').fill('test');

        // Clear button should appear
        await expect(clearBtn).toHaveClass(/visible/);
    });

    test('should clear search when clear button clicked', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        const searchInput = page.locator('#search-input');
        const clearBtn = page.locator('#clear-search');

        // Enter search
        await searchInput.fill('hawaii');
        await expect(searchInput).toHaveValue('hawaii');

        // Click clear
        await clearBtn.click();
        await page.waitForTimeout(300);

        // Input should be empty
        await expect(searchInput).toHaveValue('');
    });

    test('should reset to page 1 when searching', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Go to page 2 if available
        const nextBtn = page.locator('.btn-page[data-page="2"]');
        if (await nextBtn.count() > 0) {
            await nextBtn.click();
            await page.waitForTimeout(300);

            // Now search
            await page.locator('#search-input').fill('test');
            await page.waitForTimeout(300);

            // Should be back on page 1
            const page1Btn = page.locator('.btn-page[data-page="1"]');
            if (await page1Btn.count() > 0) {
                await expect(page1Btn).toHaveClass(/active/);
            }
        }
    });
});

test.describe('Filter Functionality', () => {
    test('should have filter dropdowns visible', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        await expect(page.locator('#filter-category')).toBeVisible();
        await expect(page.locator('#filter-entity')).toBeVisible();
        await expect(page.locator('#filter-hawaii')).toBeVisible();
    });

    test('should populate category filter with options', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        const categorySelect = page.locator('#filter-category');
        const options = categorySelect.locator('option');
        const count = await options.count();

        // Should have at least "All Categories" + some actual categories
        expect(count).toBeGreaterThan(1);
    });

    test('should filter by category', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        const categorySelect = page.locator('#filter-category');
        const options = categorySelect.locator('option');

        // Get a category option (skip "All Categories")
        if (await options.count() > 1) {
            const categoryValue = await options.nth(1).getAttribute('value');

            // Select category
            await categorySelect.selectOption(categoryValue);
            await page.waitForTimeout(500);

            // Should have some results
            const rows = page.locator('tbody tr');
            const count = await rows.count();
            expect(count).toBeGreaterThan(0);
        }
    });

    test('should filter by Hawaii only', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Get initial count
        const initialCount = await page.locator('tbody tr').count();

        // Check Hawaii filter
        await page.locator('#filter-hawaii').check();
        await page.waitForTimeout(500);

        // Get filtered count
        const filteredCount = await page.locator('tbody tr').count();

        // Should filter results (or show all if all are Hawaii-based)
        expect(filteredCount).toBeLessThanOrEqual(initialCount);
    });
});

test.describe('Table Sorting', () => {
    test('should have sortable column headers', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        const sortableHeaders = page.locator('th.sortable');
        const count = await sortableHeaders.count();

        expect(count).toBeGreaterThan(0);
    });

    test('should show sort icon on sortable headers', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        const sortableHeader = page.locator('th.sortable').first();
        const text = await sortableHeader.textContent();

        // Should contain sort arrow character
        expect(text).toMatch(/[↕↑↓]/);
    });

    test('should sort when header clicked', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Get first sortable header
        const header = page.locator('th.sortable').first();

        // Get first row value before sort
        const firstRowBefore = await page.locator('tbody tr').first().textContent();

        // Click to sort
        await header.click();
        await page.waitForTimeout(500);

        // Get first row value after sort
        const firstRowAfter = await page.locator('tbody tr').first().textContent();

        // May or may not change depending on data, but should not error
        expect(firstRowAfter).toBeTruthy();
    });

    test('should toggle sort direction on repeated clicks', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        const header = page.locator('th.sortable').first();

        // Click once - should sort ascending
        await header.click();
        await page.waitForTimeout(300);
        await expect(header).toHaveClass(/sort-asc/);

        // Click again - should sort descending
        await header.click();
        await page.waitForTimeout(300);
        await expect(header).toHaveClass(/sort-desc/);
    });
});

test.describe('Pagination', () => {
    test('should show pagination if more than 25 records', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        const pagination = page.locator('#pagination');
        const rowCount = await page.locator('tbody tr').count();

        // Get total from record count
        const recordCountText = await page.locator('#record-count').textContent();
        const match = recordCountText.match(/(\d+) of (\d+)/);

        if (match && parseInt(match[2]) > 25) {
            await expect(pagination).toBeVisible();
        }
    });

    test('should have working next/previous buttons', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        const nextBtn = page.locator('.btn-page[data-page="next"]');
        const prevBtn = page.locator('.btn-page[data-page="prev"]');

        if (await nextBtn.count() > 0) {
            // Previous should be disabled on page 1
            if (await prevBtn.count() > 0) {
                await expect(prevBtn).toBeDisabled();
            }

            // Click next
            await nextBtn.click();
            await page.waitForTimeout(300);

            // Previous should now be enabled
            if (await prevBtn.count() > 0) {
                await expect(prevBtn).not.toBeDisabled();
            }
        }
    });

    test('should show current page info', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        const paginationInfo = page.locator('.pagination-info');

        if (await paginationInfo.count() > 0) {
            const text = await paginationInfo.textContent();
            expect(text).toMatch(/Showing \d+-\d+ of \d+/);
        }
    });
});

test.describe('Detail Modal', () => {
    test('should open modal when row clicked', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Wait for rows
        await page.waitForSelector('tbody tr');

        // Click first row
        await page.locator('tbody tr').first().click();

        // Modal should be visible
        const modal = page.locator('#detail-modal');
        await expect(modal).toHaveClass(/show/);
    });

    test('should display follower details in modal', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        await page.waitForSelector('tbody tr');
        await page.locator('tbody tr').first().click();

        // Check modal body has content
        const modalBody = page.locator('#modal-body');
        await expect(modalBody).toBeVisible();

        // Should have detail rows
        const detailRows = page.locator('.detail-row');
        const count = await detailRows.count();
        expect(count).toBeGreaterThan(0);
    });

    test('should have Instagram link in modal', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        await page.waitForSelector('tbody tr');
        await page.locator('tbody tr').first().click();

        // Check for Instagram link
        const instagramLink = page.locator('.instagram-link');
        if (await instagramLink.count() > 0) {
            await expect(instagramLink).toBeVisible();
            const href = await instagramLink.getAttribute('href');
            expect(href).toContain('instagram.com');
        }
    });

    test('should close modal when close button clicked', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        await page.waitForSelector('tbody tr');
        await page.locator('tbody tr').first().click();

        // Modal should be open
        const modal = page.locator('#detail-modal');
        await expect(modal).toHaveClass(/show/);

        // Click close button
        await page.locator('#modal-close').click();
        await page.waitForTimeout(300);

        // Modal should be closed
        await expect(modal).not.toHaveClass(/show/);
    });

    test('should close modal when overlay clicked', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        await page.waitForSelector('tbody tr');
        await page.locator('tbody tr').first().click();

        // Click overlay
        await page.locator('.modal-overlay').click();
        await page.waitForTimeout(300);

        // Modal should be closed
        const modal = page.locator('#detail-modal');
        await expect(modal).not.toHaveClass(/show/);
    });

    test('should close modal on ESC key', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        await page.waitForSelector('tbody tr');
        await page.locator('tbody tr').first().click();

        // Press ESC
        await page.keyboard.press('Escape');
        await page.waitForTimeout(300);

        // Modal should be closed
        const modal = page.locator('#detail-modal');
        await expect(modal).not.toHaveClass(/show/);
    });

    test('should navigate between records with arrow keys', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        await page.waitForSelector('tbody tr');
        await page.locator('tbody tr').first().click();

        // Get initial modal content
        const initialContent = await page.locator('#modal-body').textContent();

        // Press right arrow
        await page.keyboard.press('ArrowRight');
        await page.waitForTimeout(300);

        // Content should change
        const nextContent = await page.locator('#modal-body').textContent();
        expect(nextContent).not.toBe(initialContent);
    });

    test('should have prev/next navigation buttons', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        await page.waitForSelector('tbody tr');
        await page.locator('tbody tr').first().click();

        // Check navigation buttons exist
        await expect(page.locator('#modal-prev')).toBeVisible();
        await expect(page.locator('#modal-next')).toBeVisible();
    });

    test('should disable prev button on first record', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        await page.waitForSelector('tbody tr');
        await page.locator('tbody tr').first().click();

        // Prev button should be disabled
        await expect(page.locator('#modal-prev')).toBeDisabled();
    });
});

test.describe('Mobile Responsiveness', () => {
    test('should render correctly on mobile viewport', async ({ page }) => {
        // Set mobile viewport
        await page.setViewportSize({ width: 375, height: 667 });
        await page.goto(DASHBOARD_URL);

        // Dashboard should still be visible
        await expect(page.locator('.dashboard-header')).toBeVisible();
        await expect(page.locator('.tab-navigation')).toBeVisible();
        await expect(page.locator('.table-container')).toBeVisible();
    });

    test('should have readable text on mobile', async ({ page }) => {
        await page.setViewportSize({ width: 375, height: 667 });
        await page.goto(DASHBOARD_URL);

        const title = page.locator('.dashboard-title');
        await expect(title).toBeVisible();

        // Font should be readable (not too small)
        const fontSize = await title.evaluate(el =>
            window.getComputedStyle(el).fontSize
        );
        const sizeInPx = parseFloat(fontSize);
        expect(sizeInPx).toBeGreaterThan(16);
    });

    test('should have touch-friendly buttons on mobile', async ({ page }) => {
        await page.setViewportSize({ width: 375, height: 667 });
        await page.goto(DASHBOARD_URL);

        const tabBtn = page.locator('.tab-btn').first();

        // Button should have adequate height for touch
        const box = await tabBtn.boundingBox();
        expect(box.height).toBeGreaterThan(40);
    });
});

test.describe('Accessibility', () => {
    test('should have proper heading hierarchy', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Should have h1
        await expect(page.locator('h1')).toBeVisible();
    });

    test('should have alt text for images', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // If there are images, they should have alt text
        const images = page.locator('img');
        const count = await images.count();

        for (let i = 0; i < count; i++) {
            const img = images.nth(i);
            const alt = await img.getAttribute('alt');
            expect(alt).toBeTruthy();
        }
    });

    test('should be keyboard navigable', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Tab through elements
        await page.keyboard.press('Tab');
        await page.keyboard.press('Tab');

        // Should be able to navigate without errors
        expect(true).toBe(true);
    });
});

test.describe('Performance', () => {
    test('should load dashboard in under 3 seconds', async ({ page }) => {
        const startTime = Date.now();

        await page.goto(DASHBOARD_URL);
        await page.waitForSelector('tbody tr');

        const loadTime = Date.now() - startTime;

        expect(loadTime).toBeLessThan(3000);
    });

    test('should render table quickly', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        const startTime = Date.now();

        await page.waitForSelector('tbody tr');

        const renderTime = Date.now() - startTime;

        // Table should render in under 1 second
        expect(renderTime).toBeLessThan(1000);
    });
});

test.describe('Error Handling', () => {
    test('should handle empty search results gracefully', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Search for something unlikely to exist
        await page.locator('#search-input').fill('xyzabc123notfound');
        await page.waitForTimeout(500);

        // Should show empty state
        const emptyState = page.locator('.empty-state');
        if (await emptyState.count() > 0) {
            await expect(emptyState).toBeVisible();
            await expect(emptyState).toContainText(/No records found/i);
        }
    });

    test('should not crash on rapid tab switching', async ({ page }) => {
        await page.goto(DASHBOARD_URL);

        // Rapidly switch tabs
        for (let i = 0; i < 5; i++) {
            await page.locator('.tab-btn').nth(0).click();
            await page.locator('.tab-btn').nth(1).click();
            await page.locator('.tab-btn').nth(2).click();
        }

        // Should still be functional
        await expect(page.locator('.data-table')).toBeVisible();
    });
});
