---
market: india
version: 2
draft_notice: "Draft — numerical thresholds are starting points; the authoritative narrative is the prose body below. User will iterate as portfolio data accumulates and as scoring-engine calibration exposes mismatched thresholds. Schema is per SPEC §7.6 with non-breaking extensions (preferred, goals, two risk keys) flagged in plans/M0/M0.5-philosophy.md §1."
goals:
  horizon_years_min: 10
  alpha_target_pct_min: 3
  alpha_target_pct_max: 5
thresholds:
  non_financial:
    roe_min: 12
    roce_min: 12
    de_max: 1.0
    promoter_min: 40
    pledge_max: 10
    revenue_cagr_3y_min: 10
    profit_cagr_3y_min: 10
    fcf_positive: true
    mcap_min_cr: 5000
  banking_nbfc:
    roa_min: 1.0
    roe_min: 12
    nnpa_max: 1.5
    car_min: 15
    casa_min: 30
    nim_min: 3.0
    profit_growth_min: 10
    promoter_min: 30
    pledge_max: 10
    mcap_min_cr: 5000
preferred:
  non_financial:
    roe_preferred: 18
    roce_preferred: 18
    de_preferred_max: 0.5
    promoter_preferred: 55
    pledge_preferred_max: 0
    revenue_cagr_3y_preferred: 15
    profit_cagr_3y_preferred: 15
    fcf_positive_years_preferred: 3
    mcap_preferred_cr: 20000
  banking_nbfc:
    roa_preferred: 1.5
    roe_preferred: 15
    nnpa_preferred_max: 1.0
    car_preferred: 18
    casa_preferred: 40
    nim_preferred: 4.0
    profit_growth_preferred: 15
    promoter_preferred: 40
    pledge_preferred_max: 0
    mcap_preferred_cr: 20000
position_sizing:
  max_per_stock_pct: 8
  min_per_stock_pct: 2
  top_5_max_pct: 35
  avg_per_stock_pct_min: 3
  avg_per_stock_pct_max: 5
risk:
  max_drawdown_pct: 30
  small_cap_cap_pct: 20
  price_drop_review_trigger_pct: 20
  small_cap_price_drop_review_trigger_pct: 30
  position_concentration_debate_trigger_pct: 7
  price_down_debate_trigger_pct: 15
sector_exceptions:
  hospitals:     { promoter_min: 20 }
  it_mnc:        { promoter_min: 10 }
  psus:          { promoter_min: 45, applies_to: government }
  foreign_sub:   { parent_min: 40 }
  stock_exchanges: { exempt: true }
personas_enabled: [my-philosophy, jhunjhunwala, buffett, munger, pabrai]
persona_rotation: 3
---

# Investment Philosophy

This file defines your investment goals, stock selection criteria, ideal portfolio state, and rebalancing rules. The portfolio research agent uses this as the benchmark for evaluating your portfolio and recommending actions.

---

## Investment Goals

What are you investing for? Define your primary objectives.

- Primary goal: Long-term wealth creation (10+ year horizon)
- Secondary goal: Beat Nifty 50 returns by 3-5% annually
- Income needs: Not dependent on dividends; reinvest all returns
- No hurry to book losses unless the stock has no scopes of recovery
---

## Investment Ideology

What school of investing do you follow?

- Core approach: Quality-at-reasonable-price (GARP)
- **Fundamentals-first investor:** Investment decisions are driven entirely by business fundamentals and the underlying business story.
- Preference for companies with durable competitive advantages (moats)
- Avoid highly leveraged businesses
- Prefer management with strong capital allocation track record
- Patience: willing to hold through 2-3 year business cycles. Typical holding period is 1-3+ years.
- Price drops alone do not justify selling — only a deterioration of fundamentals or a broken business thesis
- Short-term technical indicators (daily moving averages, RSI, MACD, support/resistance from recent swings) are not part of the investment process. They do not apply meaningfully to a multi-year holding horizon.
- Long-term price context is used for accumulation decisions: 50-week MA (~1 year), 100-week MA (~2 years), multi-year support/resistance levels, and relative valuation (PE/PB vs own 5-year history).

---

## Stock Selection Criteria

What makes a stock worthy of your portfolio? Define minimum thresholds.
- These are just suggestive values and while they define strength of a stock, some stocks missing these doesn't necessarily make it a bad stock.

### Non-Financial Stocks

| Criteria | Minimum Threshold | Preferred |
|----------|------------------|-----------|
| ROE | >12% | >18% |
| ROCE | >12% | >18% |
| Debt-to-Equity | <1.0 | <0.5 |
| Promoter Holding | >40% | >55% |
| Promoter Pledge | <10% | 0% |
| Revenue Growth (3Y CAGR) | >10% | >15% |
| Profit Growth (3Y CAGR) | >10% | >15% |
| Free Cash Flow | Positive | Consistently positive for 3+ years |
| Market Cap | >5,000 Cr | >20,000 Cr |

### Banking & Financial Sector

*Financial institutions operate with high leverage as part of their core business model. Standard metrics like Debt-to-Equity or traditional ROCE/Free Cash Flow do not apply in the same way. Therefore, they are evaluated separately.*

| Criteria | Minimum Threshold | Preferred |
|----------|------------------|-----------|
| ROA (Return on Assets) | >1.0% | >1.5% |
| ROE | >12% | >15% |
| Net NPA (Asset Quality) | <1.5% | <1.0% |
| Capital Adequacy Ratio (CAR) | >15% | >18% |
| CASA Ratio (Banks only) | >30% | >40% |
| Net Interest Margin (NIM) | >3.0% | >4.0% |
| Profit Growth (3Y CAGR) | >10% | >15% |
| Promoter Holding | >30% | >40% |
| Promoter Pledge | <10% | 0% |
| Market Cap | >5,000 Cr | >20,000 Cr |

