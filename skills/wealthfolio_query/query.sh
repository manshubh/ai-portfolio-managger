#!/usr/bin/env bash
# wealthfolio-query — read-only wrapper around named SQL queries.
# SPEC §6.8, §17, §18.1, §19.2 invariants 11 (read-only) and 14 (pinned schema).
# See plans/M2/M2.4-wrapper-skeleton.md.

set -euo pipefail

# Exit codes (mirror skills/wealthfolio_query/query.py).
#   0 — success or help printed
#   1 — usage error (bad flags, unknown subcommand, missing argument)
#   2 — DB / dependency / schema-version error
#   3 — data-shape error (reserved for later subcommands)
readonly EXIT_OK=0
readonly EXIT_USAGE=1
readonly EXIT_DB=2
# shellcheck disable=SC2034  # EXIT_DATA reserved for M2.6-M2.8 subcommand bodies.
readonly EXIT_DATA=3

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

err() {
  printf 'wealthfolio-query: %s\n' "$*" >&2
}

usage() {
  cat <<'USAGE'
wealthfolio-query — read-only wrapper around named SQL queries (SPEC §6.8, §18.1).

Usage:
  wealthfolio-query <subcommand> [options]
  wealthfolio-query --help

Subcommands (SPEC §18.1):
  export-snapshot \
    --market india|us \
    --scope-type market|account_group|account \
    --scope-value <value> \
    [--theses input/{market}/theses.yaml] \
    [--output temp/research/portfolio-snapshot.csv]
      → CSV matching SPEC §7.1.1, with thesis column populated.

  list-holdings    [--market india|us|all] [--scope-type ...] [--scope-value ...] [--format json|csv]
  get-cash-balance [--currency INR|USD|all] [--scope-type ...] [--scope-value ...]
  get-net-worth    [--market india|us|all] [--date <YYYY-MM-DD>] [--currency INR|USD]
  get-avg-cost     <ticker>
  get-portfolio-twr --market <...> --start <date> --end <date>

Environment:
  WEALTHFOLIO_DB   Absolute path to the Wealthfolio SQLite database. Required
                   for every subcommand. Always opened read-only.

Exit codes:
  0  success / help printed
  1  usage error (bad flags, unknown subcommand, missing argument)
  2  DB, dependency, or schema-version error
  3  data-shape error (reserved for later subcommands)
USAGE
}

require_dep() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    err "missing required dependency: $cmd"
    exit "$EXIT_DB"
  fi
}

require_db() {
  if [[ -z "${WEALTHFOLIO_DB:-}" ]]; then
    err "WEALTHFOLIO_DB is not set; export it to the Wealthfolio SQLite path"
    exit "$EXIT_DB"
  fi
  if [[ ! -f "$WEALTHFOLIO_DB" || ! -r "$WEALTHFOLIO_DB" ]]; then
    err "WEALTHFOLIO_DB path is not a readable file: $WEALTHFOLIO_DB"
    exit "$EXIT_DB"
  fi
}

validate_schema() {
  # Delegates to query.py so the SQL/config pin comparison lives in one place.
  if ! (cd "$REPO_ROOT" && python3 -m skills.wealthfolio_query.query validate-schema); then
    exit "$EXIT_DB"
  fi
}

placeholder() {
  # Recognized subcommand whose body lands in a later M2 task.
  local subcommand="$1"
  local owner="$2"
  err "$subcommand is recognized but not implemented in M2.4 — body lands in $owner"
  exit "$EXIT_DB"
}

is_choice() {
  local value="$1"
  shift
  local choice
  for choice in "$@"; do
    [[ "$value" == "$choice" ]] && return 0
  done
  return 1
}

validate_choice() {
  local flag="$1"
  local value="$2"
  shift 2
  if ! is_choice "$value" "$@"; then
    err "invalid $flag: $value"
    exit "$EXIT_USAGE"
  fi
}

validate_scope_pair() {
  local scope_type="$1"
  local scope_value="$2"

  if [[ -z "$scope_type" && -n "$scope_value" ]]; then
    err "--scope-value requires --scope-type"
    exit "$EXIT_USAGE"
  fi
  if [[ -n "$scope_type" && -z "$scope_value" ]]; then
    err "--scope-type requires --scope-value"
    exit "$EXIT_USAGE"
  fi
  if [[ -n "$scope_type" ]]; then
    validate_choice "--scope-type" "$scope_type" market account_group account
  fi
}

_load_named_query() {
  local slug="$1"
  (
    cd "$REPO_ROOT"
    python3 -B -c '
import sys
from skills.wealthfolio_query.query import load_query

sys.stdout.write(load_query(sys.argv[1]))
' "$slug"
  )
}

