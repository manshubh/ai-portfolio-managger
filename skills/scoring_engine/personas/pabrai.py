# Ported from virattt/ai-hedge-fund src/agents/mohnish_pabrai.py
# at commit 0f6ac487986f7eb80749ed42bd26fb8330c450db (THIRD_PARTY.md §2.1)
# Stripped: langchain LLM call (generate_pabrai_output), Pydantic signal model
# (MohnishPabraiSignal), src.graph.state plumbing (mohnish_pabrai_agent entry),
# src.tools.api fetchers (get_financial_metrics / search_line_items /
# get_market_cap), src.utils.progress tracker.
# Adapted: data input now flows from skills.scoring_engine.lib.line_items.
# Pabrai's analyzers all read only line_items attributes already present in the
# M3.4 schema (revenue, gross_margin, operating_income, net_income,
# free_cash_flow, total_debt, cash_and_equivalents, current_assets,
# current_liabilities, shareholders_equity, capital_expenditure,
# depreciation_and_amortization, outstanding_shares) — no per-persona
# enrichment is needed (unlike buffett.py).
"""Mohnish Pabrai persona — deterministic sub-scores + signal + confidence."""

from __future__ import annotations

from typing import Any

from skills.scoring_engine.lib import line_items as _li

# Minimum line-item periods required to emit a graded score.
# analyze_pabrai_valuation (upstream L205) early-exits when fewer than 3
# periods of free_cash_flow are available; analyze_downside_protection's
# FCF-stability block (upstream L181) and analyze_double_potential's
# revenue/FCF trend blocks (upstream L265, L277) also guard on `len >= 3`.
# Three periods is therefore the strictest bar that actually prevents a
# graded valuation score.
MIN_PERIODS_REQUIRED = 3

# Upstream combines the three 0..10 analyzer scores via a weighted sum
# (upstream L78-L82): downside*0.45 + valuation*0.35 + double*0.20. The
# resulting weighted total is itself on a 0..10 scale, which we then
# rescale to the 0..100 contract (investigation §5.2).
_UPSTREAM_MAX_SCORE = 10


# ─── Upstream analyzers (kept verbatim, attribute-access preserved) ──────────

def analyze_downside_protection(financial_line_items: list) -> dict[str, Any]:
    """Assess balance-sheet strength and downside resiliency (capital preservation first)."""
    if not financial_line_items:
        return {"score": 0, "details": "Insufficient data"}

    latest = financial_line_items[0]
    details: list[str] = []
    score = 0

    cash = getattr(latest, "cash_and_equivalents", None)
    debt = getattr(latest, "total_debt", None)
    current_assets = getattr(latest, "current_assets", None)
    current_liabilities = getattr(latest, "current_liabilities", None)
    equity = getattr(latest, "shareholders_equity", None)

    # Net cash position is a strong downside protector
    net_cash = None
    if cash is not None and debt is not None:
        net_cash = cash - debt
        if net_cash > 0:
            score += 3
            details.append(f"Net cash position: ${net_cash:,.0f}")
        else:
            details.append(f"Net debt position: ${net_cash:,.0f}")

    # Current ratio
    if current_assets is not None and current_liabilities is not None and current_liabilities > 0:
        current_ratio = current_assets / current_liabilities
        if current_ratio >= 2.0:
            score += 2
            details.append(f"Strong liquidity (current ratio {current_ratio:.2f})")
        elif current_ratio >= 1.2:
            score += 1
            details.append(f"Adequate liquidity (current ratio {current_ratio:.2f})")
        else:
            details.append(f"Weak liquidity (current ratio {current_ratio:.2f})")

    # Low leverage
    if equity is not None and equity > 0 and debt is not None:
        de_ratio = debt / equity
        if de_ratio < 0.3:
            score += 2
            details.append(f"Very low leverage (D/E {de_ratio:.2f})")
        elif de_ratio < 0.7:
            score += 1
            details.append(f"Moderate leverage (D/E {de_ratio:.2f})")
        else:
            details.append(f"High leverage (D/E {de_ratio:.2f})")

    # Free cash flow positive and stable
    fcf_values = [getattr(li, "free_cash_flow", None) for li in financial_line_items if getattr(li, "free_cash_flow", None) is not None]
    if fcf_values and len(fcf_values) >= 3:
        recent_avg = sum(fcf_values[:3]) / 3
        older = sum(fcf_values[-3:]) / 3 if len(fcf_values) >= 6 else fcf_values[-1]
        if recent_avg > 0 and recent_avg >= older:
            score += 2
            details.append("Positive and improving/stable FCF")
        elif recent_avg > 0:
            score += 1
            details.append("Positive but declining FCF")
        else:
            details.append("Negative FCF")

    return {"score": min(10, score), "details": "; ".join(details)}


