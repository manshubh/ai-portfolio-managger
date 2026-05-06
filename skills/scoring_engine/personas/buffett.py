# Ported from virattt/ai-hedge-fund src/agents/warren_buffett.py
# at commit 0f6ac487986f7eb80749ed42bd26fb8330c450db (THIRD_PARTY.md §2.1)
# Stripped: langchain LLM call (generate_buffett_output), Pydantic signal model
# (WarrenBuffettSignal), src.graph.state plumbing (warren_buffett_agent entry),
# src.tools.api fetchers (get_financial_metrics / search_line_items /
# get_market_cap), src.utils.progress tracker.
# Adapted: data input now flows from skills.scoring_engine.lib.line_items.
# Upstream's analyze_fundamentals/analyze_moat read financial_metrics objects;
# our line_items already carry the same attribute names (return_on_equity,
# return_on_invested_capital, operating_margin, gross_margin) per the M3.4
# schema. For attributes not on our line_items (debt_to_equity, current_ratio,
# asset_turnover) we derive them from sibling fields and attach them onto the
# namespace so upstream math runs verbatim.
"""Warren Buffett persona — deterministic sub-scores + signal + confidence."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from skills.scoring_engine.lib import line_items as _li

# Minimum line-item periods required to emit a graded score.
# calculate_intrinsic_value (upstream L513) early-exits when
# len(financial_line_items) < 3, which is the floor below which Buffett's
# owner-earnings DCF cannot run. analyze_consistency wants ≥4 and analyze_moat
# wants ≥5, but those gracefully return score 0 rather than hard-blocking; the
# intrinsic-value bar is the strictest that actually prevents a graded score.
MIN_PERIODS_REQUIRED = 3

# Upstream raw-score ceiling (upstream L94-L100):
#   fundamental 10 + moat 5 + management 2 + pricing_power 5 + book_value 5 = 27.
# Note: upstream budgets fundamental at 10 in max_possible_score while the
# actual analyze_fundamentals max is 7 (2+2+2+1); upstream also omits
# analyze_consistency (max 3) from max_possible_score entirely. Preserved
# verbatim per investigation §5.1 ("retain native internal math scales").
_UPSTREAM_MAX_SCORE = 27


# ─── Upstream analyzers (kept verbatim, attribute-access preserved) ──────────

def analyze_fundamentals(metrics: list) -> dict[str, Any]:
    """Analyze company fundamentals based on Buffett's criteria."""
    if not metrics:
        return {"score": 0, "details": "Insufficient fundamental data"}

    latest_metrics = metrics[0]

    score = 0
    reasoning = []

    # Check ROE (Return on Equity)
    if latest_metrics.return_on_equity and latest_metrics.return_on_equity > 0.15:  # 15% ROE threshold
        score += 2
        reasoning.append(f"Strong ROE of {latest_metrics.return_on_equity:.1%}")
    elif latest_metrics.return_on_equity:
        reasoning.append(f"Weak ROE of {latest_metrics.return_on_equity:.1%}")
    else:
        reasoning.append("ROE data not available")

    # Check Debt to Equity
    if latest_metrics.debt_to_equity and latest_metrics.debt_to_equity < 0.5:
        score += 2
        reasoning.append("Conservative debt levels")
    elif latest_metrics.debt_to_equity:
        reasoning.append(f"High debt to equity ratio of {latest_metrics.debt_to_equity:.1f}")
    else:
        reasoning.append("Debt to equity data not available")

    # Check Operating Margin
    if latest_metrics.operating_margin and latest_metrics.operating_margin > 0.15:
        score += 2
        reasoning.append("Strong operating margins")
    elif latest_metrics.operating_margin:
        reasoning.append(f"Weak operating margin of {latest_metrics.operating_margin:.1%}")
    else:
        reasoning.append("Operating margin data not available")

    # Check Current Ratio
    if latest_metrics.current_ratio and latest_metrics.current_ratio > 1.5:
        score += 1
        reasoning.append("Good liquidity position")
    elif latest_metrics.current_ratio:
        reasoning.append(f"Weak liquidity with current ratio of {latest_metrics.current_ratio:.1f}")
    else:
        reasoning.append("Current ratio data not available")

    return {"score": score, "details": "; ".join(reasoning)}


