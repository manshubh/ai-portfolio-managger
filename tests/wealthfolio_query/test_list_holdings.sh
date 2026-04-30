#!/usr/bin/env bash
# Verify list-holdings row shape, filters, formats, and deterministic order.
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

expected_header='ticker,name,market,currency,account,account_group,asset_type,quantity,avg_cost,snapshot_price,snapshot_market_value,allocation_pct,unrealized_pl_pct'

"$QUERY_SH" list-holdings --market all --format csv >"$tmpdir/all.csv"
header="$(sed -n '1p' "$tmpdir/all.csv")"
[[ "$header" == "$expected_header" ]] || fail "CSV header drifted"

python3 -B - "$tmpdir/all.csv" <<'PY'
import csv
import sys

path = sys.argv[1]
with open(path, newline="") as f:
    rows = list(csv.DictReader(f))

assert len(rows) == 9, len(rows)
keys = [(row["ticker"], row["account"]) for row in rows]
assert keys == sorted(keys), keys
assert rows[0]["ticker"] == "AAPL", rows[0]
assert rows[-1]["ticker"] == "TCS.BO", rows[-1]
assert any(row["asset_type"] == "ETF" for row in rows), rows
PY

"$QUERY_SH" list-holdings --market india --format csv >"$tmpdir/india.csv"
python3 -B - "$tmpdir/india.csv" <<'PY'
import csv
import sys

with open(sys.argv[1], newline="") as f:
    rows = list(csv.DictReader(f))

assert len(rows) == 6, len(rows)
assert {row["market"] for row in rows} == {"india"}, rows
assert all(row["currency"] == "INR" for row in rows), rows
PY

"$QUERY_SH" list-holdings \
  --scope-type account_group \
  --scope-value "India PMS" \
  --format csv >"$tmpdir/pms.csv"
python3 -B - "$tmpdir/pms.csv" <<'PY'
import csv
import sys

with open(sys.argv[1], newline="") as f:
    rows = list(csv.DictReader(f))

assert len(rows) == 2, len(rows)
assert {row["account_group"] for row in rows} == {"India PMS"}, rows
assert [row["ticker"] for row in rows] == ["PMSCORE.NS", "RELIANCE.NS"], rows
PY

"$QUERY_SH" list-holdings >"$tmpdir/all.json"
python3 -B - "$tmpdir/all.json" <<'PY'
import json
import sys

columns = [
    "ticker",
    "name",
    "market",
    "currency",
    "account",
    "account_group",
    "asset_type",
    "quantity",
    "avg_cost",
    "snapshot_price",
    "snapshot_market_value",
    "allocation_pct",
    "unrealized_pl_pct",
]

with open(sys.argv[1]) as f:
    rows = json.load(f)

assert len(rows) == 9, len(rows)
assert list(rows[0].keys()) == columns, rows[0].keys()
assert isinstance(rows[0]["quantity"], float), rows[0]
PY

"$QUERY_SH" list-holdings >"$tmpdir/run1.json"
"$QUERY_SH" list-holdings >"$tmpdir/run2.json"
diff -q "$tmpdir/run1.json" "$tmpdir/run2.json" >/dev/null \
  || fail "list-holdings output is not byte-identical across runs"

printf 'PASS  list-holdings formats, filters, and ordering\n'
