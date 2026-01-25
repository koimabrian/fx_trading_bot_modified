"""
VISUAL REFERENCE: Signal Generation & Optimization

═════════════════════════════════════════════════════════════════════════════
SIGNAL GENERATION FLOW (Current System)
═════════════════════════════════════════════════════════════════════════════

                        ┌─────────────────────┐
                        │   Market Data       │
                        │  (OHLC Candles)     │
                        └──────────┬──────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
            ┌───────▼────────┐ ┌──▼───────────┐ ┌─▼────────────┐
            │ RSI Strategy   │ │ EMA Strategy │ │ SMA Strategy │
            │                │ │              │ │              │
            │ Needs: 19 rows │ │ Needs: 25    │ │ Needs: 25    │
            │ Oversold <30   │ │ rows Golden  │ │ rows Golden  │
            │ Overbought >70 │ │ Cross        │ │ Cross        │
            └───────┬────────┘ └──┬───────────┘ └─┬────────────┘
                    │              │              │
                    └──────────────┼──────────────┘
                                   │
                        ┌──────────▼──────────┐
                        │  Generate Signal?   │
                        │  (if conditions OK) │
                        └──────────┬──────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │ (NO)                (YES)   │
                    │                             │
            ┌───────▼──────────┐      ┌──────────▼──────────────┐
            │ No Signal        │      │ Signal Created:         │
            │ Try next symbol  │      │ - Symbol: BTCUSD        │
            │                  │      │ - Action: BUY/SELL      │
            │                  │      │ - Confidence: 0.75      │
            │                  │      │ - Price: 42500          │
            │                  │      │ - Backtest metrics      │
            └───────┬──────────┘      └──────────┬──────────────┘
                    │                            │
                    └────────────────┬───────────┘
                                     │
                          ┌──────────▼───────────┐
                          │ Quality Filter Check │
                          │                      │
                          │ 1. Confidence OK?    │
                          │ 2. Win rate OK?      │
                          │ 3. Sharpe OK?        │
                          │ 4. Profit factor OK? │
                          │ 5. Sample size OK?   │
                          │ 6. Volatility OK?    │
                          │ 7. Drawdown OK?      │
                          └──────────┬───────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │ (FAIL)         │ (PASS)        │
                    │                │                │
            ┌───────▼──────────┐  ┌──▼───────────────┐
            │ Signal Rejected  │  │ Signal Approved  │
            │ Discard          │  │                  │
            │ (Log reason)     │  │ Execute Trade:   │
            │                  │  │ BUY/SELL volume  │
            └───────┬──────────┘  │ at market price  │
                    │             │                  │
                    │             └──┬───────────────┘
                    │                │
                    │          ┌─────▼──────────┐
                    │          │ Position Open  │
                    │          │                │
                    │          │ Monitor:       │
                    │          │ - P&L          │
                    │          │ - Stop loss    │
                    │          │ - Take profit  │
                    │          └─────┬──────────┘
                    │                │
                    └────────────────┼────────────────┐
                                     │                │
                          ┌──────────▼──────────┐  ┌──▼────────┐
                          │ Position Closed     │  │ Continue  │
                          │ (SL/TP/Time-based)  │  │ monitoring│
                          └─────────────────────┘  └───────────┘


═════════════════════════════════════════════════════════════════════════════
PROBLEMS & SOLUTIONS MATRIX
═════════════════════════════════════════════════════════════════════════════

SYMPTOM                    │ ROOT CAUSE                │ SOLUTION
───────────────────────────┼──────────────────────────┼─────────────────────
No signals at all          │ Market not trending      │ Adjust RSI thresholds
                           │ OR no crossovers         │ Shorten EMA periods
                           │                          │ Wait for trend
───────────────────────────┼──────────────────────────┼─────────────────────
Signals generated but      │ Quality filter too       │ Lower min_confidence
all rejected               │ strict on backtest       │ Run backtest first
                           │ metrics                  │ Lower thresholds
───────────────────────────┼──────────────────────────┼─────────────────────
Signals approved but no    │ Position limit hit       │ Close existing trades
trades execute             │ OR MT5 connection issue  │ Check MT5 status
                           │                          │ Verify account balance
───────────────────────────┼──────────────────────────┼─────────────────────
Trades execute but close   │ Stop loss too tight      │ Widen stop loss to 2%
immediately (SL hit)       │ OR high volatility       │ Use ATR-based stops
───────────────────────────┼──────────────────────────┼─────────────────────
Getting signals but low    │ Backtest data not       │ Run backtest on current
win rate                   │ current/representative  │ market data


═════════════════════════════════════════════════════════════════════════════
CONFIG TUNING GUIDE
═════════════════════════════════════════════════════════════════════════════

PARAMETER                  │ CONSERVATIVE   │ MODERATE    │ AGGRESSIVE
───────────────────────────┼────────────────┼─────────────┼─────────────
min_signal_confidence      │ 0.7            │ 0.5         │ 0.2-0.3
min_win_rate_pct           │ 60%            │ 50%         │ 40%
min_sharpe_ratio           │ 1.0            │ 0.5         │ 0.0
min_profit_factor          │ 2.0            │ 1.5         │ 0.8
───────────────────────────┼────────────────┼─────────────┼─────────────
RSI oversold               │ 30             │ 35          │ 40
RSI overbought             │ 70             │ 65          │ 60
───────────────────────────┼────────────────┼─────────────┼─────────────
EMA fast period            │ 12             │ 10          │ 8
EMA slow period            │ 26             │ 20          │ 15
───────────────────────────┼────────────────┼─────────────┼─────────────
Stop loss %                │ 0.5%           │ 1.0%        │ 2.0%
Take profit %              │ 1.0%           │ 2.0%        │ 3.0%
───────────────────────────┼────────────────┼─────────────┼─────────────
Max positions              │ 2              │ 3-5         │ 5+
───────────────────────────┼────────────────┼─────────────┼─────────────

RECOMMENDATION:
Start → MODERATE for balance of signals vs quality
Adjust → AGGRESSIVE if no signals
Tighten → CONSERVATIVE if too many losses


═════════════════════════════════════════════════════════════════════════════
STRATEGY INDICATOR REQUIREMENTS
═════════════════════════════════════════════════════════════════════════════

RSI STRATEGY (Relative Strength Index):
┌────────────────────────────────┐
│ Min Data: 19 candles           │
│ Entry: RSI < 30 (BUY)          │
│       RSI > 70 (SELL)          │
│ Exit: RSI > 50 (from 30)       │
│      RSI < 50 (from 70)        │
│ Confidence: 0.65               │
│ Best for: Mean-reversion       │
│ Market: Overbought/oversold    │
└────────────────────────────────┘

EMA STRATEGY (Exponential Moving Average):
┌────────────────────────────────┐
│ Min Data: 25 candles           │
│ Entry: EMA10 > EMA20 (BUY)     │
│        EMA10 < EMA20 (SELL)    │
│ Exit: Reverse signal           │
│ Confidence: 0.75               │
│ Best for: Trend-following      │
│ Market: Strong trends          │
└────────────────────────────────┘

SMA STRATEGY (Simple Moving Average):
┌────────────────────────────────┐
│ Min Data: 25 candles           │
│ Entry: SMA10 > SMA20 (BUY)     │
│        SMA10 < SMA20 (SELL)    │
│ Exit: Reverse signal           │
│ Confidence: 0.70               │
│ Best for: Trend-following      │
│ Market: Strong trends          │
└────────────────────────────────┘

MACD STRATEGY (MACD Histogram):
┌────────────────────────────────┐
│ Min Data: 40 candles           │
│ Entry: MACD > signal (BUY)     │
│        MACD < signal (SELL)    │
│ + histogram positive/negative  │
│ Exit: Histogram reversal       │
│ Confidence: 0.72               │
│ Best for: Momentum changes     │
│ Market: Trend reversals        │
└────────────────────────────────┘


═════════════════════════════════════════════════════════════════════════════
5-STEP QUICK DEBUGGING
═════════════════════════════════════════════════════════════════════════════

Step 1: CHECK MARKET DATA
   Command: sqlite3 src/data/market_data.sqlite \
            "SELECT symbol, COUNT(*) FROM ohlc_data GROUP BY symbol;"
   
   Expected: Each symbol has 1000+ rows
   If not:   Run "python -m src.main --mode sync"

Step 2: CHECK BACKTEST RESULTS
   Command: sqlite3 src/data/market_data.sqlite \
            "SELECT COUNT(*) FROM backtest_results;"
   
   Expected: >0 results
   If not:   Run "python -m src.main --mode backtest"

Step 3: RUN LIVE WITH DEBUG
   Command: python -m src.main --mode live 2>&1 | tee live.log
   
   Expected: See "Signal generated" messages
   If not:   Market not matching strategy conditions

Step 4: ANALYZE DEBUG OUTPUT
   Look for:
   ✓ "Signal approved" → Quality filter passed, trade should execute
   ✗ "Signal rejected" → Quality filter failed, check reason
   ✗ "No signals" → Market conditions don't match strategy

Step 5: ADJUST & RETRY
   If no signals:     Lower confidence threshold
   If rejected:       Run backtest or lower thresholds
   If approved:       Check MT5 connection & account balance


═════════════════════════════════════════════════════════════════════════════
EXPECTED BEHAVIOR BY TIME OF DAY
═════════════════════════════════════════════════════════════════════════════

During Market Hours (6 AM - 10 PM EST):
┌─────────────────────────────────────────┐
│ Expect: 2-5 signals per hour (all pairs)│
│ Execution rate: 30-50% of signals       │
│ Position holds: 30 minutes - 4 hours    │
│ Daily trades: 5-10+ trades              │
└─────────────────────────────────────────┘

During Low Liquidity (10 PM - 6 AM EST):
┌─────────────────────────────────────────┐
│ Expect: 0-2 signals per hour            │
│ Execution rate: 20-40% (wider spreads)  │
│ Position holds: 1-8 hours               │
│ Daily trades: 0-5 trades (fewer)        │
└─────────────────────────────────────────┘

During High Volatility (News Events):
┌─────────────────────────────────────────┐
│ Expect: 5-10+ signals per hour (spikes) │
│ Execution rate: 10-20% (tight filter)   │
│ Position holds: 5-30 minutes            │
│ Daily trades: 20+ trades (many)         │
└─────────────────────────────────────────┘


═════════════════════════════════════════════════════════════════════════════
SUCCESS METRICS & TARGETS
═════════════════════════════════════════════════════════════════════════════

METRIC                     │ POOR        │ OKAY       │ GOOD       │ EXCELLENT
───────────────────────────┼─────────────┼────────────┼────────────┼─────────
Signals Per Hour           │ 0           │ 1-2        │ 2-3        │ 3-5
Approved %                 │ <20%        │ 20-30%     │ 30-50%     │ 50-70%
Win Rate %                 │ <40%        │ 40-50%     │ 50-60%     │ 60%+
Avg Trade Duration         │ <5 min      │ 5-30 min   │ 30min-2hr  │ 2-4 hours
Daily Profit (% of acct)   │ <0%         │ 0-0.5%     │ 0.5-1.5%   │ 1.5-5%
Drawdown (daily)           │ >20%        │ 10-20%     │ 5-10%      │ <5%
Sharpe Ratio               │ <0          │ 0-0.5      │ 0.5-1.0    │ 1.0+


═════════════════════════════════════════════════════════════════════════════
DECISION TREE: Should I Trade Now?
═════════════════════════════════════════════════════════════════════════════

                            START
                             │
                 ┌───────────┴──────────────┐
                 │                          │
            Have signals?              Have signals?
            YES │                           │ NO
                ├─────────────────────────────────────┐
                │                                     │
            Quality filter              Adjust config:
            passing?                    - Lower thresholds
            YES │                       - Adjust parameters
                ├─────────────────────────────────────┐
                │                                     │
            Risk/reward                 Try again
            ratio OK?
            YES │
                ├─────────────────────────────────────┐
                │                                     │
            Position under              Close positions
            limit?                      reduce risk
            YES │
                ├─────────────────────────────────────┐
                │                                     │
            Account balance             Add funds
            sufficient?                 or reduce size
            YES │
                ├─────────────────────────────────────┐
                │                                     │
            Daily loss limit            STOP TRADING
            OK?                         manage losses
            YES │
                │
            EXECUTE TRADE ✓


═════════════════════════════════════════════════════════════════════════════
IMPLEMENTATION CHECKLIST
═════════════════════════════════════════════════════════════════════════════

PHASE 1: DIAGNOSIS (1 hour)
 □ Read QUICK_REFERENCE.md
 □ Enable DEBUG logging in config
 □ Run backtest
 □ Run live and look for signals
 □ Check which root cause applies

PHASE 2: QUICK FIX (30 minutes)
 □ Make 5-minute config fix
 □ Adjust RSI/EMA thresholds
 □ Lower min_confidence to 0.3
 □ Run live again

PHASE 3: DEBUGGING (2 hours)
 □ Create SignalDebugger class
 □ Integrate into adaptive_trader
 □ Log all signal attempts
 □ Analyze which signals rejected and why

PHASE 4: OPTIMIZATION (3-4 hours)
 □ Create SignalManager for persistence
 □ Refactor main loop with 10-second interval
 □ Implement ATR-based stops
 □ Add trailing stops

PHASE 5: TUNING (ongoing)
 □ Monitor daily metrics
 □ Adjust parameters based on results
 □ Run backtest weekly
 □ Track win rate and Sharpe ratio


═════════════════════════════════════════════════════════════════════════════
DOCUMENT REFERENCE BY USE CASE
═════════════════════════════════════════════════════════════════════════════

"I need signals NOW"
└─ → QUICK_REFERENCE.md → 5-Minute Fix

"Why aren't signals generating?"
└─ → QUICK_REFERENCE.md → Root Causes
└─ → SIGNAL_OPTIMIZATION_GUIDE.md → Sections 1-3

"How do I debug this?"
└─ → IMPLEMENTATION_ROADMAP.md → Debug Checklist
└─ → READY_TO_IMPLEMENT_CODE.md → SignalDebugger

"What should entries look like?"
└─ → SIGNAL_OPTIMIZATION_GUIDE.md → Section 6
└─ → MONITOR_SIGNAL_ENTRY_EXIT_FLOW.md → Component 3

"What should exits look like?"
└─ → SIGNAL_OPTIMIZATION_GUIDE.md → Section 7
└─ → READY_TO_IMPLEMENT_CODE.md → FILES 3-4

"How should monitoring work?"
└─ → SIGNAL_OPTIMIZATION_GUIDE.md → Section 8-9
└─ → MONITOR_SIGNAL_ENTRY_EXIT_FLOW.md → Component 4-5

"I want to refactor the architecture"
└─ → MONITOR_SIGNAL_ENTRY_EXIT_FLOW.md → Entire Document
└─ → READY_TO_IMPLEMENT_CODE.md → FILE 1

"I want production code to implement"
└─ → READY_TO_IMPLEMENT_CODE.md → All FILES

"I want a complete implementation guide"
└─ → IMPLEMENTATION_ROADMAP.md → Priority 1-4
"""
