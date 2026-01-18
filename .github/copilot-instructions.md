# FX Trading Bot - AI Coding Agent Instructions

## Project Overview

**FX Trading Bot** is a production-ready MetaTrader5 (MT5) algorithmic trading system featuring:
- **Adaptive strategy selection**: Auto-selects best strategies per symbol/timeframe from backtest database
- **Multi-asset support**: 50 pairs × 3 timeframes (M15/H1/H4) = 150+ asset-timeframe combinations
- **Two extensible strategies**: RSI and MACD (both implement `BaseStrategy` interface)
- **Complete 3-step workflow**: Sync data → Backtest/optimize → Live trade with adaptive/fixed modes
- **Interactive web dashboard**: Flask-based results analysis at `http://127.0.0.1:5000`

**Critical pattern**: Everything is database-driven. Backtest results stored in `optimal_params` table drive live strategy selection via `StrategySelector` (queries by rank_score, confidence thresholds).

---

## Essential 3-Step Workflow

### 1. Sync Data from MT5
```bash
python -m src.main --mode sync              # All symbols (reads from config.yaml pair_config)
python -m src.main --mode sync --symbol BTCUSD  # Single symbol
```
- Fetches latest candles from MT5 → stores in `market_data` table
- Auto-generates timeframes (M15/H1/H4) from `pair_config.timeframes`
- Required before any backtesting or live trading

### 2. Backtest & Optimize Strategies
```bash
python -m src.backtesting.backtest_manager --mode multi-backtest --strategy rsi
python -m src.backtesting.backtest_manager --mode multi-backtest --strategy macd --symbol BTCUSD
```
- Copies `market_data` → `backtest_market_data` (preserves live data integrity)
- Tests strategy params via `backtesting.py` FractionalBacktest
- Calculates: Sharpe ratio, total return, win rate, profit factor, drawdown
- Stores results in `optimal_params` table with rank_score for adaptive selection

### 3. Live Trade or Analyze
```bash
python -m src.main --mode live              # Adaptive: queries optimal_params, picks top strategies
python -m src.main --mode live --strategy rsi --symbol BTCUSD  # Fixed: uses specified strategy
python -m src.main --mode gui               # Web dashboard (http://127.0.0.1:5000)
```
- **Adaptive mode** (recommended): `AdaptiveTrader` → `StrategySelector` queries DB → returns top-3 strategies with confidence scores
- **Fixed mode**: Single strategy for specific pair
- **GUI mode**: Flask server serves interactive backtest results, equity curves, heatmaps

### Verification
```bash
pytest
python tests/verify_implementation.py  # Full workflow validation
```

---

## Critical Architecture Patterns

### Strategy Layer (Factory + Base Class Pattern)
**Location**: `src/strategies/`, `src/core/base_strategy.py`

**Pattern**: 
- Abstract `BaseStrategy` defines interface: `generate_entry_signal()`, `generate_exit_signal()`
- Two implementations: `RSIStrategy`, `MACDStrategy` 
- `StrategyFactory.create_strategy(name, params, db, mode, config)` instantiates by name
- **Key method**: `fetch_data(symbol, required_rows)` auto-routes to `market_data` (live) or `backtest_market_data` (backtest)

**Adding new strategy**:
```python
# 1. Create src/strategies/new_strategy.py
from src.core.base_strategy import BaseStrategy

class NewStrategy(BaseStrategy):
    def generate_entry_signal(self, data):
        # return True/False
    
    def generate_exit_signal(self, data):
        # return True/False

# 2. Add to factory in src/strategies/factory.py
strategy_map = {"rsi": RSIStrategy, "macd": MACDStrategy, "new": NewStrategy}

# 3. Add config entry in src/config/config.yaml
strategies:
  - name: new
    params:
      period: 14
      volume: 0.01
```

### Data Caching for Live Performance
**Location**: `src/strategy_manager.py` - `DataCache` class

- **TTL-based**: 20-second expiration (configurable)
- **Live mode only**: Reduces MT5 queries (high cost in production)
- **Cache keys**: `{symbol}_{timeframe}_{table_name}` (e.g., `BTCUSD_15_market_data`)
- **Usage pattern**: Strategies access via `self.data_cache` set by `StrategyManager`
```python
# StrategyManager auto-caches results
cache_key = f"{symbol}_{self.timeframe}_{table}"
cached_data = self.data_cache.get(cache_key)  # Returns None if expired
if cached_data is not None: return cached_data
data = fetch_fresh_data()
self.data_cache.set(cache_key, data)  # Auto-timestamps
```

