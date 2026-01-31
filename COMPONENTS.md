# FX Trading Bot - System Components Documentation

**Version:** 2.0  
**Last Updated:** January 31, 2026  
**Purpose:** Reference guide for understanding system architecture, component responsibilities, and dependencies.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Layers](#architecture-layers)
3. [Core Components](#core-components)
4. [Strategy System](#strategy-system)
5. [Backtesting System](#backtesting-system)
6. [Database Layer](#database-layer)
7. [User Interface Components](#user-interface-components)
8. [Utility Components](#utility-components)
9. [Data Flow](#data-flow)
10. [Component Dependencies](#component-dependencies)
11. [Testing Components](#testing-components)

---

## System Overview

The FX Trading Bot is a production-ready automated trading system with MetaTrader5 integration. It operates in 6 distinct modes, each orchestrated by the main entry point.

### Operating Modes

| Mode | Purpose | Entry Point | Key Components |
|------|---------|-------------|----------------|
| **init** | Database setup + symbol discovery | `src/main.py:_mode_init()` | InitManager, InitWizardDialog, MT5Connector |
| **sync** | Incremental MT5 data fetch | `src/main.py:_mode_sync()` | DataFetcher, DataValidator, DatabaseManager |
| **backtest** | Historical optimization | `src/main.py:_mode_backtest()` | BacktestManager, MetricsEngine, StrategyFactory |
| **live** | Real-time adaptive trading | `src/main.py:_mode_live()` | AdaptiveTrader, StrategySelector, Trader |
| **gui** | Web dashboard (port 5000) | `src/main.py:_mode_gui()` | DashboardServer, LiveBroadcaster |
| **test** | Full pytest suite | `run_tests.py` | All test modules |

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    UI Layer (PyQt5 + Flask)                  │
│  InitWizardDialog │ DashboardServer │ LiveBroadcaster       │
└───────────────────────────────┬─────────────────────────────┘
                                 │
┌───────────────────────────────┴─────────────────────────────┐
│                   Trading Engine Layer                       │
│  AdaptiveTrader │ Trader │ StrategyManager │ StrategySelector│
└───────────────────────────────┬─────────────────────────────┘
                                 │
┌───────────────────────────────┴─────────────────────────────┐
│              Signal & Data Processing Layer                  │
│  DataFetcher │ DataHandler │ BaseStrategy │ Indicators      │
└───────────────────────────────┬─────────────────────────────┘
                                 │
┌───────────────────────────────┴─────────────────────────────┐
│                 MT5 Integration Layer                        │
│         MT5Connector │ MT5Decorator (retry logic)           │
└───────────────────────────────┬─────────────────────────────┘
                                 │
┌───────────────────────────────┴─────────────────────────────┐
│                    Database Layer (SQLite)                   │
│    DatabaseManager │ Migrations │ Context Managers          │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Entry Point & Orchestration

#### **src/main.py**
- **Responsibility:** Central orchestrator for all operating modes
- **Key Functions:**
  - `main()` - Parses CLI arguments and routes to mode handlers
  - `_mode_init()` - Launches initialization wizard
  - `_mode_sync()` - Executes data synchronization
  - `_mode_backtest()` - Runs backtesting pipeline
  - `_mode_live()` - Starts live trading engine
  - `_mode_gui()` - Launches web dashboard
  - `_mode_test()` - Executes test suite
- **Dependencies:** All mode-specific components
- **Startup Actions:** 
  - Applies database migrations
  - Configures logging via LoggingFactory
  - Validates MT5 connection (for trading modes)

---

### 2. Trading Engine Components

#### **src/core/adaptive_trader.py** - AdaptiveTrader
- **Responsibility:** Intelligent live trading with automatic strategy selection
- **Key Features:**
  - Queries best strategies from backtest results
  - Loads strategy instances from cache or factory
  - Executes trades with confidence-based position sizing
  - Manages position limits per asset class
- **Key Methods:**
  - `execute_trades()` - Main trading loop
  - `_trade_symbol()` - Per-symbol trading logic
  - `_get_best_strategies()` - Strategy selection via StrategySelector
- **Dependencies:**
  - StrategySelector (strategy ranking)
  - StrategyManager (signal generation)
  - Trader (trade execution)
  - TradingRules (market hours validation)
  - DatabaseManager (backtest results lookup)
- **Affected By Changes To:**
  - Strategy implementations (signal generation logic)
  - StrategySelector (ranking algorithms)
  - TradingRules (trading restrictions)
  - Database schema (backtest_backtests table)

#### **src/core/trader.py** - Trader
- **Responsibility:** Trade execution and position management
- **Key Features:**
  - Position limit enforcement
  - Stop loss and take profit placement
  - Trading rules validation (weekend blocks, etc.)
  - Order lifecycle management
- **Key Methods:**
  - `execute_trades()` - Execute signals from strategy
  - `_place_order()` - MT5 order placement wrapper
  - `_check_position_limits()` - Validate against max positions
- **Dependencies:**
  - MT5Connector (order placement)
  - TradingRules (market hours)
  - DatabaseManager (trade recording)
  - ConfigManager (risk parameters)
- **Affected By Changes To:**
  - MT5Connector (connection handling)
  - TradingRules (validation logic)
  - Risk management parameters

#### **src/core/strategy_selector.py** - StrategySelector
- **Responsibility:** Ranks strategies based on backtest performance
- **Key Features:**
  - Queries `optimal_parameters` and `backtest_backtests` tables
  - Ranks by Sharpe ratio, win rate, profit factor
  - Supports volatility-based filtering
  - Caches results for performance
- **Key Methods:**
  - `get_best_strategies()` - Returns top N strategies for symbol/timeframe
  - `_calculate_confidence()` - Computes confidence score (0.5-0.9 range)
- **Dependencies:**
  - DatabaseManager (backtest results)
- **Affected By Changes To:**
  - Database schema (backtest tables)
  - Ranking algorithms
  - Confidence scoring formulas

#### **src/strategy_manager.py** - StrategyManager
- **Responsibility:** Strategy loading, data caching, signal generation
- **Key Features:**
  - Loads strategies via StrategyFactory
  - Caches market data (20s TTL)
  - Generates BUY/SELL signals
  - Handles timeframe conversions
- **Key Methods:**
  - `generate_signals()` - Main signal generation
  - `_load_strategy()` - Strategy instantiation
  - `_get_cached_data()` - Data caching logic
- **Dependencies:**
  - StrategyFactory (strategy creation)
  - DataFetcher (market data)
  - ConfigManager (timeframe settings)
- **Affected By Changes To:**
  - Strategy implementations
  - Data fetching logic
  - Caching parameters

---

### 3. Data Layer Components

#### **src/core/data_fetcher.py** - DataFetcher
- **Responsibility:** Market data retrieval from MT5 or database
- **Key Features:**
  - MT5 live data fetching
  - Database historical data queries
  - Data validation (sufficient candles)
  - Timeframe conversion support
- **Key Methods:**
  - `fetch_data()` - Main data retrieval
  - `_fetch_from_mt5()` - Live MT5 data
  - `_fetch_from_database()` - Historical DB data
- **Dependencies:**
  - MT5Connector (live data)
  - DatabaseManager (historical data)
  - TimeframeUtils (timeframe validation)
- **Affected By Changes To:**
  - MT5 API changes
  - Database schema (market_data table)
  - Timeframe definitions

#### **src/core/data_handler.py** - DataHandler
- **Responsibility:** Prepares data for backtesting
- **Key Features:**
  - Reads from `market_data` table
  - Formats for backtesting framework
  - Date range filtering
  - Data quality validation
- **Key Methods:**
  - `prepare_backtest_data()` - Main data preparation
- **Dependencies:**
  - DatabaseManager (data queries)
- **Affected By Changes To:**
  - Database schema
  - Backtesting framework requirements

#### **src/core/init_manager.py** - InitManager
- **Responsibility:** System initialization logic
- **Key Features:**
  - Database schema creation
  - Symbol discovery from MT5
  - Category auto-detection
  - Trading pair storage
- **Key Methods:**
  - `initialize_database()` - DB setup
  - `discover_symbols()` - MT5 symbol discovery
  - `save_selected_symbols()` - Store to tradable_pairs
- **Dependencies:**
  - DatabaseManager (schema creation)
  - MT5Connector (symbol discovery)
  - DatabaseMigrations (schema versioning)
- **Affected By Changes To:**
  - Database schema
  - MT5 symbol filtering logic
  - Category detection rules

---

## Strategy System

### Architecture

```
BaseStrategy (abstract)
    ↓ (inheritance)
┌───┴───┬───────┬─────────┐
│       │       │         │
RSI    MACD    EMA       SMA
```

### **src/core/base_strategy.py** - BaseStrategy
- **Responsibility:** Abstract base class for all strategies
- **Key Features:**
  - Defines strategy interface
  - Common signal generation pattern
  - Parameter validation
- **Key Methods:**
  - `generate_signals()` - Abstract method (must override)
  - `calculate_indicators()` - Abstract method (must override)
- **Used By:** All strategy implementations

### **src/strategies/factory.py** - StrategyFactory
- **Responsibility:** Strategy instantiation and registration
- **Key Features:**
  - Registry pattern (STRATEGIES dict)
  - Dynamic strategy creation
  - Parameter passing
- **Key Methods:**
  - `create_strategy()` - Factory method
  - `get_available_strategies()` - List registered strategies
- **Strategies Registered:**
  - `RSI` → RSIStrategy
  - `MACD` → MACDStrategy
  - `EMA` → EMAStrategy
  - `SMA` → SMAStrategy
- **Affected By Changes To:**
  - New strategy additions (must register)
  - Strategy parameter changes

### Strategy Implementations

#### **src/strategies/rsi_strategy.py** - RSIStrategy
- **Indicators:** RSI (Relative Strength Index)
- **Signals:** BUY when RSI < oversold, SELL when RSI > overbought
- **Parameters:** `rsi_period`, `rsi_oversold`, `rsi_overbought`

#### **src/strategies/macd_strategy.py** - MACDStrategy
- **Indicators:** MACD line, Signal line, Histogram
- **Signals:** BUY on bullish crossover, SELL on bearish crossover
- **Parameters:** `fast_period`, `slow_period`, `signal_period`

#### **src/strategies/ema_strategy.py** - EMAStrategy
- **Indicators:** EMA fast, EMA slow
- **Signals:** BUY on golden cross, SELL on death cross
- **Parameters:** `ema_fast`, `ema_slow`

#### **src/strategies/sma_strategy.py** - SMAStrategy
- **Indicators:** SMA short, SMA long
- **Signals:** BUY on moving average crossover, SELL on crossunder
- **Parameters:** `sma_short`, `sma_long`

---

## Backtesting System

### **src/backtesting/backtest_manager.py** - BacktestManager
- **Responsibility:** Core backtesting engine
- **Key Features:**
  - Strategy execution on historical data
  - Parameter grid search
  - Performance metrics calculation
  - Result storage in database
- **Key Methods:**
  - `run_backtest()` - Main backtest execution
  - `_optimize_parameters()` - Parameter search
  - `_archive_results()` - Store to database
- **Dependencies:**
  - DataHandler (data preparation)
  - StrategyFactory (strategy instances)
  - MetricsEngine (performance calculations)
  - ParameterArchiver (result storage)
- **Affected By Changes To:**
  - Strategy implementations
  - Metrics calculations
  - Database schema (backtest tables)

### **src/backtesting/backtest_orchestrator.py** - BacktestOrchestrator
- **Responsibility:** Multi-symbol/timeframe orchestration
- **Key Features:**
  - Parallel backtest execution
  - Progress tracking
  - Result aggregation
- **Key Methods:**
  - `orchestrate_backtests()` - Run all combinations
- **Dependencies:**
  - BacktestManager (individual backtests)
- **Affected By Changes To:**
  - BacktestManager interface

### **src/backtesting/metrics_engine.py** - MetricsEngine
- **Responsibility:** Performance metrics calculation
- **Key Metrics:**
  - Sharpe Ratio
  - Win Rate
  - Profit Factor
  - Maximum Drawdown
  - Total Return
  - Average Trade Duration
- **Key Methods:**
  - `calculate_metrics()` - Main calculation
  - `_calculate_sharpe_ratio()` - Risk-adjusted return
  - `_calculate_max_drawdown()` - Worst peak-to-trough
- **Dependencies:**
  - None (pure calculation)
- **Used By:** BacktestManager, StrategySelector
- **Affected By Changes To:**
  - Metric formula changes
  - New metric additions

### **src/backtesting/trade_logger.py** - TradeLogger
- **Responsibility:** Trade recording during backtests
- **Key Features:**
  - Trade entry/exit logging
  - P&L calculation
  - Trade audit trail
- **Key Methods:**
  - `log_trade()` - Record trade
- **Dependencies:**
  - DatabaseManager (trade storage)

---

## Database Layer

### **src/database/db_manager.py** - DatabaseManager
- **Responsibility:** SQLite3 database operations
- **Key Features:**
  - Connection pooling
  - Context manager pattern (auto-commit/rollback)
  - Thread-safe operations
  - Query execution wrappers
- **Key Methods:**
  - `execute_query()` - SELECT queries
  - `execute_update()` - INSERT/UPDATE/DELETE
  - `get_connection()` - Connection pool access
- **Database File:** `trading_bot.db`
- **Used By:** All components requiring data persistence
- **Affected By Changes To:**
  - Schema changes (requires migrations)
  - Query performance optimizations

### **src/database/migrations.py** - DatabaseMigrations
- **Responsibility:** Database schema management
- **Key Features:**
  - Schema versioning
  - Migration application
  - Rollback support
- **Key Methods:**
  - `apply_migrations()` - Execute pending migrations
  - `_create_schema_version_table()` - Version tracking
- **Schema Tables:**
  - `schema_version` - Migration tracking
  - `tradable_pairs` - Symbol selections
  - `market_data` - OHLCV historical data
  - `backtest_market_data` - Backtest data cache
  - `backtest_backtests` - Backtest results
  - `trades` - Trade audit trail
  - `optimal_parameters` - Best found parameters
  - `symbols` - Symbol metadata
- **Affected By Changes To:**
  - Schema requirements
  - New table additions

---

## User Interface Components

### Web Dashboard (Flask)

#### **src/ui/web/dashboard_server.py** - DashboardServer
- **Responsibility:** Flask web server for monitoring
- **Key Features:**
  - Real-time trade monitoring
  - Equity curve visualization
  - Backtest result display
  - Interactive filtering
- **Routes:**
  - `/` - Main dashboard
  - `/api/trades` - Trade data API
  - `/api/backtest_results` - Backtest results API
  - `/api/system_health` - System status
- **Port:** 5000 (default)
- **Dependencies:**
  - DashboardAPI (API logic)
  - LiveBroadcaster (WebSocket updates)
  - DatabaseManager (data queries)

#### **src/ui/web/dashboard_api.py** - DashboardAPI
- **Responsibility:** API endpoint logic
- **Key Features:**
  - Data aggregation
  - Performance calculations
  - Filtering and sorting
- **Dependencies:**
  - DatabaseManager (queries)
  - MetricsEngine (calculations)

#### **src/ui/web/live_broadcaster.py** - LiveBroadcaster
- **Responsibility:** WebSocket broadcasting for real-time updates
- **Key Features:**
  - Trade event broadcasting
  - System status updates
  - Client connection management
- **Dependencies:**
  - Flask-SocketIO

### GUI Components (PyQt5)

#### **src/ui/gui/init_wizard_dialog.py** - InitWizardDialog
- **Responsibility:** Interactive initialization wizard
- **Key Features:**
  - 6-step wizard UI
  - Symbol discovery from MT5
  - Multi-checkbox selection
  - Category-based organization
- **Steps:**
  1. Welcome
  2. System setup (DB + MT5 validation)
  3. Symbol discovery
  4. Symbol selection
  5. Review & confirm
  6. Success
- **Dependencies:**
  - InitManager (business logic)
  - MT5Connector (symbol discovery)
  - DatabaseManager (symbol storage)

#### **src/ui/gui/pair_selector_dialog.py** - PairSelectorDialog
- **Responsibility:** Symbol selection dialog
- **Key Features:**
  - Checkbox interface
  - Category grouping
  - Search/filter
- **Dependencies:**
  - DatabaseManager (tradable_pairs)

---

## Utility Components

### Configuration & Settings

#### **src/utils/config_manager.py** - ConfigManager
- **Responsibility:** Centralized configuration management
- **Key Features:**
  - Singleton pattern
  - YAML parsing with caching (2,540x speedup)
  - Environment variable overrides
  - Config validation
- **Key Methods:**
  - `get_config()` - Load/cache config
  - `reload()` - Force reload
- **Config File:** `src/config/config.yaml`
- **Used By:** All components
- **Performance:** 6.02K msg/sec throughput

#### **src/utils/logging_factory.py** - LoggingFactory
- **Responsibility:** Centralized logging setup
- **Key Features:**
  - Singleton pattern
  - File + console handlers
  - Log rotation
  - Performance: 6,015 msg/sec
- **Key Methods:**
  - `configure()` - Setup logging (call once at startup)
  - `get_logger()` - Get logger instance
- **Log Directory:** `logs/`
- **Used By:** All components

### MT5 Integration

#### **src/mt5_connector.py** - MT5Connector
- **Responsibility:** MetaTrader5 API wrapper
- **Key Features:**
  - Singleton pattern
  - Connection management
  - Order placement
  - Account information
  - Symbol data retrieval
- **Key Methods:**
  - `initialize()` - Connect to MT5
  - `place_order()` - Execute trade
  - `get_symbol_info()` - Symbol metadata
  - `get_account_info()` - Account status
- **Dependencies:**
  - MetaTrader5 Python package
- **Used By:**
  - Trader (order placement)
  - DataFetcher (market data)
  - InitManager (symbol discovery)

#### **src/utils/mt5_decorator.py** - MT5Decorator
- **Responsibility:** Automatic retry logic for MT5 operations
- **Key Features:**
  - `@mt5_safe` decorator
  - Exponential backoff
  - Connection error handling
  - Configurable retries (default: 5)
- **Usage Example:**
  ```python
  @mt5_safe(max_retries=5, retry_delay=2.0, backoff=True)
  def place_order(self, symbol, volume, side):
      return mt5.order_send(request)
  ```
- **Used By:** All MT5Connector methods

### Error Handling & Validation

#### **src/utils/error_handler.py** - ErrorHandler
- **Responsibility:** Centralized error management
- **Key Features:**
  - Error severity mapping (RECOVERABLE, WARNING, CRITICAL, IGNORE)
  - Automatic retry for recoverable errors
  - Logging integration
  - Operation context tracking
- **Key Methods:**
  - `handle()` - Main error handler
- **Used By:** All components

#### **src/utils/data_validator.py** - DataValidator
- **Responsibility:** Data quality validation
- **Key Features:**
  - Sufficient candle validation
  - Symbol validation
  - Timeframe validation
  - Data integrity checks
- **Key Methods:**
  - `validate_data()` - Main validation
- **Used By:**
  - DataFetcher
  - BacktestManager

### Trading Rules & Quality

#### **src/utils/trading_rules.py** - TradingRules
- **Responsibility:** Market hours and trading restrictions
- **Key Features:**
  - Weekend trading blocks (forex/commodities)
  - Holiday calendar
  - Category-based rules (crypto, forex, stocks, commodities, indices)
  - Session time validation
- **Key Methods:**
  - `can_trade()` - Validate if trading allowed
  - `get_category()` - Symbol categorization
- **Categories:** Loaded from `tradable_pairs.category` (database)
- **Used By:**
  - Trader (trade validation)
  - AdaptiveTrader (strategy selection)

#### **src/utils/trade_quality_filter.py** - TradeQualityFilter
- **Responsibility:** Optional trade quality filtering
- **Key Features:**
  - Volatility-based filtering
  - Time-of-day restrictions
  - Volume validation
- **Key Methods:**
  - `filter_trade()` - Quality check
- **Used By:** AdaptiveTrader (optional)

### Volatility & Analytics

#### **src/utils/volatility_manager.py** - VolatilityManager
- **Responsibility:** Volatility analysis and calculations
- **Key Features:**
  - ATR (Average True Range)
  - Historical volatility
  - Volatility percentile
  - Parkinson volatility
  - Regime detection
- **Key Methods:**
  - `calculate_volatility()` - Main calculation
  - `rank_by_volatility()` - Symbol ranking
- **Used By:**
  - AdaptiveTrader (volatility-based selection)
  - BacktestManager (market regime analysis)

#### **src/utils/indicator_analyzer.py** - IndicatorAnalyzer
- **Responsibility:** Technical indicator calculations
- **Key Features:**
  - RSI calculation
  - MACD calculation
  - Moving average calculations
- **Used By:** Strategy implementations

### Other Utilities

#### **src/utils/parameter_archiver.py** - ParameterArchiver
- **Responsibility:** Backtest result storage
- **Key Features:**
  - Archives optimal parameters
  - Stores backtest results
  - Version tracking
- **Used By:** BacktestManager

#### **src/utils/timeframe_utils.py** - TimeframeUtils
- **Responsibility:** Timeframe conversion and validation
- **Key Features:**
  - MT5 timeframe constants
  - String to constant conversion
  - Timeframe validation
- **Used By:** DataFetcher, BacktestManager

---

## Data Flow

### 1. Initialization Flow (init mode)

```
main.py (--mode init)
    ↓
InitWizardDialog (PyQt5 GUI)
    ↓
InitManager.initialize_database()
    ↓
DatabaseMigrations.apply_migrations()
    ↓
InitManager.discover_symbols() → MT5Connector.get_all_symbols()
    ↓
User selects symbols in GUI
    ↓
InitManager.save_selected_symbols() → DatabaseManager.execute_update()
    ↓
tradable_pairs table populated
```

### 2. Data Synchronization Flow (sync mode)

```
main.py (--mode sync)
    ↓
DataValidator.sync_data()
    ↓
For each symbol in tradable_pairs:
    ↓
    DataFetcher.fetch_data(symbol, timeframe)
        ↓
        MT5Connector.copy_rates_from()
        ↓
        DatabaseManager.execute_update() → market_data table
    ↓
DataValidator.validate_sync()
```

### 3. Backtesting Flow (backtest mode)

```
main.py (--mode backtest)
    ↓
BacktestOrchestrator.orchestrate_backtests()
    ↓
For each (symbol, timeframe, strategy):
    ↓
    BacktestManager.run_backtest()
        ↓
        DataHandler.prepare_backtest_data() → reads market_data
        ↓
        StrategyFactory.create_strategy()
        ↓
        Strategy.generate_signals() → BUY/SELL signals
        ↓
        Backtesting framework execution
        ↓
        MetricsEngine.calculate_metrics()
        ↓
        ParameterArchiver.archive() → backtest_backtests + optimal_parameters
```

### 4. Live Trading Flow (live mode)

```
main.py (--mode live)
    ↓
AdaptiveTrader.execute_trades()
    ↓
For each symbol in tradable_pairs:
    ↓
    AdaptiveTrader._trade_symbol()
        ↓
        StrategySelector.get_best_strategies() → reads optimal_parameters
        ↓
        StrategyManager.generate_signals()
            ↓
            StrategyFactory.create_strategy()
            ↓
            DataFetcher.fetch_data() → MT5Connector (live data)
            ↓
            Strategy.generate_signals() → BUY/SELL
        ↓
        TradingRules.can_trade() → validate market hours
        ↓
        Trader.execute_trades()
            ↓
            Trader._check_position_limits()
            ↓
            MT5Connector.place_order()
            ↓
            DatabaseManager.execute_update() → trades table
```

### 5. Dashboard Flow (gui mode)

```
main.py (--mode gui)
    ↓
DashboardServer.run() (Flask app on port 5000)
    ↓
User requests /api/trades
    ↓
DashboardAPI.get_trades()
    ↓
DatabaseManager.execute_query() → reads trades table
    ↓
JSON response to browser
    ↓
LiveBroadcaster (WebSocket) → real-time updates
```

---

## Component Dependencies

### High-Level Dependency Graph

```
                    ┌─────────────┐
                    │   main.py   │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        ↓                  ↓                   ↓
  ┌──────────┐      ┌──────────┐       ┌──────────┐
  │   Init   │      │Backtest  │       │  Live    │
  │  Mode    │      │  Mode    │       │  Mode    │
  └────┬─────┘      └────┬─────┘       └────┬─────┘
       │                 │                    │
       ↓                 ↓                    ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│InitManager   │  │BacktestMgr   │  │AdaptiveTrader│
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                  │
       ↓                 ↓                  ↓
┌──────────────────────────────────────────────┐
│           Shared Foundation Layer            │
│  MT5Connector │ DatabaseManager │            │
│  ConfigManager │ LoggingFactory  │            │
│  ErrorHandler │ TradingRules    │            │
└──────────────────────────────────────────────┘
```

### Detailed Dependency Matrix

| Component | Depends On | Used By | Change Impact |
|-----------|------------|---------|---------------|
| **ConfigManager** | - | All components | HIGH - affects entire system |
| **LoggingFactory** | - | All components | HIGH - affects logging across system |
| **DatabaseManager** | - | All data operations | HIGH - affects persistence |
| **MT5Connector** | MetaTrader5 package | Trader, DataFetcher, InitManager | HIGH - affects MT5 integration |
| **ErrorHandler** | LoggingFactory | All components | MEDIUM - affects error handling |
| **TradingRules** | DatabaseManager | Trader, AdaptiveTrader | MEDIUM - affects trading logic |
| **StrategyFactory** | BaseStrategy | StrategyManager, BacktestManager | MEDIUM - affects strategy loading |
| **DataFetcher** | MT5Connector, DatabaseManager | StrategyManager, BacktestManager | HIGH - affects data availability |
| **AdaptiveTrader** | StrategySelector, StrategyManager, Trader | main.py (live mode) | LOW - isolated to live trading |
| **BacktestManager** | DataHandler, StrategyFactory, MetricsEngine | main.py (backtest mode) | LOW - isolated to backtesting |
| **MetricsEngine** | - | BacktestManager, StrategySelector | MEDIUM - affects strategy ranking |

### Critical Paths

**Path 1: Live Trading Critical Path**
```
ConfigManager → MT5Connector → DataFetcher → StrategyManager → 
AdaptiveTrader → Trader → MT5Connector.place_order()
```
**Impact:** Any component failure in this path stops live trading.

**Path 2: Backtesting Critical Path**
```
DatabaseManager → DataHandler → BacktestManager → StrategyFactory → 
Strategy.generate_signals() → MetricsEngine → ParameterArchiver
```
**Impact:** Any component failure prevents strategy optimization.

**Path 3: Initialization Critical Path**
```
DatabaseMigrations → InitManager → MT5Connector.discover_symbols() → 
DatabaseManager.store_symbols()
```
**Impact:** Any component failure prevents system setup.

---

## Testing Components

### Test Organization

```
tests/
├── unit/                    → Component isolation tests
│   ├── test_config_and_db.py
│   ├── test_imports.py
│   ├── test_strategies.py
│   └── test_utils.py
├── integration/             → Multi-component tests
│   ├── test_live_trader.py
│   ├── test_diagnostics.py
│   └── test_data_sync.py
├── performance/             → Load & stress tests
│   └── test_high_load_scenarios.py
└── e2e/                     → End-to-end workflows
    └── test_symbol_filtering.py
```

### Test Coverage

| Component | Unit Tests | Integration Tests | Coverage Gap |
|-----------|------------|-------------------|--------------|
| ConfigManager | ✅ 10+ tests | ✅ Included | None |
| DatabaseManager | ✅ 10+ tests | ✅ Included | None |
| MT5Connector | ⚠️ Limited | ✅ Included | Add connection failure tests |
| **AdaptiveTrader** | ❌ **Missing** | ✅ Included | **10+ tests needed** |
| **Trader** | ❌ **Missing** | ✅ Included | **10+ tests needed** |
| **DataFetcher** | ❌ **Missing** | ✅ Included | **12+ tests needed** |
| Strategies (RSI, MACD, etc.) | ✅ 5+ tests | ✅ Included | None |
| **MetricsEngine** | ❌ **Missing** | ✅ Included | **10+ tests needed** |
| BacktestManager | ⚠️ Limited | ✅ Included | Add edge case tests |

**Priority:** Add unit tests for AdaptiveTrader, Trader, DataFetcher, MetricsEngine before making significant changes.

---

## Impact Analysis Guidelines

### When Modifying Components, Consider:

#### 1. Configuration Changes (config.yaml)
**Affected Components:**
- ConfigManager (reload required)
- All components reading config (validation needed)
- Unit tests (may need config mocks updated)

**Testing Required:**
- Reload test
- Validation test
- Integration tests with new config

#### 2. Database Schema Changes
**Affected Components:**
- DatabaseMigrations (new migration required)
- DatabaseManager (query updates)
- All components querying affected tables
- Unit tests (mock data updates)

**Testing Required:**
- Migration test (upgrade/rollback)
- Query tests
- Data integrity tests
- Performance tests (if indexes changed)

#### 3. Strategy Changes
**Affected Components:**
- StrategyFactory (if adding new strategy)
- BacktestManager (parameter updates)
- AdaptiveTrader (strategy selection)
- Unit tests (strategy-specific tests)

**Testing Required:**
- Strategy signal generation tests
- Backtest execution tests
- Live trading integration tests

#### 4. MT5 API Changes
**Affected Components:**
- MT5Connector (API wrapper updates)
- Trader (order placement)
- DataFetcher (data retrieval)
- MT5Decorator (error handling)

**Testing Required:**
- Connection tests
- Order placement tests
- Data retrieval tests
- Error handling tests

#### 5. Risk Management Changes
**Affected Components:**
- Trader (position limits)
- TradingRules (market hours)
- AdaptiveTrader (confidence scoring)
- Config (risk parameters)

**Testing Required:**
- Position limit enforcement tests
- Trading rules validation tests
- Risk calculation tests

---

## Component Interaction Diagrams

### Backtesting Interaction

```
┌────────────────┐
│BacktestManager │
└───────┬────────┘
        │
        ├──→ DataHandler.prepare_backtest_data()
        │    └──→ DatabaseManager.query(market_data)
        │
        ├──→ StrategyFactory.create_strategy()
        │    └──→ Strategy.generate_signals()
        │
        ├──→ Backtesting.Backtest.run()
        │    └──→ Strategy execution
        │
        ├──→ MetricsEngine.calculate_metrics()
        │    └──→ Performance calculations
        │
        └──→ ParameterArchiver.archive()
             └──→ DatabaseManager.insert(optimal_parameters)
```

### Live Trading Interaction

```
┌────────────────┐
│AdaptiveTrader  │
└───────┬────────┘
        │
        ├──→ StrategySelector.get_best_strategies()
        │    └──→ DatabaseManager.query(optimal_parameters)
        │
        ├──→ StrategyManager.generate_signals()
        │    ├──→ StrategyFactory.create_strategy()
        │    ├──→ DataFetcher.fetch_data()
        │    │    └──→ MT5Connector.copy_rates_from()
        │    └──→ Strategy.generate_signals()
        │
        ├──→ TradingRules.can_trade()
        │    └──→ Market hours validation
        │
        └──→ Trader.execute_trades()
             ├──→ Position limit checks
             └──→ MT5Connector.place_order()
                  └──→ DatabaseManager.insert(trades)
```

---

## Glossary

- **ATR:** Average True Range - volatility indicator
- **Sharpe Ratio:** Risk-adjusted return metric (higher is better)
- **Confidence Score:** 0.5-0.9 range score for strategy quality
- **Position Limit:** Maximum concurrent open trades
- **Volatility Percentile:** Current volatility vs historical baseline
- **Strategy Ranking:** Ordering strategies by backtest performance
- **Adaptive Selection:** Auto-choosing best strategies based on backtest results
- **Data Caching:** 20s TTL cache for performance optimization
- **MT5:** MetaTrader5 trading platform
- **Backtest:** Historical strategy testing
- **Singleton:** Design pattern ensuring single instance

---

## Quick Reference: Files by Purpose

### When Working On...

**Trading Logic:** `src/core/trader.py`, `src/core/adaptive_trader.py`  
**Strategy Development:** `src/strategies/*.py`, `src/core/base_strategy.py`  
**Data Fetching:** `src/core/data_fetcher.py`, `src/mt5_connector.py`  
**Backtesting:** `src/backtesting/backtest_manager.py`, `src/backtesting/metrics_engine.py`  
**Database:** `src/database/db_manager.py`, `src/database/migrations.py`  
**Configuration:** `src/utils/config_manager.py`, `src/config/config.yaml`  
**UI/Dashboard:** `src/ui/web/dashboard_server.py`, `src/ui/gui/init_wizard_dialog.py`  
**Risk Management:** `src/utils/trading_rules.py`, `src/utils/trade_quality_filter.py`  
**Error Handling:** `src/utils/error_handler.py`, `src/utils/mt5_decorator.py`  
**Logging:** `src/utils/logging_factory.py`  
**Testing:** `tests/unit/*.py`, `tests/integration/*.py`

---

**For questions or clarifications, refer to:**
- `README.md` - Quick start and overview
- `workflow.yaml` - Development workflows
- `commands.yaml` - Command reference
- This document - Architecture and components

**Last Updated:** January 31, 2026  
**Maintainer:** FX Trading Bot Team
