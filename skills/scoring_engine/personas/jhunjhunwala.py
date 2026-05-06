# Ported from virattt/ai-hedge-fund src/agents/rakesh_jhunjhunwala.py
# at commit 0f6ac487986f7eb80749ed42bd26fb8330c450db (THIRD_PARTY.md §2.1)
# Stripped: langchain LLM call, Pydantic signal model, src.graph.state plumbing,
# src.tools.api fetchers, src.utils.progress tracker.
# Adapted: data input now flows from skills.scoring_engine.lib.line_items.
"""Rakesh Jhunjhunwala persona — deterministic sub-scores + signal + confidence."""

from __future__ import annotations

from typing import Any

from skills.scoring_engine.lib import line_items as _li

# Minimum line-item periods required for the persona to emit a graded score.
# analyze_growth (upstream L251) early-exits when len(line_items) < 3, which is
# the strictest bar among the kept analyzers. Below 3 periods we cannot compute
# revenue/net-income CAGR, so we emit the insufficient_data payload.
MIN_PERIODS_REQUIRED = 3

# Upstream raw-score ceiling (upstream L87):
#   profitability 8 + growth 7 + balance_sheet 4 + cash_flow 3 + management 2 = 24.
_UPSTREAM_MAX_SCORE = 24


# ─── Upstream analyzers (kept verbatim, attribute-access preserved) ──────────

def analyze_profitability(financial_line_items: list) -> dict[str, Any]:
    """Analyze profitability metrics like net income, EBIT, EPS, operating income.
    Focus on strong, consistent earnings growth and operating efficiency.
    """
    if not financial_line_items:
        return {"score": 0, "details": "No profitability data available"}

    latest = financial_line_items[0]
    score = 0
    reasoning = []

    # Calculate ROE (Return on Equity) - Jhunjhunwala's key metric
    if (getattr(latest, 'net_income', None) and latest.net_income > 0 and
        getattr(latest, 'total_assets', None) and getattr(latest, 'total_liabilities', None) and
        latest.total_assets and latest.total_liabilities):

        shareholders_equity = latest.total_assets - latest.total_liabilities
        if shareholders_equity > 0:
            roe = (latest.net_income / shareholders_equity) * 100
            if roe > 20:
                score += 3
                reasoning.append(f"Excellent ROE: {roe:.1f}%")
            elif roe > 15:
                score += 2
                reasoning.append(f"Good ROE: {roe:.1f}%")
            elif roe > 10:
                score += 1
                reasoning.append(f"Decent ROE: {roe:.1f}%")
            else:
                reasoning.append(f"Low ROE: {roe:.1f}%")
        else:
            reasoning.append("Negative shareholders equity")
    else:
        reasoning.append("Unable to calculate ROE - missing data")

    # Operating Margin Analysis
    if (getattr(latest, "operating_income", None) and latest.operating_income and
        getattr(latest, "revenue", None) and latest.revenue and latest.revenue > 0):
        operating_margin = (latest.operating_income / latest.revenue) * 100
        if operating_margin > 20:
            score += 2
            reasoning.append(f"Excellent operating margin: {operating_margin:.1f}%")
        elif operating_margin > 15:
            score += 1
            reasoning.append(f"Good operating margin: {operating_margin:.1f}%")
        elif operating_margin > 0:
            reasoning.append(f"Positive operating margin: {operating_margin:.1f}%")
        else:
            reasoning.append(f"Negative operating margin: {operating_margin:.1f}%")
    else:
        reasoning.append("Unable to calculate operating margin")

    # EPS Growth Consistency (3-year trend)
    eps_values = [getattr(item, "earnings_per_share", None) for item in financial_line_items
                  if getattr(item, "earnings_per_share", None) is not None and getattr(item, "earnings_per_share", None) > 0]

    if len(eps_values) >= 3:
        initial_eps = eps_values[-1]
        final_eps = eps_values[0]
        years = len(eps_values) - 1

        if initial_eps > 0:
            eps_cagr = ((final_eps / initial_eps) ** (1/years) - 1) * 100
            if eps_cagr > 20:
                score += 3
                reasoning.append(f"High EPS CAGR: {eps_cagr:.1f}%")
            elif eps_cagr > 15:
                score += 2
                reasoning.append(f"Good EPS CAGR: {eps_cagr:.1f}%")
            elif eps_cagr > 10:
                score += 1
                reasoning.append(f"Moderate EPS CAGR: {eps_cagr:.1f}%")
            else:
                reasoning.append(f"Low EPS CAGR: {eps_cagr:.1f}%")
        else:
            reasoning.append("Cannot calculate EPS growth from negative base")
    else:
        reasoning.append("Insufficient EPS data for growth analysis")

    return {"score": score, "details": "; ".join(reasoning)}


