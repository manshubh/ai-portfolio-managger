#!/usr/bin/env bash
# Smoke-test the M2.4 wealthfolio-query public surfaces.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
REPO_ROOT="$(cd ../.. && pwd)"
QUERY_SH="$REPO_ROOT/skills/wealthfolio_query/query.sh"

fail() {
  printf 'FAIL  %s\n' "$*" >&2
  exit 1
}

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

"$QUERY_SH" --help >"$tmpdir/help.out"
for subcommand in \
  export-snapshot \
  list-holdings \
  get-cash-balance \
  get-net-worth \
  get-avg-cost \
  get-portfolio-twr
do
  grep -q "$subcommand" "$tmpdir/help.out" \
    || fail "--help did not include $subcommand"
done

set +e
"$QUERY_SH" nope >"$tmpdir/unknown.out" 2>"$tmpdir/unknown.err"
status=$?
set -e
[[ "$status" -eq 1 ]] || fail "unknown subcommand exited $status, expected 1"

set +e
WEALTHFOLIO_DB= "$QUERY_SH" list-holdings \
  >"$tmpdir/missing-db.out" 2>"$tmpdir/missing-db.err"
status=$?
set -e
[[ "$status" -eq 2 ]] || fail "empty WEALTHFOLIO_DB exited $status, expected 2"
grep -q 'wealthfolio-query:' "$tmpdir/missing-db.err" \
  || fail "empty WEALTHFOLIO_DB stderr lacked wrapper prefix"

(
  cd "$REPO_ROOT"
  python3 -B -c '
from skills.wealthfolio_query.query import load_queries
slugs = set(load_queries())
expected = {
    "export-snapshot",
    "list-holdings",
    "get-cash-balance",
    "get-net-worth",
    "get-avg-cost",
    "get-portfolio-twr",
}
assert expected <= slugs, slugs
'
)

(
  cd "$REPO_ROOT"
  python3 -B -c '
from skills.wealthfolio_query.query import validate_schema_version
validate_schema_version()
'
)

printf 'PASS  wrapper skeleton smoke tests\n'
