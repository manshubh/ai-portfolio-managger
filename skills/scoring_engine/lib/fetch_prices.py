"""Path-only reader for the prices.json contract.

Investigation §6: M3 defines the shape; the actual price-history fetch is a
Phase-1 artifact (M8). This stub only reads from disk — no network — so tests
can point it at a fixture and runtime can point it at `temp/research/prices.json`
after M8's Phase-1 writes it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_prices(path: str) -> dict[str, Any]:
    """Read and validate a `prices.json` file into a dict.

    Minimal validation — caller-agnostic; the concentration engine does its
    own per-holding checks (missing ticker → warning, not error).
    """
    with Path(path).open(encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object at root")
    tickers = data.get("tickers")
    if not isinstance(tickers, dict):
        raise ValueError(f"{path}: expected `tickers` object")
    for t, entry in tickers.items():
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: tickers.{t} must be an object")
        dates = entry.get("dates")
        closes = entry.get("closes")
        if not isinstance(dates, list) or not isinstance(closes, list):
            raise ValueError(f"{path}: tickers.{t} needs list `dates` and `closes`")
        if len(dates) != len(closes):
            raise ValueError(
                f"{path}: tickers.{t} dates/closes length mismatch "
                f"({len(dates)} vs {len(closes)})",
            )
    return data


def read_holdings(path: str) -> dict[str, Any]:
    """Read a `holdings.json` file into a dict.

    Minimal validation: top-level object with a `holdings` list.
    """
    with Path(path).open(encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object at root")
    hs = data.get("holdings")
    if not isinstance(hs, list):
        raise ValueError(f"{path}: expected `holdings` list")
    for i, h in enumerate(hs):
        if not isinstance(h, dict):
            raise ValueError(f"{path}: holdings[{i}] must be an object")
        if "ticker" not in h:
            raise ValueError(f"{path}: holdings[{i}] missing `ticker`")
    return data