_esc_sq() {
  printf '%s' "$1" | sed "s/'/''/g"
}

_esc_dq() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

_bind() {
  local name="$1"
  local value="$2"

  if [[ "$value" == "__WFQ_NULL__" ]]; then
    printf '.parameter set :%s NULL\n' "$name"
  else
    printf '.parameter set :%s "%s"\n' "$name" "$(_esc_dq "'$(_esc_sq "$value")'")"
  fi
}

_run_named_query() {
  local slug="$1"
  shift

  local tmp_sql
  tmp_sql="$(mktemp)"
  trap 'rm -f "$tmp_sql"' RETURN

  _load_named_query "$slug" >"$tmp_sql"
  {
    echo ".bail on"
    echo ".mode list"
    echo ".separator |"
    while [[ $# -gt 0 ]]; do
      local name="$1"
      local value="$2"
      shift 2
      _bind "$name" "$value"
    done
    printf '.read %s\n' "$tmp_sql"
  } | sqlite3 -readonly "$WEALTHFOLIO_DB"
}

format_list_holdings() {
  local format="$1"
  python3 -B -c '
import csv
import json
import sys

fmt = sys.argv[1]
columns = [
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
]
numeric_columns = {
    "quantity",
    "avg_cost",
    "snapshot_price",
    "snapshot_market_value",
    "allocation_pct",
    "unrealized_pl_pct",
}

raw_rows = []
json_rows = []
for line in sys.stdin.read().splitlines():
    if line == "":
        continue
    parts = line.split("|")
    if len(parts) != len(columns):
        raise SystemExit(
            f"expected {len(columns)} list-holdings columns, got {len(parts)}"
        )
    raw_rows.append(parts)
    row = {}
    for key, value in zip(columns, parts):
        if value == "":
            row[key] = None
        elif key in numeric_columns:
            row[key] = float(value)
        else:
            row[key] = value
    json_rows.append(row)

if fmt == "json":
    json.dump(json_rows, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")
elif fmt == "csv":
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(raw_rows)
else:
    raise SystemExit(f"unknown format: {fmt}")
' "$format"
}

cmd_list_holdings() {
  local market="all"
  local scope_type=""
  local scope_value=""
  local format="json"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --market)
        [[ $# -ge 2 ]] || { err "--market requires a value"; exit "$EXIT_USAGE"; }
        market="$2"
        shift 2
        ;;
      --scope-type)
        [[ $# -ge 2 ]] || { err "--scope-type requires a value"; exit "$EXIT_USAGE"; }
        scope_type="$2"
        shift 2
        ;;
      --scope-value)
        [[ $# -ge 2 ]] || { err "--scope-value requires a value"; exit "$EXIT_USAGE"; }
        scope_value="$2"
        shift 2
        ;;
      --format)
        [[ $# -ge 2 ]] || { err "--format requires a value"; exit "$EXIT_USAGE"; }
        format="$2"
        shift 2
        ;;
      --*)
        err "unknown flag for list-holdings: $1"
        exit "$EXIT_USAGE"
        ;;
      *)
        err "unexpected argument for list-holdings: $1"
        exit "$EXIT_USAGE"
        ;;
    esac
  done

  validate_choice "--market" "$market" india us all
  validate_choice "--format" "$format" json csv
  validate_scope_pair "$scope_type" "$scope_value"
  if [[ -z "$scope_type" ]]; then
    scope_type="market"
    scope_value="all"
  fi

  _run_named_query list-holdings \
    market "$market" \
    scope_type "$scope_type" \
    scope_value "$scope_value" \
    | format_list_holdings "$format"
}

cmd_get_cash_balance() {
  local currency="all"
  local scope_type=""
  local scope_value=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --currency)
        [[ $# -ge 2 ]] || { err "--currency requires a value"; exit "$EXIT_USAGE"; }
        currency="$2"
        shift 2
        ;;
      --scope-type)
        [[ $# -ge 2 ]] || { err "--scope-type requires a value"; exit "$EXIT_USAGE"; }
        scope_type="$2"
        shift 2
        ;;
      --scope-value)
        [[ $# -ge 2 ]] || { err "--scope-value requires a value"; exit "$EXIT_USAGE"; }
        scope_value="$2"
        shift 2
        ;;
      --*)
        err "unknown flag for get-cash-balance: $1"
        exit "$EXIT_USAGE"
        ;;
      *)
        err "unexpected argument for get-cash-balance: $1"
        exit "$EXIT_USAGE"
        ;;
    esac
  done

  validate_choice "--currency" "$currency" INR USD all
  validate_scope_pair "$scope_type" "$scope_value"
  if [[ -z "$scope_type" ]]; then
    scope_type="market"
    scope_value="all"
  fi

  local value
  value="$(_run_named_query get-cash-balance \
    currency "$currency" \
    scope_type "$scope_type" \
    scope_value "$scope_value")"
  printf '%s\n' "${value:-0.0}"
}

cmd_get_net_worth() {
  local market="all"
  local currency="none"
  local date="__WFQ_NULL__"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --market)
        [[ $# -ge 2 ]] || { err "--market requires a value"; exit "$EXIT_USAGE"; }
        market="$2"
        shift 2
        ;;
      --currency)
        [[ $# -ge 2 ]] || { err "--currency requires a value"; exit "$EXIT_USAGE"; }
        currency="$2"
        shift 2
        ;;
      --date)
        [[ $# -ge 2 ]] || { err "--date requires a value"; exit "$EXIT_USAGE"; }
        date="$2"
        shift 2
        ;;
      --*)
        err "unknown flag for get-net-worth: $1"
        exit "$EXIT_USAGE"
        ;;
      *)
        err "unexpected argument for get-net-worth: $1"
        exit "$EXIT_USAGE"
        ;;
    esac
  done

  validate_choice "--market" "$market" india us all
  validate_choice "--currency" "$currency" INR USD none
  if [[ "$date" != "__WFQ_NULL__" && ! "$date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    err "invalid --date: $date"
    exit "$EXIT_USAGE"
  fi

  local row
  row="$(_run_named_query get-net-worth \
    date "$date" \
    market "$market" \
    currency "$currency")"

  local base_total
  local fx_day
  IFS='|' read -r base_total fx_day <<<"$row"
  base_total="${base_total:-0.0}"

  if [[ "$currency" == "none" ]]; then
    printf '%s\n' "$base_total"
    return
  fi
  if [[ -z "${fx_day:-}" || "$fx_day" == "0" || "$fx_day" == "0.0" ]]; then
    err "FX rate not found for output currency: $currency"
    exit "$EXIT_DB"
  fi

  python3 -B -c '
import sys

print(str(float(sys.argv[1]) / float(sys.argv[2])))
' "$base_total" "$fx_day"
}

cmd_export_snapshot() {
  # Stay in the caller's CWD so --theses/--output relative paths resolve as
  # the user expects. PYTHONPATH lets `python3 -m` find the package without cd.
  PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
    exec python3 -B -m skills.wealthfolio_query.export_snapshot "$@"
}

cmd_get_avg_cost() {
  if [[ $# -eq 0 ]]; then
    err "get-avg-cost requires a ticker argument"
    exit "$EXIT_USAGE"
  fi
  if [[ $# -ne 1 ]]; then
    err "get-avg-cost takes exactly one ticker argument"
    exit "$EXIT_USAGE"
  fi
  if [[ "$1" == --* ]]; then
    err "unknown flag for get-avg-cost: $1"
    exit "$EXIT_USAGE"
  fi

  local ticker="$1"
  local value
  value="$(_run_named_query get-avg-cost ticker "$ticker")"
  if [[ -z "$value" ]]; then
    err "ticker not in active holdings: $ticker"
    exit "$EXIT_DB"
  fi
  printf '%s\n' "$value"
}

main() {
  if [[ $# -eq 0 ]]; then
    err "missing subcommand; run 'wealthfolio-query --help' for usage"
    exit "$EXIT_USAGE"
  fi

  case "$1" in
    -h|--help|help)
      usage
      exit "$EXIT_OK"
      ;;
  esac

  local subcommand="$1"
  shift

  case "$subcommand" in
    export-snapshot|list-holdings|get-cash-balance|get-net-worth|get-avg-cost|get-portfolio-twr)
      ;;
    *)
      err "unknown subcommand: $subcommand (run 'wealthfolio-query --help')"
      exit "$EXIT_USAGE"
      ;;
  esac

  require_dep python3
  require_db
  validate_schema

  case "$subcommand" in
    export-snapshot)
      cmd_export_snapshot "$@"
      ;;
    list-holdings)
      require_dep sqlite3
      cmd_list_holdings "$@"
      ;;
    get-cash-balance)
      require_dep sqlite3
      cmd_get_cash_balance "$@"
      ;;
    get-net-worth)
      require_dep sqlite3
      cmd_get_net_worth "$@"
      ;;
    get-avg-cost)
      require_dep sqlite3
      cmd_get_avg_cost "$@"
      ;;
    get-portfolio-twr)
      placeholder get-portfolio-twr M2.8
      ;;
  esac
}

main "$@"