Additional qualitative criteria:
- Clean audit reports (no qualifications)
- Transparent management communication
- No frequent equity dilution
- Consistent dividend or buyback history preferred

---

## Business Story Criteria

Beyond the numbers, what qualitative factors determine whether a stock deserves a place in the portfolio? These are critical for long-term conviction.

| Factor | What to Evaluate | Strong Signal | Weak Signal |
|--------|-----------------|---------------|-------------|
| **Sector Growth Runway** | Is this industry growing for the next 5-10+ years? | Large addressable market, structural tailwinds (e.g., EMS, healthcare, digital infra) | Mature/shrinking market, commoditized, or facing structural disruption |
| **Competitive Moat** | Does the company have pricing power and defensibility? | Brand strength, network effects, switching costs, proprietary tech, regulatory moats | No differentiation, easy to replicate, competing on price alone |
| **Management Quality** | Is management trustworthy and competent at capital allocation? | Consistent execution, transparent communication, prudent M&A, insider buying | Frequent guidance misses, excessive related-party transactions, equity dilution |
| **Capacity Expansion** | Is the company investing in growth with visible payoff? | Capex tied to clear demand, new plants/capacity coming online, order book visibility | No reinvestment, or capex without clear demand signal |
| **Market Share Trajectory** | Is the company gaining or losing share? | Consistent share gains in a growing market | Losing share to new entrants or competitors |
| **Corporate Governance** | Is the company run ethically and transparently? | Clean audits, independent board, minimal pledging, aligned promoter interests | Audit qualifications, excessive pledging, related-party concerns |

> **How this is used:** The Business Story is scored 0-2 in the composite scoring system. A strong business story can justify holding through temporary price weakness or one weak quarter. A broken business story (e.g., structural disruption from a new competitor permanently rebasing margins) is a stronger exit signal than any price drop.

---

## Risk Tolerance

How much risk are you willing to take?

- Risk level: Moderate-aggressive
- Maximum portfolio drawdown tolerance: 30%
- Willing to hold small-caps: Yes, but capped at 20% of portfolio
- Willing to hold cyclical stocks: Yes, with sector cap
- Stop-loss approach: If a stock drops 20% from buy price, trigger a **deep fundamental review** — do not automatically sell. Exit only if fundamentals are broken.
- Small cap stop loss threshold can be higher (25-30%) if there is high conviction on fundamental recovery

---

## Sector Allocation Targets

Define your target sector allocation. The gap analysis will compare your actual portfolio against these targets.

- There is no target however if an individual sector is getting too concentrated this should be highlighted as a warning. 
- If there is high scope in coming cycle for a particular sector or industry, then we can have more concentration in that sector. 

---

## Position Sizing Rules

How large should individual positions be?

- Maximum single stock weight: 8% of portfolio - only for very highly convicted growth stock
- Minimum position size: 2% of portfolio (avoid tiny positions)
- Average position size: 3-5% of portfolio
- Top 5 holdings should not exceed 35% of portfolio

---

## Exit Rules

When should you sell a stock? **Exits are driven by fundamentals and business story, not by price action.**


### Fundamental Exit Triggers (consider exiting)
- Fundamental deterioration: ROE drops below 10% for 2 consecutive quarters (or Net NPA rises above 2.0% / ROA drops below 1.0% for financials)
- Business story broken: structural disruption, loss of competitive moat, or permanent margin compression (e.g., new competitor rebasing industry economics)
- Excessive valuation: PE (or P/B for financials) exceeds 2x sector median without growth acceleration / improving return ratios
- Management red flags: promoter pledge increases significantly, governance issues
- Consistent earnings misses (3+ quarters) with no credible turnaround plan

### Price Drop Review Trigger (review, don't automatically sell)
- If a stock drops 20% from buy price: **conduct a deep fundamental review** — is the business thesis still intact? Are earnings, ROE, and revenue growth still on track?
- If fundamentals are intact after review → **Hold with conviction** (or accumulate if underweight)
- If fundamentals have deteriorated → proceed with exit planning
- Small-cap positions may tolerate larger drawdowns (25-30%) if there is high conviction on fundamental recovery

> [!IMPORTANT]
> A price drop alone is NOT a sell signal. It is a **review trigger**. Exit only when fundamentals justify it.

### Trim Signals (reduce position)
- Position exceeds maximum weight (8%)
- Sector exceeds maximum allocation
- Better opportunity available in the same sector

### Hold Through (don't panic sell)
- Short-term price drops with intact fundamentals and intact business story
- Broad market corrections (Nifty down >10%)
- Temporary earnings miss with maintained guidance and credible recovery plan
- Price weakness or extended consolidation when fundamentals remain strong — this is volatility, not a sell signal

---

## Transition Guidelines

How aggressively should the agent recommend changes to align your portfolio with this philosophy?

- Approach: Gradual rebalancing over 3-6 months
- Do not recommend selling more than 2 positions in a single week
- Consider tax implications: prefer trimming over full exits when possible
- Accumulation: suggest SIP-style accumulation for new entries rather than lump-sum (at least 3-4 chunks, more for stocks where downside volatility is visible)
- Priority: fix overweight positions before building underweight sectors
- Minimum holding period: 6 months before recommending exit (unless fundamental thesis is broken)
- Factor in market conditions: avoid heavy selling during broad market panic

---

## Notes

- Update this file whenever your investment philosophy evolves
- The agent treats this file as the source of truth for all portfolio recommendations
- Be specific: vague rules lead to vague recommendations
- If a rule has exceptions, document them (e.g., "max DE of 1.0, except for banks where 8x is acceptable")
