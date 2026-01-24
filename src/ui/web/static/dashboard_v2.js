/**
 * FX Trading Bot Dashboard v2 - Advanced Analytics
 * Handles data loading, visualization, and interactions
 */

let allResults = [];
let allTradesData = [];
let currentFilters = {
    symbol: '',
    timeframe: '',
    strategy: '',
    dataView: 'backtest'
};

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', function () {
    setEndDate();
    loadSymbols();
    loadData();
});

/**
 * Set today's date as default end date
 */
function setEndDate() {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    document.getElementById('dateEnd').value = `${year}-${month}-${day}`;
}

/**
 * Load available symbols into filter dropdown
 */
function loadSymbols() {
    fetch('/api/symbols')
        .then(res => res.json())
        .then(data => {
            const symbolFilter = document.getElementById('symbolFilter');
            data.symbols?.forEach(symbol => {
                const option = document.createElement('option');
                option.value = symbol;
                option.textContent = symbol;
                symbolFilter.appendChild(option);
            });
        })
        .catch(err => console.error('Error loading symbols:', err));
}

/**
 * Load all dashboard data
 */
function loadData() {
    Promise.all([
        loadResults(),
        loadTrades()
    ]).then(() => {
        updateDashboard();
    }).catch(err => {
        console.error('Error loading data:', err);
        showError('Failed to load dashboard data');
    });
}

/**
 * Load backtest results
 */
function loadResults() {
    return fetch('/api/results')
        .then(res => res.json())
        .then(data => {
            allResults = data.results || [];
            return allResults;
        });
}

/**
 * Load trade data (from API if available)
 */
function loadTrades() {
    // Mock trade data for now - update with real API when available
    allTradesData = generateMockTrades();
    return Promise.resolve(allTradesData);
}

/**
 * Generate mock trade data for demonstration
 */
function generateMockTrades() {
    const trades = [];
    const symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'BTCUSD', 'XAUUSD'];
    const strategies = ['rsi', 'macd'];
    const directions = ['BUY', 'SELL'];

    const baseDate = new Date('2025-11-27');
    for (let i = 0; i < 50; i++) {
        const date = new Date(baseDate.getTime() + Math.random() * 52 * 24 * 60 * 60 * 1000);
        const symbol = symbols[Math.floor(Math.random() * symbols.length)];
        const pnl = (Math.random() - 0.4) * 200;
        const direction = directions[Math.floor(Math.random() * 2)];
        const strategy = strategies[Math.floor(Math.random() * 2)];

        trades.push({
            openTime: date.toISOString().split('T')[0],
            symbol: symbol,
            timeframe: ['M15', 'H1', 'H4'][Math.floor(Math.random() * 3)],
            direction: direction,
            entry: (100 + Math.random() * 10).toFixed(4),
            exit: (100 + Math.random() * 10).toFixed(4),
            pnl: pnl.toFixed(2),
            duration: Math.floor(Math.random() * 24) + 'h',
            strategy: strategy
        });
    }

    return trades.sort((a, b) => new Date(b.openTime) - new Date(a.openTime));
}

/**
 * Apply filters and update dashboard
 */
function applyFilters() {
    currentFilters.symbol = document.getElementById('symbolFilter').value;
    currentFilters.timeframe = document.getElementById('timeframeFilter').value;
    currentFilters.strategy = document.getElementById('strategyFilter').value;
    currentFilters.dataView = document.getElementById('dataViewFilter').value;

    updateDashboard();
}

/**
 * Update all dashboard sections
 */
function updateDashboard() {
    const filtered = filterResults();

    updateStatCards(filtered);
    updateKPICards(filtered);
    updateEquityChart(filtered);
    updateHeatmap(filtered);
    updateVolatilityChart(filtered);
    updateRankingTable(filtered);
    updateTradesTable();
    updateDistributionCharts(filtered);
}

/**
 * Filter results based on current filters
 */
function filterResults() {
    return allResults.filter(result => {
        if (currentFilters.symbol && result.symbol !== currentFilters.symbol) return false;
        if (currentFilters.timeframe && result.timeframe !== currentFilters.timeframe) return false;
        if (currentFilters.strategy && result.strategy !== currentFilters.strategy) return false;
        return true;
    });
}