def analyze_pabrai_valuation(financial_line_items: list, market_cap: float | None) -> dict[str, Any]:
    """Value via simple FCF yield and asset-light preference (keep it simple, low mistakes)."""
    if not financial_line_items or market_cap is None or market_cap <= 0:
        return {"score": 0, "details": "Insufficient data", "fcf_yield": None, "normalized_fcf": None}

    details: list[str] = []
    fcf_values = [getattr(li, "free_cash_flow", None) for li in financial_line_items if getattr(li, "free_cash_flow", None) is not None]
    capex_vals = [abs(getattr(li, "capital_expenditure", 0) or 0) for li in financial_line_items]  # noqa: F841  (upstream dead variable, kept verbatim)

    if not fcf_values or len(fcf_values) < 3:
        return {"score": 0, "details": "Insufficient FCF history", "fcf_yield": None, "normalized_fcf": None}

    normalized_fcf = sum(fcf_values[:min(5, len(fcf_values))]) / min(5, len(fcf_values))
    if normalized_fcf <= 0:
        return {"score": 0, "details": "Non-positive normalized FCF", "fcf_yield": None, "normalized_fcf": normalized_fcf}

    fcf_yield = normalized_fcf / market_cap

    score = 0
    if fcf_yield > 0.10:
        score += 4
        details.append(f"Exceptional value: {fcf_yield:.1%} FCF yield")
    elif fcf_yield > 0.07:
        score += 3
        details.append(f"Attractive value: {fcf_yield:.1%} FCF yield")
    elif fcf_yield > 0.05:
        score += 2
        details.append(f"Reasonable value: {fcf_yield:.1%} FCF yield")
    elif fcf_yield > 0.03:
        score += 1
        details.append(f"Borderline value: {fcf_yield:.1%} FCF yield")
    else:
        details.append(f"Expensive: {fcf_yield:.1%} FCF yield")

    # Asset-light tilt: lower capex intensity preferred
    if capex_vals and len(financial_line_items) >= 3:
        revenue_vals = [getattr(li, "revenue", None) for li in financial_line_items]  # noqa: F841  (upstream dead variable, kept verbatim)
        capex_to_revenue = []
        for i, li in enumerate(financial_line_items):
            revenue = getattr(li, "revenue", None)
            capex = abs(getattr(li, "capital_expenditure", 0) or 0)
            if revenue and revenue > 0:
                capex_to_revenue.append(capex / revenue)
        if capex_to_revenue:
            avg_ratio = sum(capex_to_revenue) / len(capex_to_revenue)
            if avg_ratio < 0.05:
                score += 2
                details.append(f"Asset-light: Avg capex {avg_ratio:.1%} of revenue")
            elif avg_ratio < 0.10:
                score += 1
                details.append(f"Moderate capex: Avg capex {avg_ratio:.1%} of revenue")
            else:
                details.append(f"Capex heavy: Avg capex {avg_ratio:.1%} of revenue")

    return {"score": min(10, score), "details": "; ".join(details), "fcf_yield": fcf_yield, "normalized_fcf": normalized_fcf}


def analyze_double_potential(financial_line_items: list, market_cap: float | None) -> dict[str, Any]:
    """Estimate low-risk path to double capital in ~2-3 years: runway from FCF growth + rerating."""
    if not financial_line_items or market_cap is None or market_cap <= 0:
        return {"score": 0, "details": "Insufficient data"}

    details: list[str] = []

    # Use revenue and FCF trends as rough growth proxy (keep it simple)
    revenues = [getattr(li, "revenue", None) for li in financial_line_items if getattr(li, "revenue", None) is not None]
    fcfs = [getattr(li, "free_cash_flow", None) for li in financial_line_items if getattr(li, "free_cash_flow", None) is not None]

    score = 0
    if revenues and len(revenues) >= 3:
        recent_rev = sum(revenues[:3]) / 3
        older_rev = sum(revenues[-3:]) / 3 if len(revenues) >= 6 else revenues[-1]
        if older_rev > 0:
            rev_growth = (recent_rev / older_rev) - 1
            if rev_growth > 0.15:
                score += 2
                details.append(f"Strong revenue trajectory ({rev_growth:.1%})")
            elif rev_growth > 0.05:
                score += 1
                details.append(f"Modest revenue growth ({rev_growth:.1%})")

    if fcfs and len(fcfs) >= 3:
        recent_fcf = sum(fcfs[:3]) / 3
        older_fcf = sum(fcfs[-3:]) / 3 if len(fcfs) >= 6 else fcfs[-1]
        if older_fcf != 0:
            fcf_growth = (recent_fcf / older_fcf) - 1
            if fcf_growth > 0.20:
                score += 3
                details.append(f"Strong FCF growth ({fcf_growth:.1%})")
            elif fcf_growth > 0.08:
                score += 2
                details.append(f"Healthy FCF growth ({fcf_growth:.1%})")
            elif fcf_growth > 0:
                score += 1
                details.append(f"Positive FCF growth ({fcf_growth:.1%})")

    # If FCF yield is already high (>8%), doubling can come from cash generation alone in few years
    tmp_val = analyze_pabrai_valuation(financial_line_items, market_cap)
    fcf_yield = tmp_val.get("fcf_yield")
    if fcf_yield is not None:
        if fcf_yield > 0.08:
            score += 3
            details.append("High FCF yield can drive doubling via retained cash/Buybacks")
        elif fcf_yield > 0.05:
            score += 1
            details.append("Reasonable FCF yield supports moderate compounding")

    return {"score": min(10, score), "details": "; ".join(details)}


