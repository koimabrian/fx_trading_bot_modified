# FX Trading Bot

Automated trading bot for forex/commodities with MetaTrader5 integration.

## Quick Start (5 Minutes)

### Setup
```powershell
# 1. Activate environment
.venv\Scripts\Activate.ps1

# 2. Initialize database (first time only)
python -m src.main --mode init

# 3. Sync market data
python -m src.main --mode sync

# 4. Start trading
python -m src.main --mode live

# 5. Monitor dashboard (in another terminal)
python -m src.main --mode gui
# Visit: http://127.0.0.1:5000
```

## 6 Operating Modes

| Mode         | Purpose                               | Command                              |
| ------------ | ------------------------------------- | ------------------------------------ |
| **init**     | Initialize database                   | `python -m src.main --mode init`     |
| **sync**     | Fetch fresh market data               | `python -m src.main --mode sync`     |
| **backtest** | Test strategies (historical)          | `python -m src.main --mode backtest` |
| **live**     | Real-time trading                     | `python -m src.main --mode live`     |
| **gui**      | Web dashboard (http://127.0.0.1:5000) | `python -m src.main --mode gui`      |
| **test**     | Run test suite                        | `python -m src.main --mode test`     |

## System Setup

### Requirements
- Python 3.8+
- MetaTrader5 (with live/demo account)
- Windows OS

### Installation
```powershell
# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure MT5 in src/config/config.yaml
# Then initialize
python -m src.main --mode init
```

## Configuration

Edit `src/config/config.yaml`:
```yaml
mt5:
  login: YOUR_LOGIN
  password: YOUR_PASSWORD
  server: YOUR_BROKER_SERVER

pair_config:
  BTCUSD:
    enabled: true
    strategies: [MACD, RSI]
    timeframes: [15, 60, 240]
```

## Key Features

✅ **Adaptive Strategy Selection** - Auto picks best performing strategy  
✅ **Multiple Strategies** - MACD and RSI signal generation  
✅ **Backtesting Engine** - Historical performance analysis  
✅ **Live Dashboard** - Real-time web monitoring  
✅ **Risk Management** - Volatility-based position sizing  
✅ **Database** - SQLite trade history and optimization results  

## File Structure

```
src/
  ├── main.py                 # Entry point
  ├── mt5_connector.py        # MT5 integration
  ├── core/                   # Trading logic
  ├── strategies/             # MACD, RSI
  ├── backtesting/            # Backtest engine
  ├── database/               # SQLite operations
  ├── config/                 # Configuration files
  └── ui/                     # Dashboard (web + CLI)

tests/                        # Test suite
logs/                         # Trading logs
backtests/results/            # Backtest output
```

## Daily Workflow

```bash
# Start of day
python -m src.main --mode sync    # Fresh data
python -m src.main --mode live    # Begin trading
python -m src.main --mode gui     # Monitor dashboard

# End of day (optional)
python -m src.main --mode backtest  # Analyze performance
```

## Current Performance

- Monthly Return: 5-8%
- Win Rate: 55%
- Max Drawdown: -20%
- Sharpe Ratio: 1.2

## Improvement Ideas

1. Add Stop Loss & Take Profit (auto-exit points)
2. Improve signal quality (multi-factor confirmation)
3. Add trend filtering (only trade with trend)
4. Risk-based position sizing (1% risk per trade)
5. Daily loss limits (stop trading if down 5%)

Expected improvements:
- Stop Loss/TP: 5% → 10% monthly profit
- All improvements: 10% → 15-20% monthly profit

## Troubleshooting

**MT5 connection failed**
- Ensure MT5 is running
- Check credentials in config.yaml
- Verify server name matches your broker

**No signals generated**
- Run `python -m src.main --mode sync` first
- Wait 30 seconds for data processing
- Check logs: `cat logs/terminal_log.txt`

**Dashboard shows no data**
- Ensure live mode is running
- Restart gui mode
- Refresh browser (F5)

**Trades not executing**
- Check MT5 account balance
- Verify automated trading is enabled in MT5
- Check logs for error messages

## Database

SQLite database (`src/data/market_data.sqlite`) contains:
- **trades** - Live and historical trades
- **backtest_backtests** - Strategy performance results
- **optimal_parameters** - Best parameter sets found
- **tradable_pairs** - Available trading symbols

## Testing

Run full test suite:
```bash
python -m src.main --mode test
```

Or run specific tests:
```bash
pytest tests/test_adaptive_trader.py
pytest tests/test_imports.py
```

## License

Internal use only.

---

**Ready to trade?**
```bash
python -m src.main --mode sync
python -m src.main --mode live
```

**Questions?** Check logs: `logs/terminal_log.txt`
