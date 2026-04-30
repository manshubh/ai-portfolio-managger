#!/usr/bin/env bash
# Verify get-net-worth market, date, currency, and archived-account behavior.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
REPO_ROOT="$(cd ../.. && pwd)"
QUERY_SH="$REPO_ROOT/skills/wealthfolio_query/query.sh"
export WEALTHFOLIO_DB="$PWD/fixture.db"

fail() {
  printf 'FAIL  %s\n' "$*" >&2
  exit 1
}

assert_float() {
  local actual="$1"
  local expected="$2"
  local label="$3"
  python3 -B - "$actual" "$expected" "$label" <<'PY'
import math
import sys

actual = float(sys.argv[1])
expected = float(sys.argv[2])
label = sys.argv[3]
if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-6):
    raise SystemExit(f"{label}: got {actual}, expected {expected}")
PY
}

./build_fixture.sh >/dev/null
[[ -f "$WEALTHFOLIO_DB" ]] || fail "fixture.db was not built"

all_latest="$("$QUERY_SH" get-net-worth --market all)"
india_latest="$("$QUERY_SH" get-net-worth --market india)"
us_latest="$("$QUERY_SH" get-net-worth --market us)"
dated_all="$("$QUERY_SH" get-net-worth --market all --date 2026-03-15)"
usd_all="$("$QUERY_SH" get-net-worth --market all --currency USD)"
dated_usd="$("$QUERY_SH" get-net-worth --market all --date 2026-03-15 --currency USD)"

assert_float "$all_latest" "12575400.0" "all latest"
assert_float "$india_latest" "2425000.0" "india latest"
assert_float "$us_latest" "10150400.0" "us latest"
assert_float "$dated_all" "10586278.054" "all at 2026-03-15"
assert_float "$usd_all" "151146.63461538462" "all latest in USD"
assert_float "$dated_usd" "127238.91891826922" "dated all in USD"

printf 'PASS  get-net-worth market, date, currency, and archive filters\n'
