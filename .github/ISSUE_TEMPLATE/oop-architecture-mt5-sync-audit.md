---
name: "🏗️ OOP Architecture Audit & MT5 Trade Sync"
about: Comprehensive audit of OOP principles, SOLID compliance, duplicates, and MT5 trade sync implementation
title: "Architecture Audit: OOP Principles, SOLID Compliance, Duplicates & MT5 Trade Sync"
labels: architecture, refactoring, enhancement, tech-debt, priority-high
assignees: ''
---

## 📋 Overview

Comprehensive OOP architecture audit of `src/` to ensure advanced Python OOP principles are correctly applied, utilities are properly reused, SOLID design principles are followed, and MT5 trade synchronization is properly implemented.

---

## 🔄 PART 1: MT5 Trade Synchronization

### Current State: ❌ CRITICAL GAP

**Missing MT5 History APIs:**
- `mt5.history_orders_get()` - NOT USED anywhere in codebase
- `mt5.history_deals_get()` - NOT USED anywhere in codebase

This means:
- External trades placed via MT5 terminal are never captured
- Closed positions have no reliable sync mechanism
- Trade P&L history is incomplete

### Recommended Implementation Location: **SYNC MODE**

**Why sync mode is best:**
1. Already handles MT5 data synchronization (market data)
2. Natural extension: sync market data + sync trade history
3. Can be called before `live` mode or standalone
4. Keeps concerns separated (SRP compliance)

### Implementation Plan

**1. Create new file: `src/core/trade_syncer.py`**
```python
"""Synchronize historical trades from MT5 to database."""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
import MetaTrader5 as mt5

from src.utils.mt5_decorator import mt5_safe
from src.utils.logging_factory import LoggingFactory


class TradeSyncer:
    """Syncs historical trades from MT5 to database."""
    
    def __init__(self, db, mt5_connector):
        self.db = db
        self.mt5 = mt5_connector
        self.logger = LoggingFactory.get_logger(__name__)
    
    @mt5_safe(max_retries=3)
    def sync_deals_from_mt5(self, days_back: int = 30) -> int:
        """Sync completed deals from MT5 history.
        
        Args:
            days_back: How many days of history to sync.
            
        Returns:
            Number of deals synced.
        """
        from_date = datetime.now() - timedelta(days=days_back)
        to_date = datetime.now()
        
        deals = mt5.history_deals_get(from_date, to_date)
        if deals is None:
            self.logger.warning("No deals returned from MT5")
            return 0
            
        synced = 0
        for deal in deals:
            if self._upsert_deal(deal):
                synced += 1
        
        self.logger.info(f"Synced {synced}/{len(deals)} deals from MT5")
        return synced
    
    @mt5_safe(max_retries=3)
    def sync_orders_from_mt5(self, days_back: int = 30) -> int:
        """Sync order history from MT5.
        
        Args:
            days_back: How many days of history to sync.
            
        Returns:
            Number of orders synced.
        """
        from_date = datetime.now() - timedelta(days=days_back)
        to_date = datetime.now()
        
        orders = mt5.history_orders_get(from_date, to_date)
        if orders is None:
            self.logger.warning("No orders returned from MT5")
            return 0
            
        synced = 0
        for order in orders:
            if self._upsert_order(order):
                synced += 1
        
        self.logger.info(f"Synced {synced}/{len(orders)} orders from MT5")
        return synced
    
    def sync_open_positions(self) -> int:
        """Sync currently open positions from MT5.
        
        Returns:
            Number of positions synced.
        """
        positions = mt5.positions_get()
        if positions is None:
            return 0
            
        synced = 0
        for pos in positions:
            if self._upsert_position(pos):
                synced += 1
        
        return synced
    
    def reconcile_with_database(self) -> Dict:
        """Compare MT5 positions with database and reconcile.
        
        Returns:
            Dict with reconciliation results.
        """
        # Get open positions from MT5
        mt5_positions = {p.ticket: p for p in (mt5.positions_get() or [])}
        
        # Get 'open' trades from database
        db_open = self.db.execute_query(
            "SELECT order_id, deal_id, status FROM trades WHERE status = 'open'"
        ).fetchall()
        
        results = {
            "closed_in_mt5": [],  # DB says open, MT5 says closed
            "missing_in_db": [],  # MT5 has position, DB doesn't
            "synced": [],
        }
        
        # Check DB positions against MT5
        for row in db_open:
            ticket = row["order_id"] or row["deal_id"]
            if ticket and ticket not in mt5_positions:
                results["closed_in_mt5"].append(ticket)
                # Update DB to reflect closed status
                self._mark_trade_closed(ticket)
        
        return results
    
    def _upsert_deal(self, deal) -> bool:
        """Insert or update a deal in the database."""
        # Implementation here
        pass
    
    def _upsert_order(self, order) -> bool:
        """Insert or update an order in the database."""
        pass
    
    def _upsert_position(self, position) -> bool:
        """Insert or update a position in the database."""
        pass
    
    def _mark_trade_closed(self, ticket: int) -> None:
        """Mark a trade as closed in the database."""
        pass
```

