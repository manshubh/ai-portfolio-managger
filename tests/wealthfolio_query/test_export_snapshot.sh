#!/usr/bin/env bash
# Verify export-snapshot CSV header, theses merge, escape handling, and byte-identical re-runs.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
REPO_ROOT="$(cd ../.. && pwd)"
QUERY_SH="$REPO_ROOT/skills/wealthfolio_query/query.sh"
export WEALTHFOLIO_DB="$PWD/fixture.db"

fail() {
  printf 'FAIL  %s\n' "$*" >&2
  exit 1
}

./build_fixture.sh >/dev/null
[[ -f "$WEALTHFOLIO_DB" ]] || fail "fixture.db was not built"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

expected_header='ticker,name,market,currency,account,account_group,asset_type,quantity,avg_cost,snapshot_price,snapshot_market_value,allocation_pct,unrealized_pl_pct,thesis'

# 1. Header + row count + allocation_pct sum + escaping.
"$QUERY_SH" export-snapshot \
  --market india --scope-type market --scope-value india \
  --theses fixtures/theses.india.yaml \
  --output "$tmpdir/snap1.csv" >"$tmpdir/snap1.stdout" 2>"$tmpdir/snap1.stderr"

[[ ! -s "$tmpdir/snap1.stdout" ]] || fail "--output set but stdout was non-empty"

header="$(sed -n '1p' "$tmpdir/snap1.csv")"
[[ "$header" == "$expected_header" ]] || fail "CSV header drifted: got '$header'"

python3 -B - "$tmpdir/snap1.csv" <<'PY'
import csv
import math
import sys

path = sys.argv[1]
with open(path, newline="") as f:
    rows = list(csv.DictReader(f))

assert len(rows) == 6, f"expected 6 India rows, got {len(rows)}"
assert [r["ticker"] for r in rows] == sorted(r["ticker"] for r in rows), [r["ticker"] for r in rows]

alloc = sum(float(r["allocation_pct"]) for r in rows)
assert math.isclose(alloc, 1.0, abs_tol=1e-6), f"allocation_pct sum {alloc} != ~1.0"

by_ticker_account = {(r["ticker"], r["account"]): r for r in rows}
reliance_pms = by_ticker_account[("RELIANCE.NS", "Fixture India PMS")]
reliance_brk = by_ticker_account[("RELIANCE.NS", "Fixture India Brokerage")]
expected_thesis = "Energy + retail + telecom; also, jio."
assert reliance_pms["thesis"] == expected_thesis, reliance_pms["thesis"]
assert reliance_brk["thesis"] == expected_thesis, reliance_brk["thesis"]

tcs = by_ticker_account[("TCS.BO", "Fixture India Brokerage")]
expected_tcs = 'Multi-line\nthesis with "quotes" and, commas.\n'
assert tcs["thesis"] == expected_tcs, repr(tcs["thesis"])

infy = by_ticker_account[("INFY.NS", "Fixture India Brokerage")]
assert infy["thesis"] == "", repr(infy["thesis"])
PY

# 2. Two consecutive runs are byte-identical.
"$QUERY_SH" export-snapshot \
  --market india --scope-type market --scope-value india \
  --theses fixtures/theses.india.yaml \
  --output "$tmpdir/snap2.csv"
diff -q "$tmpdir/snap1.csv" "$tmpdir/snap2.csv" >/dev/null \
  || fail "two consecutive runs produced non-identical output"

# 3. --theses auto-resolution against the real input/india/theses.yaml — no warning,
# empty thesis column (the real file's strings are all "").
set +e
"$QUERY_SH" export-snapshot \
  --market india --scope-type market --scope-value india \
  --output "$tmpdir/auto.csv" 2>"$tmpdir/auto.stderr"
