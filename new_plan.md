# Hybrid Workflow for FX Trading Bot

## Overview
This document provides a comprehensive, professional outline of the hybrid workflow for the FX Trading Bot.

Key design principles:
- **Dynamic and Modular**: Configuration-driven for strategies, symbols, and timeframes; supports runtime adaptability without code changes.
- **Efficient Data Handling**: Unified database schema with incremental syncing to minimize overhead.
- **Prioritized Live Trading**: Volatility-based pair selection (top 10 by ATR), with preference for archived optimal parameters, falling back to adaptive ranking.
- **Read-Only Dashboard**: The GUI is strictly for monitoring and visualization; bot control (start/stop) is handled via CLI or service managers (e.g., systemd, Docker) for reliability and security. Starting the bot from the dashboard is not supported to avoid risks like accidental interruptions or orphaned processes.
- **Scalability**: Abstracts components (e.g., strategy factory, data provider) for easy extension (e.g., new strategies, data sources).
- **Auditability**: Dedicated tables for parameters, results, and trades ensure traceability.

The bot operates in six modes: `init`, `sync`, `backtest`, `live`, `gui`, and `test`. Modes are orchestrated via `main.py` with command-line arguments (e.g., `--mode live --symbol BTCUSD`). If no `--symbol` or `--strategy` flags are provided in `backtest` or `live`, the bot processes **all** pairs from the `tradable_pairs` table and **all** timeframes from `config.yaml`.

## Configuration (`config.yaml`)
The bot is highly configurable to reduce hardcoding:
- **mt5**: `{login, password, server}` – MT5 credentials.
- **database**: `{path: 'data/market_data.sqlite'}` – DB file path.
- **sync**: `{start_date, end_date, fetch_count: 10000, min_rows_threshold: 1000, incremental_interval_min: 4}` – Data sync settings.
- **risk_management**: `{stop_loss_percent: 1.0, take_profit_percent: 2.0, lot_size: 0.01, max_positions: 5}` – Trade rules.
- **strategies**: `[rsi, macd]` – List of strategy names (dynamically loaded via factory).
- **timeframes**: `[M1, M5, H1]` – List of timeframes (e.g., MetaTrader strings).
- **optimization**: `{ranges: {rsi: {period: [10-20], overbought: [70-80]}, macd: {...}}, max_combos: 200}` – Parameter grids for randomized search.
- **volatility**: `{atr_period: 14, min_threshold: 0.001, top_n_pairs: 10, lookback_bars: 200}` – ATR calculation and ranking settings.
- **modes**: Optional chaining (e.g., `full_run: [init, backtest, live]`).
- **gui**: `{host: '127.0.0.1', port: 5000}` – Dashboard settings.

## Database Schema
Redesigned for unification and flexibility:
- **tradable_pairs**: `id (PK), symbol (VARCHAR)` – Dynamically populated symbols from MT5.
- **market_data**: `id (PK), symbol_id (FK to tradable_pairs), timeframe (VARCHAR), open (FLOAT), high (FLOAT), low (FLOAT), close (FLOAT), volume (INT), time (DATETIME), type (ENUM: 'historical', 'live')` – Unified storage for all data; type flag separates sources.
- **optimal_parameters**: `id (PK), strategy_name (VARCHAR), symbol_id (FK), timeframe (VARCHAR), parameter_value (JSON), last_optimized (DATETIME)` – Archived optimal params per strategy/symbol/timeframe.
- **backtest_backtests**: `id (PK), strategy_id (FK to backtest_strategies), symbol_id (FK), timeframe (VARCHAR), metrics (JSON: {sharpe_ratio, total_return, win_rate, profit_factor, max_drawdown, atr_value, rank_score}), timestamp (DATETIME)` – Results with flexible JSON metrics.
- **backtest_strategies**: `id (PK), name (VARCHAR)` – Strategy registry.
- **backtest_trades**: `id (PK), backtest_id (FK), entry_price (FLOAT), exit_price (FLOAT), entry_time (DATETIME), exit_time (DATETIME), pnl (FLOAT), status (VARCHAR)` – Individual backtest trades.
- **trades**: `id (PK), symbol_id (FK), timeframe (VARCHAR), trade_type (ENUM: 'buy', 'sell'), volume (FLOAT), open_price (FLOAT), close_price (FLOAT), open_time (DATETIME), close_time (DATETIME), profit (FLOAT), status (VARCHAR), strategy_name (VARCHAR)` – Live trade audit trail.

Migrations handled via `migrations.py`: `create_tables()`, `migrate_tables()` ensure schema evolution.

