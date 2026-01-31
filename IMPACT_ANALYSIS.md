# Impact Analysis Template

**Purpose:** Use this template to document which system components will be affected by proposed changes. This helps with planning, testing, and code review.

---

## How to Use This Template

1. Copy the template section below for each new change/feature
2. Fill in the details before starting implementation
3. Update as you discover new impacts during development
4. Keep this document in your PR description or as a separate tracking document

---

## Change Impact Template

### Change ID: [CHANGE-YYYY-MM-DD-001]

**Date:** YYYY-MM-DD  
**Author:** [Your Name]  
**Issue/PR:** [Link to issue or PR]

---

### 1. Change Summary

**What are you changing?**
- Brief description of the change (1-2 sentences)

**Why are you making this change?**
- Problem being solved
- Expected benefit

**Scope:**
- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring
- [ ] Performance improvement
- [ ] Documentation
- [ ] Configuration change
- [ ] Database schema change

---

### 2. Affected Components

#### Primary Components (Direct Changes)

| Component | File(s) | Type of Change | Complexity |
|-----------|---------|----------------|------------|
| Example: ConfigManager | `src/utils/config_manager.py` | Add new config validation | Medium |
| | | | |

#### Secondary Components (Indirect Impact)

| Component | File(s) | Impact | Requires Update? |
|-----------|---------|--------|------------------|
| Example: AdaptiveTrader | `src/core/adaptive_trader.py` | Uses new config value | Yes - add config read |
| | | | |

---

### 3. Component Analysis

Use the checklist below to identify all affected components:

#### Core Trading Components
- [ ] **src/main.py** - Entry point / mode orchestration
- [ ] **src/core/adaptive_trader.py** - Live trading engine
- [ ] **src/core/trader.py** - Trade execution
- [ ] **src/core/strategy_selector.py** - Strategy ranking
- [ ] **src/strategy_manager.py** - Strategy loading & signals
- [ ] **src/core/data_fetcher.py** - Market data retrieval
- [ ] **src/core/data_handler.py** - Data preparation
- [ ] **src/core/init_manager.py** - Initialization logic
- [ ] **src/core/trade_manager.py** - Trade management
- [ ] **src/core/trade_monitor.py** - Trade monitoring

#### Strategy System
- [ ] **src/strategies/factory.py** - Strategy factory
- [ ] **src/core/base_strategy.py** - Strategy interface
- [ ] **src/strategies/rsi_strategy.py** - RSI implementation
- [ ] **src/strategies/macd_strategy.py** - MACD implementation
- [ ] **src/strategies/ema_strategy.py** - EMA implementation
- [ ] **src/strategies/sma_strategy.py** - SMA implementation

#### Backtesting System
- [ ] **src/backtesting/backtest_manager.py** - Backtest engine
- [ ] **src/backtesting/backtest_orchestrator.py** - Orchestration
- [ ] **src/backtesting/metrics_engine.py** - Performance metrics
- [ ] **src/backtesting/trade_logger.py** - Trade recording
- [ ] **src/backtesting/trade_extractor.py** - Trade extraction

#### Database Layer
- [ ] **src/database/db_manager.py** - Database operations
- [ ] **src/database/migrations.py** - Schema management
- [ ] **Database Schema:** `tradable_pairs`, `market_data` (unified), `backtest_backtests`, `backtest_strategies`, `backtest_results`, `backtest_trades`, `trades`, `optimal_parameters`

#### MT5 Integration
- [ ] **src/mt5_connector.py** - MT5 API wrapper
- [ ] **src/utils/mt5_decorator.py** - Retry decorator

#### UI Components
- [ ] **src/ui/web/dashboard_server.py** - Flask server
- [ ] **src/ui/web/dashboard_api.py** - API endpoints
- [ ] **src/ui/web/live_broadcaster.py** - WebSocket updates
- [ ] **src/ui/gui/init_wizard_dialog.py** - Init wizard
- [ ] **src/ui/gui/pair_selector_dialog.py** - Pair selector
- [ ] **src/ui/cli.py** - Command-line interface

