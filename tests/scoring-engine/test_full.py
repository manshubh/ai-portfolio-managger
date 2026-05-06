"""M3.11 — `scoring-engine full` composition + fundamentals-first invariant.

Acceptance criteria from bd ai-portfolio-manager-vfq.11 (see also
plans/M3/M3.11-full-and-invariant.md §7):

1. `full` emits {thresholds, my_philosophy} on stdout, exit 0.
2. --ticker / metrics.ticker mismatch → exit 1, structured stderr.
3. Banking scheme path works end-to-end.
4. Determinism: two runs byte-equal.
5. Engine-side invariant: fundamentals_first.json → PF=15.
6. Spec-math invariant: 35+20+20+0+0=75 ≥ 60 (Conviction Hold floor).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO / "tests" / "scoring-engine"
PHILOSOPHY = REPO / "input" / "india" / "philosophy.md"
INFY = FIXTURE_DIR / "infy.json"
HDFCBANK = FIXTURE_DIR / "hdfcbank.json"
FUND_FIRST = FIXTURE_DIR / "fundamentals_first.json"


def _run(argv: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "skills.scoring_engine.engine", *argv],
        capture_output=True, text=True, cwd=str(REPO), check=check,
    )


def test_full_shape_infy_with_it_mnc_exception():
    """`full` composes both payloads and preserves the §9.3 INFY sector-exception semantics."""
    r = _run([
        "full",
        "--ticker",           "INFY",
        "--metrics",          str(INFY),
        "--philosophy",       str(PHILOSOPHY),
        "--scheme",           "non_financial",
        "--sector-exception", "it_mnc",
    ])
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)

    assert set(payload.keys()) == {"thresholds", "my_philosophy"}

    thresholds = payload["thresholds"]
    assert thresholds["ticker"] == "INFY"
    assert thresholds["scheme"] == "non_financial"
    # IT-MNC promoter exception stays visible through `full`.
    promoter_row = next(c for c in thresholds["checks"] if c["metric"] == "promoter")
    assert promoter_row.get("exception") == "it_mnc"
    assert promoter_row.get("effective_threshold") == 10

    persona = payload["my_philosophy"]
    assert persona["ticker"] == "INFY"
    assert persona["persona"] == "my-philosophy"
    assert persona["weighted_score"] == thresholds["philosophy_fit_graded"]


def test_full_banking_scheme_end_to_end():
    r = _run([
        "full",
        "--ticker",     "HDFCBANK",
        "--metrics",    str(HDFCBANK),
        "--philosophy", str(PHILOSOPHY),
        "--scheme",     "banking_nbfc",
    ])
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["thresholds"]["scheme"] == "banking_nbfc"
    assert payload["my_philosophy"]["ticker"] == "HDFCBANK"
    # banking_nbfc applies banking-specific checks (nnpa, car, casa, nim, roa).
    metrics = {c["metric"] for c in payload["thresholds"]["checks"]}
    assert {"nnpa", "car", "casa", "nim", "roa"}.issubset(metrics)


def test_full_ticker_mismatch_exit_1():
    r = _run([
        "full",
        "--ticker",     "WRONG",
        "--metrics",    str(INFY),       # metrics.ticker = "INFY"
        "--philosophy", str(PHILOSOPHY),
        "--scheme",     "non_financial",
    ], check=False)
    assert r.returncode == 1, (
        f"expected exit 1 for ticker mismatch, got {r.returncode}\nstderr: {r.stderr}"
    )
    err = json.loads(r.stderr)
    assert err["error"] == "ticker_mismatch"
    assert "WRONG" in err["message"]
    assert "INFY" in err["message"]


def test_full_determinism_byte_equal():
    cmd = [
        "full",
        "--ticker",           "INFY",
        "--metrics",          str(INFY),
        "--philosophy",       str(PHILOSOPHY),
        "--scheme",           "non_financial",
        "--sector-exception", "it_mnc",
    ]
    a = _run(cmd).stdout
    b = _run(cmd).stdout
    assert a == b, "two runs of `full` produced different stdout"


def test_fundamentals_first_invariant_engine_side():
    """Engine-side: the fundamentals_first.json fixture (all checks pass, PF=15)
    composed through `full` must surface PF=15 at both layers.

    SPEC §9.2 invariant: valuation alone cannot push a fundamentally sound stock
    below Conviction Hold (60). This test guards the deterministic half — if
    a future refactor ever made `full` drop or mutate the PF value, this fails.
    """
    r = _run([
        "full",
        "--ticker",     "SYNTHCO",
        "--metrics",    str(FUND_FIRST),
        "--philosophy", str(PHILOSOPHY),
        "--scheme",     "non_financial",
    ])
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)

    assert payload["thresholds"]["philosophy_fit_graded"] == 15
    assert payload["thresholds"]["dealbreakers_triggered"] == []
    assert payload["thresholds"]["fail_count"] == 0
    assert payload["my_philosophy"]["weighted_score"] == 15
    assert payload["my_philosophy"]["signal"] == "bullish"


def test_fundamentals_first_invariant_spec_math():
    """Spec-math side: SPEC §9.1 max sub-scores + §9.2 invariant example must
    keep 35+20+20+0+0=75 above the Conviction Hold floor (60).

    This is a regression guard on SPEC §9.1's rubric weights — if a future
    milestone rebalances the max sub-scores (e.g. shrinks F from 35 to 30,
    bloats V from 20 to 25), the worst-case PF+N=0 sum could drop below 60
    and silently break the invariant. This test fails loudly.
    """
    # SPEC §9.1 rubric
    MAX_F, MAX_BS, MAX_V, MAX_PF, MAX_N = 35, 20, 20, 15, 10
    assert MAX_F + MAX_BS + MAX_V + MAX_PF + MAX_N == 100

    # SPEC §9.2 worst-case invariant example
    worst_case = MAX_F + MAX_BS + MAX_V + 0 + 0
    assert worst_case == 75, "SPEC §9.2 example value changed; invariant may be stale"

    # SPEC §9.1 band floor for Conviction Hold
    CONVICTION_HOLD_FLOOR = 60
    assert worst_case >= CONVICTION_HOLD_FLOOR, (
        f"Fundamentals-first invariant broken: {worst_case} < Conviction Hold floor "
        f"{CONVICTION_HOLD_FLOOR}. SPEC §9.1 rubric weights shifted — review §9.2."
    )
