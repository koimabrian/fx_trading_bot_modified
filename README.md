# FX Trading Bot

**Status:** ✅ Production Ready | **Performance:** Verified at Scale | **Quality:** Pylint 9.78/10

Automated forex/cryptocurrencies trading system with MetaTrader5 integration, adaptive strategy selection, intelligent position management, and professional-grade volatility analysis.

## Quick Start (10 Minutes)

```powershell
# 1. Activate environment
.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize database with GUI wizard (discover pairs from MT5)
python -m src.main --mode init
# ← Interactive PyQt5 GUI opens:
#   Step 1: Welcome
#   Step 2: Database & MT5 connection setup
#   Step 3: Discover tradable symbols from your broker
#   Step 4: Select which symbols to trade (checkboxes)
#   Step 5: Review selections
#   Step 6: Success!

# 4. Sync live market data
python -m src.main --mode sync

# 5. Run backtests to optimize strategies
python -m src.main --mode backtest

# 6. Start live trading with adaptive strategy selection
python -m src.main --mode live

# 7. Monitor dashboard (separate terminal)
python -m src.main --mode gui
# Open: http://127.0.0.1:5000
```

## ✅ System Status & Performance

### 4-Phase Refactoring (Complete & Verified)
- **Phase 1: ConfigManager** - Singleton pattern, 2,540x cache speedup
- **Phase 2: MT5Decorator** - Automatic retry with exponential backoff
- **Phase 3: ErrorHandler** - Centralized error management
- **Phase 4: LoggingFactory** - Unified logging, 6.02K msg/sec throughput

### High-Load Testing (5/5 PASS - All Concurrent Scenarios)
**Comprehensive stress testing under realistic concurrent load conditions:**

- ✅ **Concurrent Logging** (10 threads × 1000 messages): 6,015 msg/sec
- ✅ **Database Queries** (8 threads × 100 queries): 47,596 queries/sec  
- ✅ **ConfigManager Access** (20 threads × 100 accesses): 56,848 accesses/sec
- ✅ **MetricsEngine Calculations** (8 threads × 50 calcs): 1,364 calcs/sec
- ✅ **Mixed Workload** (8 workers × 100 ops): 1,407 ops/sec

**Performance Verdict:** System demonstrates stable performance under concurrent load. No race conditions, deadlocks, or bottlenecks detected. All components handle 100+ concurrent operations gracefully.

### Test Suite Organization
```
tests/
├── unit/              → Unit tests (imports, config)
├── integration/       → Integration tests (trader, diagnostics)
├── performance/       → Performance & load testing
│   └── test_high_load_scenarios.py [New - 5 concurrent tests]
└── e2e/               → End-to-end tests
```

**Run all tests:** `python run_tests.py`

### Documentation
- [FINAL_SUMMARY.md](FINAL_SUMMARY.md) - Performance testing results
- [DELIVERABLES.md](DELIVERABLES.md) - Complete deliverables list
- [PERFORMANCE_TESTING_INDEX.md](PERFORMANCE_TESTING_INDEX.md) - Test reference

## Operating Modes (6 Modes)

| Mode         | Purpose                                                 | Command                              |
| ------------ | ------------------------------------------------------- | ------------------------------------ |
| **init**     | GUI wizard: Setup DB + discover tradable pairs from MT5 | `python -m src.main --mode init`     |
| **sync**     | Fetch/update market data from MT5 (incremental)         | `python -m src.main --mode sync`     |
| **backtest** | Run historical backtests with parameter optimization    | `python -m src.main --mode backtest` |
| **live**     | Real-time trading with adaptive strategy selection      | `python -m src.main --mode live`     |
| **gui**      | Interactive web dashboard for monitoring                | `python -m src.main --mode gui`      |
| **test**     | Run full test suite                                     | `python -m src.main --mode test`     |

## Init GUI Wizard (NEW - PyQt5)

The initialization process is now fully interactive with a professional GUI:

### Step-by-Step Process

