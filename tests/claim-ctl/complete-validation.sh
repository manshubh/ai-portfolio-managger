#!/usr/bin/env bash
# complete-validation.sh — M1.8: complete-scoring / complete-persona header gates.
# SPEC §10.5, §10.6. Investigation §4.
set -euo pipefail
# shellcheck source=./_test-lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/_test-lib.sh"

test_setup_root
seed_stocks_dir
SCORING_DIR="${TEST_ROOT}/temp/research/scoring-claims"
PERSONA_DIR="${TEST_ROOT}/temp/research/persona-claims"

case_scoring_missing() {
  preclaim "$SCORING_DIR" "INFY.NS"
  write_stock_file "INFY.NS" $'[Fund]\nbody\n'
  set +e
  "${SCRIPTS_DIR}/complete-scoring.sh" INFY.NS 2>/dev/null
  local rc=$?
  set -e
  assert_eq 1 "$rc" "complete-scoring exits 1 on missing header" || return 1
  assert_file_missing "${SCORING_DIR}/INFY.NS/.done" "no .done written" || return 1
}

case_scoring_ok() {
  preclaim "$SCORING_DIR" "TCS.NS"
  write_stock_file "TCS.NS" $'[Fund]\nbody\n## Scoring\nfoo\n'
  "${SCRIPTS_DIR}/complete-scoring.sh" TCS.NS
  assert_file_exists "${SCORING_DIR}/TCS.NS/.done" ".done written" || return 1
}

case_persona_missing() {
  preclaim "$PERSONA_DIR" "HDFC.NS"
  write_stock_file "HDFC.NS" $'## Scoring\nfoo\n'
  set +e
  "${SCRIPTS_DIR}/complete-persona.sh" HDFC.NS 2>/dev/null
  local rc=$?
  set -e
  assert_eq 1 "$rc" "complete-persona exits 1 on missing header" || return 1
  assert_file_missing "${PERSONA_DIR}/HDFC.NS/.done" "no .done written" || return 1
}

case_persona_ok() {
  preclaim "$PERSONA_DIR" "RELIANCE.NS"
  write_stock_file "RELIANCE.NS" $'## Scoring\nfoo\n## Persona Cross-Check\nbar\n'
  "${SCRIPTS_DIR}/complete-persona.sh" RELIANCE.NS
  assert_file_exists "${PERSONA_DIR}/RELIANCE.NS/.done" ".done written" || return 1
}

test_case "complete-scoring missing header"   case_scoring_missing
test_case "complete-scoring ok"               case_scoring_ok
test_case "complete-persona missing header"   case_persona_missing
test_case "complete-persona ok"               case_persona_ok

test_summary_and_exit
