"""M3.10 — concentration-check (risk_manager port) regression + determinism.

Acceptance criteria from bd ai-portfolio-manager-vfq.10 (see also
plans/M3/M3.10-concentration-check.md §7):

1. HHI within 0.001 of expected (computed independently from allocation_pct).
2. Per-stock vol-adjusted limit within 0.5pp of expected.
3. top_correlation_pairs ranked by |ρ| desc, exactly 5 entries, deterministic
   tie-breakers.
4. Two consecutive subprocess runs emit byte-equal stdout (determinism).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO / "tests" / "scoring-engine"
HOLDINGS = FIXTURE_DIR / "holdings.json"
PRICES = FIXTURE_DIR / "prices.json"
PHILOSOPHY = REPO / "input" / "india" / "philosophy.md"


def _run_cli() -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "skills.scoring_engine.engine",
         "concentration-check",
         "--holdings",      str(HOLDINGS),
         "--price-history", str(PRICES),
         "--philosophy",    str(PHILOSOPHY)],
        capture_output=True, text=True, cwd=str(REPO), check=False,
    )
    assert result.returncode == 0, (
        f"exit={result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return json.loads(result.stdout)


def _run_cli_raw() -> bytes:
    return subprocess.run(
        [sys.executable, "-m", "skills.scoring_engine.engine",
         "concentration-check",
         "--holdings",      str(HOLDINGS),
         "--price-history", str(PRICES),
         "--philosophy",    str(PHILOSOPHY)],
        capture_output=True, cwd=str(REPO), check=True,
    ).stdout


def _load_holdings() -> dict:
    return json.loads(HOLDINGS.read_text())


def _expected_hhi(holdings: dict) -> float:
    return sum((h["allocation_pct"] / 100.0) ** 2 for h in holdings["holdings"])


def test_hhi_within_001():
    result = _run_cli()
    holdings = _load_holdings()
    expected = _expected_hhi(holdings)
    assert abs(result["hhi"] - expected) < 0.001, (
        f"expected HHI ≈ {expected:.4f}, got {result['hhi']:.4f}"
    )


def test_output_shape_and_completeness():
    result = _run_cli()
    holdings = _load_holdings()
    assert result["as_of"] == holdings["as_of"]
    assert result["lookback_days"] == 60
    assert result["base_limit_pct"] == 8.0   # from philosophy YAML
    assert len(result["holdings"]) == len(holdings["holdings"])
    assert result["warnings"] == []
    # Per-holding row keys
    for row in result["holdings"]:
        for key in ("ticker", "allocation_pct", "annualized_volatility",
                    "vol_adjusted_limit_pct", "delta_pct"):
            assert key in row, f"row missing key: {key}"


def test_vol_limits_plausible_and_in_upstream_ladder_bounds():
    """Every ticker's vol_adjusted_limit sits in [25%, 125%] × base_limit.

    Upstream's multiplier ladder clamps to [0.25, 1.25], so limit ∈ [2.0, 10.0]
    pp for base 8pp. Also each limit should fall within 0.5pp of what you get
    from re-applying the ladder to the emitted annualized_volatility.
    """
    result = _run_cli()

    def expected_limit(ann_vol: float, base: float = 0.08) -> float:
        if ann_vol < 0.15:
            m = 1.25
        elif ann_vol < 0.30:
            m = 1.0 - (ann_vol - 0.15) * 0.5
        elif ann_vol < 0.50:
            m = 0.75 - (ann_vol - 0.30) * 0.5
        else:
            m = 0.50
        m = max(0.25, min(1.25, m))
        return base * m * 100.0

    for row in result["holdings"]:
        vol = row["annualized_volatility"]
        limit = row["vol_adjusted_limit_pct"]
        assert vol is not None and limit is not None
        assert 2.0 <= limit <= 10.0, f"{row['ticker']} limit {limit} outside bounds"
        exp = expected_limit(vol)
        assert abs(limit - exp) < 0.5, (
            f"{row['ticker']}: limit {limit:.2f}pp outside 0.5pp of expected {exp:.2f}pp"
        )


def test_top_correlation_pairs_shape_and_ordering():
    result = _run_cli()
    pairs = result["top_correlation_pairs"]
    assert len(pairs) == 5, f"expected 5 top pairs, got {len(pairs)}"
    # Each pair has exactly two tickers, sorted within the pair deterministically.
    for p in pairs:
        assert isinstance(p["tickers"], list) and len(p["tickers"]) == 2
        # Pairs are sorted alphabetically within — check the first char is <= second
        assert p["tickers"][0] <= p["tickers"][1]
    # Ordered by |ρ| descending, tiebreak by tickers lexicographic.
    abs_corr = [abs(p["correlation"]) for p in pairs]
    assert abs_corr == sorted(abs_corr, reverse=True), (
        f"pairs not sorted by |ρ| desc: {abs_corr}"
    )


def test_top_pairs_surface_cluster_design():
    """The fixture generator plants INFY/TCS in a shared IT cluster with 0.70
    shock weight — they should dominate the top pair."""
    result = _run_cli()
    top = result["top_correlation_pairs"][0]
    assert sorted(top["tickers"]) == ["INFY.NS", "TCS.NS"]
    assert top["correlation"] > 0.3   # shared cluster means notably positive


def test_determinism_byte_equal():
    a = _run_cli_raw()
    b = _run_cli_raw()
    assert a == b, "two runs produced different stdout (non-deterministic output)"


def test_missing_ticker_graceful_degradation(tmp_path):
    """Holding not present in prices.json → warning + null vol fields, exit 0."""
    # Copy holdings and add a phantom ticker with no matching prices entry.
    holdings = json.loads(HOLDINGS.read_text())
    holdings["holdings"].append({
        "ticker":         "GHOST.NS",
        "market_value":   5000.0,
        "allocation_pct": 5.0,
        "sector":         "NA",
    })
    out = tmp_path / "holdings_with_phantom.json"
    out.write_text(json.dumps(holdings))

    result = subprocess.run(
        [sys.executable, "-m", "skills.scoring_engine.engine",
         "concentration-check",
         "--holdings",      str(out),
         "--price-history", str(PRICES),
         "--philosophy",    str(PHILOSOPHY)],
        capture_output=True, text=True, cwd=str(REPO), check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    ghost = next(r for r in payload["holdings"] if r["ticker"] == "GHOST.NS")
    assert ghost["annualized_volatility"] is None
    assert ghost["vol_adjusted_limit_pct"] is None
    assert ghost["delta_pct"] is None
    assert "no price data for GHOST.NS" in payload["warnings"]


def test_base_limit_reflects_philosophy_yaml():
    """If the philosophy YAML's position_sizing.max_per_stock_pct changes, so
    should base_limit_pct in the output."""
    # Synthesize a philosophy file with a different max_per_stock_pct.
    phil_text = PHILOSOPHY.read_text()
    front_end = phil_text.find("\n---", 4)
    front = phil_text[4:front_end]
    doc = yaml.safe_load(front)
    doc["position_sizing"]["max_per_stock_pct"] = 10
    new_front = yaml.safe_dump(doc, sort_keys=False)
    new_phil = "---\n" + new_front + "---\n" + phil_text[front_end + 4:]
    tmp_phil = FIXTURE_DIR / "_tmp_philosophy_m3_10.md"
    tmp_phil.write_text(new_phil)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "skills.scoring_engine.engine",
             "concentration-check",
             "--holdings",      str(HOLDINGS),
             "--price-history", str(PRICES),
             "--philosophy",    str(tmp_phil)],
            capture_output=True, text=True, cwd=str(REPO), check=False,
        )
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["base_limit_pct"] == 10.0
    finally:
        tmp_phil.unlink(missing_ok=True)