#### Utility Components
- [ ] **src/utils/config_manager.py** - Configuration
- [ ] **src/utils/logging_factory.py** - Logging
- [ ] **src/utils/error_handler.py** - Error handling
- [ ] **src/utils/trading_rules.py** - Trading rules
- [ ] **src/utils/volatility_manager.py** - Volatility analysis
- [ ] **src/utils/data_validator.py** - Data validation
- [ ] **src/utils/timeframe_utils.py** - Timeframe utilities
- [ ] **src/utils/parameter_archiver.py** - Parameter storage
- [ ] **src/utils/indicator_analyzer.py** - Indicator calculations
- [ ] **src/utils/trade_quality_filter.py** - Trade filtering
- [ ] **src/utils/exit_strategies.py** - Exit strategies

#### Configuration & Documentation
- [ ] **src/config/config.yaml** - System configuration
- [ ] **README.md** - Documentation
- [ ] **COMPONENTS.md** - Component documentation
- [ ] **workflow.yaml** - Workflow documentation
- [ ] **commands.yaml** - Command reference

---

### 4. Data Flow Impact

**Does this change affect the data flow?**
- [ ] Yes
- [ ] No

**If yes, describe the data flow changes:**

**Before:**
```
[Describe current data flow]
Example: MT5 → DataFetcher → StrategyManager → Strategy
```

**After:**
```
[Describe new data flow]
Example: MT5 → DataFetcher → [NEW: DataTransformer] → StrategyManager → Strategy
```

---

### 5. Database Impact

**Does this change affect the database?**
- [ ] Yes - Schema change (requires migration)
- [ ] Yes - Query change (no schema change)
- [ ] No

**If yes, provide details:**

**Tables Affected:**
- Table 1: [table_name]
  - Type of change: [ADD/MODIFY/DELETE columns]
  - Migration required: [Yes/No]
  - Backwards compatible: [Yes/No]

**New Queries:**
- [List new queries or query changes]

**Migration Plan:**
1. Create migration in `src/database/migrations.py`
2. Update DatabaseManager queries
3. Test migration (upgrade + rollback)
4. Update unit tests

---

### 6. Configuration Impact

**Does this change affect configuration?**
- [ ] Yes - New config value
- [ ] Yes - Changed config value
- [ ] Yes - Removed config value
- [ ] No

**If yes, provide details:**

**Config Changes:**
```yaml
# Add to config.yaml
new_section:
  new_value: default_value
```

**Affected Components:**
- [List components that read this config]

**Backwards Compatibility:**
- [ ] Backwards compatible (default value provided)
- [ ] Breaking change (requires config update)

---

### 7. API / Interface Changes

**Does this change affect public APIs or interfaces?**
- [ ] Yes - Breaking change
- [ ] Yes - Non-breaking addition
- [ ] No

**If yes, provide details:**

**Changed Interfaces:**
- Class: [ClassName]
  - Method: [method_name]
  - Change: [Added parameter / Changed signature / Removed method]
  - Backwards compatible: [Yes/No]

**Affected Consumers:**
- [List components that use this interface]

---

### 8. Testing Impact

**Testing Strategy:**

#### Unit Tests Required
- [ ] Test 1: [Description]
  - File: `tests/unit/test_*.py`
  - Coverage: [Component/Method]
- [ ] Test 2: [Description]
  - File: `tests/unit/test_*.py`
  - Coverage: [Component/Method]

#### Integration Tests Required
- [ ] Test 1: [Description]
  - File: `tests/integration/test_*.py`
  - Coverage: [Multi-component flow]

#### End-to-End Tests Required
- [ ] Test 1: [Description]
  - File: `tests/e2e/test_*.py`
  - Coverage: [Full workflow]

#### Manual Testing Checklist
- [ ] Test in init mode
- [ ] Test in sync mode
- [ ] Test in backtest mode
- [ ] Test in live mode (with demo account)
- [ ] Test dashboard display
- [ ] Verify logs
- [ ] Check database integrity

#### Regression Testing
**Existing tests that need updates:**
- [ ] `tests/unit/test_config_and_db.py` - [Reason]
- [ ] `tests/integration/test_*.py` - [Reason]

---

### 9. Performance Impact

**Does this change affect performance?**
- [ ] Yes - Improvement
- [ ] Yes - Potential degradation
- [ ] No impact expected

**If yes, provide details:**

**Performance Considerations:**
- Affected operations: [List operations]
- Expected impact: [+/- X% in Y metric]
- Mitigation: [How to minimize negative impact]