## Modes and Workflows

### 1. Mode: Init
**Purpose**: Explicit setup for database and initial data population (from plan). Ensures a clean starting state.
**Workflow**:
1. Load config and validate (e.g., check MT5 credentials, required sections).
2. Connect to MT5 (`mt5.initialize()` with config creds).
3. Create/migrate tables using `migrations.py`.
4. Fetch all available symbols: `all_symbols = mt5.symbols_get()`.
5. Filter tradable pairs: `if symbol.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL`, insert into `tradable_pairs`.
6. For each pair in `tradable_pairs` and timeframe in config:
   - Fetch historical data: `mt5.copy_rates_range(symbol, timeframe, start_date, end_date)`.
   - Store in `market_data` with `type='historical'`.
   - Validate sufficiency: `if row_count < min_rows_threshold`, log warning and retry or skip.
7. Log: Number of pairs stored, data lengths per pair/timeframe, total rows inserted.
**Functions**: `create_tables()`, `fetch_historical_data(symbol, timeframe, start_date, end_date)`, `store_data(data, type='historical')`, `update_tradable_pairs_table(pairs)`.
**Commands**: `python main.py --mode init`.
**Output**: Logs in `/logs/bot.log`; DB populated.

### 2. Mode: Sync
**Purpose**: Incremental or full data refresh for live updates (from actual). Keeps `market_data` current without bulk re-fetches.
**Workflow**:
1. Connect to MT5.
2. Determine scope: If `--symbol` specified, limit to it; else, all from `tradable_pairs`.
3. For each symbol/timeframe in config:
   - Check last timestamp in `market_data` (type='live').
   - If insufficient data (`< min_rows_threshold`) or `--full` flag: Fetch full `fetch_count` candles.
   - Else: Incremental fetch since last timestamp.
   - Insert new rows with `type='live'`.
4. Log: Rows added per symbol/timeframe, total sync time.
**Functions**: `sync_data(symbol=None, full=False)`, `sync_incremental(symbol, timeframe)`.
**Commands**: `python main.py --mode sync [--symbol SYMBOL] [--full]`.
**Output**: Updated `market_data`; logs.

### 3. Mode: Backtest
**Purpose**: Optimize parameters, apply volatility filter, run backtests, and generate reports. If no flags, processes all pairs × all timeframes.
**Workflow**:
1. Connect to DB and MT5 (if needed for fresh data).
2. Scope: If `--symbol/--strategy` absent, load all from `tradable_pairs`/config; else, filter.
3. For each strategy/symbol/timeframe:
   - Load historical data from `market_data` (type='historical').
   - Compute ATR: `calculate_atr(data, period=config.atr_period)`; skip if `< min_threshold`, log.
   - Optimize: Randomized grid search over config ranges (up to `max_combos`); evaluate on data.
   - Store best params in `optimal_parameters` (with symbol_id, timeframe).
   - Backtest: Run with optimal params using backtesting.py framework.
   - Compute metrics (sharpe, etc.) + ATR; store in `backtest_backtests` as JSON.
   - Store individual trades in `backtest_trades`.
4. Generate reports: Aggregate metrics across runs; export CSV/PDF/HTML (e.g., summary table with volatility ranks).
5. Visualize: Export equity curves as Plotly HTML to `/backtests/results/`.
6. Log: Optimization results, metrics, skipped pairs.
**Functions**: `perform_optimization(strategy, data)`, `store_optimal_parameters(...)`, `perform_backtest(...)`, `calculate_metrics(incl. ATR)`, `generate_report()`, `export_report(format)`.
**Commands**: `python main.py --mode backtest [--symbol SYMBOL] [--strategy STRATEGY]`.
**Output**: Updated DB tables; reports in `/reports/`; visuals in `/backtests/results/`; logs.

