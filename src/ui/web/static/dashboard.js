/**
 * FX Trading Bot Dashboard - Client-side JavaScript
 * Handles UI interactions, API calls, and dynamic content updates
 */

let selectedSymbol = 'All';
let selectedTimeframe = 'All';
let selectedRow = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function () {
    loadSymbols();
    loadTimeframes();
    loadResults();

    // Event listeners
    document.getElementById('symbol-filter').addEventListener('change', onFilterChange);
    document.getElementById('timeframe-filter').addEventListener('change', onFilterChange);
    document.getElementById('refresh-btn').addEventListener('click', loadResults);
    document.getElementById('equity-btn').addEventListener('click', viewEquityCurves);
    document.getElementById('heatmap-btn').addEventListener('click', viewHeatmap);
    document.getElementById('comparison-btn').addEventListener('click', viewComparisonCharts);
});

/**
 * Load available symbols from API
 */
async function loadSymbols() {
    try {
        const response = await fetch('/api/symbols');
        const data = await response.json();

        if (data.status === 'success') {
            const select = document.getElementById('symbol-filter');
            data.symbols.forEach(symbol => {
                const option = document.createElement('option');
                option.value = symbol;
                option.textContent = symbol;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading symbols:', error);
        showError('Failed to load symbols');
    }
}

/**
 * Load available timeframes from API
 */
async function loadTimeframes() {
    try {
        const response = await fetch('/api/timeframes');
        const data = await response.json();

        if (data.status === 'success') {
            const select = document.getElementById('timeframe-filter');
            data.timeframes.forEach(timeframe => {
                const option = document.createElement('option');
                option.value = timeframe;
                option.textContent = timeframe;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading timeframes:', error);
        showError('Failed to load timeframes');
    }
}

/**
 * Load backtest results from API
 */
async function loadResults() {
    const loading = document.getElementById('loading');
    const errorMsg = document.getElementById('error-message');
    const tbody = document.querySelector('.results-table tbody');

    // Clear previous state
    selectedRow = null;
    updateButtonStates();
    errorMsg.style.display = 'none';
    loading.style.display = 'block';
    tbody.innerHTML = '';

    try {
        selectedSymbol = document.getElementById('symbol-filter').value;
        selectedTimeframe = document.getElementById('timeframe-filter').value;

        const url = `/api/results?symbol=${selectedSymbol}&timeframe=${selectedTimeframe}`;
        const response = await fetch(url);
        const data = await response.json();

        loading.style.display = 'none';

        if (data.status === 'success') {
            if (data.results.length === 0) {
                tbody.innerHTML = '<tr><td colspan="13" style="text-align: center; color: #999;">No results found</td></tr>';
                return;
            }

            data.results.forEach(result => {
                const row = document.createElement('tr');
                row.style.cursor = 'pointer';
                row.innerHTML = `
                    <td>${result.strategy}</td>
                    <td>${result.symbol}</td>
                    <td>${result.timeframe}</td>
                    <td>${result.sharpe_ratio}</td>
                    <td>${result.sortino_ratio}</td>
                    <td>${result.profit_factor}</td>
                    <td>${result.calmar_ratio}</td>
                    <td>${result.ulcer_index}</td>
                    <td>${result.k_ratio}</td>
                    <td>${result.tail_ratio}</td>
                    <td>${result.expectancy}</td>
                    <td>${result.roe}</td>
                    <td>${result.time_to_recover}</td>
                `;

                row.addEventListener('click', function () {
                    if (selectedRow) {
                        selectedRow.style.background = '';
                    }
                    selectedRow = this;
                    this.style.background = '#e3f2fd';
                    updateButtonStates();
                });

                tbody.appendChild(row);
            });
        } else {
            showError(data.message || 'Failed to load results');
        }
    } catch (error) {
        loading.style.display = 'none';
        console.error('Error loading results:', error);
        showError('Error: ' + error.message);
    }
}

/**
 * Handle filter changes
 */
function onFilterChange() {
    loadResults();
}

/**
 * Update button enabled/disabled states
 */
function updateButtonStates() {
    const equityBtn = document.getElementById('equity-btn');
    const heatmapBtn = document.getElementById('heatmap-btn');
    const hasSelection = selectedRow !== null;

    equityBtn.disabled = !hasSelection;
    heatmapBtn.disabled = !hasSelection;
}

/**
 * View equity curves for selected result
 */
async function viewEquityCurves() {
    if (!selectedRow) {
        showError('Please select a backtest result');
        return;
    }

    const cells = selectedRow.querySelectorAll('td');
    const strategy = cells[0].textContent.trim();
    const symbol = cells[1].textContent.trim();

    try {
        const apiUrl = `/api/equity-curve/${symbol}/${strategy}`;
        console.log('Fetching equity curve from:', apiUrl);

        const response = await fetch(apiUrl);

        if (!response.ok) {
            showError(`Failed to fetch equity curve (${response.status}): ${response.statusText}`);
            console.error('API response:', await response.text());
            return;
        }

        const data = await response.json();

        if (data.status === 'success' && data.file) {
            const viewUrl = `/view-equity-curve?symbol=${encodeURIComponent(symbol)}&strategy=${encodeURIComponent(strategy)}`;
            console.log('Opening equity curve:', viewUrl);
            window.open(viewUrl, '_blank');
        } else {
            showError(data.message || 'Equity curve not found for ' + symbol + ' (' + strategy + ')');
        }
    } catch (error) {
        console.error('Error viewing equity curves:', error);
        showError('Error: ' + error.message);
    }
}

/**
 * View heatmap for selected result
 */
async function viewHeatmap() {
    if (!selectedRow) {
        showError('Please select a backtest result');
        return;
    }

    const cells = selectedRow.querySelectorAll('td');
    const symbol = cells[1].textContent.trim();
    const timeframe = cells[2].textContent.trim();

    if (timeframe === 'All') {
        showError('Please select a specific timeframe to view heatmap');
        return;
    }

    try {
        const apiUrl = `/api/heatmap/${symbol}/${timeframe}`;
        console.log('Fetching heatmap from:', apiUrl);

        const response = await fetch(apiUrl);

        if (!response.ok) {
            showError(`Failed to fetch heatmap (${response.status}): ${response.statusText}`);
            console.error('API response:', await response.text());
            return;
        }

        const data = await response.json();

        if (data.status === 'success' && data.file) {
            const viewUrl = `/view-heatmap?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}`;
            console.log('Opening heatmap:', viewUrl);
            window.open(viewUrl, '_blank');
        } else {
            showError(data.message || 'Heatmap not found for ' + symbol + ' (' + timeframe + ')');
        }
    } catch (error) {
        console.error('Error viewing heatmap:', error);
        showError('Error: ' + error.message);
    }
}

/**
 * Show error message
 */
function showError(message) {
    const errorMsg = document.getElementById('error-message');
    errorMsg.textContent = message;
    errorMsg.style.display = 'block';
    console.error('Dashboard error:', message);
}

/**
 * Hide error message
 */
function hideError() {
    document.getElementById('error-message').style.display = 'none';
}

/**
 * View comparison charts for all selected results
 */
async function viewComparisonCharts() {
    const comparisonSection = document.getElementById('comparison-section');

    try {
        selectedSymbol = document.getElementById('symbol-filter').value;
        selectedTimeframe = document.getElementById('timeframe-filter').value;

        const url = `/api/comparison?symbol=${selectedSymbol}&timeframe=${selectedTimeframe}`;
        console.log('Fetching comparison data from:', url);

        const response = await fetch(url);

        if (!response.ok) {
            showError(`Failed to fetch comparison data (${response.status}): ${response.statusText}`);
            console.error('API response:', await response.text());
            return;
        }

        const data = await response.json();

        if (data.status === 'success' && data.comparison && data.comparison.length > 0) {
            console.log('Loaded comparison data:', data.comparison);
            generateComparisonCharts(data.comparison);
            comparisonSection.style.display = 'block';
            // Scroll to comparison section
            comparisonSection.scrollIntoView({ behavior: 'smooth' });
        } else {
            showError('No comparison data available for the selected filters');
            comparisonSection.style.display = 'none';
        }
    } catch (error) {
        console.error('Error viewing comparison charts:', error);
        showError('Error: ' + error.message);
        comparisonSection.style.display = 'none';
    }
}

/**
 * Generate comparison charts using Plotly
 */
function generateComparisonCharts(comparisonData) {
    // Prepare data for charts
    const labels = comparisonData.map(d => `${d.symbol} ${d.timeframe}`);
    const sharpeRatios = comparisonData.map(d => d.sharpe_ratio || 0);
    const totalReturns = comparisonData.map(d => d.total_return_pct || 0);
    const profitFactors = comparisonData.map(d => d.profit_factor || 0);
    const winRates = comparisonData.map(d => d.win_rate_pct || 0);

    // Sharpe Ratio Chart
    const sharpeTrace = {
        x: labels,
        y: sharpeRatios,
        type: 'bar',
        marker: {
            color: sharpeRatios.map(v => v > 0 ? '#2196F3' : '#FF5722')
        }
    };
    Plotly.newPlot('sharpe-chart', [sharpeTrace], {
        title: '',
        xaxis: { title: 'Symbol / Timeframe' },
        yaxis: { title: 'Sharpe Ratio' },
        hovermode: 'x unified',
        responsive: true,
        margin: { b: 100 }
    });

    // Total Return Chart
    const returnTrace = {
        x: labels,
        y: totalReturns,
        type: 'bar',
        marker: {
            color: totalReturns.map(v => v > 0 ? '#4CAF50' : '#F44336')
        }
    };
    Plotly.newPlot('return-chart', [returnTrace], {
        title: '',
        xaxis: { title: 'Symbol / Timeframe' },
        yaxis: { title: 'Return %' },
        hovermode: 'x unified',
        responsive: true,
        margin: { b: 100 }
    });

    // Profit Factor Chart
    const profitTrace = {
        x: labels,
        y: profitFactors,
        type: 'bar',
        marker: {
            color: profitFactors.map(v => v > 1 ? '#9C27B0' : '#FF9800')
        }
    };
    Plotly.newPlot('profit-factor-chart', [profitTrace], {
        title: '',
        xaxis: { title: 'Symbol / Timeframe' },
        yaxis: { title: 'Profit Factor' },
        hovermode: 'x unified',
        responsive: true,
        margin: { b: 100 }
    });

    // Win Rate Chart
    const winRateTrace = {
        x: labels,
        y: winRates,
        type: 'bar',
        marker: {
            color: winRates.map(v => v > 50 ? '#8BC34A' : '#E91E63')
        }
    };
    Plotly.newPlot('win-rate-chart', [winRateTrace], {
        title: '',
        xaxis: { title: 'Symbol / Timeframe' },
        yaxis: { title: 'Win Rate %' },
        hovermode: 'x unified',
        responsive: true,
        margin: { b: 100 }
    });
}