**2. Update `src/main.py` _mode_sync:**
```python
def _mode_sync(config: dict, args, logger):
    # ... existing market data sync ...
    
    # NEW: Sync trade history from MT5
    logger.info("=" * 60)
    logger.info("Syncing trade history from MT5...")
    
    from src.core.trade_syncer import TradeSyncer
    trade_syncer = TradeSyncer(db, mt5_conn)
    
    # Sync deals and orders
    deals_synced = trade_syncer.sync_deals_from_mt5(days_back=30)
    orders_synced = trade_syncer.sync_orders_from_mt5(days_back=30)
    
    # Reconcile open positions
    reconciliation = trade_syncer.reconcile_with_database()
    
    logger.info(f"Trade sync complete: {deals_synced} deals, {orders_synced} orders")
    if reconciliation["closed_in_mt5"]:
        logger.info(f"Marked {len(reconciliation['closed_in_mt5'])} positions as closed")
```

**3. Database Schema Updates (add migration):**
```sql
-- Add missing fields to trades table
ALTER TABLE trades ADD COLUMN ticket INTEGER;           -- MT5 position ticket
ALTER TABLE trades ADD COLUMN magic INTEGER;            -- Magic number for bot filtering
ALTER TABLE trades ADD COLUMN swap REAL DEFAULT 0;      -- Swap charges
ALTER TABLE trades ADD COLUMN commission REAL DEFAULT 0;-- Commission
ALTER TABLE trades ADD COLUMN comment TEXT;             -- Trade comment
ALTER TABLE trades ADD COLUMN external BOOLEAN DEFAULT 0; -- Placed outside bot
ALTER TABLE trades ADD COLUMN mt5_synced_at TIMESTAMP;  -- Last sync time
```

---

## 🎯 PART 2: OOP PRINCIPLES AUDIT

### 2.1 Encapsulation Issues

| File                               | Issue                                  | Fix                           |
| ---------------------------------- | -------------------------------------- | ----------------------------- |
| `src/core/position_persistence.py` | Directly accesses `self.db.conn`       | Use `self.db.execute_query()` |
| `src/core/init_manager.py`         | `self.db.conn.cursor()` direct access  | Use `db.execute_query()`      |
| Multiple files                     | Direct `mt5.*` calls without decorator | Use `MT5Connector` methods    |

**Current (Bad):**
```python
cursor = self.db.conn.cursor()
cursor.execute(query, params)
```

**Should Be (Good):**
```python
result = self.db.execute_query(query, params)
```

### 2.2 Inheritance Issues

**BaseStrategy** ([src/core/base_strategy.py](src/core/base_strategy.py)):
- ✅ Now has `@abstractmethod` decorators (verified in audit)
- ✅ Proper ABC inheritance

**ExitStrategy hierarchy:**
- ✅ `BaseExitStrategy` is properly abstract
- ✅ All exit strategies implement `evaluate()` method

### 2.3 Polymorphism Issues

