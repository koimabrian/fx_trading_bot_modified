# FX Trading Bot

Automated forex/commodities trading system with MetaTrader5 integration, adaptive strategy selection, intelligent position management, and professional-grade volatility analysis.

## Quick Start (5 Minutes)

```powershell
# 1. Activate environment
.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize database and discover pairs from MT5
python -m src.main --mode init

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

## Operating Modes (6 Modes)

| Mode         | Purpose                                              | Command                              |
| ------------ | ---------------------------------------------------- | ------------------------------------ |
| **init**     | Initialize database and auto-discover pairs from MT5 | `python -m src.main --mode init`     |
| **sync**     | Fetch/update market data from MT5 (incremental)      | `python -m src.main --mode sync`     |
| **backtest** | Run historical backtests with parameter optimization | `python -m src.main --mode backtest` |
| **live**     | Real-time trading with adaptive strategy selection   | `python -m src.main --mode live`     |
| **gui**      | Interactive web dashboard for monitoring             | `python -m src.main --mode gui`      |
| **test**     | Run full test suite                                  | `python -m src.main --mode test`     |

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

**MT5 Connection**
```yaml
mt5:
  login: YOUR_LOGIN
  password: YOUR_PASSWORD
  server: YOUR_BROKER_SERVER
```

**Risk Management**
```yaml
risk_management:
  stop_loss_percent: 1.0         # SL as % of entry
  take_profit_percent: 2.0       # TP as % of entry
  max_positions: 5               # Max concurrent trades
  lot_size: 0.01                 # Default position size
```

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
    config.yaml              # All settings
  ui/
    cli.py                   # Command-line interface
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

### Daily Trading
```powershell
.venv\Scripts\Activate.ps1
python -m src.main --mode sync      # Sync latest data
python -m src.main --mode live      # Start trading
python -m src.main --mode gui       # Monitor (separate terminal)
```

### Weekly Optimization
```powershell
python -m src.main --mode backtest  # Re-optimize strategies
# System automatically selects best parameters
```

### First-Time Setup
```powershell
python -m src.main --mode init      # Database + pair discovery
python -m src.main --mode sync      # Download historical data
python -m src.main --mode backtest  # Establish baseline
python -m src.main --mode live      # Ready for trading
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
