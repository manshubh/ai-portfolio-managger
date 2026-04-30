#!/usr/bin/env bash
# Verify get-cash-balance currency and scope semantics.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
REPO_ROOT="$(cd ../.. && pwd)"
QUERY_SH="$REPO_ROOT/skills/wealthfolio_query/query.sh"
export WEALTHFOLIO_DB="$PWD/fixture.db"

fail() {
  printf 'FAIL  %s\n' "$*" >&2
  exit 1
}

assert_stdout() {
  local expected="$1"
  shift
  local actual
  actual="$("$QUERY_SH" get-cash-balance "$@")"
  [[ "$actual" == "$expected" ]] \
    || fail "get-cash-balance $* returned $actual, expected $expected"
}

./build_fixture.sh >/dev/null
[[ -f "$WEALTHFOLIO_DB" ]] || fail "fixture.db was not built"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

assert_stdout "1025000.0" --currency INR
assert_stdout "42000.0" --currency USD
assert_stdout "4519400.0" --currency all
assert_stdout "4519400.0"
assert_stdout "900000.0" --scope-type account_group --scope-value "India PMS"

set +e
"$QUERY_SH" get-cash-balance \
  --scope-type account \
  --scope-value "No Such Account" \
  >"$tmpdir/empty.out" 2>"$tmpdir/empty.err"
status=$?
set -e

[[ "$status" -eq 0 ]] || fail "empty scope exited $status, expected 0"
[[ "$(<"$tmpdir/empty.out")" == "0.0" ]] || fail "empty scope did not print 0.0"
[[ ! -s "$tmpdir/empty.err" ]] || fail "empty scope wrote stderr"

printf 'PASS  get-cash-balance currency and scope behavior\n'
