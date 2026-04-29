#!/usr/bin/env bash
# stale-reclaim.sh — M1.7: aged .claimed gets reclaimed; fresh ones do not.
# SPEC §10.3. Investigation §4.
set -euo pipefail
# shellcheck source=./_test-lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/_test-lib.sh"

test_setup_root
CLAIMS_DIR="${TEST_ROOT}/temp/research/claims"
seed_claim_dirs "$CLAIMS_DIR" T01 T02 T03

# Claim all 3 tickers as agent-A. claim-stocks prints them on stdout; ignore.
"${SCRIPTS_DIR}/claim-stocks.sh" 3 agent-A > /dev/null

assert_file_exists "${CLAIMS_DIR}/T01/.claimed" "T01 claimed"
assert_file_exists "${CLAIMS_DIR}/T02/.claimed" "T02 claimed"
assert_file_exists "${CLAIMS_DIR}/T03/.claimed" "T03 claimed"

# Backdate T01 to 31 min ago (> 30 min default threshold).
ts=$(date_minutes_ago 31)
touch -t "$ts" "${CLAIMS_DIR}/T01/.claimed"

# Reclaim with the SPEC §10.3 default 30-min threshold (passed explicitly to
# avoid coupling the test to the library's default constant).
"${SCRIPTS_DIR}/reclaim-stale.sh" 30

assert_file_missing "${CLAIMS_DIR}/T01/.claimed" "T01 .claimed reclaimed"
assert_file_exists  "${CLAIMS_DIR}/T02/.claimed" "T02 .claimed survived"
assert_file_exists  "${CLAIMS_DIR}/T03/.claimed" "T03 .claimed survived"

# A fresh agent claiming a batch of 3 should pick up exactly the freed ticker.
new_claims=$("${SCRIPTS_DIR}/claim-stocks.sh" 3 agent-B)
assert_eq "T01" "$new_claims" "agent-B re-claims exactly the aged ticker"

printf 'stale-reclaim: PASS\n'
