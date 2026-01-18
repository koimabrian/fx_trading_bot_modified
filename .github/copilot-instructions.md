# FX Trading Bot - Copilot Instructions

## Architecture Overview

**FX Trading Bot** is a MetaTrader5-based algorithmic trading system with pluggable strategies, backtesting, and dual interfaces (CLI + GUI).

### Core Data Flow
1. **MT5 Connection** ([src/mt5_connector.py](../src/mt5_connector.py)) → Live market data fetched via `MT5.copy_rates_from_pos()`
2. **Data Persistence** → SQLite database ([src/database/db_manager.py](../src/database/db_manager.py)) stores `market_data` (live) & `backtest_market_data` (historical)
3. **Strategy Execution** → [StrategyManager](../src/strategy_manager.py) dynamically loads strategies from config.yaml via [StrategyFactory](../src/strategies/factory.py)
4. **Trade Execution** → [Trader](../src/core/trader.py) executes buy/sell signals; [TradeMonitor](../src/core/trade_monitor.py) manages positions

### Key Components & Responsibilities

| Component | File | Purpose |
|-----------|------|---------|
| **StrategyManager** | strategy_manager.py | Loads YAML config, instantiates strategies via Factory pattern |
| **BaseStrategy** | core/base_strategy.py | Abstract base for all strategies (RSI, MACD, ML models) |
| **Trader** | core/trader.py | Executes trades from strategy signals |
| **DataHandler** | core/data_handler.py | Transforms database records to pandas DataFrames for backtesting |
| **TradingRules** | utils/trading_rules.py | Enforces symbol-specific rules (crypto 24/7, forex weekend closure) |
| **BacktestManager** | backtesting/backtest_manager.py | Syncs live→backtest data, runs parametric optimization |

---

## Strategy Development Pattern

### Adding a New Strategy

1. **Inherit BaseStrategy** ([src/strategies/](../src/strategies/)) - implements `generate_entry_signal()` and `generate_exit_signal()`
2. **Use DataFetcher** - call `self.fetch_data()` to get pandas DataFrame with OHLCV
3. **Return signal dict** - `{"action": "buy|sell", "symbol": "...", "volume": 0.01}`
4. **Register in Factory** - add to strategy_map in [strategies/factory.py](../src/strategies/factory.py) line 8
5. **Configure params in config.yaml** - strategy loads params from `config["strategies"][*]["params"]`

Example: [src/strategies/rsi_strategy.py](../src/strategies/rsi_strategy.py) uses RSI overbought/oversold thresholds from config.

### Data & Backtesting Modes

- **Live mode** (`--mode live`): Uses `market_data` table, MT5 connection required, checks TradingRules
- **Backtest mode** (`--mode backtest`): Uses `backtest_market_data` table, all data pre-loaded, no live connection
- **GUI mode** (`--mode gui`): PyQt5 dashboard, displays metrics, uses backtesting data for visualization