### 4. Mode: Live
**Purpose**: Real-time trading with volatility prioritization and parameter fallback. If no flags, considers all pairs × all timeframes.
**Workflow**:
1. Connect to MT5 and DB.
2. Initial full sync if data insufficient.
3. Enter main loop (20-second intervals, configurable):
   - Every `incremental_interval_min` minutes: Run incremental sync for active symbols.
   - **Pre-Signal Checks** (strict order, before any signal generation):
     a. Load active pairs: All from `tradable_pairs` if no `--symbol`; else, specified.
     b. Volatility Ranking: For each pair/timeframe, compute ATR on recent data (`lookback_bars` from `market_data` type='live'); rank globally (descending ATR); select top `top_n_pairs` (e.g., 10). Log skipped low-vol pairs.
     c. For each selected pair/timeframe:
        - Priority 1: Query `optimal_parameters` for exact `symbol_id + timeframe`; if found, load strategy_name and params.
        - Fallback: If no optimal, query `backtest_backtests` for that pair/timeframe; select top 1-3 by `rank_score` (composite metric); infer params from metrics JSON.
     d. Cache strategies: Instantiate via factory with chosen params; store in dict for reuse.
   - Generate Signals: For each selected pair/timeframe/strategy: Fetch latest data; call `generate_signal(data)`.
   - If signal ('buy'/'sell'): Apply risk (SL/TP, lot_size, check max_positions); execute via `mt5.order_send()`.
   - Monitor: Check open positions; evaluate exits (SL/TP hit, strategy exit signal); update `trades` table.
   - Log: Signals, executions, profits, params source (optimal/adaptive).
4. Graceful shutdown: Close positions if configured; log session end.
**Functions**: `volatility_rank_pairs(active_pairs, lookback_bars, top_n)`, `load_optimal_parameters(symbol_id, tf)`, `query_top_strategies_by_rank_score(symbol, tf, top_n)`, `generate_signal(...)`, `execute_trade(signal, params, risk)`, `monitor_positions()`.
**Commands**: `python main.py --mode live [--symbol SYMBOL] [--strategy STRATEGY]`. Run as service for production (e.g., `nohup python main.py --mode live &`).
**Output**: Trades in DB; logs; real-time MT5 executions.

### 5. Mode: GUI
**Purpose**: Read-only dashboard for monitoring and analysis (Flask/Plotly). No bot control (start/stop) to ensure safety.
**Workflow**:
1. Launch Flask app on config host/port.
2. Routes:
   - `/`: Overview (metrics cards: total profit, active pairs, volatility ranks table).
   - `/api/results`: Filtered data from `backtest_backtests`/`trades` (by symbol/tf/strategy).
   - `/api/equity/<symbol>/<strategy>`: Plotly JSON for curves.
   - `/api/trades`: Paginated trade logs.
   - `/api/volatility`: Ranked pairs by ATR (query recent data).
   - `/export/report?format=csv/pdf`: Download aggregates.
3. Real-time: Poll DB for updates (e.g., via JS intervals); show "Live Trading: RUNNING" banner (query status flag in DB or file).
4. Log: Startup, access.
**Functions**: `run(host, port)`.
**Commands**: `python main.py --mode gui [--host HOST] [--port PORT]`.
**Output**: Browser UI at e.g., http://127.0.0.1:5000.

### 6. Mode: Test
**Purpose**: Comprehensive validation.
**Workflow**:
1. Run pytest suite: DB ops (`test_db.py`), strategies (`test_strategies.py`), backtest (`test_backtesting.py`), volatility (`test_volatility.py`), etc.
2. Coverage: Unit (e.g., ATR calc), integration (e.g., full backtest cycle), performance (e.g., sync timing).
3. Log: Results, coverage %.
**Functions**: `run_tests()`.
**Commands**: `python main.py --mode test` or `pytest tests/`.
**Output**: Console/logs; fails if issues.

## Filesystem Structure
- `/config/config.yaml`: Settings.
- `/database`: `db_manager.py` (connections), `migrations.py`.
- `/core`: Abstracts (e.g., `adaptive_trader.py`, `data_fetcher.py`).
- `/data/market_data.sqlite`: DB.
- `/strategies`: Factory and implementations.
- `/utils`: Helpers (e.g., `backtesting_utils.py` with `calculate_atr()`).
- `/tests`: Pytest files.
- `/logs/bot.log`: Operations.
- `/reports`: Exports.
- `/backtests/results`: Visuals.
- `main.py`: Entry point.

## Commands Summary
- `python main.py --mode init`: Setup.
- `python main.py --mode sync`: Data refresh.
- `python main.py --mode backtest`: Test/optimize.
- `python main.py --mode live`: Trade (service-recommended).
- `python main.py --mode gui`: Monitor.
- `python main.py --mode test`: Validate.

## Implementation Notes
- **Error Handling**: All modes include try/except for MT5/DB failures; retries for sync.
- **Logging**: Centralized via `logging_utils.py` (info/warn/error).
- **Extensibility**: Add strategies by dropping files in `/strategies` and updating config; swap data providers in `data_fetcher.py`.
- **Security**: MT5 creds encrypted in config; dashboard no-auth for local use (add if exposed).
- **Performance**: Caching (e.g., strategies dict); batch DB inserts.

This workflow ensures a robust, dynamic bot ready for production. For code snippets or further refinements, provide specifics.