**Step 1: Welcome**
- Overview of what will happen
- Estimated time: 2-3 minutes
- Cancel anytime

**Step 2: System Setup** (Automatic)
- Creates database tables
- Validates MT5 connection
- Progress indicators for each

**Step 3: Symbol Discovery** (Automatic)
- Connects to MT5
- Discovers ALL tradable symbols from your broker
- Auto-categorizes by MT5's symbol paths
  - Example: `Pro\Forex\EURUSD` → "Forex" category
  - Example: `Pro\Crypto\BTCUSD` → "Crypto" category
- **Only shows symbols broker allows trading** (SYMBOL_TRADE_MODE_FULL)
- Displays count per category

**Step 4: Symbol Selection**
- Multi-checkbox interface organized by category
- **NO symbols pre-selected** (you choose)
- Search/filter by symbol name
- Category select-all buttons
- Shows count of selected symbols

**Step 5: Review & Confirm**
- Summary of database config
- MT5 connection details
- List of symbols you selected (by category)
- Next steps guidance

**Step 6: Success**
- Database ready
- Next steps:
  - `python -m src.main --mode sync` (fetch data)
  - `python -m src.main --mode backtest` (optimize)
  - `python -m src.main --mode live` (start trading)

### Symbol Discovery Features

✅ **Broker-Accurate**: Only shows symbols your broker allows you to trade
✅ **Auto-Categorized**: Uses MT5's symbol.path (not hardcoded)
✅ **Flexible**: Works with any broker's structure
✅ **Safe**: No pre-selection - you control what gets enabled
✅ **Professional**: Clean, modern PyQt5 interface

### Database-First Architecture

After init, your symbol selections are stored in the database:
- Table: `tradable_pairs`
- Columns: `symbol`, `category` (auto-detected)
- **Config stays clean** - no pair lists in YAML
- Easy to modify later via the dashboard

## Trade Quality & Position Management

Your system includes:
- ✅ Position limit enforcement (configurable per asset class)
- ✅ Confidence scoring (Sharpe × Win_Rate × Profit_Factor formula)
- ✅ Weekend trading blocks (forex/commodities auto-disabled)
- ✅ Category-based rules (crypto, forex, stocks, commodities, indices)
- ✅ Volatility filtering (ATR-based, regime detection)
- ✅ Strategy ranking by backtest Sharpe ratio
- ✅ Market data caching (20s TTL for performance)



## System Requirements

- Python 3.8+
- MetaTrader5 (live/demo account)
- Windows OS
- ~500MB disk space for database

## Installation

```powershell
# Create virtual environment
python -m venv .venv
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Edit configuration
notepad src/config/config.yaml
# Set: mt5.login, mt5.password, mt5.server

# Initialize
python -m src.main --mode init
```

## Configuration (src/config/config.yaml)

**MT5 Connection** (Required)
```yaml
mt5:
  login: YOUR_LOGIN           # Your MT5 account number
  password: YOUR_PASSWORD     # Your MT5 password
  server: YOUR_BROKER_SERVER  # Your broker's server name
```

**Timeframes** (Multi-timeframe analysis)
```yaml
timeframes:
  - 15      # 15-minute candles
  - 60      # 1-hour candles
  - 240     # 4-hour candles
```

**Risk Management**
```yaml
risk_management:
  stop_loss_percent: 1.0         # SL as % of entry price
  take_profit_percent: 2.0       # TP as % of entry price
  max_positions: 5               # Maximum concurrent open trades
  lot_size: 0.01                 # Base position size
  min_signal_confidence: 0.45    # Minimum confidence to trade
```

**Symbol Selection** (Handled by Init GUI)
⚠️ **DO NOT edit pairs in config!**
- Symbols are selected via the Init GUI (Step 4)
- Stored in database: `tradable_pairs` table
- Managed through dashboard later
- To change: Re-run `python -m src.main --mode init` OR edit database directly