def analyze_consistency(financial_line_items: list) -> dict[str, Any]:
    """Analyze earnings consistency and growth."""
    if len(financial_line_items) < 4:  # Need at least 4 periods for trend analysis
        return {"score": 0, "details": "Insufficient historical data"}

    score = 0
    reasoning = []

    # Check earnings growth trend
    earnings_values = [item.net_income for item in financial_line_items if item.net_income]
    if len(earnings_values) >= 4:
        # Simple check: is each period's earnings bigger than the next?
        earnings_growth = all(earnings_values[i] > earnings_values[i + 1] for i in range(len(earnings_values) - 1))

        if earnings_growth:
            score += 3
            reasoning.append("Consistent earnings growth over past periods")
        else:
            reasoning.append("Inconsistent earnings growth pattern")

        # Calculate total growth rate from oldest to latest
        if len(earnings_values) >= 2 and earnings_values[-1] != 0:
            growth_rate = (earnings_values[0] - earnings_values[-1]) / abs(earnings_values[-1])
            reasoning.append(f"Total earnings growth of {growth_rate:.1%} over past {len(earnings_values)} periods")
    else:
        reasoning.append("Insufficient earnings data for trend analysis")

    return {"score": score, "details": "; ".join(reasoning)}


def analyze_moat(metrics: list) -> dict[str, Any]:
    """Evaluate whether the company likely has a durable competitive advantage (moat).

    Enhanced to include multiple moat indicators that Buffett actually looks for:
    1. Consistent high returns on capital
    2. Pricing power (stable/growing margins)
    3. Scale advantages (improving metrics with size)
    4. Brand strength (inferred from margins and consistency)
    5. Switching costs (inferred from customer retention)
    """
    if not metrics or len(metrics) < 5:  # Need more data for proper moat analysis
        return {"score": 0, "max_score": 5, "details": "Insufficient data for comprehensive moat analysis"}

    reasoning = []
    moat_score = 0
    max_score = 5

    # 1. Return on Capital Consistency (Buffett's favorite moat indicator)
    historical_roes = [m.return_on_equity for m in metrics if m.return_on_equity is not None]
    historical_roics = [m.return_on_invested_capital for m in metrics if  # noqa: F841  (upstream dead variable, kept verbatim)
                        hasattr(m, 'return_on_invested_capital') and m.return_on_invested_capital is not None]

    if len(historical_roes) >= 5:
        # Check for consistently high ROE (>15% for most periods)
        high_roe_periods = sum(1 for roe in historical_roes if roe > 0.15)
        roe_consistency = high_roe_periods / len(historical_roes)

        if roe_consistency >= 0.8:  # 80%+ of periods with ROE > 15%
            moat_score += 2
            avg_roe = sum(historical_roes) / len(historical_roes)
            reasoning.append(
                f"Excellent ROE consistency: {high_roe_periods}/{len(historical_roes)} periods >15% (avg: {avg_roe:.1%}) - indicates durable competitive advantage")
        elif roe_consistency >= 0.6:
            moat_score += 1
            reasoning.append(f"Good ROE performance: {high_roe_periods}/{len(historical_roes)} periods >15%")
        else:
            reasoning.append(f"Inconsistent ROE: only {high_roe_periods}/{len(historical_roes)} periods >15%")
    else:
        reasoning.append("Insufficient ROE history for moat analysis")

    # 2. Operating Margin Stability (Pricing Power Indicator)
    historical_margins = [m.operating_margin for m in metrics if m.operating_margin is not None]
    if len(historical_margins) >= 5:
        # Check for stable or improving margins (sign of pricing power)
        avg_margin = sum(historical_margins) / len(historical_margins)
        recent_margins = historical_margins[:3]  # Last 3 periods
        older_margins = historical_margins[-3:]  # First 3 periods

        recent_avg = sum(recent_margins) / len(recent_margins)
        older_avg = sum(older_margins) / len(older_margins)

        if avg_margin > 0.2 and recent_avg >= older_avg:  # 20%+ margins and stable/improving
            moat_score += 1
            reasoning.append(f"Strong and stable operating margins (avg: {avg_margin:.1%}) indicate pricing power moat")
        elif avg_margin > 0.15:  # At least decent margins
            reasoning.append(f"Decent operating margins (avg: {avg_margin:.1%}) suggest some competitive advantage")
        else:
            reasoning.append(f"Low operating margins (avg: {avg_margin:.1%}) suggest limited pricing power")

    # 3. Asset Efficiency and Scale Advantages
    if len(metrics) >= 5:
        # Check asset turnover trends (revenue efficiency)
        asset_turnovers = []
        for m in metrics:
            if hasattr(m, 'asset_turnover') and m.asset_turnover is not None:
                asset_turnovers.append(m.asset_turnover)

        if len(asset_turnovers) >= 3:
            if any(turnover > 1.0 for turnover in asset_turnovers):  # Efficient asset use
                moat_score += 1
                reasoning.append("Efficient asset utilization suggests operational moat")

    # 4. Competitive Position Strength (inferred from trend stability)
    if len(historical_roes) >= 5 and len(historical_margins) >= 5:
        # Calculate coefficient of variation (stability measure)
        roe_avg = sum(historical_roes) / len(historical_roes)
        roe_variance = sum((roe - roe_avg) ** 2 for roe in historical_roes) / len(historical_roes)
        roe_stability = 1 - (roe_variance ** 0.5) / roe_avg if roe_avg > 0 else 0

        margin_avg = sum(historical_margins) / len(historical_margins)
        margin_variance = sum((margin - margin_avg) ** 2 for margin in historical_margins) / len(historical_margins)
        margin_stability = 1 - (margin_variance ** 0.5) / margin_avg if margin_avg > 0 else 0

        overall_stability = (roe_stability + margin_stability) / 2

        if overall_stability > 0.7:  # High stability indicates strong competitive position
            moat_score += 1
            reasoning.append(f"High performance stability ({overall_stability:.1%}) suggests strong competitive moat")

    # Cap the score at max_score
    moat_score = min(moat_score, max_score)

    return {
        "score": moat_score,
        "max_score": max_score,
        "details": "; ".join(reasoning) if reasoning else "Limited moat analysis available",
    }