def analyze_growth(financial_line_items: list) -> dict[str, Any]:
    """Analyze revenue and net income growth trends using CAGR.
    Jhunjhunwala favored companies with strong, consistent compound growth.
    """
    if len(financial_line_items) < 3:
        return {"score": 0, "details": "Insufficient data for growth analysis"}

    score = 0
    reasoning = []

    revenues = [getattr(item, "revenue", None) for item in financial_line_items
                if getattr(item, "revenue", None) is not None and getattr(item, "revenue", None) > 0]

    if len(revenues) >= 3:
        initial_revenue = revenues[-1]
        final_revenue = revenues[0]
        years = len(revenues) - 1

        if initial_revenue > 0:
            revenue_cagr = ((final_revenue / initial_revenue) ** (1/years) - 1) * 100

            if revenue_cagr > 20:
                score += 3
                reasoning.append(f"Excellent revenue CAGR: {revenue_cagr:.1f}%")
            elif revenue_cagr > 15:
                score += 2
                reasoning.append(f"Good revenue CAGR: {revenue_cagr:.1f}%")
            elif revenue_cagr > 10:
                score += 1
                reasoning.append(f"Moderate revenue CAGR: {revenue_cagr:.1f}%")
            else:
                reasoning.append(f"Low revenue CAGR: {revenue_cagr:.1f}%")
        else:
            reasoning.append("Cannot calculate revenue CAGR from zero base")
    else:
        reasoning.append("Insufficient revenue data for CAGR calculation")

    net_incomes = [getattr(item, "net_income", None) for item in financial_line_items
                   if getattr(item, "net_income", None) is not None and getattr(item, "net_income", None) > 0]

    if len(net_incomes) >= 3:
        initial_income = net_incomes[-1]
        final_income = net_incomes[0]
        years = len(net_incomes) - 1

        if initial_income > 0:
            income_cagr = ((final_income / initial_income) ** (1/years) - 1) * 100

            if income_cagr > 25:
                score += 3
                reasoning.append(f"Excellent income CAGR: {income_cagr:.1f}%")
            elif income_cagr > 20:
                score += 2
                reasoning.append(f"High income CAGR: {income_cagr:.1f}%")
            elif income_cagr > 15:
                score += 1
                reasoning.append(f"Good income CAGR: {income_cagr:.1f}%")
            else:
                reasoning.append(f"Moderate income CAGR: {income_cagr:.1f}%")
        else:
            reasoning.append("Cannot calculate income CAGR from zero base")
    else:
        reasoning.append("Insufficient net income data for CAGR calculation")

    if len(revenues) >= 3:
        declining_years = sum(1 for i in range(1, len(revenues)) if revenues[i-1] > revenues[i])
        consistency_ratio = 1 - (declining_years / (len(revenues) - 1))

        if consistency_ratio >= 0.8:
            score += 1
            reasoning.append(f"Consistent growth pattern ({consistency_ratio*100:.0f}% of years)")
        else:
            reasoning.append(f"Inconsistent growth pattern ({consistency_ratio*100:.0f}% of years)")

    return {"score": score, "details": "; ".join(reasoning)}


