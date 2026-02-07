---
name: "🐛 Trade Sync UNIQUE Constraint Failure + Table Rename"
about: TradeSyncer fails with UNIQUE constraint violated on order_id; also rename trades to live_trades
title: "[BUG] Trade Sync fails: UNIQUE constraint failed: trades.order_id"
labels: bug, priority-high, database, mt5-sync
assignees: ''
---

## 🐛 Bug Description

The TradeSyncer fails to sync 271/814 deals (33%) due to `UNIQUE constraint failed: trades.order_id` errors. This happens because multiple MT5 deals can share the same `order_id` (e.g., partial fills, split executions).

**Additional Change:** Rename `trades` table to `live_trades` to clearly distinguish from `backtest_trades`.

## 📊 Error Log Summary

```
2026-02-07 16:01:24 - src.core.trade_syncer - INFO - Retrieved 814 deals from MT5
2026-02-07 16:01:26 - src.database.db_manager - ERROR - Query execution failed: ... UNIQUE constraint failed: trades.order_id
2026-02-07 16:01:27 - src.core.trade_syncer - INFO - Synced 543/814 deals from MT5 to database
```

**Success Rate:** 543/814 = **66.7%** (271 deals lost)

## 🔍 Root Cause Analysis

### The Problem

1. **Migrations** ([migrations.py#L137](src/database/migrations.py#L137)) defines `order_id` as UNIQUE in the CREATE TABLE:
   ```sql
   CREATE TABLE IF NOT EXISTS trades (
       ...
       order_id INTEGER UNIQUE,  -- ❌ WRONG: Multiple deals share same order
       deal_id INTEGER UNIQUE,   -- ✅ CORRECT: Each deal is unique
       ticket INTEGER UNIQUE,    -- ✅ CORRECT: Each position ticket is unique
       ...
   )
   ```

2. **TradeSyncer** ([trade_syncer.py#L277](src/core/trade_syncer.py#L277)) uses `ON CONFLICT(deal_id)`:
   ```sql
   INSERT INTO trades (..., order_id, deal_id, ...)
   VALUES (...)
   ON CONFLICT(deal_id) DO UPDATE SET ...
   ```

3. **MT5 Deal Structure:**
   - Multiple deals can have the SAME `order_id` (partial fills, split executions)
   - Each deal has a UNIQUE `deal_id` (deal ticket)
   - The INSERT targets `deal_id` for conflict resolution but hits `order_id` constraint first

### Example Scenario
```
Order #12345 (Buy 1.0 lot EURUSD)
├── Deal #1001 (filled 0.5 lot) ← order_id = 12345
├── Deal #1002 (filled 0.3 lot) ← order_id = 12345 (FAILS: duplicate!)
└── Deal #1003 (filled 0.2 lot) ← order_id = 12345 (FAILS: duplicate!)
```

## ✅ Solution: Fix CREATE TABLE Statement (Fresh Schema)

Since we're doing a clean schema rebuild, update the table definition in `create_tables()`:
1. **Rename** `trades` → `live_trades` (consistent with `backtest_trades`)
2. **Fix** the UNIQUE constraint on `order_id`

### Updated live_trades Table (Complete Schema)

```sql
-- Table 7: live_trades (live trading audit trail from MT5)
CREATE TABLE IF NOT EXISTS live_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol_id INTEGER NOT NULL,
    timeframe TEXT NOT NULL,
    strategy_name TEXT NOT NULL,
    trade_type TEXT NOT NULL,
    volume REAL NOT NULL,
    open_price REAL NOT NULL,
    close_price REAL,
    open_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    close_time TIMESTAMP,
    profit REAL,
    status TEXT DEFAULT 'open',
    order_id INTEGER,                    -- NOT UNIQUE (multiple deals per order)
    deal_id INTEGER UNIQUE,              -- UNIQUE (each deal is unique)
    ticket INTEGER UNIQUE,               -- UNIQUE (each position ticket is unique)
    magic INTEGER,
    swap REAL DEFAULT 0,
    commission REAL DEFAULT 0,
    comment TEXT,
    external BOOLEAN DEFAULT 0,
    mt5_synced_at TIMESTAMP,
    FOREIGN KEY (symbol_id) REFERENCES tradable_pairs(id)
)
```

### Table Naming Convention

| Table             | Purpose                              | Source                    |
| ----------------- | ------------------------------------ | ------------------------- |
| `live_trades`     | Real MT5 trades (synced from broker) | MT5 `history_deals_get()` |
| `backtest_trades` | Simulated trades from backtests      | Backtest engine           |

### Key Changes

| Change     | Before           | After            | Reason                              |
| ---------- | ---------------- | ---------------- | ----------------------------------- |
| Table name | `trades`         | `live_trades`    | Clarity vs `backtest_trades`        |
| `order_id` | `INTEGER UNIQUE` | `INTEGER`        | Multiple deals can share same order |
| `deal_id`  | `INTEGER UNIQUE` | `INTEGER UNIQUE` | No change - each deal is unique     |
| `ticket`   | `INTEGER UNIQUE` | `INTEGER UNIQUE` | No change - each position is unique |

### Index Strategy

After CREATE TABLE, add indexes for query performance:

```sql
-- Unique indexes for conflict resolution
CREATE UNIQUE INDEX IF NOT EXISTS idx_live_trades_deal_id_unique 
    ON live_trades(deal_id) WHERE deal_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_live_trades_ticket_unique 
    ON live_trades(ticket) WHERE ticket IS NOT NULL;

-- Non-unique index for order lookups (grouping deals by order)
CREATE INDEX IF NOT EXISTS idx_live_trades_order_id 
    ON live_trades(order_id) WHERE order_id IS NOT NULL;

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_live_trades_symbol_status 
    ON live_trades(symbol_id, status);
CREATE INDEX IF NOT EXISTS idx_live_trades_open_time 
    ON live_trades(open_time);
```

## 📋 Implementation Checklist

- [ ] **Step 1:** Rename `trades` → `live_trades` in CREATE TABLE statement
- [ ] **Step 2:** Remove UNIQUE from `order_id` column
- [ ] **Step 3:** Update all references from `trades` to `live_trades`:
  - [ ] `src/database/migrations.py` - CREATE TABLE and indexes
  - [ ] `src/core/trade_syncer.py` - INSERT/SELECT queries
  - [ ] `src/core/trade_manager.py` - trade queries
  - [ ] `src/core/trade_monitor.py` - trade queries
  - [ ] `src/core/position_persistence.py` - trade queries
  - [ ] `src/ui/web/dashboard_server.py` - API queries
  - [ ] `src/database/db_manager.py` - any trade-related methods
- [ ] **Step 4:** Delete existing database file (fresh start)
- [ ] **Step 5:** Run `python -m src.main --mode init` to create fresh schema
- [ ] **Step 6:** Run `python -m src.main --mode sync` to verify all 814 deals sync

## 📁 Files to Modify

| File                               | Change                                              |
| ---------------------------------- | --------------------------------------------------- |
| `src/database/migrations.py`       | Rename table, fix UNIQUE constraint, update indexes |
| `src/core/trade_syncer.py`         | Change `trades` → `live_trades` in queries          |
| `src/core/trade_manager.py`        | Change `trades` → `live_trades` in queries          |
| `src/core/trade_monitor.py`        | Change `trades` → `live_trades` in queries          |
| `src/core/position_persistence.py` | Change `trades` → `live_trades` in queries          |
| `src/ui/web/dashboard_server.py`   | Change `trades` → `live_trades` in queries          |
| `src/database/db_manager.py`       | Change `trades` → `live_trades` in any methods      |
| `src/data/market_data.sqlite`      | Delete for fresh schema (backup first!)             |

## 🔍 Find All References

Run this to find all files referencing the `trades` table:

```bash
grep -rn "FROM trades" src/
grep -rn "INTO trades" src/
grep -rn "UPDATE trades" src/
grep -rn '"trades"' src/
```

## 🧪 Verification

After fix, run:
```bash
# Delete old DB and recreate
rm src/data/market_data.sqlite
python -m src.main --mode init
python -m src.main --mode sync
```

**Expected output:**
```
Synced 814/814 deals from MT5 to database
Synced 740/740 orders from MT5 to database
```

## 📊 Impact

| Metric         | Before               | After                 |
| -------------- | -------------------- | --------------------- |
| Table name     | `trades` (ambiguous) | `live_trades` (clear) |
| Deals synced   | 543/814 (66.7%)      | 814/814 (100%)        |
| Orders synced  | 542/740 (73.2%)      | 740/740 (100%)        |
| Data integrity | ⚠️ Incomplete         | ✅ Complete            |

---

**Priority:** HIGH
**Effort:** 1 hour (includes updating all references)
**Breaking Changes:** Yes (table rename requires updating all queries)