def analyze_management_quality(financial_line_items: list) -> dict[str, Any]:
    """Checks for share dilution or consistent buybacks, and some dividend track record.

    A simplified approach:
      - if there's net share repurchase or stable share count, it suggests management
        might be shareholder-friendly.
      - if there's a big new issuance, it might be a negative sign (dilution).
    """
    if not financial_line_items:
        return {"score": 0, "max_score": 2, "details": "Insufficient data for management analysis"}

    reasoning = []
    mgmt_score = 0

    latest = financial_line_items[0]
    if hasattr(latest,
               "issuance_or_purchase_of_equity_shares") and latest.issuance_or_purchase_of_equity_shares and latest.issuance_or_purchase_of_equity_shares < 0:
        # Negative means the company spent money on buybacks
        mgmt_score += 1
        reasoning.append("Company has been repurchasing shares (shareholder-friendly)")

    if hasattr(latest,
               "issuance_or_purchase_of_equity_shares") and latest.issuance_or_purchase_of_equity_shares and latest.issuance_or_purchase_of_equity_shares > 0:
        # Positive issuance means new shares => possible dilution
        reasoning.append("Recent common stock issuance (potential dilution)")
    else:
        reasoning.append("No significant new stock issuance detected")

    # Check for any dividends
    if hasattr(latest,
               "dividends_and_other_cash_distributions") and latest.dividends_and_other_cash_distributions and latest.dividends_and_other_cash_distributions < 0:
        mgmt_score += 1
        reasoning.append("Company has a track record of paying dividends")
    else:
        reasoning.append("No or minimal dividends paid")

    return {
        "score": mgmt_score,
        "max_score": 2,
        "details": "; ".join(reasoning),
    }


