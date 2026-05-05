"""scoring-engine CLI shell — see docs/SPEC.md §18.3.

M3.2 lands the argparse surface and exit-code matrix only; subcommand
handlers are no-ops that exit 2 ("not implemented yet"). Real handlers
land in M3.3 (check-thresholds + my-philosophy persona), M3.6-M3.9
(persona ports), M3.10 (concentration-check), M3.11 (full).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import NoReturn

EXIT_OK = 0
EXIT_BAD_INPUT = 1
EXIT_INTERNAL = 2

PERSONAS = ["my-philosophy", "jhunjhunwala", "buffett", "munger", "pabrai"]
SCHEMES = ["non_financial", "banking_nbfc"]


def _not_implemented(subcommand: str, lands_in: str) -> NoReturn:
    err = {
        "error": "not_implemented",
        "subcommand": subcommand,
        "lands_in": lands_in,
        "message": (
            f"M3.2 ships the CLI shell only; `{subcommand}` handler is a no-op "
            f"and will be wired in {lands_in}."
        ),
    }
    print(json.dumps(err), file=sys.stderr)
    sys.exit(EXIT_INTERNAL)


def _handle_check_thresholds(_args: argparse.Namespace) -> NoReturn:
    _not_implemented("check-thresholds", "M3.3")


def _handle_persona(_args: argparse.Namespace) -> NoReturn:
    _not_implemented("persona", "M3.3 (my-philosophy) / M3.6-M3.9 (rotating personas)")


def _handle_concentration_check(_args: argparse.Namespace) -> NoReturn:
    _not_implemented("concentration-check", "M3.10")


def _handle_full(_args: argparse.Namespace) -> NoReturn:
    _not_implemented("full", "M3.11")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scoring-engine",
        description=(
            "Deterministic scoring math for ai-portfolio-manager. "
            "All output is JSON on stdout; errors are JSON on stderr. "
            "Exit codes: 0=success, 1=bad input, 2=internal error. "
            "See docs/SPEC.md §18.3 for the full contract."
        ),
    )
    sub = parser.add_subparsers(dest="subcommand", metavar="<subcommand>")
    sub.required = True

    # check-thresholds — SPEC §9.3, §18.3
    p_ct = sub.add_parser(
        "check-thresholds",
        help="Pass/fail every metric in metrics.json against the philosophy YAML thresholds.",
        description=(
            "Run the deterministic §9.3 pass/fail table against a metrics.json. "
            "Output includes per-check rows, dealbreakers triggered, and "
            "philosophy_fit_graded (PF/15: 0|8|15 per the §9.2 ladder). "
            "F/BS/V/N sub-scores are NOT computed here — Phase 4 LLM owns those."
        ),
    )
    p_ct.add_argument("--philosophy", required=True, metavar="<path>",
                     help="Path to philosophy.md (with §7.6 YAML front-matter).")
    p_ct.add_argument("--scheme", required=True, choices=SCHEMES,
                     help="Threshold scheme to apply (caller-decided per investigation §2).")
    p_ct.add_argument("--metrics", required=True, metavar="<path>",
                     help="Path to metrics.json (§18.2 shape, optionally extended per §3).")
    p_ct.add_argument("--sector-exception", metavar="<name>", default=None,
                     help="Optional sector exception key from sector_exceptions: "
                          "(e.g. it_mnc, psus, hospitals, foreign_sub, stock_exchanges).")
    p_ct.set_defaults(func=_handle_check_thresholds)

    # persona — SPEC §9.4, §18.3
    p_pe = sub.add_parser(
        "persona",
        help="Run a single persona's deterministic base scoring against metrics.json.",
        description=(
            "Run one persona's base-score math against metrics.json. Output is "
            "{ticker, persona, sub_scores, weighted_score, max_score, signal, "
            "confidence, details}. When required line-items are missing the "
            "persona emits {signal:'insufficient_data', missing_fields:[...]} "
            "with exit code 0 (per investigation §5.2). my-philosophy is "
            "exempt from insufficient_data."
        ),
    )
    p_pe.add_argument("--persona", required=True, choices=PERSONAS,
                     help="Persona to run (MVP roster per investigation §4).")
    p_pe.add_argument("--metrics", required=True, metavar="<path>",
                     help="Path to metrics.json.")
    p_pe.add_argument("--price-context", metavar="<path>", default=None,
                     help="Optional price-context JSON (e.g. for technicals).")
    p_pe.set_defaults(func=_handle_persona)

    # concentration-check — SPEC §9.5, §18.3
    p_cc = sub.add_parser(
        "concentration-check",
        help="HHI, per-stock vol-adjusted limits, top-5 correlation pairs across the portfolio.",
        description=(
            "Portfolio-level concentration sanity per SPEC §9.5. Output: HHI, "
            "per-stock volatility-adjusted position limit (base from "
            "position_sizing.max_per_stock_pct in the philosophy YAML), and "
            "the top-5 correlation pairs by absolute Pearson correlation over "
            "the lookback window. Price-history shape defined in investigation §6; "
            "the actual fetch is Phase-1 (M8), not this skill."
        ),
    )
    p_cc.add_argument("--holdings", required=True, metavar="<path>",
                     help="Path to holdings.json (ticker, market_value, allocation_pct, sector).")
    p_cc.add_argument("--price-history", required=True, metavar="<path>",
                     help="Path to prices.json (per-ticker dates+closes, lookback window).")
    p_cc.add_argument("--philosophy", required=True, metavar="<path>",
                     help="Path to philosophy.md (reads position_sizing.max_per_stock_pct).")
    p_cc.set_defaults(func=_handle_concentration_check)

    # full — SPEC §18.3, investigation §7
    p_fu = sub.add_parser(
        "full",
        help="Combined check-thresholds + my-philosophy persona for one ticker (Phase 4 convenience).",
        description=(
            "Convenience wrapper that emits {thresholds: {...}, my_philosophy: {...}} "
            "for a single ticker — combines `check-thresholds` and "
            "`persona --persona my-philosophy`. Rotating personas (jhunjhunwala / "
            "buffett / munger / pabrai) are NOT included here; Phase 5 calls "
            "them individually per investigation §7."
        ),
    )
    p_fu.add_argument("--ticker", required=True, metavar="<T>",
                     help="Ticker symbol (e.g. INFY, RELIANCE).")
    p_fu.add_argument("--metrics", required=True, metavar="<path>",
                     help="Path to metrics.json.")
    p_fu.add_argument("--philosophy", required=True, metavar="<path>",
                     help="Path to philosophy.md.")
    p_fu.set_defaults(func=_handle_full)

    return parser


def main(argv: list[str] | None = None) -> NoReturn:
    parser = _build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
