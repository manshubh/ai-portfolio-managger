"""Tests for skills.scoring_engine.lib.line_items (M3.5 adapter).

Covers: newest-first preservation, attribute-access compatibility with
upstream's `getattr` / `hasattr` / bare-attr patterns, graceful handling
of missing `history` blocks, `limit` slicing, and type validation.
"""

from __future__ import annotations

import pytest

from skills.scoring_engine.lib import line_items as li


# ---------- Shape & newest-first ordering ---------------------------------

def test_returns_list_of_namespaces_in_input_order() -> None:
    metrics = {
        "ticker": "X",
        "history": {
            "period_type": "annual",
            "periods": ["FY26", "FY25", "FY24"],
            "line_items": [
                {"revenue": 300, "net_income": 30},
                {"revenue": 200, "net_income": 20},
                {"revenue": 100, "net_income": 10},
            ],
        },
    }
    out = li.to_line_items(metrics)
    assert len(out) == 3
    # Newest-first contract: index 0 is the most recent period.
    assert out[0].revenue == 300
    assert out[1].revenue == 200
    assert out[2].revenue == 100


# ---------- Upstream access patterns --------------------------------------

def test_supports_getattr_with_default_for_absent_field() -> None:
    # Upstream mohnish_pabrai.py:180 uses this pattern heavily.
    metrics = {"history": {"line_items": [{"revenue": 100}]}}
    (item,) = li.to_line_items(metrics)
    assert getattr(item, "revenue", None) == 100
    assert getattr(item, "free_cash_flow", None) is None


def test_supports_hasattr_for_absent_field() -> None:
    # Upstream charlie_munger.py:243 uses hasattr before reading.
    metrics = {"history": {"line_items": [{"revenue": 100}]}}
    (item,) = li.to_line_items(metrics)
    assert hasattr(item, "revenue") is True
    assert hasattr(item, "research_and_development") is False


def test_supports_bare_attribute_access() -> None:
    metrics = {"history": {"line_items": [{"ebit": 42, "gross_margin": 0.37}]}}
    (item,) = li.to_line_items(metrics)
    assert item.ebit == 42
    assert item.gross_margin == 0.37


# ---------- Limit --------------------------------------------------------

def test_limit_slices_from_front_newest_first() -> None:
    metrics = {
        "history": {"line_items": [{"revenue": v} for v in (8, 7, 6, 5, 4, 3, 2, 1)]},
    }
    out = li.to_line_items(metrics, limit=5)
    assert [o.revenue for o in out] == [8, 7, 6, 5, 4]


def test_limit_larger_than_available_returns_all() -> None:
    metrics = {"history": {"line_items": [{"revenue": 1}, {"revenue": 2}]}}
    out = li.to_line_items(metrics, limit=10)
    assert len(out) == 2


def test_limit_zero_returns_empty() -> None:
    metrics = {"history": {"line_items": [{"revenue": 1}]}}
    assert li.to_line_items(metrics, limit=0) == []


def test_negative_limit_raises() -> None:
    with pytest.raises(ValueError):
        li.to_line_items({"history": {"line_items": []}}, limit=-1)


# ---------- Graceful empty cases -----------------------------------------

def test_missing_history_returns_empty_list() -> None:
    # No `history` key at all: personas see [] and emit insufficient_data themselves.
    assert li.to_line_items({"ticker": "X", "fund": {}}) == []


def test_missing_line_items_returns_empty_list() -> None:
    assert li.to_line_items({"history": {"period_type": "annual"}}) == []


def test_empty_line_items_returns_empty_list() -> None:
    assert li.to_line_items({"history": {"line_items": []}}) == []


# ---------- Type validation ----------------------------------------------

def test_history_wrong_type_raises() -> None:
    with pytest.raises(TypeError, match="metrics.history must be an object"):
        li.to_line_items({"history": ["not", "an", "object"]})


def test_line_items_wrong_type_raises() -> None:
    with pytest.raises(TypeError, match="line_items must be a list"):
        li.to_line_items({"history": {"line_items": "not-a-list"}})


def test_line_item_entry_wrong_type_raises() -> None:
    with pytest.raises(TypeError, match=r"line_items\[1\] must be an object"):
        li.to_line_items({"history": {"line_items": [{"revenue": 1}, "oops"]}})


# ---------- Auxiliary accessors ------------------------------------------

def test_periods_returns_list() -> None:
    metrics = {"history": {"periods": ["FY26", "FY25", "FY24"]}}
    assert li.periods(metrics) == ["FY26", "FY25", "FY24"]


def test_periods_missing_returns_empty() -> None:
    assert li.periods({"history": {}}) == []
    assert li.periods({}) == []


def test_periods_wrong_type_raises() -> None:
    with pytest.raises(TypeError, match="periods must be a list"):
        li.periods({"history": {"periods": "FY26"}})


def test_period_type_roundtrip() -> None:
    assert li.period_type({"history": {"period_type": "annual"}}) == "annual"
    assert li.period_type({"history": {"period_type": "ttm"}}) == "ttm"
    assert li.period_type({"history": {}}) is None
    assert li.period_type({}) is None


def test_period_type_wrong_type_raises() -> None:
    with pytest.raises(TypeError, match="period_type must be a string"):
        li.period_type({"history": {"period_type": 42}})


# ---------- Simulated persona consumption --------------------------------

def test_ported_pabrai_style_consumption_works_unchanged() -> None:
    """Emulate upstream mohnish_pabrai.analyze_downside_protection prelude.

    The adapter's whole job is to make this pattern from upstream work
    verbatim against our JSON input.
    """
    metrics = {
        "history": {
            "line_items": [
                {
                    "cash_and_equivalents": 4500,
                    "total_debt": 230,
                    "current_assets": 8900,
                    "current_liabilities": 3400,
                    "shareholders_equity": 15200,
                    "free_cash_flow": 1670,
                    "capital_expenditure": 400,
                },
                {"free_cash_flow": 1500, "capital_expenditure": 380},
                {"free_cash_flow": 1300, "capital_expenditure": 360},
            ],
        },
    }
    financial_line_items = li.to_line_items(metrics, limit=8)

    # Exact upstream snippet pattern (mohnish_pabrai.py:139-142).
    latest = financial_line_items[0]
    cash = getattr(latest, "cash_and_equivalents", None)
    debt = getattr(latest, "total_debt", None)
    equity = getattr(latest, "shareholders_equity", None)
    assert cash == 4500 and debt == 230 and equity == 15200

    # Upstream mohnish_pabrai.py:180 filter pattern.
    fcf_values = [getattr(li_, "free_cash_flow", None) for li_ in financial_line_items
                  if getattr(li_, "free_cash_flow", None) is not None]
    assert fcf_values == [1670, 1500, 1300]
