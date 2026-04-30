#!/usr/bin/env bash
# Verify get-avg-cost weighted averages and miss/usage exits.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
REPO_ROOT="$(cd ../.. && pwd)"
QUERY_SH="$REPO_ROOT/skills/wealthfolio_query/query.sh"
export WEALTHFOLIO_DB="$PWD/fixture.db"

fail() {
  printf 'FAIL  %s\n' "$*" >&2
  exit 1
}

assert_avg_cost() {
  local ticker="$1"
  local expected="$2"
  local actual
  actual="$("$QUERY_SH" get-avg-cost "$ticker")"
  python3 -B - "$actual" "$expected" "$ticker" <<'PY'
import math
import sys

actual = float(sys.argv[1])
expected = float(sys.argv[2])
ticker = sys.argv[3]
if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-6):
    raise SystemExit(f"{ticker}: got {actual}, expected {expected}")
PY
}

./build_fixture.sh >/dev/null
[[ -f "$WEALTHFOLIO_DB" ]] || fail "fixture.db was not built"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

assert_avg_cost "RELIANCE.NS" "2377.77777777778"
assert_avg_cost "PMSCORE.NS" "95.0"
assert_avg_cost "AAPL" "170.0"
assert_avg_cost "ARKK" "45.0"

set +e
"$QUERY_SH" get-avg-cost ZZZZ.NS >"$tmpdir/unknown.out" 2>"$tmpdir/unknown.err"
status=$?
set -e
[[ "$status" -eq 2 ]] || fail "unknown ticker exited $status, expected 2"
[[ ! -s "$tmpdir/unknown.out" ]] || fail "unknown ticker wrote stdout"
grep -q 'ticker not in active holdings' "$tmpdir/unknown.err" \
  || fail "unknown ticker stderr missed data-not-found message"

set +e
"$QUERY_SH" get-avg-cost >"$tmpdir/missing.out" 2>"$tmpdir/missing.err"
status=$?
set -e
[[ "$status" -eq 1 ]] || fail "missing ticker exited $status, expected 1"
grep -q 'requires a ticker argument' "$tmpdir/missing.err" \
  || fail "missing ticker stderr missed usage message"

printf 'PASS  get-avg-cost weighted averages and error paths\n'