**Benchmarks Required:**
- [ ] Benchmark 1: [Description]
- [ ] Benchmark 2: [Description]

---

### 10. Security Impact

**Does this change affect security?**
- [ ] Yes - Security improvement
- [ ] Yes - Potential security concern
- [ ] No

**If yes, provide details:**

**Security Considerations:**
- [Describe security implications]
- [List any new credentials/secrets]
- [Describe access control changes]

**Security Review Required:**
- [ ] Code review for security issues
- [ ] Credential handling verification
- [ ] Input validation checks

---

### 11. Dependencies

**Does this change introduce new dependencies?**
- [ ] Yes - New Python package
- [ ] Yes - New external service
- [ ] No

**If yes, provide details:**

**New Dependencies:**
| Dependency | Version | Purpose | Required/Optional |
|------------|---------|---------|-------------------|
| package-name | 1.0.0 | [Purpose] | Required |

**Installation Impact:**
- Update `requirements.txt`
- Update installation documentation
- Check for version conflicts

---

### 12. Rollback Plan

**How to rollback this change if needed:**

1. **Database:** [Rollback migration / Restore backup]
2. **Code:** [Git revert / Cherry-pick]
3. **Configuration:** [Restore old config.yaml]
4. **Verification:** [How to verify rollback success]

**Rollback Complexity:**
- [ ] Simple (code-only change)
- [ ] Medium (code + config)
- [ ] Complex (code + database + config)

---

### 13. Deployment Notes

**Pre-deployment:**
- [ ] Backup database
- [ ] Review configuration changes
- [ ] Notify users (if needed)

**Deployment Steps:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Post-deployment Verification:**
- [ ] Check logs for errors
- [ ] Verify dashboard loads
- [ ] Test critical workflows
- [ ] Monitor system health for 24 hours

---

### 14. Risk Assessment

**Overall Risk Level:**
- [ ] Low (minor change, well-tested)
- [ ] Medium (moderate impact, some risk)
- [ ] High (significant change, high impact)

**Risk Factors:**
- **Technical Risk:** [Low/Medium/High] - [Reason]
- **Data Risk:** [Low/Medium/High] - [Reason]
- **User Impact:** [Low/Medium/High] - [Reason]

**Mitigation Strategies:**
1. [Strategy 1]
2. [Strategy 2]

---

### 15. Timeline

**Estimated Effort:**
- Analysis: [X hours]
- Implementation: [Y hours]
- Testing: [Z hours]
- Documentation: [W hours]
- **Total:** [Total hours]

**Critical Path Dependencies:**
- [List any blocking dependencies]

---

### 16. Sign-off

**Reviewed By:**
- Developer: [Name] - [Date]
- Code Reviewer: [Name] - [Date]
- QA: [Name] - [Date]

**Status:**
- [ ] Planning
- [ ] In Progress
- [ ] Ready for Review
- [ ] Approved
- [ ] Deployed
- [ ] Verified

---

## Example: Complete Impact Analysis

### Change ID: CHANGE-2026-01-31-001

**Date:** 2026-01-31  
**Author:** Trading Bot Team  
**Issue/PR:** #123

---

### 1. Change Summary

**What are you changing?**
- Adding a new Bollinger Bands strategy to the strategy system

**Why are you making this change?**
- Users requested Bollinger Bands as an alternative volatility-based strategy
- Expected to improve performance in ranging markets

**Scope:**
- [x] New feature

---

### 2. Affected Components

#### Primary Components (Direct Changes)

| Component | File(s) | Type of Change | Complexity |
|-----------|---------|----------------|------------|
| StrategyFactory | `src/strategies/factory.py` | Register new strategy | Low |
| New Strategy | `src/strategies/bollinger_strategy.py` | New file | Medium |

#### Secondary Components (Indirect Impact)

| Component | File(s) | Impact | Requires Update? |
|-----------|---------|--------|------------------|
| BacktestManager | `src/backtesting/backtest_manager.py` | Will test new strategy | No - automatic |
| AdaptiveTrader | `src/core/adaptive_trader.py` | Will use if best performer | No - automatic |
| Documentation | `README.md`, `COMPONENTS.md` | List new strategy | Yes |

