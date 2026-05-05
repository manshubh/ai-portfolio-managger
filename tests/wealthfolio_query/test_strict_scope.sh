#!/usr/bin/env bash
# Verify --strict-scope behavior across the three scoped subcommands and the
# rejection on non-scoped subcommands. M2.9.
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

# --- 1. Bogus account name on list-holdings: exit 2, "scope" in stderr, no "readonly" ---
set +e
"$QUERY_SH" list-holdings \
  --scope-type account \
  --scope-value "No Such Account" \
  --strict-scope \
  >"$tmpdir/bogus_acct.out" 2>"$tmpdir/bogus_acct.err"
status=$?
set -e
[[ "$status" -eq 2 ]] || fail "bogus account exited $status, expected 2"
grep -q 'scope' "$tmpdir/bogus_acct.err" \
  || fail "bogus account stderr missing 'scope': $(<"$tmpdir/bogus_acct.err")"
if grep -q 'readonly' "$tmpdir/bogus_acct.err"; then
  fail "bogus account stderr should not mention readonly: $(<"$tmpdir/bogus_acct.err")"
fi

# --- 2. Bogus market literal on list-holdings: exit 2 ---
# (Use account_group with a typo'd name to exercise the DB-validation path too.)
set +e
"$QUERY_SH" list-holdings \
  --scope-type account_group \
  --scope-value "No Such Group" \
  --strict-scope \
  >/dev/null 2>"$tmpdir/bogus_group.err"
status=$?
set -e
[[ "$status" -eq 2 ]] || fail "bogus group exited $status, expected 2"
grep -q 'scope account_group=' "$tmpdir/bogus_group.err" \
  || fail "bogus group stderr drift: $(<"$tmpdir/bogus_group.err")"

# --- 3. Valid market literal on list-holdings: exit 0 ---
"$QUERY_SH" list-holdings \
  --market all \
  --scope-type market \
  --scope-value india \
  --strict-scope \
  >"$tmpdir/india.json"
[[ -s "$tmpdir/india.json" ]] || fail "valid india scope produced empty output"

# --- 4. Valid account_group on get-cash-balance --strict-scope: matches non-strict ---
non_strict="$("$QUERY_SH" get-cash-balance \
  --scope-type account_group --scope-value "India PMS")"
strict="$("$QUERY_SH" get-cash-balance \
  --scope-type account_group --scope-value "India PMS" --strict-scope)"
[[ "$non_strict" == "$strict" ]] \
  || fail "strict and non-strict cash-balance diverged ($non_strict vs $strict)"

# --- 5. export-snapshot bogus scope + --output: exit 2 AND output file not created ---
output_path="$tmpdir/should-not-exist.csv"
set +e
"$QUERY_SH" export-snapshot \
  --market india \
  --scope-type account \
  --scope-value "No Such Account" \
  --strict-scope \
  --output "$output_path" \
  >"$tmpdir/export.out" 2>"$tmpdir/export.err"
status=$?
set -e
[[ "$status" -eq 2 ]] || fail "export-snapshot bogus scope exited $status, expected 2"
[[ ! -e "$output_path" ]] \
  || fail "export-snapshot wrote --output despite strict-scope rejection"

# --- 6. --strict-scope on non-scoped subcommands: exit 1 with "only applies" ---
for sub in get-net-worth get-avg-cost get-portfolio-twr; do
  set +e
  case "$sub" in
    get-avg-cost)
      "$QUERY_SH" "$sub" --strict-scope RELIANCE.NS \
        >/dev/null 2>"$tmpdir/$sub.err"
      ;;
    get-portfolio-twr)
      "$QUERY_SH" "$sub" --strict-scope \
        --market india --start 2026-01-01 --end 2026-01-10 \
        >/dev/null 2>"$tmpdir/$sub.err"
      ;;
    *)
      "$QUERY_SH" "$sub" --strict-scope \
        >/dev/null 2>"$tmpdir/$sub.err"
      ;;
  esac
  status=$?
  set -e
  [[ "$status" -eq 1 ]] || fail "$sub --strict-scope exited $status, expected 1"
  grep -q 'only applies' "$tmpdir/$sub.err" \
    || fail "$sub stderr missing 'only applies': $(<"$tmpdir/$sub.err")"
done

# --- 7. Regression: non-strict empty scope still exits 0 silently ---
set +e
"$QUERY_SH" get-cash-balance \
  --scope-type account \
  --scope-value "No Such Account" \
  >"$tmpdir/silent.out" 2>"$tmpdir/silent.err"
status=$?
set -e
[[ "$status" -eq 0 ]] || fail "non-strict empty scope exited $status, expected 0"
[[ "$(<"$tmpdir/silent.out")" == "0.0" ]] \
  || fail "non-strict empty scope did not print 0.0"
[[ ! -s "$tmpdir/silent.err" ]] \
  || fail "non-strict empty scope wrote stderr: $(<"$tmpdir/silent.err")"

# --- 8. --strict-scope without scope pair: exit 1 (usage error) ---
set +e
"$QUERY_SH" list-holdings --strict-scope \
  >/dev/null 2>"$tmpdir/missing_scope.err"
status=$?
set -e
[[ "$status" -eq 1 ]] || fail "strict-scope w/o scope exited $status, expected 1"
grep -q 'requires --scope-type' "$tmpdir/missing_scope.err" \
  || fail "missing-scope stderr drift: $(<"$tmpdir/missing_scope.err")"

printf 'PASS  --strict-scope validation across scoped + non-scoped subcommands\n'