def calculate_owner_earnings(financial_line_items: list) -> dict[str, Any]:
    """Calculate owner earnings (Buffett's preferred measure of true earnings power).

    Enhanced methodology: Net Income + Depreciation/Amortization - Maintenance CapEx - Working Capital Changes.
    Uses multi-period analysis for better maintenance capex estimation.
    """
    if not financial_line_items or len(financial_line_items) < 2:
        return {"owner_earnings": None, "details": ["Insufficient data for owner earnings calculation"]}

    latest = financial_line_items[0]
    details = []

    # Core components
    net_income = latest.net_income
    depreciation = latest.depreciation_and_amortization
    capex = latest.capital_expenditure

    if not all([net_income is not None, depreciation is not None, capex is not None]):
        missing = []
        if net_income is None:
            missing.append("net income")
        if depreciation is None:
            missing.append("depreciation")
        if capex is None:
            missing.append("capital expenditure")
        return {"owner_earnings": None, "details": [f"Missing components: {', '.join(missing)}"]}

    # Enhanced maintenance capex estimation using historical analysis
    maintenance_capex = estimate_maintenance_capex(financial_line_items)

    # Working capital change analysis (if data available)
    working_capital_change = 0
    if len(financial_line_items) >= 2:
        try:
            current_assets_current = getattr(latest, 'current_assets', None)
            current_liab_current = getattr(latest, 'current_liabilities', None)

            previous = financial_line_items[1]
            current_assets_previous = getattr(previous, 'current_assets', None)
            current_liab_previous = getattr(previous, 'current_liabilities', None)

            if all([current_assets_current, current_liab_current, current_assets_previous, current_liab_previous]):
                wc_current = current_assets_current - current_liab_current
                wc_previous = current_assets_previous - current_liab_previous
                working_capital_change = wc_current - wc_previous
                details.append(f"Working capital change: ${working_capital_change:,.0f}")
        except Exception:
            pass  # Skip working capital adjustment if data unavailable

    # Calculate owner earnings
    owner_earnings = net_income + depreciation - maintenance_capex - working_capital_change

    # Sanity checks
    if owner_earnings < net_income * 0.3:  # Owner earnings shouldn't be less than 30% of net income typically
        details.append("Warning: Owner earnings significantly below net income - high capex intensity")

    if maintenance_capex > depreciation * 2:  # Maintenance capex shouldn't typically exceed 2x depreciation
        details.append("Warning: Estimated maintenance capex seems high relative to depreciation")

    details.extend([
        f"Net income: ${net_income:,.0f}",
        f"Depreciation: ${depreciation:,.0f}",
        f"Estimated maintenance capex: ${maintenance_capex:,.0f}",
        f"Owner earnings: ${owner_earnings:,.0f}",
    ])

    return {
        "owner_earnings": owner_earnings,
        "components": {
            "net_income":             net_income,
            "depreciation":           depreciation,
            "maintenance_capex":      maintenance_capex,
            "working_capital_change": working_capital_change,
            "total_capex":            abs(capex) if capex else 0,
        },
        "details": details,
    }


def estimate_maintenance_capex(financial_line_items: list) -> float:
    """Estimate maintenance capital expenditure using multiple approaches.

    Buffett considers this crucial for understanding true owner earnings.
    """
    if not financial_line_items:
        return 0

    # Approach 1: Historical average as % of revenue
    capex_ratios = []
    depreciation_values = []

    for item in financial_line_items[:5]:  # Last 5 periods
        if hasattr(item, 'capital_expenditure') and hasattr(item, 'revenue'):
            if item.capital_expenditure and item.revenue and item.revenue > 0:
                capex_ratio = abs(item.capital_expenditure) / item.revenue
                capex_ratios.append(capex_ratio)

        if hasattr(item, 'depreciation_and_amortization') and item.depreciation_and_amortization:
            depreciation_values.append(item.depreciation_and_amortization)

    # Approach 2: Percentage of depreciation (typically 80-120% for maintenance)
    latest_depreciation = financial_line_items[0].depreciation_and_amortization if financial_line_items[
        0].depreciation_and_amortization else 0

    # Approach 3: Industry-specific heuristics
    latest_capex = abs(financial_line_items[0].capital_expenditure) if financial_line_items[
        0].capital_expenditure else 0

    # Conservative estimate: Use the higher of:
    # 1. 85% of total capex (assuming 15% is growth capex)
    # 2. 100% of depreciation (replacement of worn-out assets)
    # 3. Historical average if stable

    method_1 = latest_capex * 0.85  # 85% of total capex
    method_2 = latest_depreciation  # 100% of depreciation

    # If we have historical data, use average capex ratio
    if len(capex_ratios) >= 3:
        avg_capex_ratio = sum(capex_ratios) / len(capex_ratios)
        latest_revenue = financial_line_items[0].revenue if hasattr(financial_line_items[0], 'revenue') and \
                                                            financial_line_items[0].revenue else 0
        method_3 = avg_capex_ratio * latest_revenue if latest_revenue else 0

        # Use the median of the three approaches for conservatism
        estimates = sorted([method_1, method_2, method_3])
        return estimates[1]  # Median
    else:
        # Use the higher of method 1 and 2
        return max(method_1, method_2)