### Adaptive Strategy Selection (Query → Rank → Execute)
**Location**: `src/core/adaptive_trader.py`, `src/core/strategy_selector.py`

**Flow**:
1. `AdaptiveTrader.execute_trades()` called with symbol + timeframe
2. `StrategySelector.get_best_strategies(symbol, timeframe)` queries `optimal_params` table
3. **Ranking formula** (in `strategy_selector.py`): Weighted combination of Sharpe ratio, total return, win rate, profit factor
4. Returns **top-3 strategies** with **confidence scores** (0.5-1.0):
   - 0.9+: Excellent (Sharpe > 1.5, win rate > 60%)
   - 0.7-0.9: Good (reliable metrics)
   - 0.5-0.7: Moderate (decent)
5. `AdaptiveTrader` instantiates via `StrategyFactory` + caches in `self.loaded_strategies`
6. Executes signals via `MT5Connector.place_order()`

### Database Schema (SQLite)
**Path**: `src/data/market_data.sqlite` (auto-created by `DatabaseManager`)

**Key tables**:
- `market_data`: Live trading data synced from MT5 (symbol, timeframe, time, open, high, low, close, volume)
- `backtest_market_data`: Copy of historical data used for backtesting (avoids live data corruption)
- `backtest_backtests`: Backtest results with metrics (strategy_id, symbol, timeframe, metrics, timestamp)
  - **UNIQUE constraint**: (strategy_id, symbol, timeframe) prevents duplicate entries
  - Uses `INSERT OR REPLACE` to update existing results on re-run
- `optimal_params`: Best strategy parameters per symbol/timeframe

**Context manager pattern** (always use this):
```python
with DatabaseManager(config["database"]) as db:
    db.create_tables()
    data = db.execute_query(sql, params)
    # Auto-closes on exit
```

### Configuration & Symbol Generation
**File**: `src/config/config.yaml`

**Key sections**:
- `pair_config`: Organize pairs by category (forex, stocks, commodities, indices, crypto)
- `pair_config.timeframes`: [15, 60, 240] = M15, H1, H4 (in minutes)
- `pairs`: Auto-generated list at startup via `generate_pairs_from_config(config)`

**Auto-generation in main.py**:
```python
def generate_pairs_from_config(config):
    pairs = []
    for timeframe in config["pair_config"]["timeframes"]:
        for category, data in config["pair_config"]["categories"].items():
            for symbol in data["symbols"]:
                pairs.append({"symbol": symbol, "timeframe": timeframe, "category": category})
    config["pairs"] = pairs
```
This creates 150+ trading combos (50 symbols × 3 timeframes)

---

## Key Configuration Points

**File**: `src/config/config.yaml`
- **`pair_config`**: Define trading pairs by category (forex, stocks, commodities, indices, crypto)
- **`pair_config.timeframes`**: [15, 60, 240] = M15, H1, H4 in minutes
- **`strategies`**: Strategy parameters (RSI period, MACD fast/slow, volumes)
- **`mt5`**: MT5 credentials (login, server, password)
- **`risk_management`**: Position limits, stop-loss/take-profit percentages
- **`data`**: Fetch limits (1000 max rows per query, 5000 from MT5 API, 5000 minimum before trading)
- **`backtesting.optimization`**: Parameter ranges for each strategy (e.g., RSI period: [10, 12, 14, 16])

**Auto-generated on startup**: `pairs` list populated from `pair_config` categories + timeframes (150+ combos).

---

## Testing & Verification

**Test location**: `tests/` directory with pytest
- **test_imports.py**: Validates core module imports (MT5Connector, DatabaseManager, StrategyManager)
- **test_config.py**, **test_params.py**: Configuration and parameter validation
- **verify_implementation.py**: Full 3-step workflow validation

**Run tests**:
```bash
pytest                                 # All tests
pytest tests/test_imports.py -v       # Specific test file
python tests/verify_implementation.py  # Full workflow check
```

---

## Common Development Tasks

### Modifying Strategy Logic
- **File**: Strategy implementation (e.g., `src/strategies/rsi_strategy.py`)
- **Pattern**: Override `generate_entry_signal()` and `generate_exit_signal()` in BaseStrategy subclass
- **Data access**: Use `self.fetch_data(symbol, required_rows)` for database retrieval with auto-caching
- **Backtesting integration**: Implement nested `BacktestRSIStrategy(Strategy)` class for backtesting.py framework

### Adding New Trading Rules
- **File**: `src/utils/trading_rules.py`
- **Current rules**: Weekend checks for forex/commodities, position limits
- **Integration point**: `Trader.execute_trades()` calls rules before signal execution