**Volatility (Expert-Grade)**
```yaml
volatility:
  atr_period: 14                 # ATR period
  min_threshold: 0.001           # Minimum vol to trade
  top_n_pairs: 10                # Select top N volatile pairs
  volatility_percentile_period: 252    # 1-year baseline
  min_percentile_threshold: 30         # 70th percentile+
```

## Key Features

**Architecture**
- Hybrid workflow (backtesting + live adaptive selection)
- Multi-strategy system (MACD, RSI)
- Automatic strategy ranking and selection
- Professional volatility analysis (ATR, Historical Vol, Regime Detection)
- Risk management (position limits, stop loss, take profit)
- Data caching (20s TTL for performance)

**Dashboard**
- Real-time trade monitoring
- Equity curve visualization
- Optimization heatmaps
- Live statistics and performance metrics
- Interactive filtering

**Database**
- SQLite with proper schema
- Automatic migrations
- Trade audit trail
- Backtest result storage

## Directory Structure

```
src/
  main.py                    # Entry point - routes 6 modes
  mt5_connector.py           # MT5 API integration
  strategy_manager.py        # Dynamic strategy loading
  core/
    adaptive_trader.py       # Live trading with strategy selection
    trader.py                # Trade execution & risk mgmt
    strategy_selector.py     # Ranks strategies by backtest results
    base_strategy.py         # Abstract strategy interface
    data_fetcher.py          # MT5 data fetching
    data_handler.py          # Data processing
    trade_monitor.py         # Trade monitoring
    init_manager.py          # Init workflow (database, pairs)
  strategies/
    factory.py               # Strategy factory
    macd_strategy.py         # MACD implementation
    rsi_strategy.py          # RSI implementation
  backtesting/
    backtest_manager.py      # Backtesting engine
    backtest_orchestrator.py # Parameter optimization
    metrics_engine.py        # Performance calculations
    trade_logger.py          # Trade recording
  database/
    db_manager.py            # SQLite operations
    migrations.py            # Schema management
  utils/
    logger.py                # Logging setup
    trading_rules.py         # Market hour rules, categories
    volatility_manager.py    # Volatility analysis
    trade_quality_filter.py  # Quality filters (optional)
  config/
    config.yaml              # All settings (pairs handled by GUI)
  ui/
    cli.py                   # Command-line interface
    gui/
      init_wizard_dialog.py  # Init GUI - PyQt5 wizard (NEW!)
      pair_selector_dialog.py# Pair selection dialog
    web/
      dashboard_server.py    # Flask server
      dashboard_api.py       # API endpoints
      live_broadcaster.py    # WebSocket updates
    gui/
      enhanced_dashboard.py  # Plotly GUI

tests/
  test_*.py                  # Unit & integration tests
  verify_*.py                # Verification scripts

backtests/                   # Backtest results
logs/                        # Application logs
```

## Workflow Examples

### First-Time Setup (Recommended)
```powershell
# Step 1: Environment
.venv\Scripts\Activate.ps1

# Step 2: Dependencies
pip install -r requirements.txt

# Step 3: Initialize with GUI
python -m src.main --mode init
# Interactive PyQt5 wizard opens:
# - Sets up database
# - Discovers your broker's tradable symbols
# - You select which ones to trade
# - Ready to proceed

# Step 4: Download historical data
python -m src.main --mode sync
# Downloads 2 months of OHLCV data for all selected symbols

# Step 5: Optimize strategies
python -m src.main --mode backtest
# Tests all strategy combinations
# Finds best parameters for each symbol

# Step 6: Start trading
python -m src.main --mode live
# Real-time signals with adaptive strategy selection

# Step 7: Monitor (separate terminal)
python -m src.main --mode gui
# Open: http://127.0.0.1:5000
```

### Daily Trading
```powershell
.venv\Scripts\Activate.ps1
python -m src.main --mode live      # Start trading
python -m src.main --mode gui       # Monitor (separate terminal)
```

