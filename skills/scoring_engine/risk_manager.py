# Ported from virattt/ai-hedge-fund src/agents/risk_manager.py
# at commit 0f6ac487986f7eb80749ed42bd26fb8330c450db (THIRD_PARTY.md §2.1)
# Stripped: langchain HumanMessage return, src.graph.state plumbing, src.tools.api
# (get_prices / prices_to_df), src.utils.progress tracker, per-ticker
# remaining-position-limit / available-cash accounting, calculate_correlation_multiplier
# (not used by SPEC §9.5; the §9.5 output only needs HHI + vol-adjusted limit +
# top-5 correlation pairs).
# Adapted: base_limit parameterized from philosophy position_sizing.max_per_stock_pct
# (upstream hardcoded 0.20); pandas → numpy for vol + corrcoef so the skill's only
# heavy dep is numpy; correlation output reshaped from per-ticker top-3 neighbors
# to portfolio-wide top-5 pairs by |ρ| per investigation §6 / SPEC §9.5 prose.
"""Concentration sanity math — HHI, vol-adjusted position limit, top-5 correlation pairs.

See SPEC §9.5 and research/milestones/M3-investigation.md §6. No LLM, no network,
no wall-clock — byte-equal stdout on byte-equal input.
"""

from __future__ import annotations

from typing import Any

import numpy as np

# Upstream's default lookback window for the vol calculation (L220).
_DEFAULT_LOOKBACK_DAYS = 60

# Upstream's annualization factor (L246).
_TRADING_DAYS_PER_YEAR = 252


# ─── Upstream analyzers (math kept verbatim; pandas → numpy) ─────────────────

def calculate_volatility_metrics(
    closes: list[float], lookback_days: int = _DEFAULT_LOOKBACK_DAYS,
) -> dict[str, Any]:
    """Daily + annualized volatility for a ticker's close series.

    Port of upstream L220-L270. Input is an ascending-ordered list of close
    prices (pandas DataFrame in upstream); output is the same shape.
    """
    n = len(closes)
    if n < 2:
        return {
            "daily_volatility":      0.05,
            "annualized_volatility": 0.05 * np.sqrt(_TRADING_DAYS_PER_YEAR),
            "data_points":           n,
        }

    arr = np.asarray(closes, dtype=float)
    # Upstream: prices_df["close"].pct_change().dropna()
    daily_returns = arr[1:] / arr[:-1] - 1.0

    if len(daily_returns) < 2:
        return {
            "daily_volatility":      0.05,
            "annualized_volatility": 0.05 * np.sqrt(_TRADING_DAYS_PER_YEAR),
            "data_points":           len(daily_returns),
        }

    # Upstream: daily_returns.tail(min(lookback_days, len(daily_returns)))
    window = min(lookback_days, len(daily_returns))
    recent = daily_returns[-window:]

    # Upstream uses pandas .std() which is sample stdev (ddof=1). Match it.
    daily_vol = float(np.std(recent, ddof=1))
    annualized_vol = daily_vol * np.sqrt(_TRADING_DAYS_PER_YEAR)

    return {
        "daily_volatility":      daily_vol,
        "annualized_volatility": annualized_vol,
        "data_points":           int(len(recent)),
    }


def calculate_volatility_adjusted_limit(
    annualized_volatility: float, base_limit: float,
) -> float:
    """Map annualized vol to a position-size percentage of the portfolio.

    Port of upstream L272-L302. `base_limit` is the fraction (e.g. 0.08 for
    max_per_stock_pct=8); upstream hardcoded 0.20. Multiplier ladder kept
    verbatim.
    """
    if annualized_volatility < 0.15:
        vol_multiplier = 1.25
    elif annualized_volatility < 0.30:
        vol_multiplier = 1.0 - (annualized_volatility - 0.15) * 0.5
    elif annualized_volatility < 0.50:
        vol_multiplier = 0.75 - (annualized_volatility - 0.30) * 0.5
    else:
        vol_multiplier = 0.50

    vol_multiplier = max(0.25, min(1.25, vol_multiplier))
    return base_limit * vol_multiplier


# ─── Pairwise correlation (numpy port of pandas DataFrame.corr) ──────────────