### Extending Backtesting Metrics
- **File**: `src/backtesting/metrics_engine.py`
- **Current metrics**: Sharpe ratio, return, win rate, profit factor
- **Storage**: Results saved in `optimal_params` table with timestamp for ranking

### Debugging Live Mode
- **Logs**: `logs/terminal_log.txt` (configured via `src/utils/logger.py`)
- **Debug flags**: Use `self.logger.debug()` in components; enable via logging config
- **MT5 issues**: Check `mt5_connector.py` for connection state and error handling

### Web Dashboard Architecture
**Location**: `src/ui/web/dashboard_server.py`, `src/ui/web/static/dashboard.js`

**Flask Route Patterns**:

```python
# Pattern 1: GET with filtering (returns JSON)
@app.route('/api/results')
def api_results(self):
    """Fetch backtest results with optional symbol/timeframe filters."""
    symbol = request.args.get("symbol", "All")  # Query parameter
    timeframe = request.args.get("timeframe", "All")
    
    # Query database with parameterized queries (prevent SQL injection)
    query = "SELECT ... WHERE (:symbol = 'All' OR symbol = :symbol)"
    results = db.execute_query(query, {"symbol": symbol})
    
    # CRITICAL: Handle NaN values (from metrics) - use _safe_round()
    # NaN is not valid JSON, so convert to 0:
    formatted_data = {
        "sharpe_ratio": self._safe_round(metrics.get("sharpe_ratio", 0), 2),
        "roe": self._safe_round(metrics.get("roe", 0), 2),
    }
    return jsonify({"results": formatted_data, "status": "success"})

# Pattern 2: API endpoints return file paths (metadata only)
@app.route('/api/equity-curve/<symbol>/<strategy>')
def api_equity_curve(self, symbol, strategy):
    """Return equity curve file info (does NOT serve the file)."""
    results_dir = "backtests/results"
    file_path = f"{results_dir}/equity_curve_{symbol}_{strategy}.html"
    
    if os.path.exists(file_path):
        return jsonify({
            "file": file_path,
            "status": "success",
            "filename": os.path.basename(file_path)
        })
    return jsonify({"file": None, "status": "error"}), 404

# Pattern 3: File serving routes (GET with query params)
@app.route('/view-equity-curve')
def view_equity_curve(self):
    """Serve pre-generated HTML equity curve charts."""
    symbol = request.args.get("symbol")  # e.g., BTCUSD
    strategy = request.args.get("strategy")  # e.g., rsi
    
    # Files generated during backtesting: backtests/results/equity_curve_BTCUSD_rsi.html
    file_path = f"backtests/results/equity_curve_{symbol}_{strategy}.html"
    return send_file(file_path) if os.path.exists(file_path) else "Not found", 404

# Pattern 4: Heatmap with timeframe conversion (numeric to string format)
@app.route('/api/heatmap/<symbol>/<timeframe>')
def api_heatmap(self, symbol, timeframe):
    """Return heatmap file info with timeframe format conversion.
    
    Important: Database stores timeframe as numeric (15, 60, 240)
    but files are named with string format (M15, H1, H4).
    Use _timeframe_to_string() to convert before searching for files.
    """
    timeframe_str = self._timeframe_to_string(timeframe)  # 60 -> H1
    file_path = f"backtests/results/rsi_optimization_heatmap_{symbol}_{timeframe_str}.png"
    # ... search and return
```

**Frontend Integration (dashboard.js)**:
```javascript
// Async fetch with error handling - click handlers call API then open view routes
async function viewEquityCurves() {
    // 1. Get symbol/strategy from selected table row
    const symbol = cells[1].textContent.trim();
    const strategy = cells[0].textContent.trim();
    
    // 2. Check metadata at API endpoint
    const apiUrl = `/api/equity-curve/${symbol}/${strategy}`;
    const response = await fetch(apiUrl);
    const data = await response.json();
    
    if (data.status === 'success') {
        // 3. Open actual file viewer
        window.open(`/view-equity-curve?symbol=${symbol}&strategy=${strategy}`, '_blank');
    }
}
```

**Key implementation details**:
- **Timeframe conversion**: Database stores 15/60/240, files use M15/H1/H4. Use `_timeframe_to_string()` in `/api/heatmap` and `/view-heatmap` routes
- **Two-step file serving**: API endpoints return metadata/status, view endpoints serve actual files via `send_file()`
- **NaN handling**: Use `_safe_round()` utility method to convert NaN/None → 0 before jsonify()
- **Thread-safe database access**: Use `self._get_db()` to create fresh connection per request
- **Error responses**: Always return JSON with `"status": "error"` and HTTP status for API endpoints
- **File encoding**: Use `encodeURIComponent()` in JavaScript for URL parameters (handles special characters)