def calculate_intrinsic_value(financial_line_items: list) -> dict[str, Any]:
    """Calculate intrinsic value using enhanced DCF with owner earnings.

    Uses more sophisticated assumptions and conservative approach like Buffett.
    """
    if not financial_line_items or len(financial_line_items) < 3:
        return {"intrinsic_value": None, "details": ["Insufficient data for reliable valuation"]}

    # Calculate owner earnings with better methodology
    earnings_data = calculate_owner_earnings(financial_line_items)
    if not earnings_data["owner_earnings"]:
        return {"intrinsic_value": None, "details": earnings_data["details"]}

    owner_earnings = earnings_data["owner_earnings"]
    latest_financial_line_items = financial_line_items[0]
    shares_outstanding = latest_financial_line_items.outstanding_shares

    if not shares_outstanding or shares_outstanding <= 0:
        return {"intrinsic_value": None, "details": ["Missing or invalid shares outstanding data"]}

    # Enhanced DCF with more realistic assumptions
    details = []

    # Estimate growth rate based on historical performance (more conservative)
    historical_earnings = []
    for item in financial_line_items[:5]:  # Last 5 years
        if hasattr(item, 'net_income') and item.net_income:
            historical_earnings.append(item.net_income)

    # Calculate historical growth rate
    if len(historical_earnings) >= 3:
        oldest_earnings = historical_earnings[-1]
        latest_earnings = historical_earnings[0]
        years = len(historical_earnings) - 1

        if oldest_earnings > 0:
            historical_growth = ((latest_earnings / oldest_earnings) ** (1 / years)) - 1
            # Conservative adjustment - cap growth and apply haircut
            historical_growth = max(-0.05, min(historical_growth, 0.15))  # Cap between -5% and 15%
            conservative_growth = historical_growth * 0.7  # Apply 30% haircut for conservatism
        else:
            conservative_growth = 0.03  # Default 3% if negative base
    else:
        conservative_growth = 0.03  # Default conservative growth

    # Buffett's conservative assumptions
    stage1_growth = min(conservative_growth, 0.08)  # Stage 1: cap at 8%
    stage2_growth = min(conservative_growth * 0.5, 0.04)  # Stage 2: half of stage 1, cap at 4%
    terminal_growth = 0.025  # Long-term GDP growth rate

    # Risk-adjusted discount rate based on business quality
    # For now, use conservative 10%
    discount_rate = 0.10

    # Three-stage DCF model
    stage1_years = 5  # High growth phase
    stage2_years = 5  # Transition phase

    details.append(
        f"Using three-stage DCF: Stage 1 ({stage1_growth:.1%}, {stage1_years}y), Stage 2 ({stage2_growth:.1%}, {stage2_years}y), Terminal ({terminal_growth:.1%})")

    # Stage 1: Higher growth
    stage1_pv = 0
    for year in range(1, stage1_years + 1):
        future_earnings = owner_earnings * (1 + stage1_growth) ** year
        pv = future_earnings / (1 + discount_rate) ** year
        stage1_pv += pv

    # Stage 2: Transition growth
    stage2_pv = 0
    stage1_final_earnings = owner_earnings * (1 + stage1_growth) ** stage1_years
    for year in range(1, stage2_years + 1):
        future_earnings = stage1_final_earnings * (1 + stage2_growth) ** year
        pv = future_earnings / (1 + discount_rate) ** (stage1_years + year)
        stage2_pv += pv

    # Terminal value using Gordon Growth Model
    final_earnings = stage1_final_earnings * (1 + stage2_growth) ** stage2_years
    terminal_earnings = final_earnings * (1 + terminal_growth)
    terminal_value = terminal_earnings / (discount_rate - terminal_growth)
    terminal_pv = terminal_value / (1 + discount_rate) ** (stage1_years + stage2_years)

    # Total intrinsic value
    intrinsic_value = stage1_pv + stage2_pv + terminal_pv

    # Apply additional margin of safety (Buffett's conservatism)
    conservative_intrinsic_value = intrinsic_value * 0.85  # 15% additional haircut

    details.extend([
        f"Stage 1 PV: ${stage1_pv:,.0f}",
        f"Stage 2 PV: ${stage2_pv:,.0f}",
        f"Terminal PV: ${terminal_pv:,.0f}",
        f"Total IV: ${intrinsic_value:,.0f}",
        f"Conservative IV (15% haircut): ${conservative_intrinsic_value:,.0f}",
        f"Owner earnings: ${owner_earnings:,.0f}",
        f"Discount rate: {discount_rate:.1%}",
    ])

    return {
        "intrinsic_value":     conservative_intrinsic_value,
        "raw_intrinsic_value": intrinsic_value,
        "owner_earnings":      owner_earnings,
        "assumptions": {
            "stage1_growth":     stage1_growth,
            "stage2_growth":     stage2_growth,
            "terminal_growth":   terminal_growth,
            "discount_rate":     discount_rate,
            "stage1_years":      stage1_years,
            "stage2_years":      stage2_years,
            "historical_growth": conservative_growth,
        },
        "details": details,
    }


