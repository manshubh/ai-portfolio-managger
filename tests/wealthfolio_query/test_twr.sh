#!/usr/bin/env bash
# Verify get-portfolio-twr chained product, forward-fill, and edge cases.
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

# 1. Happy path, India: query the wrapper, recompute the chain in Python from
#    the same SQL aggregate, assert |actual - expected| < 1bp. Also asserts the
#    JSON shape (date/series anchor, market/start/end fields) and pins a single
#    C[t] value as a regression guard against the cumulative-vs-delta drift
#    risk in plans/M2/M2.8 §Risks.
"$QUERY_SH" get-portfolio-twr \
  --market india --start 2026-03-30 --end 2026-04-30 \
  >"$tmpdir/india.json"

python3 -B - "$WEALTHFOLIO_DB" "$tmpdir/india.json" <<'PY'
import json
import sqlite3
import sys
from datetime import date, timedelta

db_path, json_path = sys.argv[1], sys.argv[2]
with open(json_path) as f:
    payload = json.load(f)

assert payload["market"] == "india"
assert payload["start"] == "2026-03-30"
assert payload["end"] == "2026-04-30"
# 32 calendar days from 2026-03-30 to 2026-04-30 inclusive.
assert len(payload["series"]) == 32, len(payload["series"])
assert payload["series"][0]["r"] is None
assert payload["series"][0]["C"] == 0.0
assert payload["series"][0]["date"] == "2026-03-30"
assert payload["series"][-1]["date"] == "2026-04-30"
for entry in payload["series"][1:]:
    assert entry["r"] is not None

# Recompute the chain from the SQL aggregate with the same forward-fill rule
# the wrapper uses. End-to-end test: wrapper plumbing (CLI parse, SQL bind,
# JSON shape) must agree with this reference loop within 1bp.
con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
cur = con.execute(
    """
    SELECT dav.valuation_date,
        SUM(CAST(dav.total_value AS REAL) * CAST(dav.fx_rate_to_base AS REAL)) AS v,
        SUM(CAST(dav.net_contribution AS REAL) * CAST(dav.fx_rate_to_base AS REAL)) AS cum
    FROM daily_account_valuation dav
    JOIN accounts acc ON acc.id = dav.account_id
    WHERE dav.valuation_date BETWEEN '2026-03-16' AND '2026-04-30'
      AND acc.is_active = 1 AND acc.is_archived = 0
      AND acc.currency = 'INR'
    GROUP BY dav.valuation_date
    ORDER BY dav.valuation_date
    """
)
by_date = {row[0]: (float(row[1]), float(row[2])) for row in cur.fetchall()}
con.close()

start, end = date(2026, 3, 30), date(2026, 4, 30)
anchor_v, anchor_cum = by_date[start.isoformat()]
prev_v, prev_cum = anchor_v, anchor_cum
twr = 1.0
d = start + timedelta(days=1)
while d <= end:
    v, cum = by_date.get(d.isoformat(), (prev_v, prev_cum))
    c = cum - prev_cum
    r = 0.0 if prev_v == 0 else (v - prev_v - c) / prev_v
    twr *= 1.0 + r
    prev_v, prev_cum = v, cum
    d += timedelta(days=1)
expected = round(twr - 1.0, 6)
assert abs(payload["twr"] - expected) < 1e-4, (payload["twr"], expected)

# C[t] regression: 2026-04-15 is broker-only on the India side (pms only has
# the 04-30 row), so daily contribution equals the broker_in net_contribution
# step (~222.22). If upstream switches to per-day deltas, this fires.
by_series = {entry["date"]: entry for entry in payload["series"]}
assert abs(by_series["2026-04-15"]["C"] - 222.22) < 0.05, by_series["2026-04-15"]["C"]
PY

# 2. Zero-day window.
"$QUERY_SH" get-portfolio-twr \
  --market india --start 2026-04-30 --end 2026-04-30 \
  >"$tmpdir/zero.json"
python3 -B - "$tmpdir/zero.json" <<'PY'
import json
import sys

