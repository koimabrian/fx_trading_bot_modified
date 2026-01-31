# AI Copilot Instructions for FX Trading Bot

## Project Overview
**FX Trading Bot** is an automated Forex/cryptocurrency trading system with MetaTrader5 integration. It combines backtesting, live trading with adaptive strategy selection, and professional dashboards. Status: ✅ Production Ready (Pylint 9.78/10, 55/55 unit tests passing).

## Architecture

### Core Components (Layer Model)
```
UI Layer (PyQt5 GUI + Flask Web Dashboard)
    ↓
Trading Engine (AdaptiveTrader + StrategyManager)
    ↓
Signal & Data Layer (DataFetcher + Indicators)
    ↓
MT5 Integration (MT5Connector + MT5Decorator)
    ↓
Database Layer (DatabaseManager + Migrations)
```

### Key Directories
- **src/core/** - Trading logic: `adaptive_trader.py`, `trader.py`, `strategy_selector.py`, `data_fetcher.py`
- **src/strategies/** - Strategy implementations (RSI, MACD, EMA, Bollinger Bands)
- **src/backtesting/** - Backtest execution: `backtest_manager.py`, `metrics_engine.py`
- **src/utils/** - Shared utilities with centralized patterns (see Patterns below)
- **src/database/** - SQLite schema and migrations
- **src/ui/** - CLI, PyQt5 wizard, Flask web dashboard
- **tests/** - Unit, integration, performance, E2E tests (55/55 passing)

### Operating Modes (via `python -m src.main --mode <MODE>`)
| Mode | Purpose | Entry Point |
|------|---------|-------------|
| `init` | PyQt5 wizard: DB setup + symbol discovery | `src/main.py:_mode_init()` |
| `sync` | Incremental MT5 data fetch | `src/main.py:_mode_sync()` |
| `backtest` | Historical optimization (parameter archiving) | `src/main.py:_mode_backtest()` |
| `live` | Real-time adaptive trading | `src/main.py:_mode_live()` |
| `gui` | Flask web dashboard (port 5000) | `src/main.py:_mode_gui()` |
| `test` | Full pytest suite | `run_tests.py` |

## Critical Patterns & Conventions

### 1. Singleton Pattern (ConfigManager, MT5Connector)
```python
# CORRECT: Cache config once, reuse everywhere
config = ConfigManager.get_config()  # Loads once, caches internally

# WRONG: Avoid reloading YAML in loops
for symbol in symbols:
    config = yaml.safe_load(open("config.yaml"))  # ✗ Inefficient
```
**Files:** `src/utils/config_manager.py` (2,540x cache speedup), `src/mt5_connector.py`

### 2. Centralized Logging (LoggingFactory)
```python
# ALWAYS use LoggingFactory, NEVER raw logging module
from src.utils.logging_factory import LoggingFactory
logger = LoggingFactory.get_logger(__name__)

# At app startup (only once):
LoggingFactory.configure(level="INFO", log_dir="logs")
```
**Files:** `src/utils/logging_factory.py`, `src/main.py` (6,015 msg/sec throughput)

### 3. MT5 Automatic Retry Decorator
```python
# Apply @mt5_safe to any MT5 operation (auto-reconnect + exponential backoff)
@mt5_safe(max_retries=5, retry_delay=2.0, backoff=True)
def place_order(self, symbol, volume, side):
    ticket = mt5.order_send(request)
    return ticket
```
**File:** `src/utils/mt5_decorator.py` (eliminates boilerplate error handling)

### 4. Centralized Error Handling (ErrorHandler)
```python
# Map errors to severity levels (RECOVERABLE, WARNING, CRITICAL, IGNORE)
error_handler = ErrorHandler()
error_handler.handle(ValueError("invalid params"), operation="trade_placement")
# Auto-logs, auto-retries if RECOVERABLE, stops if CRITICAL
```
**File:** `src/utils/error_handler.py`

### 5. Adaptive Strategy Selection
The system queries **historical backtest results** to auto-select best strategies:
```python
# In AdaptiveTrader._trade_symbol():
# 1. Query top strategies by volatility rank + score
# 2. Load strategy instance from cache or factory
# 3. Execute with confidence-based position sizing
```
**Files:** `src/core/adaptive_trader.py`, `src/core/strategy_selector.py`

### 6. MT5 SafeGuards
- **Connection:** Always wrapped by `@mt5_safe` decorator
- **Timeframe validation:** Via `src/utils/timeframe_utils.py`
- **Symbol validation:** Via `src/utils/data_validator.py`
- **Order lifecycle:** Tracked in `src/core/trade_manager.py`

## Testing Patterns

### Test Organization
- **Unit tests** (55 passing): `tests/unit/*.py` - Config, DB, utilities, strategies
- **Integration tests**: `tests/integration/*.py` - Live trader, data sync, diagnostics
- **Performance tests**: `tests/performance/*.py` - Concurrent load (5/5 scenarios pass)
- **E2E tests**: `tests/e2e/*.py` - Symbol filtering pipeline

### Running Tests
```bash
# All tests
python run_tests.py

# Specific category
python -m pytest tests/unit -v
python -m pytest tests/integration -v
pytest tests/performance/test_high_load_scenarios.py
```

### Test Coverage Gaps
**Critical untested modules (add tests before modifying):**
- `src/core/adaptive_trader.py` (10+ test cases needed)
- `src/core/trader.py` (10+ test cases needed)
- `src/core/data_fetcher.py` (12+ test cases needed)
- `src/backtesting/metrics_engine.py` (10+ test cases needed)

## Critical Workflows

### Adding a New Strategy
1. Create `src/strategies/my_strategy.py` inheriting `BaseStrategy`
2. Implement `generate_signals(df) → {'BUY': [...], 'SELL': [...]}`
3. Register in `src/strategies/factory.py` (StrategyFactory.STRATEGIES dict)
4. Backtest via `python -m src.main --mode backtest --strategy my_strategy`
5. Rankings stored in DB; AdaptiveTrader auto-selects on next `live` run

### Modifying Database Schema
1. Create migration in `src/database/migrations.py`
2. Call `DatabaseMigrations.apply_migrations()` in `src/main.py` startup
3. Update `src/database/db_manager.py` query methods
4. Add tests in `tests/unit/test_config_and_db.py`

### Adding MT5 Operations
1. Wrap new method with `@mt5_safe(max_retries=5, retry_delay=2.0)`
2. Use `MT5Connector.get_instance()` for singleton access
3. Log errors via `LoggingFactory.get_logger()`
4. Handle `ConnectionError`, `TimeoutError` via ErrorHandler

## Key Files Reference

| File | Purpose | Key Pattern |
|------|---------|-------------|
| [src/main.py](src/main.py) | Entry point, mode routing | 6 operational modes |
| [src/utils/config_manager.py](src/utils/config_manager.py) | Config singleton | Caching + YAML parsing |
| [src/utils/logging_factory.py](src/utils/logging_factory.py) | Centralized logging | Single configure() call |
| [src/utils/mt5_decorator.py](src/utils/mt5_decorator.py) | MT5 retry logic | Exponential backoff |
| [src/utils/error_handler.py](src/utils/error_handler.py) | Error mapping | Severity-based responses |
| [src/core/adaptive_trader.py](src/core/adaptive_trader.py) | Trading engine | Strategy auto-selection |
| [src/database/db_manager.py](src/database/db_manager.py) | SQLite access | Context manager pattern |
| [tests/unit/](tests/unit/) | Unit tests | Import, config, strategies |

## Configuration (config.yaml)
```yaml
# src/config/config.yaml structure
trading:
  symbol_list: [EURUSD, GBPUSD, ...]
  timeframes: [H1, H4, D1]
  leverage: 30
  lot_size: 0.1
backtesting:
  start_date: 2023-01-01
  end_date: 2024-01-01
  initial_balance: 10000
mt5:
  server: "Your Broker MT5 Server"
  account: YOUR_ACCOUNT_NUMBER
  password: "YOUR_PASSWORD"
```

## External Dependencies
- **MetaTrader5** (>=5.0.0) - Trading platform integration
- **pytest** (9.0.0) - Testing framework
- **Flask** (>=2.0.0) - Web dashboard
- **Plotly** (>=5.0.0) - Charts
- **PyQt5** (>=5.15.0) - Init wizard GUI
- **pandas, scikit-learn, numba** - Data analysis

## Common Pitfalls to Avoid
1. ❌ Don't use `yaml.safe_load()` directly → ✅ Use `ConfigManager.get_config()`
2. ❌ Don't create multiple MT5Connector instances → ✅ Use singleton via `get_instance()`
3. ❌ Don't catch generic exceptions → ✅ Use ErrorHandler with severity levels
4. ❌ Don't log with `print()` → ✅ Use LoggingFactory
5. ❌ Don't assume MT5 stays connected → ✅ Always use `@mt5_safe` decorator
6. ❌ Don't modify DB schema without migrations → ✅ Add to migrations.py first

## Debugging Commands
```bash
# Check MT5 connection
python -c "from src.mt5_connector import MT5Connector; MT5Connector.get_instance().initialize()"

# Run specific test
python -m pytest tests/unit/test_config_and_db.py::test_config_manager_singleton -v

# Check code quality
pylint src/ --disable=all --enable=E,F  # Errors & fatals only

# View logs
tail -f logs/trading_bot.log
```

---
**Last Updated:** 2026-01-31 | **Pylint:** 9.78/10 | **Tests:** 55/55 ✅