status=$?
set -e
[[ "$status" -eq 0 ]] || fail "auto-resolve --theses exited $status"
[[ ! -s "$tmpdir/auto.stderr" ]] \
  || fail "auto-resolve --theses produced stderr: $(cat "$tmpdir/auto.stderr")"
python3 -B - "$tmpdir/auto.csv" <<'PY'
import csv
import sys

with open(sys.argv[1], newline="") as f:
    rows = list(csv.DictReader(f))
assert len(rows) == 6, len(rows)
assert all(r["thesis"] == "" for r in rows), [r["thesis"] for r in rows]
PY

# 4. --market us auto-resolves input/us/theses.yaml; 3 rows; byte-identical.
"$QUERY_SH" export-snapshot \
  --market us --scope-type market --scope-value us \
  --output "$tmpdir/us1.csv"
"$QUERY_SH" export-snapshot \
  --market us --scope-type market --scope-value us \
  --output "$tmpdir/us2.csv"
diff -q "$tmpdir/us1.csv" "$tmpdir/us2.csv" >/dev/null \
  || fail "us export-snapshot not byte-identical across runs"
python3 -B - "$tmpdir/us1.csv" <<'PY'
import csv
import sys

with open(sys.argv[1], newline="") as f:
    rows = list(csv.DictReader(f))
assert len(rows) == 3, len(rows)
assert {r["ticker"] for r in rows} == {"AAPL", "ARKK", "BRK.B"}, [r["ticker"] for r in rows]
PY

# 5. Stream to stdout when --output is omitted.
"$QUERY_SH" export-snapshot \
  --market india --scope-type market --scope-value india \
  --theses fixtures/theses.india.yaml >"$tmpdir/stdout.csv"
diff -q "$tmpdir/snap1.csv" "$tmpdir/stdout.csv" >/dev/null \
  || fail "stdout output diverged from --output file"

# 6. Malformed YAML exits 3.
printf 'theses:\n  AAPL: [unclosed\n' >"$tmpdir/bad.yaml"
set +e
"$QUERY_SH" export-snapshot \
  --market india --scope-type market --scope-value india \
  --theses "$tmpdir/bad.yaml" \
  --output "$tmpdir/bad.csv" >"$tmpdir/bad.stdout" 2>"$tmpdir/bad.stderr"
status=$?
set -e
[[ "$status" -eq 3 ]] || fail "malformed YAML exited $status, expected 3"
grep -q 'wealthfolio-query:' "$tmpdir/bad.stderr" \
  || fail "malformed YAML stderr missed 'wealthfolio-query:' prefix"
grep -q 'not valid YAML' "$tmpdir/bad.stderr" \
  || fail "malformed YAML stderr missed 'not valid YAML' substring"

# 7. Missing theses file warns but exits 0; CSV still written; thesis column empty.
set +e
"$QUERY_SH" export-snapshot \
  --market india --scope-type market --scope-value india \
  --theses "$tmpdir/does-not-exist.yaml" \
  --output "$tmpdir/missing.csv" 2>"$tmpdir/missing.stderr"
status=$?
set -e
[[ "$status" -eq 0 ]] || fail "missing theses exited $status, expected 0"
grep -q 'theses file not found' "$tmpdir/missing.stderr" \
  || fail "missing theses stderr missed 'theses file not found' substring"
python3 -B - "$tmpdir/missing.csv" <<'PY'
import csv
import sys

with open(sys.argv[1], newline="") as f:
    rows = list(csv.DictReader(f))
assert len(rows) == 6, len(rows)
assert all(r["thesis"] == "" for r in rows), [r["thesis"] for r in rows]
PY

# 8. Missing required arg exits 1.
set +e
"$QUERY_SH" export-snapshot >"$tmpdir/usage.out" 2>"$tmpdir/usage.err"
status=$?
set -e
[[ "$status" -eq 1 ]] || fail "missing required args exited $status, expected 1"

printf 'PASS  export-snapshot header, theses merge, escape handling, byte-identical re-runs\n'