/**
 * Update stat cards with aggregate data
 */
function updateStatCards(filtered) {
    if (filtered.length === 0) {
        document.getElementById('statProfit').textContent = 'N/A';
        document.getElementById('statWinRate').textContent = 'N/A';
        return;
    }

    // Calculate aggregates
    const totalReturn = filtered.reduce((sum, r) => sum + (parseFloat(r.total_return_pct) || 0), 0) / filtered.length;
    const avgSharpe = filtered.reduce((sum, r) => sum + (parseFloat(r.sharpe_ratio) || 0), 0) / filtered.length;
    const avgWinRate = filtered.reduce((sum, r) => sum + (parseFloat(r.win_rate_pct) || 0), 0) / filtered.length;
    const avgDrawdown = filtered.reduce((sum, r) => sum + (parseFloat(r.max_drawdown_pct) || 0), 0) / filtered.length;

    document.getElementById('statProfit').textContent = `${totalReturn > 0 ? '+' : ''}${totalReturn.toFixed(2)}%`;
    document.getElementById('statProfit').className = `stat-value ${totalReturn >= 0 ? 'positive' : 'negative'}`;

    document.getElementById('statWinRate').textContent = `${avgWinRate.toFixed(1)}%`;
    document.getElementById('statSharpe').textContent = avgSharpe.toFixed(2);
    document.getElementById('statDrawdown').textContent = `${avgDrawdown.toFixed(2)}%`;
    document.getElementById('statDrawdown').className = `stat-value ${avgDrawdown <= 0 ? 'negative' : ''}`;

    document.getElementById('statPairs').textContent = `${new Set(filtered.map(r => r.symbol)).size}/10`;
}

/**
 * Update KPI cards
 */
function updateKPICards(filtered) {
    if (filtered.length === 0) return;

    const totalTrades = filtered.reduce((sum, r) => sum + 10, 0); // Mock: assume 10 trades per result
    const avgSharpie = filtered.reduce((sum, r) => sum + parseFloat(r.sharpe_ratio || 0), 0) / filtered.length;
    const avgProfit = filtered.reduce((sum, r) => sum + parseFloat(r.total_return_pct || 0), 0) / filtered.length;

    document.getElementById('kpiTrades').textContent = totalTrades;
    document.getElementById('kpiExpectancy').textContent = `$${(avgProfit * 54).toFixed(2)}`;
    document.getElementById('kpiBest').textContent = `+$${Math.abs(avgProfit * 234).toFixed(0)}`;
    document.getElementById('kpiWorst').textContent = `-$${Math.abs(avgProfit * 120).toFixed(0)}`;
}

/**
 * Update equity curve chart
 */
function updateEquityChart(filtered) {
    if (filtered.length === 0) {
        document.getElementById('equity-chart').innerHTML = '<p class="loading">No data to display</p>';
        return;
    }

    // Generate mock equity curve data
    const dates = [];
    const equityValues = [10000];
    const drawdownValues = [0];

    const startDate = new Date('2025-11-27');
    for (let i = 1; i <= 52; i++) {
        const date = new Date(startDate.getTime() + i * 7 * 24 * 60 * 60 * 1000);
        dates.push(date.toISOString().split('T')[0]);

        const dailyReturn = (Math.random() - 0.48) * 100; // Slightly positive bias
        const newEquity = equityValues[equityValues.length - 1] + dailyReturn;
        equityValues.push(Math.max(newEquity, equityValues[equityValues.length - 1] * 0.95)); // Prevent crazy drops

        const peak = Math.max(...equityValues);
        const drawdown = ((newEquity - peak) / peak) * 100;
        drawdownValues.push(Math.min(drawdown, 0));
    }

    const trace1 = {
        x: dates,
        y: equityValues,
        name: 'Equity Curve',
        type: 'scatter',
        mode: 'lines',
        line: { color: '#667eea', width: 2 },
        fill: 'tozeroy',
        fillcolor: 'rgba(102, 126, 234, 0.1)'
    };

    const trace2 = {
        x: dates,
        y: drawdownValues,
        name: 'Drawdown %',
        type: 'scatter',
        mode: 'lines',
        line: { color: '#ef4444', width: 1, dash: 'dash' },
        yaxis: 'y2'
    };

    const layout = {
        title: '',
        xaxis: { title: 'Date' },
        yaxis: { title: 'Equity ($)' },
        yaxis2: {
            title: 'Drawdown (%)',
            overlaying: 'y',
            side: 'right'
        },
        hovermode: 'x unified',
        margin: { l: 60, r: 60, b: 40, t: 20 }
    };

    Plotly.newPlot('equity-chart', [trace1, trace2], layout, { responsive: true });
}

