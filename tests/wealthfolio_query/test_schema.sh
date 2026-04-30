#!/usr/bin/env bash
# Verify fixture schema drift and active-asset MIC coverage.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
REPO_ROOT="$(cd ../.. && pwd)"
FIXTURE_DB="$PWD/fixture.db"
SCHEMA_FILE="$REPO_ROOT/research/wealthfolio-schema-v3.2.1.txt"

fail() {
  printf 'FAIL  %s\n' "$*" >&2
  exit 1
}

./build_fixture.sh >/dev/null
[[ -f "$FIXTURE_DB" ]] || fail "fixture.db was not built"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

sed -E 's/[[:space:]]+$//' "$SCHEMA_FILE" >"$tmpdir/expected.schema"
sqlite3 "$FIXTURE_DB" '.schema' \
  | sed -E 's/[[:space:]]+$//' >"$tmpdir/actual.schema"

if ! diff -u "$tmpdir/expected.schema" "$tmpdir/actual.schema"; then
  fail "fixture schema differs from $SCHEMA_FILE"
fi

expected_mics='<NULL>
ARCX
XBOM
XNAS
XNSE
XNYS'
actual_mics="$(
  sqlite3 -readonly "$FIXTURE_DB" \
    "SELECT DISTINCT COALESCE(instrument_exchange_mic, '<NULL>')
     FROM assets WHERE is_active = 1 ORDER BY 1"
)"

[[ "$actual_mics" == "$expected_mics" ]] || {
  printf 'Expected MIC set:\n%s\n\nActual MIC set:\n%s\n' \
    "$expected_mics" "$actual_mics" >&2
  fail "active asset MIC coverage drifted"
}

printf 'PASS  schema drift and MIC coverage\n'