def analyze_book_value_growth(financial_line_items: list) -> dict[str, Any]:
    """Analyze book value per share growth - a key Buffett metric."""
    if len(financial_line_items) < 3:
        return {"score": 0, "details": "Insufficient data for book value analysis"}

    # Extract book values per share
    book_values = [
        item.shareholders_equity / item.outstanding_shares
        for item in financial_line_items
        if hasattr(item, 'shareholders_equity') and hasattr(item, 'outstanding_shares')
        and item.shareholders_equity and item.outstanding_shares
    ]

    if len(book_values) < 3:
        return {"score": 0, "details": "Insufficient book value data for growth analysis"}

    score = 0
    reasoning = []

    # Analyze growth consistency
    growth_periods = sum(1 for i in range(len(book_values) - 1) if book_values[i] > book_values[i + 1])
    growth_rate = growth_periods / (len(book_values) - 1)

    # Score based on consistency
    if growth_rate >= 0.8:
        score += 3
        reasoning.append("Consistent book value per share growth (Buffett's favorite metric)")
    elif growth_rate >= 0.6:
        score += 2
        reasoning.append("Good book value per share growth pattern")
    elif growth_rate >= 0.4:
        score += 1
        reasoning.append("Moderate book value per share growth")
    else:
        reasoning.append("Inconsistent book value per share growth")

    # Calculate and score CAGR
    cagr_score, cagr_reason = _calculate_book_value_cagr(book_values)
    score += cagr_score
    reasoning.append(cagr_reason)

    return {"score": score, "details": "; ".join(reasoning)}


def _calculate_book_value_cagr(book_values: list) -> tuple[int, str]:
    """Helper function to safely calculate book value CAGR and return score + reasoning."""
    if len(book_values) < 2:
        return 0, "Insufficient data for CAGR calculation"

    oldest_bv, latest_bv = book_values[-1], book_values[0]
    years = len(book_values) - 1

    # Handle different scenarios
    if oldest_bv > 0 and latest_bv > 0:
        cagr = ((latest_bv / oldest_bv) ** (1 / years)) - 1
        if cagr > 0.15:
            return 2, f"Excellent book value CAGR: {cagr:.1%}"
        elif cagr > 0.1:
            return 1, f"Good book value CAGR: {cagr:.1%}"
        else:
            return 0, f"Book value CAGR: {cagr:.1%}"
    elif oldest_bv < 0 < latest_bv:
        return 3, "Excellent: Company improved from negative to positive book value"
    elif oldest_bv > 0 > latest_bv:
        return 0, "Warning: Company declined from positive to negative book value"
    else:
        return 0, "Unable to calculate meaningful book value CAGR due to negative values"