**Critical**: Strategies fetch from different tables based on mode via `self.mode` in [base_strategy.py](../src/core/base_strategy.py#L27-L31).

---

## Configuration & Initialization

### config.yaml Structure
```yaml
pairs:
  - symbol: BTCUSD
    timeframe: 15      # Minutes; stored as "M15" in DB
  - symbol: BTCUSD
    timeframe: 60      # Stored as "H1"
strategies:
  - name: rsi          # Must match factory key & .py filename (lowercase)
    params:            # Passed to strategy __init__
      period: 14
      overbought: 70
      volume: 0.01
```

### MT5 Credentials
- **Source Priority**: Environment variables (`MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`) > config.yaml
- **Loaded by**: [MT5Connector.__init__](../src/mt5_connector.py#L20-L30)
- **Terminal Requirement**: MT5 must be running in Windows; bot connects locally

---

## Database Schema (SQLite)

### market_data (live) & backtest_market_data (historical)
```sql
CREATE TABLE market_data (
  symbol TEXT,           -- "BTCUSD", "EURUSD", etc.
  timeframe TEXT,        -- "M15", "H1", "D1" (minutes or hours)
  time TEXT PRIMARY KEY, -- ISO 8601 datetime
  open, high, low, close REAL,
  tick_volume INT
);
```

### strategies & positions tables
- **strategies**: Stores strategy name, params JSON, score, status (live/backtest)
- **positions**: Tracks open trades with entry_time, volume, symbol, strategy_id

---

## Critical Workflows

### Live Trading Loop ([main.py](../src/main.py#L54-L61))
```python
while True:
    data_fetcher.sync_data()      # Pulls latest OHLCV from MT5
    trader.execute_trades(strategy_name)  # Checks all signals
    trade_monitor.monitor_positions()     # Closes exits
    time.sleep(20)                # Update interval (configurable)
```

### Backtesting Optimization ([BacktestManager.optimize](../src/backtesting/backtest_manager.py#L150+))
- Iterates parameter combinations from config.yaml `backtesting.optimization.*`
- Runs Backtest class (external library), calculates Sharpe ratio/returns
- Saves optimal params to `optimal_params` table

### Data Sync for Backtesting
```powershell
python -m src.backtesting.backtest_manager --mode sync --symbol BTCUSD
```
Copies live `market_data` → `backtest_market_data` to prevent test contamination.

---

## Environment Setup

### Python & Dependencies
- **Python Version**: 3.10+ required (3.10.x recommended for compatibility with MetaTrader5 & backtesting.py)
- **Platform**: Windows only (MT5 terminal is Windows-only)
- **Virtual Environment**: Always use `.venv` (created with `python -m venv .venv`)

### Package Incompatibilities & Known Issues
- **MetaTrader5 (MT5)**: 
  - Windows-only; will fail on macOS/Linux
  - Requires MetaTrader 5 terminal running in background
  - Python 3.11+ may have compatibility issues; stick with 3.10.x for stability
  - Import fails silently if MT5 not installed; check logs carefully
- **PyQt5 vs backtesting.py**: Both heavy dependencies; install in order: `pip install -r requirements.txt`
- **numba (JIT compiler)**: Required for backtesting.py performance; uses `@jit` decorators
- **ta (technical-analysis)**: Must be installed; RSI, MACD indicators depend on it

### Validation Commands
```powershell
# Verify Python version
python --version  # Should be 3.10.x

# Verify MT5 installation (will fail if MT5 not running)
python -c "import MetaTrader5 as mt5; print('MT5 OK' if mt5 else 'MT5 Missing')"

# Verify all packages
pip list | findstr "MetaTrader5 pandas PyQt5 backtesting ta"
```

---

## Error Handling

### MT5 Connection Loss (Critical)
**Scenario**: `MT5Connector.initialize()` returns `False` or MT5 disconnect during live trading

**Handling in [MT5Connector](../src/mt5_connector.py#L36-L65)**:
- Logs error code & message from `mt5.last_error()`
- Checks: Terminal running? Credentials correct? Network accessible?
- **Agent Action**: Don't retry immediately; wait 30s before retry (exponential backoff)
- **Impact**: Live trades halt until reconnected; positions not managed

**Prevention**:
```python
# Before live trading, validate MT5 is accessible
if not mt5_conn.initialize():
    raise RuntimeError("MT5 unavailable - check terminal, credentials, network")
```

### Data Gaps (Non-Critical but Impactful)
**Scenario**: `fetch_market_data()` returns empty DataFrame or <5000 rows

**Handling in [DataValidator](../src/utils/data_validator.py#L80-L120)**:
- Detects row count < 5000 per symbol/timeframe
- Auto-fetches from MT5 via `_fetch_and_sync()`
- Logs warning; strategy proceeds with available data (not ideal but operational)

**Agent Action**: When adding new pairs:
- [ ] Ensure config.yaml has `fetch_limit: 1000` or higher
- [ ] Run `DataValidator.validate_and_init()` on startup (auto-fills gaps)
- [ ] Check `data.empty` in strategies before calculating indicators

```python
# Safe pattern in strategy:
data = self.fetch_data(symbol)
if data.empty:
    self.logger.warning("No data for %s", symbol)
    return None  # Skip signal generation
```

### Invalid Symbol (Runtime Error)
**Scenario**: Symbol not in MT5 (e.g., typo "BTCUD" vs "BTCUSD"), or `mt5.symbol_info_tick()` returns None

**Handling in [MT5Connector.place_order()](../src/mt5_connector.py#L155-L180)**:
- `mt5.symbol_info_tick(symbol)` returns None if symbol invalid
- Logs error; order placement fails
- **Agent Action**: Validate symbol in config.yaml against MT5's symbol list before trading

```python
# Validation in strategy or trader:
tick = mt5.symbol_info_tick(symbol)
if tick is None:
    logger.error("Symbol %s not found in MT5", symbol)
    return False
```

### Strategy Signal Validation (Logic Error)
**Scenario**: Strategy returns malformed signal (missing "action", wrong volume, etc.)

**Handling in [Trader.execute_trades()](../src/core/trader.py#L28-L50)**:
- Trader expects: `{"action": "buy|sell", "symbol": "...", "volume": float}`
- Missing fields cause KeyError; caught but not traded
- **Agent Action**: All strategies MUST return dict with required keys

```python
# Always validate signal in strategy:
signal = {
    "action": "buy",     # REQUIRED
    "symbol": symbol,    # REQUIRED
    "volume": 0.01,      # REQUIRED
    "reason": "RSI > 70" # Optional
}
if not all(k in signal for k in ["action", "symbol", "volume"]):
    return None  # Skip malformed signal
```

### Weekend Trading on Forex/Commodities (Business Logic Error)
**Scenario**: Live trader attempts EURUSD trade on Friday 6 PM UTC

**Handling in [Trader.execute_trades()](../src/core/trader.py#L30-L35)**:
- `TradingRules.can_trade(symbol)` returns False for forex/commodities on weekends
- Trade blocked; logged as warning
- **Agent Action**: Check symbol type in TradingRules before adding new pairs

```python
# In TradingRules:
FOREX_SYMBOLS = {"EURUSD", "GBPUSD", "USDJPY", ...}
CRYPTO_SYMBOLS = {"BTCUSD", "ETHUSD", ...}
# Crypto: always tradeable
# Forex/Commodities: blocked Friday 5 PM UTC - Sunday 5 PM UTC
```

### Backtest Data Mismatch (Configuration Error)
**Scenario**: Attempting backtest on symbol with no `backtest_market_data` rows

**Handling in [DataHandler.prepare_backtest_data()](../src/core/data_handler.py#L20-L40)**:
- Queries `backtest_market_data` table; returns None if empty
- Logs warning with sync command: `python -m src.backtesting.backtest_manager --mode sync --symbol BTCUSD`
- **Agent Action**: Always sync backtest data before running optimization

```powershell
# REQUIRED: Sync before backtest
python -m src.backtesting.backtest_manager --mode sync --symbol BTCUSD
```

---

## Testing & Validation

### Run Full Test Suite
```powershell
python test_bot.py
```
Validates: data initialization (5000+ rows), weekend rules, backtest readiness, strategy loading.

### Data Initialization
- [DataValidator](../src/utils/data_validator.py) auto-fills missing data on startup
- Target: 5000 rows per symbol/timeframe via MT5 fetch (`fetch_limit: 1000` in config)
- Stored immediately in `market_data` table

---

## Common Pitfalls & Design Notes

### TradingRules Enforcement
- **Crypto** (BTCUSD, ETHUSD): Always tradeable (24/7)
- **Forex/Commodities** (EURUSD, XAUUSD): Blocked on weekends (Friday 5 PM UTC → Sunday 5 PM UTC)
- See [trading_rules.py](../src/utils/trading_rules.py#L30-L60) for symbol classification

### Mode-Specific Behavior
- Strategies automatically select `market_data` (live) vs `backtest_market_data` based on `self.mode`
- DataHandler renames DB columns to match backtesting.py requirements (e.g., "close" → "Close")
- Do NOT mix live/backtest data tables in strategy logic

### Strategy Signal Format
All strategies must return consistent signal dict:
```python
{"action": "buy|sell|hold", "symbol": "BTCUSD", "volume": 0.01, "reason": "RSI > 70"}
```
Trader validates signal before execution.

---

## Key Files Reference

- **Entry Point**: [src/main.py](../src/main.py) - argument parsing, component initialization
- **Config**: [src/config/config.yaml](../src/config/config.yaml) - strategy params, MT5 credentials, data ranges
- **Tests**: [test_bot.py](../test_bot.py) - validation suite; run before deployment
- **CLI**: [src/ui/cli.py](../src/ui/cli.py) - argument parser for --mode, --strategy flags
- **GUI**: [src/ui/gui/dashboard.py](../src/ui/gui/dashboard.py) - PyQt5 interface (optional)

---

## Development Checklist

When adding features:
- [ ] Update config.yaml if adding new params or symbols
- [ ] Add strategy to factory.py if implementing new strategy
- [ ] Test with `python test_bot.py` before live trading
- [ ] Check TradingRules for symbol type if adding new pairs
- [ ] Verify backtesting sync via `backtest_manager --mode sync`
- [ ] Log all decision points for debugging (see logger.py setup)