**Strategy Factory** ([src/strategies/factory.py](src/strategies/factory.py)):
- ✅ Properly returns different strategy types
- ⚠️ Could use Protocol/Interface typing for better IDE support

### 2.4 Abstraction Candidates

| Code Pattern             | Current Location  | Should Be                           |
| ------------------------ | ----------------- | ----------------------------------- |
| ATR calculation          | 3 different files | `src/utils/indicators.py`           |
| Position limit checking  | 2 files           | Single `PositionLimitManager`       |
| Account status retrieval | 3 files           | `MT5Connector.get_account_status()` |
| MT5 position retrieval   | 8 files           | `MT5Connector.get_open_positions()` |

---

## 📐 PART 3: SOLID PRINCIPLES CHECK

### Single Responsibility Principle (SRP) ❌ VIOLATIONS

| File                             | Issue                                         | Lines       |
| -------------------------------- | --------------------------------------------- | ----------- |
| `src/main.py`                    | `_mode_live()` is ~500 lines doing too much   | 200-700     |
| `src/core/adaptive_trader.py`    | Handles trading, logging, position management | 497 lines   |
| `src/ui/web/dashboard_server.py` | API routes + data processing + MT5 calls      | 1200+ lines |

**Fix:** Extract into smaller classes:
- `LiveTradingLoop` - Main loop logic
- `SignalProcessor` - Signal generation
- `PositionSizer` - Lot size calculations
- `TradeExecutor` - Order placement

### Open/Closed Principle (OCP) ✅ MOSTLY GOOD

- Strategy system is extensible via factory
- Exit strategies are pluggable

### Liskov Substitution Principle (LSP) ⚠️ MINOR ISSUES

| Issue                                                   | Location           |
| ------------------------------------------------------- | ------------------ |
| `BaseStrategy.generate_entry_signal()` signature varies | All strategy files |

### Interface Segregation (ISP) ✅ GOOD

- Exit strategies have small, focused interface
- Strategies implement only required methods

### Dependency Inversion (DIP) ⚠️ NEEDS IMPROVEMENT

| Issue                                       | Fix                      |
| ------------------------------------------- | ------------------------ |
| Hard-coded `DatabaseManager` in many places | Inject via constructor   |
| Direct `ConfigManager.get_config()` calls   | Pass config as parameter |

---

## 🔍 PART 4: DUPLICATE CODE ANALYSIS

### HIGH PRIORITY Duplicates (Must Fix)

| Duplicate                   | Count | Locations                                                   | Priority |
| --------------------------- | ----- | ----------------------------------------------------------- | -------- |
| MT5 `positions_get()` calls | 8     | dashboard_server, trade_monitor, position_persistence, etc. | 🔴 HIGH   |
| ATR calculation             | 3     | base_strategy, atr_calculator, risk_manager                 | 🔴 HIGH   |
| Category position limits    | 2     | trade_quality_filter, position_persistence                  | 🔴 HIGH   |
| MT5 without `@mt5_safe`     | 6     | dashboard_server, trade_monitor, main                       | 🔴 HIGH   |

### MEDIUM PRIORITY Duplicates

| Duplicate                 | Count | Locations                                     | Priority |
| ------------------------- | ----- | --------------------------------------------- | -------- |
| Timeframe conversion      | 2     | timeframe_utils, data_fetcher                 | 🟡 MEDIUM |
| Account status retrieval  | 3     | dashboard_server, risk_manager, trade_manager | 🟡 MEDIUM |
| Direct `db.conn.cursor()` | 15+   | Multiple files                                | 🟡 MEDIUM |

### Consolidation Actions

1. **Create `src/utils/indicators.py`:**
```python
"""Centralized technical indicator calculations."""
import ta
import pandas as pd

def calculate_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Canonical ATR calculation."""
    return ta.volatility.AverageTrueRange(
        high=data["high"], low=data["low"], close=data["close"], window=period
    ).average_true_range()

def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Canonical RSI calculation."""
    return ta.momentum.RSIIndicator(close, window=period).rsi()
```