def analyze_pricing_power(financial_line_items: list, metrics: list) -> dict[str, Any]:
    """Analyze pricing power - Buffett's key indicator of a business moat.

    Looks at ability to raise prices without losing customers (margin expansion during inflation).
    """
    if not financial_line_items or not metrics:
        return {"score": 0, "details": "Insufficient data for pricing power analysis"}

    score = 0
    reasoning = []

    # Check gross margin trends (ability to maintain/expand margins)
    gross_margins = []
    for item in financial_line_items:
        if hasattr(item, 'gross_margin') and item.gross_margin is not None:
            gross_margins.append(item.gross_margin)

    if len(gross_margins) >= 3:
        # Check margin stability/improvement
        recent_avg = sum(gross_margins[:2]) / 2 if len(gross_margins) >= 2 else gross_margins[0]
        older_avg = sum(gross_margins[-2:]) / 2 if len(gross_margins) >= 2 else gross_margins[-1]

        if recent_avg > older_avg + 0.02:  # 2%+ improvement
            score += 3
            reasoning.append("Expanding gross margins indicate strong pricing power")
        elif recent_avg > older_avg:
            score += 2
            reasoning.append("Improving gross margins suggest good pricing power")
        elif abs(recent_avg - older_avg) < 0.01:  # Stable within 1%
            score += 1
            reasoning.append("Stable gross margins during economic uncertainty")
        else:
            reasoning.append("Declining gross margins may indicate pricing pressure")

    # Check if company has been able to maintain high margins consistently
    if gross_margins:
        avg_margin = sum(gross_margins) / len(gross_margins)
        if avg_margin > 0.5:  # 50%+ gross margins
            score += 2
            reasoning.append(f"Consistently high gross margins ({avg_margin:.1%}) indicate strong pricing power")
        elif avg_margin > 0.3:  # 30%+ gross margins
            score += 1
            reasoning.append(f"Good gross margins ({avg_margin:.1%}) suggest decent pricing power")

    return {
        "score": score,
        "details": "; ".join(reasoning) if reasoning else "Limited pricing power analysis available",
    }


# ─── Adapter: our line_items → upstream-shaped objects ────────────────────────

def _enrich_line_items(items: list[SimpleNamespace]) -> list[SimpleNamespace]:
    """Derive upstream-expected ratios (debt_to_equity, current_ratio, asset_turnover)
    from sibling line-item fields and attach them onto each namespace.

    Upstream's analyze_fundamentals/analyze_moat read these off per-period objects;
    our M3.4 line-item schema does not emit them directly, but carries the raw
    fields needed to derive them. Kept here (not in lib/line_items.py) because
    the derivations are Buffett-specific — other personas may want different ones.
    """
    for it in items:
        # debt_to_equity = total_debt / shareholders_equity
        total_debt = getattr(it, "total_debt", None)
        equity = getattr(it, "shareholders_equity", None)
        if total_debt is not None and equity and equity > 0:
            it.debt_to_equity = total_debt / equity
        else:
            it.debt_to_equity = None

        # current_ratio = current_assets / current_liabilities
        ca = getattr(it, "current_assets", None)
        cl = getattr(it, "current_liabilities", None)
        if ca is not None and cl and cl > 0:
            it.current_ratio = ca / cl
        else:
            it.current_ratio = None

        # asset_turnover = revenue / total_assets
        rev = getattr(it, "revenue", None)
        ta = getattr(it, "total_assets", None)
        if rev is not None and ta and ta > 0:
            it.asset_turnover = rev / ta
        else:
            it.asset_turnover = None
    return items


# ─── Public entrypoint ────────────────────────────────────────────────────────

# Sub-score names match upstream's analyzer function names. Fixed insertion
# order → deterministic JSON output (investigation §5.3).
_SUB_SCORE_ORDER = (
    "fundamentals",
    "consistency",
    "moat",
    "management_quality",
    "pricing_power",
    "book_value_growth",
)


def _required_fields_for_insufficient_data(available: int) -> list[str]:
    """Produce jsonpath-like citations for the missing periods below the minimum.

    Buffett's intrinsic-value DCF (upstream L513) needs ≥3 periods of net_income
    to estimate historical growth, plus depreciation_and_amortization and
    capital_expenditure on the latest period for owner earnings. Cite the
    earliest missing indices for the CAGR-driving field.
    """
    missing: list[str] = []
    for idx in range(available, MIN_PERIODS_REQUIRED):
        missing.append(f"history.line_items[{idx}].net_income")
        missing.append(f"history.line_items[{idx}].depreciation_and_amortization")
        missing.append(f"history.line_items[{idx}].capital_expenditure")
    return missing