---

## Important Conventions

1. **Symbol naming**: All uppercase (BTCUSD, EURUSD, AAPL)
2. **Timeframe format**: M15, M60, H1, H4 (stored as minutes internally: 15, 60, 240)
3. **Mode parameter**: Always "live" or "backtest" when instantiating strategies
4. **Config loading**: YAML files loaded at initialization; changes require restart
5. **Database context**: Always use `with DatabaseManager() as db:` for proper cleanup
6. **Cache keys**: Use consistent format: `{symbol}_{timeframe}_{table}` for cross-component reuse

---

## Integration Points & External Dependencies

- **MetaTrader5 (MT5)**: Order placement, market data fetch, account info via `src/mt5_connector.py`
- **backtesting.py**: Historical testing framework (FractionalBacktest for fractional volumes)
- **TA-Lib (ta)**: Technical indicators (RSI, MACD)
- **Flask**: Web dashboard in `src/ui/web/dashboard_server.py`
- **Plotly/Kaleido**: HTML equity curve reports in `backtests/results/`
- **pandas/numpy**: Data processing
- **SQLite**: Local database (no external DB required)

---

## When Making Changes

- **Multi-timeframe testing**: Changes to signal logic must work across M15, H1, H4 (verify in config)
- **Backward compatibility**: New strategy parameters should have sensible defaults
- **Database migrations**: Use `src/database/migrations.py` pattern for schema changes
- **Performance**: Monitor cache hit rates; logging statements debug expensive operations
- **Validation**: Use `src/utils/data_validator.py` for data integrity before trading

---

## Troubleshooting Common Issues

### Duplicate Timeframes in backtest_backtests Table
**Problem**: Each pair has multiple identical rows with the same timeframe

**Root cause**: Previous code allowed duplicate inserts without UNIQUE constraint.

**Fixed in v2**: 
- Added `UNIQUE(strategy_id, symbol, timeframe)` constraint to `backtest_backtests` table
- Changed `INSERT` to `INSERT OR REPLACE` in backtest_manager.py
- Now re-running a backtest updates the previous result instead of creating duplicates

**Clean up existing duplicates**:
```sql
-- Delete old duplicate records, keep only the most recent per (strategy_id, symbol, timeframe)
DELETE FROM backtest_backtests WHERE id NOT IN (
    SELECT MAX(id) FROM backtest_backtests 
    GROUP BY strategy_id, symbol, timeframe
);
```

Then delete and recreate the database to apply the UNIQUE constraint:
```bash
# Backup current database
cp src/data/market_data.sqlite src/data/market_data.sqlite.backup

# Delete and restart
rm src/data/market_data.sqlite
python -m src.main --mode sync       # Recreates empty database with UNIQUE constraints
```

### View Equity Curves and Heatmap Buttons Not Working
**Problem**: Buttons disabled or clicking opens blank pages

**Causes & Fixes**:
1. **No row selected**: Must click a result row first (row highlights in blue)
   - JavaScript sets `selectedRow = null` on load, buttons disabled until selection made
   
2. **File doesn't exist**: Equity curves/heatmaps only exist for symbols that were backtested
   - Heatmaps named: `rsi_optimization_heatmap_{SYMBOL}_{TIMEFRAME}.png` (TIMEFRAME = M15/H1/H4, NOT 15/60/240)
   - Equity curves named: `equity_curve_{SYMBOL}_{STRATEGY}.html`
   
3. **Timeframe format mismatch** (most common):
   - Database stores timeframe as numeric: 15, 60, 240
   - Files named with string format: M15, H1, H4
   - Solution: Dashboard uses `_timeframe_to_string()` to convert 60 → H1
   - If this conversion fails, heatmap won't be found
   
4. **Browser dev tools debugging**:
   - Open browser console (F12)
   - Click button and check console output:
     - Shows API URLs being called
     - Shows fetch errors if file not found
     - Example: `Fetching heatmap from: /api/heatmap/BTCUSD/60`

**Verification**:
```bash
# Check that files exist with correct naming
ls backtests/results/ | grep equity_curve_BTCUSD
# Should show: equity_curve_BTCUSD_rsi.html, equity_curve_BTCUSD_macd.html

ls backtests/results/ | grep "optimization_heatmap_BTCUSD"
# Should show: rsi_optimization_heatmap_BTCUSD_M15.png, rsi_optimization_heatmap_BTCUSD_H1.png, etc.
```

