"""Tests for skills.scoring_engine.personas.jhunjhunwala (M3.6).

Covers: output-contract shape (investigation §5.2), determinism (§5.3),
insufficient-data graceful degradation, and a regression snapshot that pins
the ported upstream math to this commit.
"""

from __future__ import annotations

import json
from pathlib import Path

from skills.scoring_engine.personas import jhunjhunwala

FIXTURES = Path(__file__).resolve().parent


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


# ---------- Shape ---------------------------------------------------------

def test_happy_path_produces_expected_shape() -> None:
    metrics = _load("infy.json")
    result = jhunjhunwala.run(metrics)

    assert set(result.keys()) == {
        "ticker", "persona", "sub_scores", "weighted_score",
        "max_score", "signal", "confidence", "details",
    }
    assert result["persona"] == "jhunjhunwala"
    assert result["ticker"] == "INFY"

    assert isinstance(result["weighted_score"], int)
    assert 0 <= result["weighted_score"] <= 100
    assert result["max_score"] == 100

    assert result["signal"] in {"bullish", "neutral", "bearish"}
    assert 0.0 <= result["confidence"] <= 1.0

    expected_sub_scores = {
        "profitability", "growth", "balance_sheet", "cash_flow", "management_actions",
    }
    assert set(result["sub_scores"].keys()) == expected_sub_scores
    assert set(result["details"].keys()) == expected_sub_scores
    for detail in result["details"].values():
        assert isinstance(detail, str) and detail


# ---------- Determinism ---------------------------------------------------

def test_determinism_byte_equal_across_two_runs() -> None:
    metrics = _load("infy.json")
    a = jhunjhunwala.run(metrics)
    b = jhunjhunwala.run(metrics)
    assert json.dumps(a, sort_keys=False) == json.dumps(b, sort_keys=False)


# ---------- Insufficient-data graceful degradation ------------------------

def test_insufficient_data_path_exits_zero_and_reports_shortfall() -> None:
    metrics = _load("jhunjhunwala_insufficient_data.json")
    result = jhunjhunwala.run(metrics)

    assert result["signal"] == "insufficient_data"
    assert result["confidence"] == 0.0
    assert isinstance(result["min_periods_required"], int)
    assert result["min_periods_required"] >= 3
    assert result["min_periods_available"] < result["min_periods_required"]

    missing = result["missing_fields"]
    assert isinstance(missing, list) and missing
    assert all(isinstance(m, str) for m in missing)


# ---------- Regression snapshot -------------------------------------------

def test_regression_snapshot_sub_scores_and_weighted_score() -> None:
    """Pins current behavior so future edits surface regressions.

    Values computed once from infy.json against the port at M3.6 landing.
    """
    metrics = _load("infy.json")
    result = jhunjhunwala.run(metrics)

    assert result["sub_scores"] == {
        "profitability":      5,
        "growth":             2,
        "balance_sheet":      4,
        "cash_flow":          2,
        "management_actions": 1,
    }
    assert result["weighted_score"] == 58
    assert result["signal"] == "bearish"
    assert result["confidence"] == 0.7
