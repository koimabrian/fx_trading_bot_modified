/**
 * Dashboard Initialization & Auto-refresh
 * Main entry point for the dashboard application
 */

/**
 * Initialize the dashboard on page load
 */
function initDashboard() {
    console.log('Initializing FX Trading Bot Dashboard...');

    // Load initial data
    loadLiveData();

    // Set up auto-refresh
    setupAutoRefresh();

    // Set up event listeners
    setupEventListeners();

    console.log('Dashboard initialized successfully');
}

/**
 * Set up auto-refresh interval
 * Refreshes the currently active tab every N seconds
 */
function setupAutoRefresh() {
    setInterval(() => {
        const activeTab = getActiveTab();
        if (activeTab) {
            loadTabData(activeTab);
        }
    }, DASHBOARD_CONFIG.REFRESH_INTERVAL);
}

/**
 * Set up event listeners for interactive elements
 */
function setupEventListeners() {
    // Timeframe selectors
    const strategyTf = document.getElementById('strategyTimeframe');
    if (strategyTf) {
        strategyTf.addEventListener('change', debounce(loadStrategyComparison, 300));
    }

    const pairTf = document.getElementById('pairTimeframe');
    if (pairTf) {
        pairTf.addEventListener('change', debounce(loadPairComparison, 300));
    }

    const matrixTf = document.getElementById('matrixTimeframe');
    if (matrixTf) {
        matrixTf.addEventListener('change', debounce(loadPerformanceMatrix, 300));
    }

    console.log('Event listeners attached');
}

/**
 * Manual refresh handler for refresh button
 */
function manualRefresh() {
    const activeTab = getActiveTab();
    if (activeTab) {
        loadTabData(activeTab);
    }
}

// ==================== PAGE LOAD ====================
// Initialize dashboard when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
} else {
    initDashboard();
}
