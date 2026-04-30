#!/usr/bin/env bash
# Verify the fixture and static SQL layer stay read-only.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
REPO_ROOT="$(cd ../.. && pwd)"
FIXTURE_DB="$PWD/fixture.db"

fail() {
  printf 'FAIL  %s\n' "$*" >&2
  exit 1
}

./build_fixture.sh >/dev/null
[[ -f "$FIXTURE_DB" ]] || fail "fixture.db was not built"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

set +e
sqlite3 -readonly "$FIXTURE_DB" "UPDATE accounts SET name = 'x'" \
  >"$tmpdir/update.out" 2>"$tmpdir/update.err"
status=$?
set -e

[[ "$status" -ne 0 ]] || fail "sqlite3 -readonly accepted an UPDATE"
grep -qi 'readonly' "$tmpdir/update.err" \
  || fail "readonly UPDATE stderr did not mention readonly"

ddl_count="$(
  sed -E 's|--.*$||' "$REPO_ROOT/skills/sql/wealthfolio-queries.sql" \
    | grep -cE '^[[:space:]]*(CREATE|INSERT|UPDATE|DELETE|DROP|ALTER)\b' \
    || true
)"
[[ "$ddl_count" == "0" ]] \
  || fail "wealthfolio-queries.sql contains top-level DDL/DML statements"

printf 'PASS  readonly enforcement and static SQL write scan\n'
