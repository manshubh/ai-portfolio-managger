#!/usr/bin/env bash
# Assert every non-null instrument_exchange_mic in assets is in the pinned set.
# Subset check (⊆), not equality — distinct from test_schema.sh's active-only
# equality check. Catches drift to a MIC we have not validated downstream.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
FIXTURE_DB="$PWD/fixture.db"

fail() {
  printf 'FAIL  %s\n' "$*" >&2
  exit 1
}

./build_fixture.sh >/dev/null
[[ -f "$FIXTURE_DB" ]] || fail "fixture.db was not built"

allowed='ARCX XBOM XNAS XNSE XNYS'

actual="$(
  sqlite3 -readonly "$FIXTURE_DB" \
    "SELECT DISTINCT instrument_exchange_mic
     FROM assets
     WHERE instrument_exchange_mic IS NOT NULL
     ORDER BY 1"
)"

while IFS= read -r mic; do
  [[ -z "$mic" ]] && continue
  found=0
  for a in $allowed; do
    [[ "$mic" == "$a" ]] && { found=1; break; }
  done
  [[ "$found" -eq 1 ]] || fail "unexpected MIC '$mic' not in {$allowed}"
done <<<"$actual"

printf 'PASS  MIC drift subset check (%s)\n' "$(echo "$actual" | tr '\n' ',' | sed 's/,$//')"