### Web Dashboard JSON Parse Error
**Problem**: `dashboard.js:136 Error loading results: SyntaxError: Unexpected token 'N', ..."t_factor":NaN..."`

**Cause**: Flask JSON serializer encounters NaN (from metrics calculations) which is not valid JSON.

**Solution**: Use `_safe_round()` method in Flask routes to convert NaN → 0:
```python
# WRONG - returns NaN in JSON
"sharpe_ratio": round(metrics.get("sharpe_ratio", 0), 2)

# CORRECT - converts NaN to 0
"sharpe_ratio": self._safe_round(metrics.get("sharpe_ratio", 0), 2)

# _safe_round utility:
@staticmethod
def _safe_round(value, decimals=2):
    import math
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0
    return round(value, decimals)
```

**Verification**: Check browser console - JSON should parse cleanly after fix.

### Web Dashboard Not Loading Data
**Problem**: Results table shows "No results found" despite backtests run

**Debug steps**:
1. **Check database has data**: `SELECT COUNT(*) FROM backtest_backtests;`
2. **Verify Flask route responses**: Open browser dev tools → Network tab → check `/api/results` response
3. **Check table names**: Routes query `backtest_backtests`, ensure data synced to correct table
4. **Clear cache**: Hard refresh browser (Ctrl+Shift+R) to clear stale data

### Data Sync Failures
**Problem**: `TypeError: '<' not supported between instances of 'NoneType' and 'int'` in `data_validator.py`

**Solution**: The `_fetch_and_sync()` method now handles `timeframe=None` by syncing all configured timeframes (M15, H1, H4) for a symbol. If calling this method, pass either:
- A specific timeframe (15, 60, 240) for single timeframe sync
- `None` to sync all timeframes for that symbol

### Missing market_data Table
**Problem**: `no such table: market_data` errors during backtest

**Causes & Fixes**:
1. **Data sync didn't complete**: Run `python -m src.main --mode sync` first
2. **Database connection closed prematurely**: Check `DatabaseManager` context manager usage - always use `with DatabaseManager(config) as db:`
3. **Fresh database**: Delete `src/data/market_data.sqlite` and rerun sync

### MT5 Connection Failures
**Problem**: `MT5 connection initialized but no data fetched`

**Debug steps**:
1. Verify MT5 terminal is running on the machine
2. Check credentials in `src/config/config.yaml` (login, server, password)
3. Verify symbol exists in MT5 (case-sensitive: BTCUSD not BTC)
4. Check `logs/terminal_log.txt` for specific MT5 error codes

### Database Context Issues
**Pattern**: Always close database connections properly:
```python
# CORRECT - automatic cleanup
with DatabaseManager(config) as db:
    db.execute_query(...)

# WRONG - connection stays open
db = DatabaseManager(config)
db.connect()
```

### GUI Mode Unnecessary MT5 Connections (FIXED)
**Problem** (Now Resolved): `python -m src.main --mode gui` was making unnecessary MT5 connection attempts, causing "Terminal: Authorization failed" errors and delays.

**Root Cause**:
- `data_validator.validate_and_init()` was called for all modes including GUI
- When symbols had <5000 rows of data, validator attempted to fetch from MT5
- GUI mode only needs to **read** existing data, doesn't need MT5 connection

**Fix Implemented** (v2):
- **In `src/main.py` line 93**: Added mode check - skip data validation entirely for GUI mode:
  ```python
  if args.mode != "gui":
      logger.info("Running data validation and initialization...")
      validator = DataValidator(db, config, mt5_conn_temp)
      validator.validate_and_init()
  ```
- **In `src/main.py` line 149**: Fixed DashboardServer initialization to pass proper host/port parameters:
  ```python
  elif args.mode == "gui":
      logger.info("Launching web dashboard...")
      host = config.get("web", {}).get("host", "127.0.0.1")
      port = config.get("web", {}).get("port", 5000)
      dashboard = DashboardServer(config, host=host, port=port)
      dashboard.run(debug=False)
  ```

**Result**: 
- ✅ GUI mode launches immediately without MT5 connection attempts
- ✅ Dashboard available at `http://127.0.0.1:5000` within 1-2 seconds
- ✅ No "Authorization failed" errors in logs

**Why this matters**: 
- GUI is analysis-only mode (reads backtests from database)
- MT5 connection should only be used in sync/live modes
- Prevents connection delays and unnecessary auth failures during testing
