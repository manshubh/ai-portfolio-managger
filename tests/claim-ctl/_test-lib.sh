# shellcheck shell=bash
# _test-lib.sh — shared fixtures + assertions for tests/claim-ctl/*.sh.
#
# Sourced only — no shebang, no `main`. See plans/M1/M1.6-1.8-claim-ctl-tests.md.
#
# Two call patterns:
#   1. Single-scenario tests (concurrent.sh, stale-reclaim.sh):
#        bare `assert_*` calls. Failure trips set -e and exits 1.
#   2. Multi-case tests (complete-validation.sh, validate-prerequisites.sh):
#        wrap each case in `test_case <name> <fn>`. Inside the case fn use
#        `assert_* || return 1` so one failure does not kill the suite.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPTS_DIR="${REPO_ROOT}/skills/scripts"

TEST_PASS=0
TEST_FAIL=0
TEST_ROOT=""

# ---- temp root + cleanup ---------------------------------------------------

test_setup_root() {
  TEST_ROOT="$(mktemp -d)"
  export CLAIM_CTL_ROOT="$TEST_ROOT"
  trap '_test_cleanup' EXIT INT TERM
}

_test_cleanup() {
  if [[ -n "${TEST_ROOT:-}" && -d "$TEST_ROOT" ]]; then
    rm -rf "$TEST_ROOT"
  fi
}

# ---- fixture seeders -------------------------------------------------------

seed_claim_dirs() {
  # seed_claim_dirs <claim-root> <ticker>...
  local root="$1"; shift
  mkdir -p "$root"
  local t
  for t in "$@"; do
    mkdir -p "${root}/${t}"
  done
}

seed_stocks_dir() {
  mkdir -p "${TEST_ROOT}/temp/research/stocks"
}

write_stock_file() {
  # write_stock_file <ticker> <content-with-newlines>
  printf '%s' "$2" > "${TEST_ROOT}/temp/research/stocks/${1}.md"
}

preclaim() {
  # preclaim <claim-root> <ticker> [<agent-id>]
  # Pre-creates a .claimed sentinel so complete-* can run without first
  # going through claim-stocks. Bypasses the noclobber primitive on purpose:
  # we are testing complete-*, not claim-*.
  local root="$1" ticker="$2" agent_id="${3:-agent-T}"
  mkdir -p "${root}/${ticker}"
  printf 'agent_id=%s\nclaimed_at_epoch=%s\n' \
    "$agent_id" "$(date +%s)" > "${root}/${ticker}/.claimed"
}

# ---- BSD/GNU date compat ---------------------------------------------------

date_minutes_ago() {
  # date_minutes_ago <minutes>  -> stdout: YYYYMMDDHHMM.SS for `touch -t`
  local mins="$1"
  if date -v-1M +%s >/dev/null 2>&1; then
    date -v-"${mins}"M +"%Y%m%d%H%M.%S"     # BSD (macOS host)
  else
    date -d "${mins} minutes ago" +"%Y%m%d%H%M.%S"  # GNU (container)
  fi
}

# ---- assertions ------------------------------------------------------------

assert_eq() {
  # assert_eq <expected> <actual> <message>
  if [[ "$1" == "$2" ]]; then return 0; fi
  printf '  assert_eq failed: %s\n    expected: %q\n    actual:   %q\n' \
    "$3" "$1" "$2" >&2
  return 1
}

assert_file_exists() {
  if [[ -e "$1" ]]; then return 0; fi
  printf '  assert_file_exists failed: %s (no file: %s)\n' "$2" "$1" >&2
  return 1
}

assert_file_missing() {
  if [[ ! -e "$1" ]]; then return 0; fi
  printf '  assert_file_missing failed: %s (unexpected file: %s)\n' "$2" "$1" >&2
  return 1
}

# ---- multi-case wrapper ----------------------------------------------------

test_case() {
  # test_case <name> <fn>
  local name="$1" fn="$2"
  if "$fn"; then
    printf 'PASS  %s\n' "$name"
    TEST_PASS=$((TEST_PASS + 1))
  else
    printf 'FAIL  %s\n' "$name" >&2
    TEST_FAIL=$((TEST_FAIL + 1))
  fi
}

test_summary_and_exit() {
  printf '\n%d passed, %d failed\n' "$TEST_PASS" "$TEST_FAIL"
  if [[ "$TEST_FAIL" -gt 0 ]]; then exit 1; fi
  exit 0
}
