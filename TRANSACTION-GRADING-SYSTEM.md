# Transaction Grading System

**Created:** 2026-05-28  
**Purpose:** Design a sophisticated, research-backed system to score individual buy/sell transactions and overall trading quality, with special emphasis on opportunity cost and selling near local tops/bottoms.  
**Goal:** Enable measurable improvement in trade execution quality over 3–6 months.

---

## 1. Objective

Current realized P&L only tells part of the story. Two traders can have identical P&L but very different timing quality:

- Trader A sells near a local top → avoids a 25% drawdown
- Trader B sells the same position 3 weeks earlier → misses a 40% rally

We want a **Transaction Quality Score** that rewards good timing (especially selling before drops or near local tops) and penalizes poor timing (selling too early before major upside).

The system should produce:
- Per-transaction score (–100 to +100)
- Aggregate Trader Score (single number)
- Time-series evolution of trading quality

---

## 2. Research Foundation

### Existing Approaches

| Approach | Source / Paper | Strengths | Weaknesses | Relevance |
|----------|----------------|-----------|------------|---------|
| Implementation Shortfall | Perold (1988), "The Implementation Shortfall" | Rigorous cost measurement | Focused on execution cost, not timing | Medium |
| Post-Trade Analysis / Regret | Various quant funds | Captures "could have done better" | Often subjective | High |
| Peak Detection + Labeling | Technical analysis + ML (e.g., `scipy.signal.find_peaks`) | Objective local extrema | Sensitive to window size | High |
| Profit vs. Maximum Favorable Excursion (MFE) | Trading literature (e.g., "Trade Your Way to Financial Freedom") | Quantifies missed profit | Doesn't penalize selling before drops | High |
| Sell Timing Alpha | Academic studies on retail investor behavior (e.g., Barber & Odean) | Shows systematic errors | Not a scoring system | Medium |

**Key Insight from Research:** The best sell-timing metrics combine two dimensions:
1. **Avoided Loss** (selling before a significant drawdown)
2. **Missed Gain** (opportunity cost of selling before a significant rally)

---

## 3. Proposed Transaction Grading Metric

### 3.1 Core Formula (Sell Transactions)

For each **sell** transaction on symbol `S` at time `t`:

```
QualityScore(sell) = 
    + α × AvoidedDropScore
    - β × MissedGainScore
    + γ × RealizedProfitScore
    - δ × VolatilityPenalty
```

Where:

- **AvoidedDropScore** = max drawdown in next N days after sell (capped at –30%)
- **MissedGainScore** = maximum favorable excursion (MFE) in next N days after sell
- **RealizedProfitScore** = realized gain % normalized by volatility
- **VolatilityPenalty** = σ (symbol) over lookback window (prevents penalizing high-vol names unfairly)

**Recommended weights (initial):**
- α = 1.0 (avoiding losses is valuable)
- β = 0.8 (missing gains hurts but less than avoiding losses for most investors)
- γ = 0.6
- δ = 0.3

### 3.2 Local Extremum Detection

To detect "sold near local top":

Use a **rolling window peak detection** approach:

```python
from scipy.signal import find_peaks

def detect_local_top(prices: pd.Series, window: int = 20, prominence: float = 0.08) -> bool:
    """Returns True if the sell occurred within 3 days of a local peak."""
    peaks, _ = find_peaks(prices.values, distance=window, prominence=prominence)
    # Check if sell date is within ±3 trading days of any peak
    ...
```

**Tunable parameters** (document in code):
- `window`: 15–30 trading days (balances noise vs. meaningful swings)
- `prominence`: 7–12% (depends on symbol volatility)

### 3.3 Buy Transaction Scoring (Secondary)

Buys are harder to grade in isolation. Initial approach:

- Score buys based on subsequent price action (did price go up meaningfully after buy?)
- Lower weight than sells initially

---

## 4. Aggregate Trader Score

Single number per time period (monthly / quarterly):

```
TraderScore = median(QualityScore over all sells in period) 
              + 0.3 × (AvoidedBigDrops / TotalSells)
              - 0.2 × (SoldBeforeRallies / TotalSells)
```

Also track:
- **Timing Alpha** vs. simple "buy & hold" benchmark for the same holdings
- **Improvement Rate** (TraderScore trend over 3–6 months)

---

## 5. Data Requirements

- Transaction MASTER CSV (already exists)
- Daily price history for all symbols traded (need to build or fetch via `price_fetcher.py`)
- 20–60 trading days of forward price data after each sell for opportunity cost calculation
- Realized Gain/Loss details (for cost basis accuracy)

---

## 6. Implementation Roadmap (Phased)

### Phase 0: Research & Design (Current)
- [x] Create this document
- [ ] Literature review expansion (add specific papers)
- [ ] Finalize formula + parameters

### Phase 1: Data Foundation (1–2 agent sessions)
- Build daily price history cache for all symbols in transaction history
- Implement local peak/valley detection module
- Add forward-looking MFE / max drawdown calculation

### Phase 2: Per-Transaction Scoring (2–3 sessions)
- Implement `calculate_sell_quality()` function
- Add scoring to existing transactions (backfill)
- Create API endpoint `/transactions/grading`

### Phase 3: Dashboard Integration
- New tab or section in `portfolio-dashboard`
- Per-symbol timing quality heatmap
- Trader Score trend line

### Phase 4: Feedback Loop
- Monthly "Trade Review" report (top 5 best/worst timed sells)
- Suggested improvements based on recurring patterns

---

## 7. Edge Cases & Anti-Gaming

- **Wash sales** — Ignore or down-weight scores on wash-sale transactions
- **Partial sells** — Score each lot separately when possible
- **High-volatility names** (e.g., options, small caps) — Stronger volatility normalization
- **Forced sells** (margin calls, tax-loss harvesting) — Flag and exclude from scoring
- **Very recent sells** (< 10 trading days) — Mark as "provisional" until forward window completes

---

## 8. Integration with Existing Systems

- **Monte Carlo** (`monte_carlo.py`): Use graded transaction history to create "quality-weighted" return distributions
- **Sentiment Indexes**: Add as exogenous variable to timing model (e.g., sell quality is higher when VIX > 25)
- **Earnings Calendar**: Penalize sells right before earnings if they were actually good timing (or vice versa)

---

## 9. Success Metrics (3–6 Months)

- Trader Score improves by ≥ 15–20 points
- Reduction in "sold before 20%+ rally" events by 30%
- Clear identification of 2–3 recurring timing mistakes

---

## References & Further Reading

- Perold, A. F. (1988). *The Implementation Shortfall: Paper versus Reality*
- Barber, B. M., & Odean, T. (various papers on retail investor timing)
- "Maximum Favorable Excursion" concept — from trading system design literature
- Peak detection algorithms: `scipy.signal.find_peaks` documentation + financial adaptations

---

**Next Agent Instructions:**

When implementing, start with Phase 1. Do **not** hardcode any private dollar amounts or specific holdings. All scoring should be relative and volatility-normalized. Validate against historical transactions before exposing in UI.