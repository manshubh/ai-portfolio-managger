"""Tests for skills.scoring_engine.my_philosophy (M3.3).

Fixtures assert the deterministic §9.3 pass/fail table, §9.2 PF/15 ladder,
sector-exception application, and the three dealbreakers. One extra test
pins byte-equal stdout across repeated CLI runs (determinism — investigation §5.3).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent
PHILOSOPHY = REPO / "input" / "india" / "philosophy.md"


def _run_cli(*extra: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "skills.scoring_engine.engine", *extra],
        cwd=REPO, capture_output=True, text=True, check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _run_check(metrics: Path, scheme: str = "non_financial",
               sector_exception: str | None = None) -> dict:
    args = ["check-thresholds",
            "--philosophy", str(PHILOSOPHY),
            "--scheme", scheme,
            "--metrics", str(metrics)]
    if sector_exception:
        args += ["--sector-exception", sector_exception]
    rc, out, err = _run_cli(*args)
    assert rc == 0, f"exit={rc}, stderr={err}"
    return json.loads(out)


# ---------- INFY: IT-MNC exception, SPEC §9.3 example reproduction ----------

def test_infy_reproduces_spec_9_3_example() -> None:
    result = _run_check(FIXTURES / "infy.json",
                        sector_exception="it_mnc")

    assert result["ticker"] == "INFY"
    assert result["scheme"] == "non_financial"
    assert result["dealbreakers_triggered"] == []
    assert result["philosophy_fit_graded"] == 8  # 1 non-dealbreaker fail
    assert result["pass_count"] == 8
    assert result["fail_count"] == 1

    by_metric = {c["metric"]: c for c in result["checks"]}
    promoter = by_metric["promoter"]
    assert promoter["pass"] is False
    assert promoter["exception"] == "it_mnc"
    assert promoter["effective_threshold"] == 10
    assert promoter["pass_with_exception"] is True

    # The one non-dealbreaker fail is pat_cagr_3y (8.2 < 10).
    assert by_metric["pat_cagr_3y"]["pass"] is False
    for m in ("roe", "roce", "de", "pledge", "rev_cagr_3y", "fcf_positive", "mcap_cr"):
        assert by_metric[m]["pass"] is True, m


# ---------- HDFCBANK: banking_nbfc graded fail path ----------

def test_hdfcbank_banking_nbfc_graded_fail() -> None:
    result = _run_check(FIXTURES / "hdfcbank.json", scheme="banking_nbfc")
    assert result["scheme"] == "banking_nbfc"
    assert result["dealbreakers_triggered"] == []
    by_metric = {c["metric"]: c for c in result["checks"]}
    # NIM 2.8 < 3.0 fails; rest pass.
    assert by_metric["nim"]["pass"] is False
    assert result["fail_count"] == 1
    assert result["philosophy_fit_graded"] == 8


# ---------- COALINDIA: psus exception (stricter promoter_min) ----------

def test_coalindia_psus_exception() -> None:
    result = _run_check(FIXTURES / "coalindia.json", sector_exception="psus")
    assert result["dealbreakers_triggered"] == []
    by_metric = {c["metric"]: c for c in result["checks"]}
    promoter = by_metric["promoter"]
    # psus sets promoter_min=45; base is 40. 63.1 passes both.
    assert promoter["pass"] is True
    assert promoter["exception"] == "psus"
    assert promoter["effective_threshold"] == 45
    # No pass_with_exception key since base and effective agree.
    assert "pass_with_exception" not in promoter
    assert result["philosophy_fit_graded"] == 15


# ---------- BSE: stock_exchanges.exempt suppresses zero-promoter dealbreaker ----------

def test_bse_stock_exchanges_exempt() -> None:
    result = _run_check(FIXTURES / "bse.json", sector_exception="stock_exchanges")
    assert result["dealbreakers_triggered"] == []  # exempt blocks zero_promoter
    by_metric = {c["metric"]: c for c in result["checks"]}
    promoter = by_metric["promoter"]
    assert promoter["exception"] == "stock_exchanges"
    assert promoter["exempt"] is True
    assert promoter["pass_with_exception"] is True
    assert result["philosophy_fit_graded"] == 15


# ---------- fundamentals_first: all pass → PF=15 ----------

def test_fundamentals_first_all_pass() -> None:
    result = _run_check(FIXTURES / "fundamentals_first.json")
    assert result["dealbreakers_triggered"] == []
    assert result["fail_count"] == 0
    assert result["philosophy_fit_graded"] == 15


# ---------- Dealbreakers ----------

def test_dealbreaker_zero_promoter() -> None:
    result = _run_check(FIXTURES / "dealbreaker_zero_promoter.json")
    assert "zero_promoter" in result["dealbreakers_triggered"]
    assert result["philosophy_fit_graded"] == 0


def test_dealbreaker_user_thesis_exit() -> None:
    result = _run_check(FIXTURES / "dealbreaker_thesis_sell.json")
    assert "user_thesis_exit" in result["dealbreakers_triggered"]
    # Even though every check passes, PF is forced to 0 by the dealbreaker.
    assert result["fail_count"] == 0
    assert result["philosophy_fit_graded"] == 0


# ---------- Determinism: byte-equal stdout across two runs ----------

@pytest.mark.parametrize("fixture,sector_exception,scheme", [
    ("infy.json", "it_mnc", "non_financial"),
    ("hdfcbank.json", None, "banking_nbfc"),
    ("bse.json", "stock_exchanges", "non_financial"),
    ("dealbreaker_zero_promoter.json", None, "non_financial"),
])
def test_determinism(fixture: str, sector_exception: str | None, scheme: str) -> None:
    args = ["check-thresholds",
            "--philosophy", str(PHILOSOPHY),
            "--scheme", scheme,
            "--metrics", str(FIXTURES / fixture)]
    if sector_exception:
        args += ["--sector-exception", sector_exception]
    _, out1, _ = _run_cli(*args)
    _, out2, _ = _run_cli(*args)
    assert out1 == out2


# ---------- persona --persona my-philosophy ----------

def test_persona_my_philosophy_wraps_pf() -> None:
    rc, out, err = _run_cli(
        "persona", "--persona", "my-philosophy",
        "--philosophy", str(PHILOSOPHY),
        "--scheme", "non_financial",
        "--sector-exception", "it_mnc",
        "--metrics", str(FIXTURES / "infy.json"),
    )
    assert rc == 0, err
    result = json.loads(out)
    assert result["persona"] == "my-philosophy"
    assert result["sub_scores"] == {"philosophy_fit": 8}
    assert result["weighted_score"] == 8
    assert result["max_score"] == 15
    assert result["signal"] == "neutral"


