#!/usr/bin/env bash
# Rebuild tests/wealthfolio_query/fixture.db from the canonical schema and seeds.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

REPO_ROOT="$(cd ../.. && pwd)"
SCHEMA_FILE="${REPO_ROOT}/research/wealthfolio-schema-v3.3.0.txt"
FIXTURE_SQL="fixture.sql"
FIXTURE_DB="fixture.db"

if ! command -v sqlite3 >/dev/null 2>&1; then
  printf 'build_fixture.sh: missing required dependency: sqlite3\n' >&2
  exit 1
fi

if [[ ! -f "$SCHEMA_FILE" ]]; then
  printf 'build_fixture.sh: missing schema file: %s\n' "$SCHEMA_FILE" >&2
  exit 1
fi

if [[ ! -f "$FIXTURE_SQL" ]]; then
  printf 'build_fixture.sh: missing seed file: %s/%s\n' "$PWD" "$FIXTURE_SQL" >&2
  exit 1
fi

rm -f fixture.db fixture.db-wal fixture.db-shm

tmp_schema="$(mktemp)"
schema_err="$(mktemp)"
seed_err="$(mktemp)"
fk_err="$(mktemp)"
trap 'rm -f "$tmp_schema" "$schema_err" "$seed_err" "$fk_err"' EXIT

# The canonical .schema dump includes SQLite's internal sqlite_sequence table.
# SQLite refuses direct user creation of that name, so recreate it by creating
# and dropping an AUTOINCREMENT table at the same point in the schema stream.
awk '
  /^CREATE TABLE sqlite_sequence\(name,seq\);$/ {
    print "CREATE TABLE __fixture_sqlite_sequence_seed(id INTEGER PRIMARY KEY AUTOINCREMENT);"
    print "DROP TABLE __fixture_sqlite_sequence_seed;"
    next
  }
  { print }
' "$SCHEMA_FILE" > "$tmp_schema"

if ! sqlite3 "$FIXTURE_DB" ".read $tmp_schema" 2>"$schema_err"; then
  cat "$schema_err" >&2
  exit 1
fi
if [[ -s "$schema_err" ]]; then
  cat "$schema_err" >&2
  exit 1
fi

if ! sqlite3 "$FIXTURE_DB" "PRAGMA foreign_keys=ON;" ".read $FIXTURE_SQL" 2>"$seed_err"; then
  cat "$seed_err" >&2
  exit 1
fi
if [[ -s "$seed_err" ]]; then
  cat "$seed_err" >&2
  exit 1
fi

if sqlite3 "$FIXTURE_DB" "PRAGMA foreign_key_check;" 2>"$fk_err" | grep -q .; then
  cat "$fk_err" >&2
  sqlite3 "$FIXTURE_DB" "PRAGMA foreign_key_check;" >&2
  exit 1
fi
if [[ -s "$fk_err" ]]; then
  cat "$fk_err" >&2
  exit 1
fi

printf 'Built %s/%s\n' "$PWD" "$FIXTURE_DB"
