"""metrics.json.history → upstream-shaped line-item objects.

Ported personas (virattt/ai-hedge-fund@0f6ac48) call `search_line_items(...)`
and then consume the returned list with attribute access — `li.revenue`,
`getattr(li, "free_cash_flow", None)`, `hasattr(li, "research_and_development")`.
See charlie_munger.py L243-L254 and mohnish_pabrai.py L139-L142 for the
three access patterns in use.

M3.4 landed the schema (SPEC §18.2 extension). This module is the thin
adapter personas call to get that list; it does not fetch, it does not
impute, and it does not decide what counts as "insufficient data" — that's
per-persona (see M3 investigation §5.2).

Contract:

  to_line_items(metrics)       → list[SimpleNamespace], newest-first
  to_line_items(metrics, n=5)  → first N entries (newest-first slice)

Missing `history` / empty `line_items` → empty list (persona grace-degrades).
Malformed `history` (wrong type) → TypeError / ValueError to the caller.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any


def to_line_items(
    metrics: dict[str, Any],
    limit: int | None = None,
) -> list[SimpleNamespace]:
    """Return `metrics.history.line_items` as attribute-access objects, newest-first.

    The input shape is the §18.2 extension from M3.4:

        metrics["history"]["line_items"] = [
            {"revenue": ..., "net_income": ..., ...},   # newest
            ...
        ]

    Each output entry is a `SimpleNamespace` so upstream-ported code that does
    `getattr(li, "free_cash_flow", None)` and `hasattr(li, "goodwill_and_intangible_assets")`
    continues to work unchanged. Attributes absent from the source dict are
    simply absent on the namespace — `getattr(..., None)` returns None, which
    is what upstream already handles.

    `limit` slices to the first N entries (newest-first). Useful for personas
    that only want a recent window (Jhunjhunwala's upstream `limit=5`, etc.).
    """
    history = metrics.get("history")
    if history is None:
        return []
    if not isinstance(history, dict):
        raise TypeError(
            f"metrics.history must be an object, got {type(history).__name__}",
        )

    raw = history.get("line_items")
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise TypeError(
            f"metrics.history.line_items must be a list, got {type(raw).__name__}",
        )

    items: list[SimpleNamespace] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise TypeError(
                f"metrics.history.line_items[{i}] must be an object, "
                f"got {type(entry).__name__}",
            )
        items.append(SimpleNamespace(**entry))

    if limit is not None:
        if limit < 0:
            raise ValueError(f"limit must be non-negative, got {limit}")
        items = items[:limit]

    return items


def periods(metrics: dict[str, Any]) -> list[str]:
    """Return `metrics.history.periods` (newest-first), or [] if absent.

    Personas that report `missing_periods_*` in their `insufficient_data`
    payload read this to cite which periods were available.
    """
    history = metrics.get("history")
    if not isinstance(history, dict):
        return []
    got = history.get("periods")
    if got is None:
        return []
    if not isinstance(got, list):
        raise TypeError(
            f"metrics.history.periods must be a list, got {type(got).__name__}",
        )
    return list(got)


def period_type(metrics: dict[str, Any]) -> str | None:
    """Return `metrics.history.period_type` ("annual" | "ttm"), or None if absent."""
    history = metrics.get("history")
    if not isinstance(history, dict):
        return None
    got = history.get("period_type")
    if got is None:
        return None
    if not isinstance(got, str):
        raise TypeError(
            f"metrics.history.period_type must be a string, got {type(got).__name__}",
        )
    return got
