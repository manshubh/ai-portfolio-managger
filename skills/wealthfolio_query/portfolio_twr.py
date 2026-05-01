"""get-portfolio-twr — chain daily returns over a window into TWR.

SPEC §6.8, §17, §18.1, §19.2 invariants 11/14.
See plans/M2/M2.8-get-portfolio-twr.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from typing import Iterator

from skills.wealthfolio_query.query import (
    EXIT_DATA,
    EXIT_OK,
    EXIT_USAGE,
    execute,
)

# 14-day lookback covers weekends + long holidays for anchor-row resolution
# at :start when the user picks a non-trading day. The wrapper widens the
# SQL :start by this many days; the SQL filter itself is unchanged.
_ANCHOR_LOOKBACK_DAYS = 14


def _err(message: str) -> None:
    print(f"wealthfolio-query: {message}", file=sys.stderr)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        _err(message)
        raise SystemExit(EXIT_USAGE)


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="wealthfolio-query get-portfolio-twr",
        description=(
            "Chain daily returns over [start, end] into a time-weighted "
            "return for a market slice."
        ),
        add_help=True,
    )
    parser.add_argument("--market", required=True, choices=["india", "us"])
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    return parser


def _parse_date(flag: str, value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        _err(f"invalid {flag}: {value!r} (expected YYYY-MM-DD)")
        raise SystemExit(EXIT_USAGE)


def _calendar(start: date, end: date) -> Iterator[date]:
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def _emit(payload: dict) -> None:
    json.dump(payload, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")


def main(argv: list[str] | None = None) -> int:
    args_in = list(argv) if argv is not None else sys.argv[1:]
    parser = _build_parser()
    args = parser.parse_args(args_in)

    start = _parse_date("--start", args.start)
    end = _parse_date("--end", args.end)

    if end < start:
        _err("--end must be >= --start")
        return EXIT_USAGE

    if start == end:
        _emit(
            {
                "twr": 0.0,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "market": args.market,
                "series": [],
            }
        )
        return EXIT_OK

    lookback = start - timedelta(days=_ANCHOR_LOOKBACK_DAYS)
    rows = execute(
        "get-portfolio-twr",
        {
            "market": args.market,
            "start": lookback.isoformat(),
            "end": end.isoformat(),
        },
    )

    by_date: dict[date, tuple[float, float]] = {}
    for row in rows:
        d = date.fromisoformat(row["date"])
        v = row["portfolio_value_base"]
        cum = row["cumulative_net_contribution_base"]
        if v is None or cum is None:
            continue
        by_date[d] = (float(v), float(cum))

    if start in by_date:
        anchor_v, anchor_cum = by_date[start]
    else:
        prior = [d for d in by_date if d < start]
        if not prior:
            _err("no valuation rows at or before :start")
            return EXIT_DATA
        anchor_v, anchor_cum = by_date[max(prior)]

    series: list[dict] = [
        {
            "date": start.isoformat(),
            "V": anchor_v,
            "C": 0.0,
            "r": None,
        }
    ]

    twr = 1.0
    prev_v, prev_cum = anchor_v, anchor_cum
    for d in _calendar(start + timedelta(days=1), end):
        if d in by_date:
            v, cum = by_date[d]
        else:
            v, cum = prev_v, prev_cum
        c = cum - prev_cum
        r = 0.0 if prev_v == 0 else (v - prev_v - c) / prev_v
        twr *= 1.0 + r
        series.append({"date": d.isoformat(), "V": v, "C": c, "r": r})
        prev_v, prev_cum = v, cum

    _emit(
        {
            "twr": round(twr - 1.0, 6),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "market": args.market,
            "series": series,
        }
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
