/**
 * Tab Navigation Management
 * Handles tab switching and associated data loading
 */

/**
 * Switch to a different tab and load its data
 * @param {string} tabName - Name of the tab to switch to
 */
function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    const selectedTab = document.getElementById(tabName);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }

    // Mark button as active
    const activeBtn = event?.target;
    if (activeBtn) {
        activeBtn.classList.add('active');
    }

    // Load data for the new tab
    loadTabData(tabName);
}

/**
 * Load data for a specific tab
 * @param {string} tabName - Name of the tab
 */
function loadTabData(tabName) {
    switch (tabName) {
        case 'live':
            loadLiveData();
            break;
        case 'backtest':
            loadBacktestData();
            break;
        case 'strategies':
            loadStrategyComparison();
            break;
        case 'pairs':
            loadPairComparison();
            break;
        case 'matrix':
            loadPerformanceMatrix();
            break;
        default:
            console.warn(`Unknown tab: ${tabName}`);
    }
}

/**
 * Get the currently active tab
 * @returns {string|null} Active tab name or null
 */
function getActiveTab() {
    const activeContent = document.querySelector('.tab-content.active');
    return activeContent ? activeContent.id : null;
}

/**
 * Programmatically switch to a tab
 * @param {string} tabName - Tab name to switch to
 */
function switchTabProgrammatic(tabName) {
    const tab = document.getElementById(tabName);
    const btn = document.querySelector(`[onclick="switchTab('${tabName}')"]`);

    if (tab && btn) {
        // Hide all
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));

        // Show selected
        tab.classList.add('active');
        btn.classList.add('active');

        loadTabData(tabName);
    }
}