def analyze_balance_sheet(financial_line_items: list) -> dict[str, Any]:
    """Check financial strength - healthy asset/liability structure, liquidity.
    Jhunjhunwala favored companies with clean balance sheets and manageable debt.
    """
    if not financial_line_items:
        return {"score": 0, "details": "No balance sheet data"}

    latest = financial_line_items[0]
    score = 0
    reasoning = []

    if (getattr(latest, "total_assets", None) and getattr(latest, "total_liabilities", None)
        and latest.total_assets and latest.total_liabilities
        and latest.total_assets > 0):
        debt_ratio = latest.total_liabilities / latest.total_assets
        if debt_ratio < 0.5:
            score += 2
            reasoning.append(f"Low debt ratio: {debt_ratio:.2f}")
        elif debt_ratio < 0.7:
            score += 1
            reasoning.append(f"Moderate debt ratio: {debt_ratio:.2f}")
        else:
            reasoning.append(f"High debt ratio: {debt_ratio:.2f}")
    else:
        reasoning.append("Insufficient data to calculate debt ratio")

    if (getattr(latest, "current_assets", None) and getattr(latest, "current_liabilities", None)
        and latest.current_assets and latest.current_liabilities
        and latest.current_liabilities > 0):
        current_ratio = latest.current_assets / latest.current_liabilities
        if current_ratio > 2.0:
            score += 2
            reasoning.append(f"Excellent liquidity with current ratio: {current_ratio:.2f}")
        elif current_ratio > 1.5:
            score += 1
            reasoning.append(f"Good liquidity with current ratio: {current_ratio:.2f}")
        else:
            reasoning.append(f"Weak liquidity with current ratio: {current_ratio:.2f}")
    else:
        reasoning.append("Insufficient data to calculate current ratio")

    return {"score": score, "details": "; ".join(reasoning)}


def analyze_cash_flow(financial_line_items: list) -> dict[str, Any]:
    """Evaluate free cash flow and dividend behavior.
    Jhunjhunwala appreciated companies generating strong free cash flow and rewarding shareholders.
    """
    if not financial_line_items:
        return {"score": 0, "details": "No cash flow data"}

    latest = financial_line_items[0]
    score = 0
    reasoning = []

    if getattr(latest, "free_cash_flow", None) and latest.free_cash_flow:
        if latest.free_cash_flow > 0:
            score += 2
            reasoning.append(f"Positive free cash flow: {latest.free_cash_flow}")
        else:
            reasoning.append(f"Negative free cash flow: {latest.free_cash_flow}")
    else:
        reasoning.append("Free cash flow data not available")

    if getattr(latest, "dividends_and_other_cash_distributions", None) and latest.dividends_and_other_cash_distributions:
        if latest.dividends_and_other_cash_distributions < 0:
            score += 1
            reasoning.append("Company pays dividends to shareholders")
        else:
            reasoning.append("No significant dividend payments")
    else:
        reasoning.append("No dividend payment data available")

    return {"score": score, "details": "; ".join(reasoning)}


def analyze_management_actions(financial_line_items: list) -> dict[str, Any]:
    """Look at share issuance or buybacks to assess shareholder friendliness.
    Jhunjhunwala liked managements who buy back shares or avoid dilution.
    """
    if not financial_line_items:
        return {"score": 0, "details": "No management action data"}

    latest = financial_line_items[0]
    score = 0
    reasoning = []

    issuance = getattr(latest, "issuance_or_purchase_of_equity_shares", None)
    if issuance is not None:
        if issuance < 0:
            score += 2
            reasoning.append(f"Company buying back shares: {abs(issuance)}")
        elif issuance > 0:
            reasoning.append(f"Share issuance detected (potential dilution): {issuance}")
        else:
            score += 1
            reasoning.append("No recent share issuance or buyback")
    else:
        reasoning.append("No data on share issuance or buybacks")

    return {"score": score, "details": "; ".join(reasoning)}