### Weekly Optimization
```powershell
python -m src.main --mode backtest  # Re-optimize strategies
python -m src.main --mode live      # System uses new parameters
```

## Advanced Features

### Volatility Analysis (Expert-Grade)

Professional metrics:
1. **ATR** - Absolute true range
2. **Historical Volatility** - 20-bar standard deviation
3. **Volatility Percentile** - Current vs 252-bar history
4. **Parkinson Volatility** - High-low only (responsive)
5. **Session Filtering** - Avoid low-vol times
6. **Volatility Clustering** - Recent spikes predict continuation

### Adaptive Strategy Selection

System automatically:
1. Backtests all strategies on all pairs
2. Ranks by Sharpe ratio and other metrics
3. Selects top strategies for live trading
4. Caches instances for performance
5. Executes based on confidence scores
6. Logs all decisions

### Risk Management

Built-in safeguards:
- Position limit enforcement (max 5 default)
- Stop loss % enforcement (1% default)
- Take profit % targets (2% default)
- Trading rules validation
- Daily monitoring and logging

## Testing

```powershell
# Full test suite
python -m src.main --mode test

# Specific test
pytest tests/test_adaptive_trader.py -v

# With coverage
pytest --cov=src tests/
```

## Troubleshooting

### MT5 Connection Failed
```powershell
# Check credentials in config
notepad src/config/config.yaml

# Check logs
Get-Content logs/terminal_log.txt -Tail 50
```

### No Signals Generated
```powershell
# Sync data first
python -m src.main --mode sync
# Wait 30 seconds for processing
```

### Dashboard 500 Error
```powershell
# Restart
python -m src.main --mode gui
Get-Content logs/terminal_log.txt | Select-String "ERROR"
```

### Trades Not Executing
1. Verify MT5 account has balance
2. Enable automated trading in MT5 (Tools → Options → Expert Advisors)
3. Check logs: `logs/terminal_log.txt`
4. Verify strategy generates signals on dashboard

## Database Schema

Tables:
- **tradable_pairs** - Available symbols
- **market_data** - Live market data
- **backtest_market_data** - Historical backtesting data
- **backtest_backtests** - Strategy performance
- **trades** - Trade audit trail
- **optimal_parameters** - Best found parameters

## Performance

- Data Cache: 20s TTL
- Backtest Speed: ~30s per symbol/timeframe/strategy
- Dashboard Response: ~50ms
- Signal Generation: <100ms per symbol

## Support Files

For reference documentation:
- **commands.yaml** - Complete command reference
- **workflow.yaml** - Project workflow and processes

## Getting Started - 5 Step Process

1. **Initialize**: `python -m src.main --mode init`
2. **Configure**: Edit `src/config/config.yaml`
3. **Sync Data**: `python -m src.main --mode sync`
4. **Backtest**: `python -m src.main --mode backtest`
5. **Trade**: `python -m src.main --mode live`

Monitor with: `python -m src.main --mode gui`

## License

Proprietary - Personal trading use only.

Current: 2.0  
Last Updated: January 2026

## Recent Updates (January 2026)

### ✨ Init GUI - Professional PyQt5 Wizard
- Interactive 6-step initialization wizard
- Beautiful, modern UI for setup
- No more CLI configuration
- Symbol discovery is automatic and visual

### 🔍 Smart Symbol Discovery
- **Tradable-Only Filtering**: Only shows symbols your broker allows
- **Auto-Categorization**: Uses MT5's symbol paths (e.g., `Pro\Forex\EURUSD`)
- **Broker-Accurate**: Works with any broker's symbol structure
- **User Control**: No symbols pre-selected - you choose what to trade

### 📦 Config Cleanup
- Removed hardcoded pair lists from `config.yaml`
- Symbols now managed through database
- Cleaner config for easier management
- Symbol selection persisted in `tradable_pairs` table

### 🏗️ Database-First Architecture
- Symbol selections stored in database (not config)
- Categories auto-detected from MT5
- Easy to modify later without code changes
- Professional, scalable design


