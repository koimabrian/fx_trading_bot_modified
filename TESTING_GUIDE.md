# Trade Sync Fix - Testing Guide

## Overview
This guide explains how to test the fix for the UNIQUE constraint issue on `order_id` in the `live_trades` table (formerly `trades`).

## Changes Summary

### Schema Changes
1. **Table Rename**: `trades` → `live_trades` (clarity vs `backtest_trades`)
2. **Fixed UNIQUE Constraint**: `order_id` changed from `INTEGER UNIQUE` to `INTEGER`
3. **Index Strategy**:
   - `deal_id`: UNIQUE (each deal is unique)
   - `ticket`: UNIQUE (each position ticket is unique)
   - `order_id`: NON-UNIQUE (multiple deals can share same order)

### Code Changes
- `src/database/migrations.py` - Schema definition and migration methods
- `src/core/trade_syncer.py` - Trade sync queries (7 changes)
- `src/core/position_persistence.py` - Position tracking queries (9 changes)
- `src/main.py` - Live trading queries (6 changes)
- `src/ui/web/dashboard_server.py` - Dashboard queries (6 changes)

### Test Changes
- `tests/unit/test_trade_syncer.py` - Updated assertions
- `tests/integration/test_live_exhaustive.py` - Updated SQL queries

## Testing Instructions

### 1. Backup Existing Database (Optional)
```bash
# Backup current database
cp src/data/market_data.sqlite src/data/market_data.sqlite.backup
```

### 2. Delete Old Database
```bash
# Remove old database to start fresh
rm src/data/market_data.sqlite
```

### 3. Run Init Mode
```bash
# Create fresh schema with live_trades table
python -m src.main --mode init
```

**Expected Output:**
```
Database tables created successfully
All database indexes created successfully
```

### 4. Verify Table Schema
```bash
# Check that live_trades table exists
sqlite3 src/data/market_data.sqlite "SELECT name FROM sqlite_master WHERE type='table' AND name='live_trades';"
```

**Expected Output:**
```
live_trades
```

### 5. Verify Indexes
```bash
# Check indexes on live_trades
sqlite3 src/data/market_data.sqlite "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='live_trades';"
```

**Expected Output:**
```
idx_live_trades_symbol_status|CREATE INDEX ...
idx_live_trades_open_time|CREATE INDEX ...
idx_live_trades_strategy|CREATE INDEX ...
idx_live_trades_deal_id_unique|CREATE UNIQUE INDEX ...
idx_live_trades_ticket_unique|CREATE UNIQUE INDEX ...
idx_live_trades_order_id|CREATE INDEX ...
```

### 6. Test MT5 Sync (Requires MT5 Connection)
```bash
# Sync historical deals from MT5
python -m src.main --mode sync
```

**Expected Output (Before Fix):**
```
Retrieved 814 deals from MT5
Synced 543/814 deals from MT5 to database  # 66.7% success rate
```

**Expected Output (After Fix):**
```
Retrieved 814 deals from MT5
Synced 814/814 deals from MT5 to database  # 100% success rate
Synced 740/740 orders from MT5 to database
```

### 7. Verify Duplicate order_id Handling
```bash
# Check for deals with duplicate order_id (should now be allowed)
sqlite3 src/data/market_data.sqlite "
SELECT order_id, COUNT(*) as deal_count 
FROM live_trades 
WHERE order_id IS NOT NULL 
GROUP BY order_id 
HAVING deal_count > 1 
LIMIT 5;"
```

**Expected Output:**
```
12345|3
12346|2
12347|2
...
```

This confirms multiple deals can share the same order_id.

### 8. Run Unit Tests
```bash
# Run all unit tests
python -m pytest tests/unit/test_trade_syncer.py tests/unit/test_config_and_db.py -v
```

**Expected Output:**
```
======================== 20 passed in 0.09s =========================
```

### 9. Check Code Quality
```bash
# Run pylint on modified files
pylint src/database/migrations.py src/core/trade_syncer.py --disable=all --enable=E,F
```

**Expected Output:**
```
Your code has been rated at 10.00/10
```

## Validation Criteria

### ✅ Success Indicators
1. `live_trades` table exists (not `trades`)
2. `order_id` column allows duplicates
3. `deal_id` and `ticket` columns reject duplicates
4. All 814 deals sync successfully (100% success rate)
5. All 20 unit tests pass
6. Pylint shows no errors or fatals

### ❌ Failure Indicators
1. Table still named `trades`
2. "UNIQUE constraint failed: live_trades.order_id" errors
3. Deals with same order_id fail to insert
4. Unit tests fail
5. Pylint shows errors

## Troubleshooting

### Issue: "no such table: live_trades"
**Solution:** Run `python -m src.main --mode init` to create tables

### Issue: "UNIQUE constraint failed: live_trades.order_id"
**Solution:** 
1. Delete database: `rm src/data/market_data.sqlite`
2. Re-run init: `python -m src.main --mode init`

### Issue: Still seeing "trades" table instead of "live_trades"
**Solution:** Old database still exists. Delete it and run init mode.

### Issue: Tests fail with "no such table: trades"
**Solution:** Tests updated to use `live_trades`. Pull latest changes.

## Expected Impact

| Metric | Before | After |
|--------|--------|-------|
| Table Name | `trades` (ambiguous) | `live_trades` (clear) |
| Deals Synced | 543/814 (66.7%) | 814/814 (100%) |
| Orders Synced | 542/740 (73.2%) | 740/740 (100%) |
| Data Integrity | ⚠️ Incomplete | ✅ Complete |

## Files Modified
- `src/database/migrations.py` (schema definition)
- `src/core/trade_syncer.py` (sync logic)
- `src/core/position_persistence.py` (position tracking)
- `src/main.py` (live trading)
- `src/ui/web/dashboard_server.py` (dashboard)
- `tests/unit/test_trade_syncer.py` (tests)
- `tests/integration/test_live_exhaustive.py` (tests)

## Related Documentation
- Issue: [BUG] Trade Sync fails: UNIQUE constraint failed: trades.order_id
- Root Cause: Multiple MT5 deals can share same order_id (partial fills, split executions)
- Solution: Remove UNIQUE constraint from order_id, rename table for clarity

## Notes
- This is a **breaking change** - requires database recreation
- All historical sync data will be lost (must re-sync from MT5)
- Backup existing database before testing if needed
- Table rename improves clarity: `live_trades` vs `backtest_trades`