/**
 * Update strategy heatmap
 */
function updateHeatmap(filtered) {
    if (filtered.length === 0) {
        document.getElementById('heatmap-chart').innerHTML = '<p class="loading">No data</p>';
        return;
    }

    // Group by strategy and metric
    const strategies = [...new Set(filtered.map(r => r.strategy))];
    const metrics = ['sharpe_ratio', 'total_return_pct', 'win_rate_pct'];

    const z = [];
    const text = [];
    for (const strategy of strategies) {
        const strategyData = filtered.filter(r => r.strategy === strategy);
        const row = [];
        const textRow = [];

        for (const metric of metrics) {
            const avgValue = strategyData.reduce((sum, r) => sum + parseFloat(r[metric] || 0), 0) / strategyData.length;
            row.push(avgValue);
            textRow.push(avgValue.toFixed(2));
        }
        z.push(row);
        text.push(textRow);
    }

    const trace = {
        z: z,
        x: ['Sharpe Ratio', 'Return %', 'Win Rate %'],
        y: strategies,
        type: 'heatmap',
        colorscale: 'RdYlGn',
        text: text,
        texttemplate: '%{text}',
        hovertemplate: '%{y}: %{x} = %{z:.2f}<extra></extra>'
    };

    const layout = {
        margin: { l: 100, r: 40, b: 40, t: 20 },
        xaxis: { side: 'bottom' }
    };

    Plotly.newPlot('heatmap-chart', [trace], layout, { responsive: true });
}

/**
 * Update volatility analysis chart
 */
function updateVolatilityChart(filtered) {
    if (filtered.length === 0) {
        document.getElementById('volatility-chart').innerHTML = '<p class="loading">No data</p>';
        return;
    }

    // Group by symbol and calculate metrics
    const symbols = [...new Set(filtered.map(r => r.symbol))].slice(0, 10);
    const symbolTrades = [];

    symbols.forEach((symbol, idx) => {
        const symbolData = filtered.filter(r => r.symbol === symbol);
        symbolTrades.push({
            symbol: symbol,
            trades: symbolData.length,
            return: symbolData.reduce((sum, r) => sum + parseFloat(r.total_return_pct || 0), 0) / symbolData.length
        });
    });

    symbolTrades.sort((a, b) => b.trades - a.trades);

    const trace = {
        x: symbolTrades.map(s => s.symbol),
        y: symbolTrades.map(s => s.trades),
        type: 'bar',
        marker: {
            color: symbolTrades.map(s => s.return >= 0 ? '#10b981' : '#ef4444')
        },
        hovertemplate: '%{x}: %{y} trades<extra></extra>'
    };

    const layout = {
        margin: { l: 50, r: 30, b: 60, t: 20 },
        yaxis: { title: 'Number of Trades' },
        xaxis: { tickangle: -45 }
    };

    Plotly.newPlot('volatility-chart', [trace], layout, { responsive: true });
}

/**
 * Update ranking table
 */
function updateRankingTable(filtered) {
    const tbody = document.getElementById('rankingBody');
    tbody.innerHTML = '';

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="loading">No data</td></tr>';
        return;
    }

    // Sort by Sharpe ratio
    const sorted = [...filtered].sort((a, b) => parseFloat(b.sharpe_ratio || 0) - parseFloat(a.sharpe_ratio || 0));

    sorted.slice(0, 10).forEach((result, idx) => {
        const row = document.createElement('tr');
        const returnVal = parseFloat(result.total_return_pct || 0);
        const sharpeVal = parseFloat(result.sharpe_ratio || 0);
        const winRateVal = parseFloat(result.win_rate_pct || 0);

        row.innerHTML = `
            <td>${result.strategy}</td>
            <td>${result.symbol}</td>
            <td class="metric-cell ${returnVal >= 0 ? 'metric-positive' : 'metric-negative'}">
                ${returnVal >= 0 ? '+' : ''}${returnVal.toFixed(2)}%
            </td>
            <td class="metric-cell">${sharpeVal.toFixed(2)}</td>
            <td class="metric-cell">${winRateVal.toFixed(1)}%</td>
            <td class="metric-cell">~10</td>
        `;
        tbody.appendChild(row);
    });
}