---

### 3. Component Analysis

#### Strategy System
- [x] **src/strategies/factory.py** - Register new strategy
- [x] **src/core/base_strategy.py** - Inherit from this
- [ ] **src/strategies/rsi_strategy.py** - No change
- [ ] **src/strategies/macd_strategy.py** - No change
- [ ] **src/strategies/ema_strategy.py** - No change
- [ ] **src/strategies/sma_strategy.py** - No change

#### Configuration & Documentation
- [x] **README.md** - Add to strategy list
- [x] **COMPONENTS.md** - Document new strategy

---

### 4. Data Flow Impact

**Does this change affect the data flow?**
- [ ] Yes
- [x] No

---

### 5. Database Impact

**Does this change affect the database?**
- [ ] Yes - Schema change
- [ ] Yes - Query change
- [x] No

---

### 6. Configuration Impact

**Does this change affect configuration?**
- [x] Yes - New config value

**Config Changes:**
```yaml
# Add to config.yaml under strategies section
strategies:
  bollinger:
    period: 20
    std_dev: 2.0
```

**Affected Components:**
- BollingerStrategy (reads config)

**Backwards Compatibility:**
- [x] Backwards compatible (default values in code)

---

### 7. API / Interface Changes

**Does this change affect public APIs or interfaces?**
- [x] Yes - Non-breaking addition

**Changed Interfaces:**
- Class: StrategyFactory
  - Method: STRATEGIES dict
  - Change: Added 'BOLLINGER' → BollingerStrategy
  - Backwards compatible: Yes

---

### 8. Testing Impact

#### Unit Tests Required
- [x] Test 1: BollingerStrategy signal generation
  - File: `tests/unit/test_strategies.py`
  - Coverage: generate_signals(), calculate_indicators()
- [x] Test 2: StrategyFactory creates BollingerStrategy
  - File: `tests/unit/test_strategies.py`
  - Coverage: StrategyFactory.create_strategy('BOLLINGER')

#### Integration Tests Required
- [x] Test 1: Backtest with Bollinger strategy
  - File: `tests/integration/test_backtest_integration.py`
  - Coverage: Full backtest execution

---

### 9. Performance Impact

**Does this change affect performance?**
- [x] Yes - Potential degradation

**Performance Considerations:**
- Affected operations: Backtesting will take longer (one more strategy)
- Expected impact: +~5% backtest time (4 strategies → 5 strategies)
- Mitigation: Parallel backtest execution already implemented

---

### 10. Security Impact

**Does this change affect security?**
- [ ] Yes
- [x] No

---

### 11. Dependencies

**Does this change introduce new dependencies?**
- [ ] Yes
- [x] No

---

### 12. Rollback Plan

**How to rollback this change if needed:**

1. **Database:** No database changes
2. **Code:** Git revert commit
3. **Configuration:** Remove bollinger section from config.yaml (optional)
4. **Verification:** Backtest with remaining strategies

**Rollback Complexity:**
- [x] Simple (code-only change)

---

### 13. Deployment Notes

**Pre-deployment:**
- [x] Backup database
- [x] Review configuration changes

**Deployment Steps:**
1. Deploy code
2. Add bollinger config to config.yaml (optional)
3. Run backtest to generate optimal parameters

**Post-deployment Verification:**
- [x] Run backtest mode with new strategy
- [x] Verify strategy appears in dashboard
- [x] Check logs for errors

---

### 14. Risk Assessment

**Overall Risk Level:**
- [x] Low (minor change, well-tested)

**Risk Factors:**
- **Technical Risk:** Low - Following existing strategy pattern
- **Data Risk:** Low - No database changes
- **User Impact:** Low - Non-breaking addition

---

### 15. Timeline

**Estimated Effort:**
- Analysis: 1 hour
- Implementation: 3 hours
- Testing: 2 hours
- Documentation: 1 hour
- **Total:** 7 hours

---

### 16. Sign-off

**Status:**
- [x] Approved
- [x] Deployed
- [x] Verified

---

## Additional Resources

**See Also:**
- [COMPONENTS.md](COMPONENTS.md) - Detailed component documentation
- [README.md](README.md) - System overview
- [workflow.yaml](workflow.yaml) - Development workflows

**Last Updated:** January 31, 2026