# ─── Public entrypoint ────────────────────────────────────────────────────────

# Sub-score names match upstream's analyzer function names. Fixed insertion
# order → deterministic JSON output (investigation §5.3).
_SUB_SCORE_ORDER = ("downside_protection", "valuation", "double_potential")


def _required_fields_for_insufficient_data(available: int) -> list[str]:
    """Produce jsonpath-like citations for the missing periods below the minimum.

    Pabrai's valuation (upstream L205) needs ≥3 periods of free_cash_flow to
    normalize owner earnings. Cite the earliest missing indices for that field.
    """
    missing: list[str] = []
    for idx in range(available, MIN_PERIODS_REQUIRED):
        missing.append(f"history.line_items[{idx}].free_cash_flow")
    return missing


def _round(x: float | int, n: int = 2) -> float:
    """Round for deterministic JSON output; mirrors munger.py's `_round`."""
    return round(float(x), n)


def run(metrics: dict) -> dict:
    """Produce the Mohnish Pabrai persona output payload.

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
            "persona":               "pabrai",
            "signal":                "insufficient_data",
            "confidence":            0.0,
            "missing_fields":        _required_fields_for_insufficient_data(available),
            "min_periods_required":  MIN_PERIODS_REQUIRED,
            "min_periods_available": available,
        }

    # Upstream called get_market_cap() in native currency; our fixtures carry
    # market cap in ₹ Cr under fund.mcap_cr. Pabrai's valuation compares
    # normalized_fcf (₹ Cr) to market_cap (₹ Cr), so the FCF yield is
    # scale-free — no currency conversion needed.
    fund = metrics.get("fund") or {}
    market_cap = fund.get("mcap_cr")

    downside = analyze_downside_protection(financial_line_items)
    valuation = analyze_pabrai_valuation(financial_line_items, market_cap)
    double_potential = analyze_double_potential(financial_line_items, market_cap)

    # Upstream L78-L82: Pabrai's combination weights heavily favor capital
    # preservation (downside 0.45) over valuation (0.35) and upside (0.20).
    total_score = (
        downside["score"] * 0.45
        + valuation["score"] * 0.35
        + double_potential["score"] * 0.20
    )

    # Signal rules (upstream L85-L90). Pabrai's bars are asymmetric: bullish
    # requires ≥7.5 (conviction for a "heads I win" setup), bearish ≤4.0
    # (the "tails I lose much" rejection bar).
    if total_score >= 7.5:
        signal = "bullish"
    elif total_score <= 4.0:
        signal = "bearish"
    else:
        signal = "neutral"

    # Confidence — upstream's LLM prompt returns 0-100 (L339); we derive a
    # deterministic proxy by rescaling the already-computed weighted total.
    # Clamped to [10, 95] to match the bucket semantics used by sibling
    # personas (jhunjhunwala / buffett) when no margin-of-safety signal is
    # available (both personas use the same [10/20, 80/95] clamp when
    # falling back to score_ratio). Pabrai has no intrinsic-value output,
    # so the score-ratio path is the only available signal.
    confidence_raw = min(max((total_score / _UPSTREAM_MAX_SCORE) * 100, 10), 95)
    confidence = round(confidence_raw / 100.0, 2)

    # Scale upstream's 0..10 weighted total to the 0..100 contract (investigation §5.2).
    weighted_score = round(total_score * 10)

    # Fixed-order sub_scores and details for deterministic JSON output.
    by_name = {
        "downside_protection": downside,
        "valuation":           valuation,
        "double_potential":    double_potential,
    }
    sub_scores: dict[str, float] = {}
    details: dict[str, str] = {}
    for name in _SUB_SCORE_ORDER:
        sub_scores[name] = _round(by_name[name]["score"])
        details[name] = by_name[name]["details"]

    return {
        "ticker":         ticker,
        "persona":        "pabrai",
        "sub_scores":     sub_scores,
        "weighted_score": weighted_score,
        "max_score":      100,
        "signal":         signal,
        "confidence":     confidence,
        "details":        details,
    }
