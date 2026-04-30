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
  get-net-worth    [--date <YYYY-MM-DD>] [--currency INR|USD]
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
      placeholder export-snapshot M2.7
      ;;
    list-holdings|get-cash-balance|get-net-worth|get-avg-cost)
      require_dep sqlite3
      placeholder "$subcommand" M2.6
      ;;
    get-portfolio-twr)
      placeholder get-portfolio-twr M2.8
      ;;
  esac
}

main "$@"
