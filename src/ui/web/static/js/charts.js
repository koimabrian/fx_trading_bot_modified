/**
 * Chart Functions
 * Plotly chart creation and management (DRY - single source of truth for chart config)
 */

/**
 * Lazy Loading Chart System
 * Load charts only when needed to improve initial page load performance
 */
const lazyCharts = {
    loaded: new Set(),
    pendingData: {},

    /**
     * Register chart data for lazy loading
     * @param {string} chartId - Chart HTML ID
     * @param {object} config - Chart configuration {chartData, layout, title}
     */
    register(chartId, config) {
        this.pendingData[chartId] = config;
    },

    /**
     * Load a chart when needed
     * @param {string} chartId - Chart HTML ID
     */
    load(chartId) {
        if (this.loaded.has(chartId)) {
            console.log(`[ALREADY LOADED] Chart: ${chartId}`);
            return;
        }

        const config = this.pendingData[chartId];
        if (!config) {
            console.warn(`[LAZY LOAD] No config found for chart: ${chartId}`);
            return;
        }

        console.log(`[LAZY LOAD] Loading chart: ${chartId}`);
        Plotly.newPlot(
            chartId,
            config.chartData,
            config.layout,
            DASHBOARD_CONFIG.PLOTLY_CONFIG
        );

        this.loaded.add(chartId);
        delete this.pendingData[chartId];
    },

    /**
     * Load multiple charts at once
     * @param {array} chartIds - Array of chart IDs to load
     */
    loadMultiple(chartIds) {
        chartIds.forEach(id => this.load(id));
    },

    /**
     * Clear all loaded charts
     */
    clearAll() {
        this.loaded.clear();
        this.pendingData = {};
    }
};

/**
 * Setup lazy loading for chart tabs
 * Call this when tabs are initialized
 */
function setupChartLazyLoading() {
    const tabButtons = document.querySelectorAll('[data-chart-tab]');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const chartId = btn.dataset.chartTab;
            lazyCharts.load(chartId);
        });
    });

    console.log('[LAZY LOAD] Chart lazy loading initialized');
}

/**
 * Create a standard bar chart using Plotly
 * @param {string} chartId - HTML element ID to render chart in
 * @param {array} xData - X-axis data (categories)
 * @param {array} yData - Y-axis data (values)
 * @param {string} title - Chart title
 * @param {string} xLabel - X-axis label
 * @param {string} yLabel - Y-axis label
 * @param {array} colors - Optional array of colors for bars
 */
function createBarChart(chartId, xData, yData, title, xLabel, yLabel, colors = null) {
    if (!colors) {
        colors = createColorArray(yData);
    }

    const chartData = [{
        x: xData,
        y: yData,
        type: 'bar',
        marker: { color: colors },
        hovertemplate: '<b>%{x}</b><br>' + yLabel + ': %{y:.3f}<extra></extra>'
    }];

    const layout = {
        title: title,
        xaxis: { title: xLabel },
        yaxis: { title: yLabel },
        margin: { b: 80 },
        plot_bgcolor: '#f8fafc',
        paper_bgcolor: 'white'
    };

    Plotly.newPlot(chartId, chartData, layout, DASHBOARD_CONFIG.PLOTLY_CONFIG);
}

/**
 * Create a standard heatmap using Plotly
 * @param {string} chartId - HTML element ID to render chart in
 * @param {array} zData - 2D array of values
 * @param {array} xData - X-axis labels (columns)
 * @param {array} yData - Y-axis labels (rows)
 * @param {string} title - Chart title
 * @param {string} xLabel - X-axis label
 * @param {string} yLabel - Y-axis label
 */
function createHeatmap(chartId, zData, xData, yData, title, xLabel = 'Strategy', yLabel = 'Pair') {
    const chartData = [{
        z: zData,
        x: xData,
        y: yData,
        type: 'heatmap',
        colorscale: 'RdYlGn',
        hovertemplate: '<b>%{y} × %{x}</b><br>Sharpe: %{z:.3f}<extra></extra>'
    }];

    const layout = {
        title: title,
        xaxis: { title: xLabel },
        yaxis: { title: yLabel },
        plot_bgcolor: '#f8fafc',
        paper_bgcolor: 'white'
    };

    Plotly.newPlot(chartId, chartData, layout, DASHBOARD_CONFIG.PLOTLY_CONFIG);
}

/**
 * Create a line chart using Plotly
 * @param {string} chartId - HTML element ID to render chart in
 * @param {array} xData - X-axis data (dates/time)
 * @param {array} yData - Y-axis data (values)
 * @param {string} title - Chart title
 * @param {string} xLabel - X-axis label
 * @param {string} yLabel - Y-axis label
 * @param {string} color - Line color
 */
function createLineChart(chartId, xData, yData, title, xLabel, yLabel, color = '#667eea') {
    const chartData = [{
        x: xData,
        y: yData,
        type: 'scatter',
        mode: 'lines',
        line: { color: color, width: 2 },
        hovertemplate: '<b>%{x}</b><br>' + yLabel + ': %{y:.2f}<extra></extra>'
    }];

    const layout = {
        title: title,
        xaxis: { title: xLabel },
        yaxis: { title: yLabel },
        plot_bgcolor: '#f8fafc',
        paper_bgcolor: 'white'
    };

    Plotly.newPlot(chartId, chartData, layout, DASHBOARD_CONFIG.PLOTLY_CONFIG);
}

/**
 * Update an existing chart
 * @param {string} chartId - HTML element ID of chart
 * @param {array} xData - New X-axis data
 * @param {array} yData - New Y-axis data
 */
function updateChart(chartId, xData, yData) {
    Plotly.restyle(chartId, { x: [xData], y: [yData] });
}

/**
 * Clear/destroy a chart
 * @param {string} chartId - HTML element ID of chart
 */
function clearChart(chartId) {
    Plotly.purge(chartId);
}