d = json.load(open(sys.argv[1]))
assert d["twr"] == 0.0, d["twr"]
assert d["series"] == [], d["series"]
assert d["start"] == d["end"] == "2026-04-30"
PY

# 3. Forward-fill across a middle gap. Copy the fixture, delete a few daily
#    valuation rows, and verify the chained TWR matches the dense-fixture run
#    within 1bp (gap days contribute no-op factors of 1). This proves the
#    wrapper's forward-fill produces the mathematically equivalent result.
cp "$WEALTHFOLIO_DB" "$tmpdir/gap.db"
sqlite3 "$tmpdir/gap.db" \
  "DELETE FROM daily_account_valuation \
     WHERE account_id='acct_us_broker' \
       AND valuation_date IN ('2026-03-15','2026-03-16','2026-03-17')"

dense_twr="$(
  "$QUERY_SH" get-portfolio-twr \
    --market us --start 2026-03-10 --end 2026-03-20 \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["twr"])'
)"
gap_twr="$(
  WEALTHFOLIO_DB="$tmpdir/gap.db" "$QUERY_SH" get-portfolio-twr \
    --market us --start 2026-03-10 --end 2026-03-20 \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["twr"])'
)"
python3 -B - "$dense_twr" "$gap_twr" <<'PY'
import sys

dense, gap = float(sys.argv[1]), float(sys.argv[2])
assert abs(dense - gap) < 1e-4, (dense, gap)
assert gap != 0.0, "gap-day TWR was exactly zero — chain likely never ran"
PY

# 4. US market: base-currency series multiplied by fx_rate_to_base = 83.20.
"$QUERY_SH" get-portfolio-twr \
  --market us --start 2026-03-30 --end 2026-04-30 \
  >"$tmpdir/us.json"
python3 -B - "$tmpdir/us.json" <<'PY'
import json
import math
import sys

d = json.load(open(sys.argv[1]))
assert d["market"] == "us"
assert len(d["series"]) == 32, len(d["series"])
# US native total_value at 2026-03-30 ~ 119,460 USD; * 83.20 fx ≈ 9.94 M INR.
v0 = d["series"][0]["V"]
assert v0 > 9_000_000 and v0 < 11_000_000, v0
assert math.isfinite(d["twr"])
PY

# 5. Usage errors.
set +e
"$QUERY_SH" get-portfolio-twr --market india --end 2026-04-30 \
  >"$tmpdir/u1.out" 2>"$tmpdir/u1.err"
status=$?
set -e
[[ "$status" -eq 1 ]] || fail "missing --start exited $status, expected 1"

set +e
"$QUERY_SH" get-portfolio-twr --market india --start 2026-04-30 --end 2026-04-29 \
  >"$tmpdir/u2.out" 2>"$tmpdir/u2.err"
status=$?
set -e
[[ "$status" -eq 1 ]] || fail "--end < --start exited $status, expected 1"
grep -q -- '--end must be >= --start' "$tmpdir/u2.err" \
  || fail "--end < --start stderr missed pinned message"

# 6. Unknown market.
set +e
"$QUERY_SH" get-portfolio-twr --market europe --start 2026-04-01 --end 2026-04-30 \
  >"$tmpdir/u3.out" 2>"$tmpdir/u3.err"
status=$?
set -e
[[ "$status" -eq 1 ]] || fail "--market europe exited $status, expected 1"

# 7. No anchor at or before :start.
set +e
"$QUERY_SH" get-portfolio-twr --market india --start 2020-01-01 --end 2020-01-31 \
  >"$tmpdir/u4.out" 2>"$tmpdir/u4.err"
status=$?
set -e
[[ "$status" -eq 3 ]] || fail "pre-fixture window exited $status, expected 3"
grep -q 'no valuation rows at or before :start' "$tmpdir/u4.err" \
  || fail "pre-fixture stderr missed anchor message"

printf 'PASS  get-portfolio-twr chained product, forward-fill, and edge cases\n'
