/**
 * API Service
 * Centralized API calls to follow DRY principle
 */

/**
 * API Result Cache with TTL
 * Reduces repeated requests by caching responses
 */
const apiCache = {
    data: {},
    ttl: 5 * 60 * 1000,  // 5 minutes cache

    set(key, value) {
        this.data[key] = {
            value,
            timestamp: Date.now()
        };
    },

    get(key) {
        const cached = this.data[key];
        if (!cached) return null;

        const age = Date.now() - cached.timestamp;
        if (age > this.ttl) {
            delete this.data[key];
            return null;
        }

        return cached.value;
    },

    clear() {
        this.data = {};
    }
};

/**
 * Generic fetch wrapper with error handling and caching
 * @param {string} endpoint - API endpoint (relative path)
 * @param {object} options - Fetch options
 * @returns {Promise} Response data
 */
async function apiCall(endpoint, options = {}) {
    const url = `${DASHBOARD_CONFIG.API_BASE}${endpoint}`;
    const cacheKey = `${endpoint}`;

    // Check cache for GET requests (default)
    if (!options.method || options.method === 'GET') {
        const cached = apiCache.get(cacheKey);
        if (cached) {
            console.log(`[CACHE HIT] ${endpoint}`);
            return cached;
        }
    }

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json'
        }
    };

    try {
        console.log(`[CACHE MISS] ${endpoint}`);
        const response = await fetch(url, { ...defaultOptions, ...options });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();

        // Cache successful GET responses
        if (!options.method || options.method === 'GET') {
            apiCache.set(cacheKey, data);
        }

        return data;
    } catch (error) {
        console.error(`API Call Failed: ${url}`, error);
        throw error;
    }
}

/**
 * Fetch live trading data
 * @returns {Promise} Live data object
 */
async function fetchLiveData() {
    return apiCall('/live-data');
}

/**
 * Fetch backtest results
 * @returns {Promise} Backtest results object
 */
async function fetchBacktestResults() {
    return apiCall('/results');
}

/**
 * Fetch optimal parameters
 * @returns {Promise} Optimal parameters object
 */
async function fetchOptimalParameters() {
    return apiCall('/optimal-parameters');
}

/**
 * Fetch strategy comparison for given timeframe
 * @param {number} timeframe - Timeframe in minutes
 * @returns {Promise} Strategy comparison data
 */
async function fetchStrategyComparison(timeframe) {
    return apiCall(`/comparison/strategies/${timeframe}`);
}

/**
 * Fetch pair comparison for given timeframe
 * @param {number} timeframe - Timeframe in minutes
 * @returns {Promise} Pair comparison data
 */
async function fetchPairComparison(timeframe) {
    return apiCall(`/comparison/pairs/${timeframe}`);
}

/**
 * Fetch performance matrix for given timeframe
 * @param {number} timeframe - Timeframe in minutes
 * @returns {Promise} Performance matrix data
 */
async function fetchPerformanceMatrix(timeframe) {
    return apiCall(`/comparison/matrix/${timeframe}`);
}

/**
 * Fetch both results and parameters in parallel
 * @returns {Promise} Object with both results and parameters
 */
async function fetchBacktestData() {
    try {
        const [resultsData, paramsData] = await Promise.allSettled([
            fetchBacktestResults(),
            fetchOptimalParameters()
        ]);

        return {
            results: resultsData.status === 'fulfilled' ? resultsData.value : { results: [] },
            params: paramsData.status === 'fulfilled' ? paramsData.value : {}
        };
    } catch (error) {
        console.error('Error fetching backtest data:', error);
        throw error;
    }
}
