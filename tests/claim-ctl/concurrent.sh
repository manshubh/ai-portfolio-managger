#!/usr/bin/env bash
# concurrent.sh — M1.6: 3 shells race for 15 ticker claims; assert clean partition.
# SPEC §6.7. Investigation §4.
set -euo pipefail
# shellcheck source=./_test-lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/_test-lib.sh"

test_setup_root
CLAIMS_DIR="${TEST_ROOT}/temp/research/claims"
seed_claim_dirs "$CLAIMS_DIR" \
  T01 T02 T03 T04 T05 T06 T07 T08 T09 T10 T11 T12 T13 T14 T15

out_a="${TEST_ROOT}/out-A.txt"
out_b="${TEST_ROOT}/out-B.txt"
out_c="${TEST_ROOT}/out-C.txt"

# 0.1s settle so all 3 background shells reach the claim near-simultaneously.
# Outcome assertions don't depend on this — even if one finishes first, a
# broken O_EXCL still surfaces via duplicate ticker output.
(sleep 0.1; "${SCRIPTS_DIR}/claim-stocks.sh" 5 agent-A) >"$out_a" 2>&1 &
(sleep 0.1; "${SCRIPTS_DIR}/claim-stocks.sh" 5 agent-B) >"$out_b" 2>&1 &
(sleep 0.1; "${SCRIPTS_DIR}/claim-stocks.sh" 5 agent-C) >"$out_c" 2>&1 &
wait

# (1) Coverage at the filesystem layer.
total_claimed=$(find "$CLAIMS_DIR" -mindepth 2 -maxdepth 2 -name '.claimed' | wc -l | tr -d ' ')
assert_eq 15 "$total_claimed" "exactly 15 .claimed files written"

# (2) Coverage at the output layer.
union_count=$(cat "$out_a" "$out_b" "$out_c" | sort -u | wc -l | tr -d ' ')
assert_eq 15 "$union_count" "union of claimed tickers has cardinality 15"

# (3) Exclusivity: no ticker printed by more than one shell.
duplicates=$(cat "$out_a" "$out_b" "$out_c" | sort | uniq -d | wc -l | tr -d ' ')
assert_eq 0 "$duplicates" "no ticker claimed by more than one agent"

# (4) Every .claimed payload has a recognized agent_id.
bad=0
while IFS= read -r f; do
  aid=$(awk -F= '/^agent_id=/ {print $2; exit}' "$f")
  case "$aid" in
    agent-A|agent-B|agent-C) ;;
    *) bad=$((bad + 1)) ;;
  esac
done < <(find "$CLAIMS_DIR" -mindepth 2 -maxdepth 2 -name '.claimed')
assert_eq 0 "$bad" "all .claimed payloads carry a known agent_id"

printf 'concurrent: PASS\n'