def assess_quality_metrics(financial_line_items: list) -> float:
    """Assess company quality based on Jhunjhunwala's criteria.
    Returns a score between 0 and 1.
    """
    if not financial_line_items:
        return 0.5

    latest = financial_line_items[0]
    quality_factors = []

    if (getattr(latest, 'net_income', None) and getattr(latest, 'total_assets', None) and
        getattr(latest, 'total_liabilities', None) and latest.total_assets and latest.total_liabilities):

        shareholders_equity = latest.total_assets - latest.total_liabilities
        if shareholders_equity > 0 and latest.net_income:
            roe = latest.net_income / shareholders_equity
            if roe > 0.20:
                quality_factors.append(1.0)
            elif roe > 0.15:
                quality_factors.append(0.8)
            elif roe > 0.10:
                quality_factors.append(0.6)
            else:
                quality_factors.append(0.3)
        else:
            quality_factors.append(0.0)
    else:
        quality_factors.append(0.5)

    if (getattr(latest, 'total_assets', None) and getattr(latest, 'total_liabilities', None) and
        latest.total_assets and latest.total_liabilities):
        debt_ratio = latest.total_liabilities / latest.total_assets
        if debt_ratio < 0.3:
            quality_factors.append(1.0)
        elif debt_ratio < 0.5:
            quality_factors.append(0.7)
        elif debt_ratio < 0.7:
            quality_factors.append(0.4)
        else:
            quality_factors.append(0.1)
    else:
        quality_factors.append(0.5)

    net_incomes = [getattr(item, "net_income", None) for item in financial_line_items[:4]
                   if getattr(item, "net_income", None) is not None and getattr(item, "net_income", None) > 0]

    if len(net_incomes) >= 3:
        declining_years = sum(1 for i in range(1, len(net_incomes)) if net_incomes[i-1] > net_incomes[i])
        consistency = 1 - (declining_years / (len(net_incomes) - 1))
        quality_factors.append(consistency)
    else:
        quality_factors.append(0.5)

    return sum(quality_factors) / len(quality_factors) if quality_factors else 0.5


def calculate_intrinsic_value(financial_line_items: list, market_cap: float) -> float | None:
    """Calculate intrinsic value using Rakesh Jhunjhunwala's approach:
    - Focus on earnings power and growth
    - Conservative discount rates
    - Quality premium for consistent performers
    """
    if not financial_line_items or not market_cap:
        return None

    try:
        latest = financial_line_items[0]

        if not getattr(latest, 'net_income', None) or latest.net_income <= 0:
            return None

        net_incomes = [getattr(item, "net_income", None) for item in financial_line_items[:5]
                       if getattr(item, "net_income", None) is not None and getattr(item, "net_income", None) > 0]

        if len(net_incomes) < 2:
            return latest.net_income * 12

        initial_income = net_incomes[-1]
        final_income = net_incomes[0]
        years = len(net_incomes) - 1

        if initial_income > 0:
            historical_growth = ((final_income / initial_income) ** (1/years) - 1)
        else:
            historical_growth = 0.05

        if historical_growth > 0.25:
            sustainable_growth = 0.20
        elif historical_growth > 0.15:
            sustainable_growth = historical_growth * 0.8
        elif historical_growth > 0.05:
            sustainable_growth = historical_growth * 0.9
        else:
            sustainable_growth = 0.05

        quality_score = assess_quality_metrics(financial_line_items)

        if quality_score >= 0.8:
            discount_rate = 0.12
            terminal_multiple = 18
        elif quality_score >= 0.6:
            discount_rate = 0.15
            terminal_multiple = 15
        else:
            discount_rate = 0.18
            terminal_multiple = 12

        current_earnings = latest.net_income
        dcf_value = 0.0

        for year in range(1, 6):
            projected_earnings = current_earnings * ((1 + sustainable_growth) ** year)
            present_value = projected_earnings / ((1 + discount_rate) ** year)
            dcf_value += present_value

        year_5_earnings = current_earnings * ((1 + sustainable_growth) ** 5)
        terminal_value = (year_5_earnings * terminal_multiple) / ((1 + discount_rate) ** 5)

        total_intrinsic_value = dcf_value + terminal_value

        return total_intrinsic_value

    except Exception:
        if getattr(latest, 'net_income', None) and latest.net_income > 0:
            return latest.net_income * 15
        return None


# ─── Public entrypoint ────────────────────────────────────────────────────────

