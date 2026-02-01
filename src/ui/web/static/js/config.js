/**
 * Dashboard Configuration
 * Centralized constants and configuration for the dashboard
 */

const DASHBOARD_CONFIG = {
    // API Configuration
    API_BASE: '/api',
    REFRESH_INTERVAL: 10000, // 10 seconds

    // Timeframe Options
    TIMEFRAMES: {
        '15': '15 Min',
        '60': '1 Hour',
        '240': '4 Hours'
    },

    // Default Timeframe
    DEFAULT_TIMEFRAME: 60,

    // Plotly Configuration
    PLOTLY_CONFIG: {
        responsive: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d']
    },

    // Color Scheme
    COLORS: {
        positive: '#10b981',
        negative: '#ef4444',
        neutral: '#667eea',
        warning: '#f59e0b'
    },

    // Chart Heights
    CHART_HEIGHT: 400,
    CHART_HEIGHT_MOBILE: 300,

    // Table Limits
    TABLE_LIMITS: {
        live_signals: 15,
        recent_trades: 15,
        backtest_results: 20,
        strategy_ranking: 10,
        pair_ranking: 10
    }
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DASHBOARD_CONFIG;
}