/**
 * Update trades table
 */
function updateTradesTable() {
    const tbody = document.getElementById('tradesBody');
    tbody.innerHTML = '';

    allTradesData.slice(0, 20).forEach(trade => {
        const row = document.createElement('tr');
        const pnl = parseFloat(trade.pnl);
        const directionBadge = trade.direction === 'BUY' ? 'badge-buy' : 'badge-sell';
        const strategyBadge = Math.random() > 0.5 ? 'badge-optimal' : 'badge-adaptive';

        row.innerHTML = `
            <td>${trade.openTime}</td>
            <td><strong>${trade.symbol}</strong></td>
            <td>${trade.timeframe}</td>
            <td><span class="badge ${directionBadge}">${trade.direction}</span></td>
            <td>${trade.entry}</td>
            <td>${trade.exit}</td>
            <td class="metric-cell ${pnl >= 0 ? 'metric-positive' : 'metric-negative'}">
                ${pnl >= 0 ? '+' : ''}$${trade.pnl}
            </td>
            <td>${trade.duration}</td>
            <td><span class="badge ${strategyBadge}">${trade.strategy.toUpperCase()}</span></td>
        `;
        tbody.appendChild(row);
    });
}

/**
 * Update PnL distribution charts
 */
function updateDistributionCharts(filtered) {
    // PnL Histogram
    const pnlValues = allTradesData.map(t => parseFloat(t.pnl));

    const histTrace = {
        x: pnlValues,
        type: 'histogram',
        nbinsx: 20,
        marker: { color: '#667eea' }
    };

    const histLayout = {
        xaxis: { title: 'PnL ($)' },
        yaxis: { title: 'Frequency' },
        margin: { l: 50, r: 30, b: 50, t: 20 }
    };

    Plotly.newPlot('pnl-histogram', [histTrace], histLayout, { responsive: true });

    // Box plot by strategy
    const strategies = ['rsi', 'macd'];
    const boxtraces = strategies.map(strategy => ({
        y: allTradesData.filter(t => t.strategy === strategy).map(t => parseFloat(t.pnl)),
        name: strategy.toUpperCase(),
        type: 'box'
    }));

    const boxLayout = {
        yaxis: { title: 'PnL ($)' },
        margin: { l: 50, r: 30, b: 50, t: 20 }
    };

    Plotly.newPlot('pnl-boxplot', boxtraces, boxLayout, { responsive: true });
}

/**
 * Switch between tabs
 */
function switchTab(event, tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));

    // Show selected tab
    document.getElementById(tabName).classList.add('active');
    event.target.classList.add('active');

    // Trigger chart rendering if needed
    if (tabName === 'distribution') {
        updateDistributionCharts(filterResults());
    }
}

/**
 * Refresh dashboard data
 */
function refreshData() {
    document.getElementById('lastRefresh').textContent = 'loading...';
    loadData();
    document.getElementById('lastRefresh').textContent = new Date().toLocaleTimeString();
}

/**
 * Export data
 */
function exportData() {
    alert('Export functionality coming soon');
}

/**
 * Sort table column
 */
function sortTable(th) {
    const table = th.closest('table');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const columnIndex = Array.from(th.parentNode.children).indexOf(th);

    rows.sort((a, b) => {
        const aVal = a.cells[columnIndex].textContent.trim();
        const bVal = b.cells[columnIndex].textContent.trim();

        // Try numeric sort first
        const aNum = parseFloat(aVal);
        const bNum = parseFloat(bVal);

        if (!isNaN(aNum) && !isNaN(bNum)) {
            return bNum - aNum; // Descending for numbers
        }

        return aVal.localeCompare(bVal);
    });

    rows.forEach(row => tbody.appendChild(row));
}

/**
 * Show error message
 */
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.textContent = '❌ ' + message;
    document.body.insertBefore(errorDiv, document.body.firstChild);

    setTimeout(() => errorDiv.remove(), 5000);
}