def run(metrics: dict) -> dict:
    """Produce the Warren Buffett persona output payload.

    Input: our extended metrics.json dict (SPEC §18.2 + M3.4 extension).
    Output: either the graded persona payload (investigation §5.2) or an
    insufficient_data payload when fewer than `MIN_PERIODS_REQUIRED` periods
    of line-items are available.
    """
    ticker = metrics.get("ticker")

    financial_line_items = _li.to_line_items(metrics)
    available = len(financial_line_items)

    if available < MIN_PERIODS_REQUIRED:
        return {
            "ticker":                ticker,
            "persona":               "buffett",
            "signal":                "insufficient_data",
            "confidence":            0.0,
            "missing_fields":        _required_fields_for_insufficient_data(available),
            "min_periods_required":  MIN_PERIODS_REQUIRED,
            "min_periods_available": available,
        }

    # Enrich with derived ratios (debt_to_equity, current_ratio, asset_turnover)
    # expected by upstream analyze_fundamentals / analyze_moat.
    financial_line_items = _enrich_line_items(financial_line_items)

    # Upstream called get_market_cap() in native currency; our fixtures carry
    # market cap in ₹ Cr under fund.mcap_cr. Intrinsic value comes out in the
    # same native unit as net_income (₹ Cr), so the margin_of_safety ratio is
    # scale-free — USD-vs-INR asymmetry does not distort the comparison so long
    # as both sides are in the same ledger currency, which our fixtures ensure.
    fund = metrics.get("fund") or {}
    market_cap = fund.get("mcap_cr")

    # Upstream passes `metrics` (financial_metrics list) to analyze_fundamentals
    # and analyze_moat; we pass the same enriched line-items list because our
    # schema carries the attribute names upstream reads (return_on_equity,
    # return_on_invested_capital, operating_margin, gross_margin), plus the
    # derived ratios attached by _enrich_line_items.
    fundamentals = analyze_fundamentals(financial_line_items)
    consistency = analyze_consistency(financial_line_items)
    moat = analyze_moat(financial_line_items)
    management = analyze_management_quality(financial_line_items)
    pricing_power = analyze_pricing_power(financial_line_items, financial_line_items)
    book_value = analyze_book_value_growth(financial_line_items)

    # Upstream L84-L91: total_score sums all six analyzer scores.
    total_score = (
        fundamentals["score"]
        + consistency["score"]
        + moat["score"]
        + management["score"]
        + pricing_power["score"]
        + book_value["score"]
    )

    intrinsic_value_analysis = calculate_intrinsic_value(financial_line_items)
    intrinsic_value = intrinsic_value_analysis["intrinsic_value"]
    margin_of_safety: float | None = None
    if intrinsic_value is not None and market_cap:
        margin_of_safety = (intrinsic_value - market_cap) / market_cap

    # Signal rules — translated from upstream's LLM prompt (generate_buffett_output,
    # L783-L786) onto a deterministic score/margin-of-safety mapping.
    #   Bullish: strong business AND margin_of_safety > 0.
    #   Bearish: poor business OR clearly overvalued (margin_of_safety ≤ -0.30).
    #   Neutral: otherwise.
    score_ratio = total_score / _UPSTREAM_MAX_SCORE if _UPSTREAM_MAX_SCORE else 0
    if score_ratio >= 0.70 and margin_of_safety is not None and margin_of_safety > 0:
        signal = "bullish"
    elif score_ratio <= 0.30 or (margin_of_safety is not None and margin_of_safety <= -0.30):
        signal = "bearish"
    else:
        signal = "neutral"

    # Confidence — upstream's prompt scale is 10-100 (L789-L793); we normalize
    # to 0.0-1.0. When margin_of_safety is known, weight it more heavily (it's
    # upstream's primary bullish/bearish driver); otherwise fall back to the
    # score ratio.
    if margin_of_safety is not None:
        confidence_raw = min(max(abs(margin_of_safety) * 150, 20), 95)
    else:
        confidence_raw = min(max(score_ratio * 100, 10), 80)
    confidence = round(confidence_raw / 100.0, 2)

    # Scale upstream's 0..27 raw total to the 0..100 contract (investigation §5.2).
    weighted_score = round(total_score / _UPSTREAM_MAX_SCORE * 100)

    # Fixed-order sub_scores and details for deterministic JSON output.
    sub_scores: dict[str, int] = {}
    details: dict[str, str] = {}
    by_name = {
        "fundamentals":       fundamentals,
        "consistency":        consistency,
        "moat":               moat,
        "management_quality": management,
        "pricing_power":      pricing_power,
        "book_value_growth":  book_value,
    }
    for name in _SUB_SCORE_ORDER:
        sub_scores[name] = by_name[name]["score"]
        details[name] = by_name[name]["details"]

    return {
        "ticker":         ticker,
        "persona":        "buffett",
        "sub_scores":     sub_scores,
        "weighted_score": weighted_score,
        "max_score":      100,
        "signal":         signal,
        "confidence":     confidence,
        "details":        details,
    }
