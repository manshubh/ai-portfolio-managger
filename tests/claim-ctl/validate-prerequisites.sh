#!/usr/bin/env bash
# validate-prerequisites.sh — M1.8: phase-4/5 prerequisite-gate cases.
# SPEC §7.3, §10.5, §10.6, §18.8. M1.5 plan §verification.
set -euo pipefail
# shellcheck source=./_test-lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/_test-lib.sh"

VP="${SCRIPTS_DIR}/validate-prerequisites.sh"

reset_stocks() {
  rm -rf "${TEST_ROOT}/temp"
  seed_stocks_dir
}

case_usage_no_args() {
  set +e; "$VP" 2>/dev/null; local rc=$?; set -e
  assert_eq 2 "$rc" "no args -> exit 2" || return 1
}

case_usage_bad_phase() {
  set +e; "$VP" 6 2>/dev/null; local rc=$?; set -e
  assert_eq 2 "$rc" "phase=6 -> exit 2" || return 1
}

case_missing_stocks_dir() {
  rm -rf "${TEST_ROOT}/temp"
  set +e; "$VP" 4 2>/dev/null; local rc=$?; set -e
  assert_eq 2 "$rc" "missing stocks dir -> exit 2" || return 1
}

case_empty_stocks_dir() {
  reset_stocks
  set +e; "$VP" 4 2>/dev/null; local rc=$?; set -e
  assert_eq 2 "$rc" "empty stocks dir -> exit 2" || return 1
}

case_phase4_pass() {
  reset_stocks
  write_stock_file "INFY.NS" $'[Fund]\n[Valu]\nbody\n'
  "$VP" 4
}

case_phase4_fail_missing_valu() {
  reset_stocks
  write_stock_file "INFY.NS" $'[Fund]\nbody\n'
  set +e; "$VP" 4 2>/dev/null; local rc=$?; set -e
  assert_eq 1 "$rc" "missing [Valu] -> exit 1" || return 1
}

case_phase5_pass() {
  reset_stocks
  write_stock_file "INFY.NS" $'## Scoring\n'
  "$VP" 5
}

case_phase5_fail_missing_scoring() {
  reset_stocks
  write_stock_file "INFY.NS" $'no scoring header\n'
  set +e; "$VP" 5 2>/dev/null; local rc=$?; set -e
  assert_eq 1 "$rc" "missing ## Scoring -> exit 1" || return 1
}

test_setup_root

test_case "usage: no args"                       case_usage_no_args
test_case "usage: bad phase number"              case_usage_bad_phase
test_case "missing stocks dir"                   case_missing_stocks_dir
test_case "empty stocks dir"                     case_empty_stocks_dir
test_case "phase 4 pass"                         case_phase4_pass
test_case "phase 4 fail (missing [Valu])"        case_phase4_fail_missing_valu
test_case "phase 5 pass"                         case_phase5_pass
test_case "phase 5 fail (missing ## Scoring)"    case_phase5_fail_missing_scoring

test_summary_and_exit
