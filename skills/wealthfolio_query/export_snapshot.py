"""export-snapshot — run the named query, merge thesis sidecar, write CSV.

SPEC §5.4 (Phase 1 frozen snapshot pipeline), §6.8 (subcommand contract — `--output`
is silent, no preview echo), §7.1.1 (14-column normalized schema, byte-authoritative),
§7.1.2 (thesis sidecar), §17/§18.1 (skill layout), §19.2 invariants 11/13/14.

See plans/M2/M2.7-export-snapshot.md.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from skills.wealthfolio_query.query import (
    EXIT_DATA,
    EXIT_DB,
    EXIT_OK,
    EXIT_USAGE,
    execute,
    repo_root,
)

CSV_COLUMNS = [
    "ticker",
    "name",
    "market",
    "currency",
    "account",
    "account_group",
    "asset_type",
    "quantity",
    "avg_cost",
    "snapshot_price",
    "snapshot_market_value",
    "allocation_pct",
    "unrealized_pl_pct",
    "thesis",
]


def _err(message: str) -> None:
    print(f"wealthfolio-query: {message}", file=sys.stderr)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        _err(message)
        raise SystemExit(EXIT_USAGE)


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="wealthfolio-query export-snapshot",
        description="Run export-snapshot named query, merge thesis sidecar, emit SPEC §7.1.1 CSV.",
        add_help=True,
    )
    parser.add_argument("--market", required=True, choices=["india", "us"])
    parser.add_argument(
        "--scope-type", required=True, choices=["market", "account_group", "account"]
    )
    parser.add_argument("--scope-value", required=True)
    parser.add_argument("--theses")
    parser.add_argument("--output")
    return parser


def _load_theses(path: Path) -> dict[str, str]:
    if not path.exists():
        _err(
            f"theses file not found at {path}; continuing with empty thesis column"
        )
        return {}
    try:
        import yaml
    except ImportError:  # pragma: no cover - environment misconfig
        _err("PyYAML is required to load thesis sidecars")
        raise SystemExit(EXIT_DB)

    text = path.read_text()
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        _err(f"theses file is not valid YAML: {path}: {exc}")
        raise SystemExit(EXIT_DATA)

    if data is None:
        return {}
    if not isinstance(data, dict):
        _err(f"theses file top-level must be a mapping: {path}")
        raise SystemExit(EXIT_DATA)
    raw = data.get("theses")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        _err(f"theses file 'theses:' must be a mapping: {path}")
        raise SystemExit(EXIT_DATA)

    out: dict[str, str] = {}
    coerced = False
    for ticker, body in raw.items():
        key = str(ticker)
        if body is None or body == "":
            out[key] = ""
            continue
        if isinstance(body, str):
            out[key] = body
            continue
        if not coerced:
            _err(
                f"theses file has non-string values; coercing to string: {path}"
            )
            coerced = True
        out[key] = str(body)
    return out


def main(argv: list[str] | None = None) -> int:
    args_in = list(argv) if argv is not None else sys.argv[1:]
    parser = _build_parser()
    args = parser.parse_args(args_in)

    theses_path = (
        Path(args.theses)
        if args.theses
        else repo_root() / "input" / args.market / "theses.yaml"
    )
    theses = _load_theses(theses_path)

    rows = execute(
        "export-snapshot",
        {
            "market": args.market,
            "scope_type": args.scope_type,
            "scope_value": args.scope_value,
        },
    )

    if args.output:
        try:
            handle = open(args.output, "w", newline="")
        except OSError as exc:
            _err(f"cannot open --output {args.output}: {exc}")
            return EXIT_DB
        close_handle = True
    else:
        handle = sys.stdout
        close_handle = False

    try:
        writer = csv.writer(handle, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(CSV_COLUMNS)
        for row in rows:
            ticker = row[0]
            data = list(row) + [theses.get(ticker, "")]
            writer.writerow(data)
    finally:
        if close_handle:
            handle.close()

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
