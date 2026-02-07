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

### Key Directories & Components
- **src/main.py** - Entry point routing 6 operational modes (init, sync, backtest, live, gui, test)
- **src/core/** - Trading logic: `adaptive_trader.py`, `trader.py`, `strategy_selector.py`, `data_fetcher.py`, `trade_manager.py`
- **src/strategies/** - Strategy implementations (RSI, MACD, EMA, Bollinger Bands) with factory pattern
- **src/backtesting/** - Backtest execution: `backtest_manager.py`, `metrics_engine.py`, `backtest_orchestrator.py`
- **src/utils/** - **22 utility modules** with centralized patterns (config, logging, MT5 operations, error handling, exit strategies, etc.)
- **src/database/** - SQLite schema and migrations
- **src/ui/** - CLI, PyQt5 init wizard, Flask web dashboard with WebSocket support
- **tests/** - 55 passing tests (unit, integration, performance, E2E)

### Operating Modes (via `python -m src.main --mode <MODE>`)
| Mode | Purpose | Key Features |
|------|---------|-------------|
| `init` | PyQt5 wizard: DB setup + symbol discovery | Interactive GUI, auto-categorizes symbols by broker |
| `sync` | Incremental MT5 data fetch | Caches 20s, syncs only new data |
| `backtest` | Historical optimization | Parameter archiving, volatility ranking |
| `live` | Real-time adaptive trading | Auto-selects best strategies, confidence scoring |
| `gui` | Flask web dashboard (port 5000) | Real-time updates, Plotly charts, WebSocket |
| `test` | Full pytest suite | 55 tests, 5 concurrent load scenarios |

## Critical Patterns & Conventions

### 1. Singleton Pattern (ConfigManager, MT5Connector)
**File:** [src/utils/config_manager.py](src/utils/config_manager.py)

```python
# CORRECT: Cache config once, reuse everywhere
config = ConfigManager.get_config()  # Loads once, caches internally

# WRONG: Avoid reloading YAML in loops
for symbol in symbols:
    config = yaml.safe_load(open("config.yaml"))  # ✗ Inefficient
```
**Benefits:** 2,540x cache speedup. Used by 8+ modules for consistent config access.

### 2. Centralized Logging (LoggingFactory)
**File:** [src/utils/logging_factory.py](src/utils/logging_factory.py)

```python
# ALWAYS use LoggingFactory, NEVER raw logging module
from src.utils.logging_factory import LoggingFactory
logger = LoggingFactory.get_logger(__name__)

# At app startup (only once):
LoggingFactory.configure(level="INFO", log_dir="logs")
```
**Throughput:** 6,015 msg/sec verified under load. Eliminates print() statements entirely.

### 3. MT5 Automatic Retry Decorator
**File:** [src/utils/mt5_decorator.py](src/utils/mt5_decorator.py)

```python
# Apply @mt5_safe to any MT5 operation (auto-reconnect + exponential backoff)
@mt5_safe(max_retries=5, retry_delay=2.0, backoff=True)
def place_order(self, symbol, volume, side):
    ticket = mt5.order_send(request)
    return ticket
```
**Benefit:** Eliminates boilerplate error handling, handles connection dropouts transparently.

### 4. Centralized Error Handling (ErrorHandler)
**File:** [src/utils/error_handler.py](src/utils/error_handler.py)

```python
# Map errors to severity levels (RECOVERABLE, WARNING, CRITICAL, IGNORE)
from src.utils.error_handler import ErrorHandler
ErrorHandler.handle_error(ValueError("invalid params"), operation="trade_placement")
# Auto-logs, auto-retries if RECOVERABLE, stops if CRITICAL
```

### 5. Adaptive Strategy Selection
**Files:** [src/core/adaptive_trader.py](src/core/adaptive_trader.py), [src/core/strategy_selector.py](src/core/strategy_selector.py)

The system queries **historical backtest results** to auto-select best strategies:
```python
# In live mode:
# 1. Query top strategies by volatility rank + score from DB
# 2. Load strategy instance from cache or factory
# 3. Execute with confidence-based position sizing
# 4. Track performance, update rankings for next run
```
**Data Flow:** Backtest results → DB → StrategySelector → AdaptiveTrader → live trades

### 6. Trade Lifecycle Management
**Files:** [src/core/trade_manager.py](src/core/trade_manager.py), [src/core/trade_monitor.py](src/core/trade_monitor.py)

- **Position tracking:** Entry price, bars held, max profit/loss
- **Exit strategies:** Multiple exit types via [src/utils/exit_strategies.py](src/utils/exit_strategies.py)
- **Trade quality filter:** [src/utils/trade_quality_filter.py](src/utils/trade_quality_filter.py) validates confidence, win rate, Sharpe ratio

## Testing Patterns

### Test Organization (55 Tests, All Passing)
- **Unit tests:** [tests/unit/](tests/unit/) - Config, DB, utilities, strategies
- **Integration tests:** [tests/integration/](tests/integration/) - Live trader, data sync, diagnostics
- **Performance tests:** [tests/performance/](tests/performance/) - **5 concurrent load scenarios pass**
  - Concurrent logging (6,015 msg/sec)
  - Database queries (47,596 queries/sec)
  - ConfigManager access (56,848 accesses/sec)
- **E2E tests:** [tests/e2e/](tests/e2e/) - Symbol filtering pipeline

### Running Tests
```bash
# All tests (via run_tests.py)
python run_tests.py

# Specific category
python -m pytest tests/unit -v
python -m pytest tests/integration -v
python -m pytest tests/performance/test_high_load_scenarios.py -v

# Single test
python -m pytest tests/unit/test_config_and_db.py::test_config_manager_singleton -v
```

### Test Coverage Gaps
**Critical untested modules (add tests before modifying):**
- [src/core/adaptive_trader.py](src/core/adaptive_trader.py) (10+ test cases needed)
- [src/core/trader.py](src/core/trader.py) (10+ test cases needed)
- [src/core/data_fetcher.py](src/core/data_fetcher.py) (12+ test cases needed)
- [src/backtesting/metrics_engine.py](src/backtesting/metrics_engine.py) (10+ test cases needed)

## Critical Workflows

### Adding a New Strategy
1. Create [src/strategies/my_strategy.py](src/strategies/my_strategy.py) inheriting `BaseStrategy`
2. Implement `generate_entry_signal()` and `generate_exit_signal()` methods
3. Register in [src/strategies/factory.py](src/strategies/factory.py) (StrategyFactory.STRATEGIES dict)
4. Backtest via `python -m src.main --mode backtest --strategy my_strategy`
5. Rankings stored in DB; AdaptiveTrader auto-selects on next `live` run

### Modifying Database Schema
1. Create migration in [src/database/migrations.py](src/database/migrations.py)
2. Call `DatabaseMigrations.apply_migrations()` in [src/main.py](src/main.py) startup
3. Update [src/database/db_manager.py](src/database/db_manager.py) query methods
4. Add tests in [tests/unit/test_config_and_db.py](tests/unit/test_config_and_db.py)

### Adding MT5 Operations
1. Wrap new method with `@mt5_safe(max_retries=5, retry_delay=2.0)`
2. Use `MT5Connector.get_instance()` for singleton access (NOT creating new instances)
3. Log errors via `LoggingFactory.get_logger(__name__)`
4. Handle `ConnectionError`, `TimeoutError` via ErrorHandler

### Debugging Live Trading Issues
1. Check MT5 connection: `python -c "from src.mt5_connector import MT5Connector; MT5Connector.get_instance().initialize()"`
2. Run diagnostic: `python -m src.main --mode live --diagnostics`
3. View real-time logs: `tail -f logs/trading_bot.log`
4. Check dashboard: `http://127.0.0.1:5000` (start GUI mode in separate terminal)

## Key Files Reference

| File | Purpose | Pattern |
|------|---------|---------|
| [src/main.py](src/main.py) | Entry point, mode routing | 6 modes, setup_parser() |
| [src/utils/config_manager.py](src/utils/config_manager.py) | Config singleton | get_config() caching |
| [src/utils/logging_factory.py](src/utils/logging_factory.py) | Centralized logging | configure() once per startup |
| [src/utils/mt5_decorator.py](src/utils/mt5_decorator.py) | MT5 retry logic | @mt5_safe decorator |
| [src/utils/error_handler.py](src/utils/error_handler.py) | Error mapping | Severity levels (RECOVERABLE, CRITICAL) |
| [src/core/adaptive_trader.py](src/core/adaptive_trader.py) | Trading engine | Strategy cache, auto-selection |
| [src/core/strategy_selector.py](src/core/strategy_selector.py) | Strategy ranking | Query DB for top performers |
| [src/core/trader.py](src/core/trader.py) | Trade execution | Position limits, trading rules |
| [src/core/trade_manager.py](src/core/trade_manager.py) | Position management | Exit strategies, profit tracking |
| [src/database/db_manager.py](src/database/db_manager.py) | SQLite access | Context manager, migrations |
| [src/strategies/factory.py](src/strategies/factory.py) | Strategy factory | StrategyFactory.create_strategy() |
| [tests/unit/](tests/unit/) | Unit tests | Mocks, fixtures, config testing |

## Configuration (config.yaml)
**Location:** [src/config/config.yaml](src/config/config.yaml)

```yaml
trading:
  symbol_list: [EURUSD, GBPUSD, USDJPY]  # Configured via init GUI, stored in DB
  timeframes: [H1, H4, D1]
  leverage: 30
  lot_size: 0.1
  max_positions: 10
  min_signal_confidence: 0.6
  aggressive_mode: false

backtesting:
  start_date: 2023-01-01
  end_date: 2024-01-01
  initial_balance: 10000
  max_drawdown_pct: 10.0

mt5:
  server: "Your Broker MT5 Server"
  account: YOUR_ACCOUNT_NUMBER
  password: "YOUR_PASSWORD"

strategies:
  - name: rsi
    enabled: true
    params:
      period: 14
      overbought: 70
      oversold: 30
  # ... more strategies
```

## External Dependencies & Performance
- **MetaTrader5** (>=5.0.0) - Trading platform integration
- **Flask** (>=2.0.0) - Web dashboard with WebSocket
- **PyQt5** (>=5.15.0) - Init wizard GUI
- **pandas, numpy, scikit-learn** - Data analysis
- **pytest** (9.0.0) - Testing framework

**Verified Performance:**
- Data cache TTL: 20 seconds
- Dashboard response: ~50ms
- Signal generation: <100ms per symbol
- Backtest speed: ~30s per symbol/timeframe/strategy

## Common Pitfalls to Avoid
1. ❌ Don't use `yaml.safe_load()` directly → ✅ Use `ConfigManager.get_config()`
2. ❌ Don't create multiple MT5Connector instances → ✅ Use singleton via `get_instance()`
3. ❌ Don't catch generic exceptions → ✅ Use ErrorHandler with severity levels
4. ❌ Don't log with `print()` → ✅ Use LoggingFactory
5. ❌ Don't assume MT5 stays connected → ✅ Always use `@mt5_safe` decorator
6. ❌ Don't modify DB schema without migrations → ✅ Add to migrations.py first
7. ❌ Don't reload config in loops → ✅ Load once, cache reference
8. ❌ Don't hard-code file paths → ✅ Use Path or os.path relative to project root

## Debugging Commands
```bash
# Check MT5 connection
python -c "from src.mt5_connector import MT5Connector; MT5Connector.get_instance().initialize()"

# Run specific test with verbose output
python -m pytest tests/unit/test_config_and_db.py::test_config_manager_singleton -v

# Check code quality (errors & fatals only)
pylint src/ --disable=all --enable=E,F

# View logs in real-time
tail -f logs/trading_bot.log

# Run performance tests
python -m pytest tests/performance/test_high_load_scenarios.py -v

# Check which strategies passed backtest
python -c "from src.database.db_manager import DatabaseManager; db = DatabaseManager(); print(db.get_optimal_parameters())"
```

---
**Last Updated:** 2026-02-01 | **Pylint:** 9.78/10 | **Tests:** 55/55 ✅ | **Load Tests:** 5/5 ✅
