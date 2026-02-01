/**
 * Utility Functions
 * Reusable helper functions to follow DRY principle
 */

/**
 * Debounce utility - delays function execution until user stops calling
 * Reduces rapid function calls (e.g., from 1000/sec to 3/sec)
 * @param {function} func - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @returns {function} Debounced function
 */
function debounce(func, delay) {
    let timeoutId;

    return function debounced(...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
            func.apply(this, args);
        }, delay);
    };
}

/**
 * Throttle utility - limits function calls to once per interval
 * Useful for scroll/resize events that fire frequently
 * @param {function} func - Function to throttle
 * @param {number} interval - Minimum interval in milliseconds
 * @returns {function} Throttled function
 */
function throttle(func, interval) {
    let lastCall = 0;

    return function throttled(...args) {
        const now = Date.now();
        if (now - lastCall >= interval) {
            func.apply(this, args);
            lastCall = now;
        }
    };
}

/**
 * Format a number to percentage
 * @param {number} value - The decimal value (0.5 = 50%)
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {string} Formatted percentage with + or - sign
 */
function formatPercent(value, decimals = 2) {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${(value * 100).toFixed(decimals)}%`;
}

/**
 * Format a number to currency
 * @param {number} value - The value to format
 * @param {string} symbol - Currency symbol (default: $)
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {string} Formatted currency
 */
function formatCurrency(value, symbol = '$', decimals = 2) {
    const sign = value >= 0 ? '' : '-';
    return `${sign}${symbol}${Math.abs(value).toFixed(decimals)}`;
}

/**
 * Format a number with fixed decimals
 * @param {number} value - The value to format
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted number
 */
function formatNumber(value, decimals = 2) {
    return (value || 0).toFixed(decimals);
}

/**
 * Format date to readable string
 * @param {string|Date} dateStr - Date string or Date object
 * @returns {string} Formatted date and time
 */
function formatDateTime(dateStr) {
    const date = typeof dateStr === 'string' ? new Date(dateStr) : dateStr;
    return date.toLocaleString();
}

/**
 * Get CSS class based on numeric value
 * @param {number} value - The value to evaluate
 * @param {number} threshold - Threshold for positive/negative (default: 0)
 * @returns {string} CSS class name
 */
function getValueClass(value, threshold = 0) {
    return value >= threshold ? 'highlight-positive' : 'highlight-negative';
}

/**
 * Get status badge HTML
 * @param {string} status - Status type ('active', 'signal', 'closed')
 * @returns {string} HTML string
 */
function getStatusBadge(status) {
    const statusMap = {
        'active': 'status-active',
        'signal': 'status-signal',
        'closed': 'status-closed',
        'executed': 'status-active'
    };
    const statusClass = statusMap[status] || 'status-active';
    return `<span class="status ${statusClass}">${status.toUpperCase()}</span>`;
}

/**
 * Get rank badge HTML
 * @param {number} rank - Rank position (1-based)
 * @returns {string} HTML string
 */
function getRankBadge(rank) {
    return `<span class="rank-badge">${rank}</span>`;
}

/**
 * Get heatmap cell CSS class
 * @param {number} value - Sharpe ratio or performance value
 * @returns {string} CSS class name
 */
function getHeatmapCellClass(value) {
    if (value >= 1) {
        return 'heatmap-good';
    } else if (value < 0) {
        return 'heatmap-poor';
    }
    return 'heatmap-neutral';
}

/**
 * Get color based on value performance
 * @param {number} value - The value to evaluate
 * @param {number} positiveThreshold - Value above which it's considered positive
 * @returns {string} Hex color code
 */
function getValueColor(value, positiveThreshold = 0) {
    if (value > positiveThreshold) {
        return DASHBOARD_CONFIG.COLORS.positive;
    } else if (value < positiveThreshold) {
        return DASHBOARD_CONFIG.COLORS.negative;
    }
    return DASHBOARD_CONFIG.COLORS.neutral;
}

/**
 * Create color array for bar chart
 * @param {array} values - Array of numeric values
 * @param {number} threshold - Threshold for positive/negative color
 * @returns {array} Array of color codes
 */
function createColorArray(values, threshold = 0) {
    return values.map(v => getValueColor(v, threshold));
}

/**
 * Safely access nested object properties
 * @param {object} obj - Object to access
 * @param {string} path - Dot-separated path (e.g., 'data.user.name')
 * @param {*} defaultValue - Default value if path doesn't exist
 * @returns {*} Value at path or defaultValue
 */
function getNestedValue(obj, path, defaultValue = null) {
    return path.split('.').reduce((current, prop) => {
        return current?.[prop] !== undefined ? current[prop] : defaultValue;
    }, obj);
}

/**
 * Show loading state in a container
 * @param {string} elementId - Element ID to show loading in
 */
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '<div class="loading">Loading...</div>';
    }
}

/**
 * Show error message in a container
 * @param {string} elementId - Element ID to show error in
 * @param {string} message - Error message
 */
function showError(elementId, message) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `<div class="empty-state">⚠️ ${message}</div>`;
    }
}

/**
 * Show empty state in a container
 * @param {string} elementId - Element ID to show empty state in
 * @param {string} icon - Emoji icon
 * @param {string} message - Empty state message
 */
function showEmptyState(elementId, icon = '📭', message = 'No data available') {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `<div class="empty-state"><div class="empty-state-icon">${icon}</div><p>${message}</p></div>`;
    }
}