def _pairwise_correlation(
    returns_by_ticker: dict[str, np.ndarray],
    dates_by_ticker: dict[str, list[str]],
) -> list[dict[str, Any]]:
    """Pearson correlation on the intersection of each pair's available dates.

    Upstream builds one aligned DataFrame and calls .corr(). We do the same
    thing per pair — the pairwise-intersection semantics are equivalent when
    every series has the same date axis, and more forgiving (no row dropped
    because a third ticker is missing) when axes differ.
    """
    tickers = sorted(returns_by_ticker.keys())
    pairs: list[dict[str, Any]] = []
    for i, a in enumerate(tickers):
        for b in tickers[i + 1:]:
            dates_a = dates_by_ticker[a]
            dates_b = dates_by_ticker[b]
            # Each returns array corresponds to dates[1:] (one shorter than closes).
            ret_dates_a = dates_a[1:]
            ret_dates_b = dates_b[1:]
            common = sorted(set(ret_dates_a) & set(ret_dates_b))
            if len(common) < 5:
                continue
            idx_a = {d: k for k, d in enumerate(ret_dates_a)}
            idx_b = {d: k for k, d in enumerate(ret_dates_b)}
            ra = np.array([returns_by_ticker[a][idx_a[d]] for d in common])
            rb = np.array([returns_by_ticker[b][idx_b[d]] for d in common])
            if np.std(ra) == 0 or np.std(rb) == 0:
                continue
            rho = float(np.corrcoef(ra, rb)[0, 1])
            if np.isnan(rho):
                continue
            pairs.append({"tickers": [a, b], "correlation": rho})
    return pairs


# ─── Public entrypoint ───────────────────────────────────────────────────────

def _round(x: float | int | None, n: int) -> float | None:
    if x is None:
        return None
    return round(float(x), n)


def run(
    holdings: dict[str, Any],
    prices: dict[str, Any],
    philosophy: dict[str, Any],
) -> dict[str, Any]:
    """Concentration sanity payload per SPEC §9.5.

    Input shapes:
      holdings   — {as_of, holdings: [{ticker, market_value, allocation_pct, sector}, ...]}
      prices     — {as_of, lookback_days, tickers: {T: {dates: [...], closes: [...]}}}
      philosophy — parsed YAML front-matter (reads position_sizing.max_per_stock_pct)

    Missing-price-data path (investigation §2.6): emit a warning and null fields
    for the affected holding; exclude it from correlation. Exit 0.
    """
    pos_sizing = philosophy.get("position_sizing") or {}
    max_per_stock_pct = pos_sizing.get("max_per_stock_pct")
    if not isinstance(max_per_stock_pct, (int, float)):
        raise ValueError(
            "philosophy.position_sizing.max_per_stock_pct missing or non-numeric",
        )
    base_limit = float(max_per_stock_pct) / 100.0  # 8 → 0.08

    ticker_prices = prices.get("tickers") or {}

    # HHI uses the declared allocation_pct directly (investigation §2.3).
    hhi = 0.0
    for h in holdings.get("holdings", []):
        w = float(h.get("allocation_pct", 0)) / 100.0
        hhi += w * w

    # Per-ticker vol + limit.
    returns_by_ticker: dict[str, np.ndarray] = {}
    dates_by_ticker: dict[str, list[str]] = {}
    per_holding: list[dict[str, Any]] = []
    warnings: list[str] = []

    for h in holdings.get("holdings", []):
        ticker = h["ticker"]
        alloc = float(h.get("allocation_pct", 0))
        entry = ticker_prices.get(ticker)

        if not entry or not entry.get("closes") or len(entry["closes"]) < 2:
            warnings.append(f"no price data for {ticker}")
            per_holding.append({
                "ticker":                ticker,
                "allocation_pct":        _round(alloc, 2),
                "annualized_volatility": None,
                "vol_adjusted_limit_pct": None,
                "delta_pct":             None,
            })
            continue

        closes = entry["closes"]
        dates = entry.get("dates") or []
        vol_metrics = calculate_volatility_metrics(closes)
        ann_vol = vol_metrics["annualized_volatility"]
        limit_frac = calculate_volatility_adjusted_limit(ann_vol, base_limit)
        limit_pct = limit_frac * 100.0

        per_holding.append({
            "ticker":                 ticker,
            "allocation_pct":         _round(alloc, 2),
            "annualized_volatility":  _round(ann_vol, 3),
            "vol_adjusted_limit_pct": _round(limit_pct, 2),
            "delta_pct":              _round(alloc - limit_pct, 2),
        })

        # Store the full daily-returns series for correlation (not just the 60d window).
        arr = np.asarray(closes, dtype=float)
        returns_by_ticker[ticker] = arr[1:] / arr[:-1] - 1.0
        dates_by_ticker[ticker] = dates

    # Top-5 correlation pairs by |ρ|, break ties lexicographically for determinism.
    pairs = _pairwise_correlation(returns_by_ticker, dates_by_ticker)
    pairs.sort(key=lambda p: (-abs(p["correlation"]), p["tickers"]))
    top_pairs = [
        {"tickers": p["tickers"], "correlation": _round(p["correlation"], 3)}
        for p in pairs[:5]
    ]

    return {
        "as_of":                 holdings.get("as_of"),
        "lookback_days":         _DEFAULT_LOOKBACK_DAYS,
        "base_limit_pct":        _round(max_per_stock_pct, 2),
        "hhi":                   _round(hhi, 4),
        "holdings":              per_holding,
        "top_correlation_pairs": top_pairs,
        "warnings":              warnings,
    }