2. **Add to `MT5Connector`:**
```python
@mt5_safe(max_retries=3)
def get_account_status(self) -> Dict:
    """Get current account information."""
    account = mt5.account_info()
    return {"balance": account.balance, ...} if account else {}
```

3. **Merge position limit logic** to single `PositionLimitManager` class

---

## 📁 PART 5: FILE STRUCTURE ISSUES

### Current Structure Problems

| File                  | Current Location         | Should Be            | Reason             |
| --------------------- | ------------------------ | -------------------- | ------------------ |
| `mt5_connector.py`    | `src/`                   | `src/core/`          | Core trading logic |
| `strategy_manager.py` | `src/`                   | `src/core/`          | Core trading logic |
| `DataCache` class     | Inside `data_fetcher.py` | `src/utils/cache.py` | Reusable utility   |

### Recommended Structure

```
src/
├── __init__.py
├── main.py                      # Entry point only
├── core/                        # Business logic
│   ├── adaptive_trader.py
│   ├── base_strategy.py
│   ├── data_fetcher.py
│   ├── data_handler.py
│   ├── init_manager.py
│   ├── mt5_connector.py         # MOVE HERE
│   ├── position_persistence.py
│   ├── strategy_manager.py      # MOVE HERE
│   ├── strategy_selector.py
│   ├── trade_manager.py
│   ├── trade_monitor.py
│   ├── trade_syncer.py          # NEW
│   └── __init__.py
├── strategies/                  # Strategy implementations
├── backtesting/                 # Backtesting modules
├── database/                    # DB access layer
├── utils/                       # Reusable utilities
│   ├── indicators.py            # NEW - consolidate ATR/RSI
│   ├── cache.py                 # NEW - extract DataCache
│   └── ...existing utils...
├── ui/                          # GUI/Web interfaces
├── reports/                     # Report generation
└── config/                      # Configuration
```

---

## ✅ PART 6: ACTION CHECKLIST

### Phase 1: Critical Fixes (Week 1)
- [ ] Create `src/core/trade_syncer.py` with MT5 history sync
- [ ] Add trade sync to `_mode_sync()` in main.py
- [ ] Add missing columns to trades table (migration)
- [ ] Move `mt5_connector.py` to `src/core/`
- [ ] Move `strategy_manager.py` to `src/core/`

### Phase 2: Duplicate Consolidation (Week 2)
- [ ] Create `src/utils/indicators.py` with canonical ATR/RSI
- [ ] Add `get_account_status()` to MT5Connector
- [ ] Merge position limit logic to single class
- [ ] Remove duplicate timeframe conversion from data_fetcher.py
- [ ] Replace all `positions_get()` calls with `MT5Connector.get_open_positions()`

### Phase 3: OOP/SOLID Improvements (Week 3)
- [ ] Refactor `_mode_live()` into smaller classes
- [ ] Replace direct `db.conn.cursor()` with `db.execute_query()`
- [ ] Add `@mt5_safe` decorator to all MT5 operations
- [ ] Extract `DataCache` to `src/utils/cache.py`

### Phase 4: Testing & Documentation (Week 4)
- [ ] Add unit tests for TradeSyncer
- [ ] Add integration tests for MT5 trade sync
- [ ] Update copilot-instructions.md with new architecture
- [ ] Update docstrings for moved/refactored classes

---

## 📊 Impact Assessment

| Metric            | Before      | After (Expected) |
| ----------------- | ----------- | ---------------- |
| Code Duplication  | ~200 lines  | ~50 lines        |
| MT5 Trade Sync    | ❌ Missing   | ✅ Complete       |
| OOP Violations    | 8           | 0                |
| SOLID Violations  | 5           | 1 (acceptable)   |
| File Organization | 3 misplaced | 0 misplaced      |

---

## 🔗 Related Issues

- Dashboard Position Count Fixed (#previous)
- Trading Bot DB at Root (#previous)

---

**Priority:** HIGH
**Estimated Effort:** 4 weeks
**Breaking Changes:** Yes - file relocations require import updates