# Sub-score names match upstream's analyzer function names. Fixed insertion
# order → deterministic JSON output (investigation §5.3).
_SUB_SCORE_ORDER = ("profitability", "growth", "balance_sheet", "cash_flow", "management_actions")


def _required_fields_for_insufficient_data(available: int) -> list[str]:
    """Produce jsonpath-like citations for the missing periods below the minimum.

    Growth CAGR needs revenue and net_income across `MIN_PERIODS_REQUIRED` periods
    (upstream L258, L286). Cite the earliest missing indices for both fields.
    """
    missing: list[str] = []
    for idx in range(available, MIN_PERIODS_REQUIRED):
        missing.append(f"history.line_items[{idx}].revenue")
        missing.append(f"history.line_items[{idx}].net_income")
    return missing


def run(metrics: dict) -> dict:
    """Produce the Jhunjhunwala persona output payload.

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
            "persona":               "jhunjhunwala",
            "signal":                "insufficient_data",
            "confidence":            0.0,
            "missing_fields":        _required_fields_for_insufficient_data(available),
            "min_periods_required":  MIN_PERIODS_REQUIRED,
            "min_periods_available": available,
        }

    # Upstream consumed market_cap in native currency units; our fixtures carry
    # market cap in ₹ Cr under fund.mcap_cr. The intrinsic-value output will be
    # in the same native unit as net_income (₹ Cr), keeping the ratio scale-free.
    fund = metrics.get("fund") or {}
    market_cap = fund.get("mcap_cr")

    profitability = analyze_profitability(financial_line_items)
    growth = analyze_growth(financial_line_items)
    balance_sheet = analyze_balance_sheet(financial_line_items)
    cash_flow = analyze_cash_flow(financial_line_items)
    management = analyze_management_actions(financial_line_items)

    total_score = (
        profitability["score"]
        + growth["score"]
        + balance_sheet["score"]
        + cash_flow["score"]
        + management["score"]
    )

    intrinsic_value = calculate_intrinsic_value(financial_line_items, market_cap)
    margin_of_safety: float | None = None
    if intrinsic_value is not None and market_cap:
        margin_of_safety = (intrinsic_value - market_cap) / market_cap

    # Signal rules (upstream L95-L107).
    if margin_of_safety is not None and margin_of_safety >= 0.30:
        signal = "bullish"
    elif margin_of_safety is not None and margin_of_safety <= -0.30:
        signal = "bearish"
    else:
        quality_score = assess_quality_metrics(financial_line_items)
        if quality_score >= 0.7 and total_score >= _UPSTREAM_MAX_SCORE * 0.6:
            signal = "bullish"
        elif quality_score <= 0.4 or total_score <= _UPSTREAM_MAX_SCORE * 0.3:
            signal = "bearish"
        else:
            signal = "neutral"

    # Confidence (upstream L110-L113). Upstream emits 0-100; we normalize to 0.0-1.0.
    if margin_of_safety is not None:
        confidence_raw = min(max(abs(margin_of_safety) * 150, 20), 95)
    else:
        confidence_raw = min(max((total_score / _UPSTREAM_MAX_SCORE) * 100, 10), 80)
    confidence = round(confidence_raw / 100.0, 2)

    # Scale upstream's 0..24 raw total to the 0..100 contract (investigation §5.2).
    weighted_score = round(total_score / _UPSTREAM_MAX_SCORE * 100)

    # Fixed-order sub_scores and details for deterministic JSON output.
    sub_scores: dict[str, int] = {}
    details: dict[str, str] = {}
    by_name = {
        "profitability":       profitability,
        "growth":              growth,
        "balance_sheet":       balance_sheet,
        "cash_flow":           cash_flow,
        "management_actions":  management,
    }
    for name in _SUB_SCORE_ORDER:
        sub_scores[name] = by_name[name]["score"]
        details[name] = by_name[name]["details"]

    return {
        "ticker":         ticker,
        "persona":        "jhunjhunwala",
        "sub_scores":     sub_scores,
        "weighted_score": weighted_score,
        "max_score":      100,
        "signal":         signal,
        "confidence":     confidence,
        "details":        details,
    }
