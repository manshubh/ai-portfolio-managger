"""Deterministic generator for tests/scoring-engine/{prices,holdings}.json.

Invocation: `python3 tests/scoring-engine/gen_prices_fixture.py`.

Re-running produces byte-identical JSON (seeded np.random.RandomState; stable
key ordering via json.dumps sort_keys=True; monotone back-dated trading-day
calendar from 2026-04-17). The generated fixtures are committed to the repo;
this script is kept around so the fixture can be regenerated / inspected.

See plans/M3/M3.10-concentration-check.md §6 for fixture design rationale.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np

# Deterministic seed — any change alters the fixture bit-for-bit.
SEED = 42
TRADING_DAYS = 252
AS_OF = dt.date(2026, 4, 17)

# 10 tickers with India-flavored names and synthetic params (μ_annual, σ_annual,
# shared_shock_weight_with_cluster, cluster_id). Clusters share a common daily
# shock so correlations aren't uniform.
#
# Cluster layout:
#   IT: INFY.NS, TCS.NS                           (high intra-IT correlation)
#   Financials: HDFCBANK.NS                       (lone financial)
#   Consumer: ITC.NS, HINDUNILVR.NS               (moderate intra-consumer)
#   Industrials: RELIANCE.NS, LT.NS               (moderate)
#   Auto: MARUTI.NS                               (lone)
#   Telecom: BHARTIARTL.NS                        (lone)
#   PSU: COALINDIA.NS                             (lone)
TICKERS = [
    # ticker,          mu,    sigma, shock_w, cluster, alloc_pct, sector
    ("RELIANCE.NS",   0.12, 0.22, 0.55, "industrial", 15.0, "Energy"),
    ("INFY.NS",       0.10, 0.24, 0.70, "it",          9.0, "IT"),
    ("HDFCBANK.NS",   0.11, 0.20, 0.00, "solo",       12.0, "Financials"),
    ("TCS.NS",        0.09, 0.22, 0.70, "it",          8.0, "IT"),
    ("BHARTIARTL.NS", 0.14, 0.28, 0.00, "solo",        7.0, "Telecom"),
    ("ITC.NS",        0.08, 0.18, 0.50, "consumer",   10.0, "Consumer"),
    ("LT.NS",         0.13, 0.26, 0.55, "industrial",  6.0, "Industrials"),
    ("HINDUNILVR.NS", 0.07, 0.16, 0.50, "consumer",   11.0, "Consumer"),
    ("MARUTI.NS",     0.10, 0.25, 0.00, "solo",        8.0, "Auto"),
    ("COALINDIA.NS",  0.09, 0.23, 0.00, "solo",       14.0, "Energy"),
]


def _trading_days(end: dt.date, n: int) -> list[str]:
    """Generate `n` ascending ISO-date trading days ending at `end` (Mon-Fri)."""
    out: list[str] = []
    cur = end
    while len(out) < n:
        if cur.weekday() < 5:  # Mon–Fri (no holiday calendar; synthetic fixture)
            out.append(cur.isoformat())
        cur -= dt.timedelta(days=1)
    out.reverse()
    return out


def _gbm_path(
    rng: np.random.RandomState,
    s0: float,
    mu: float,
    sigma: float,
    n_days: int,
    cluster_shock: np.ndarray | None,
    shock_w: float,
) -> np.ndarray:
    """Generate a geometric-Brownian-motion close-price path.

    Shares `shock_w` of the daily z-score with `cluster_shock` (if given); the
    remaining `sqrt(1 - w²)` is idiosyncratic — preserves unit variance.
    """
    dt_ = 1.0 / TRADING_DAYS
    idio = rng.standard_normal(n_days - 1)
    if cluster_shock is not None and shock_w > 0:
        w = shock_w
        z = w * cluster_shock + np.sqrt(1 - w * w) * idio
    else:
        z = idio
    log_returns = (mu - 0.5 * sigma * sigma) * dt_ + sigma * np.sqrt(dt_) * z
    path = np.empty(n_days)
    path[0] = s0
    path[1:] = s0 * np.exp(np.cumsum(log_returns))
    return path


def main() -> None:
    out_dir = Path(__file__).parent
    rng = np.random.RandomState(SEED)

    dates = _trading_days(AS_OF, TRADING_DAYS)

    # Pre-roll one shared shock series per non-solo cluster. Insertion order of
    # clusters must be deterministic — use the order tickers first appear.
    cluster_shocks: dict[str, np.ndarray] = {}
    for _, _, _, _, cluster, _, _ in TICKERS:
        if cluster != "solo" and cluster not in cluster_shocks:
            cluster_shocks[cluster] = rng.standard_normal(TRADING_DAYS - 1)

    # Per-ticker starting price: deterministic but varied.
    start_prices = {
        "RELIANCE.NS":   2840.0,
        "INFY.NS":       1455.0,
        "HDFCBANK.NS":   1620.0,
        "TCS.NS":        3780.0,
        "BHARTIARTL.NS": 1180.0,
        "ITC.NS":         432.0,
        "LT.NS":         3590.0,
        "HINDUNILVR.NS": 2410.0,
        "MARUTI.NS":    11230.0,
        "COALINDIA.NS":   388.0,
    }

    prices_out: dict[str, dict] = {}
    holdings_out: list[dict] = []
    for ticker, mu, sigma, shock_w, cluster, alloc, sector in TICKERS:
        cs = cluster_shocks.get(cluster) if cluster != "solo" else None
        path = _gbm_path(rng, start_prices[ticker], mu, sigma, TRADING_DAYS, cs, shock_w)
        prices_out[ticker] = {
            "dates":  list(dates),
            "closes": [round(float(x), 4) for x in path],
        }
        holdings_out.append({
            "ticker":         ticker,
            "market_value":   round(alloc * 10000.0, 2),  # synthetic ₹, just scale-free
            "allocation_pct": alloc,
            "sector":         sector,
        })

    prices_doc = {
        "as_of":         AS_OF.isoformat(),
        "lookback_days": TRADING_DAYS,
        "tickers":       prices_out,
    }
    holdings_doc = {
        "as_of":    AS_OF.isoformat(),
        "holdings": holdings_out,
    }

    (out_dir / "prices.json").write_text(
        json.dumps(prices_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    (out_dir / "holdings.json").write_text(
        json.dumps(holdings_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(
        f"wrote {out_dir / 'prices.json'} and {out_dir / 'holdings.json'} "
        f"({len(TICKERS)} tickers × {TRADING_DAYS} days, seed={SEED})",
    )


if __name__ == "__main__":
    main()
