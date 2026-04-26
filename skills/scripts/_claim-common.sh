# shellcheck shell=bash
# _claim-common.sh — shared library for claim-ctl phase shims.
#
# Sourced only — no shebang and no `main`. See plans/M1/M1.1-claim-common-lib.md
# and research/milestones/M1-investigation.md for the full design. Shim contracts
# (claim-stocks.sh, complete-scoring.sh, …) live in M1.2/M1.3/M1.4 and call the
# `_claim_*` public API below.
#
# SPEC §6.7 (atomic O_EXCL via noclobber), §10.3 / §10.5 / §10.6 (per-phase
# behavior), §17 (claim-namespace dirs), §18.8 (sub-command signatures).

set -euo pipefail

# REPO_ROOT — derived once from the library's own script location. Tests
# override via CLAIM_CTL_ROOT to redirect into an isolated temp tree
# (investigation §6.1).
REPO_ROOT="${CLAIM_CTL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

# Default stale threshold in minutes (SPEC §10.3). Shim CLI args override.
: "${CLAIM_STALE_MINUTES_DEFAULT:=30}"

# ---- internal helpers -------------------------------------------------------

_claim_assert_root() {
  if [[ -z "${CLAIM_ROOT:-}" ]]; then
    printf 'claim-ctl: CLAIM_ROOT is not set\n' >&2
    return 2
  fi
  if [[ ! -d "$CLAIM_ROOT" ]]; then
    printf 'claim-ctl: CLAIM_ROOT does not exist: %s\n' "$CLAIM_ROOT" >&2
    return 2
  fi
}

_claim_payload() {
  # _claim_payload <claimed|done> <agent_id>
  local kind="$1" agent_id="$2" ts_key
  case "$kind" in
    claimed) ts_key="claimed_at_epoch" ;;
    done)    ts_key="completed_at_epoch" ;;
    *) printf 'claim-ctl: bad payload kind: %s\n' "$kind" >&2; return 2 ;;
  esac
  printf 'agent_id=%s\n%s=%s\n' "$agent_id" "$ts_key" "$(date +%s)"
  if [[ -n "${CLAIM_MODEL_ID:-}" ]]; then
    printf 'model_id=%s\n' "$CLAIM_MODEL_ID"
  fi
}

_claim_one() {
  # _claim_one <ticker_dir> <agent_id> -> 0 on win, 1 on loss.
  # The noclobber subshell scopes the option so it never leaks to the caller
  # (investigation §6.7). The kernel guarantees exactly one creator.
  local ticker_dir="$1" agent_id="$2"
  local claimed="${ticker_dir}/.claimed"
  if ( set -o noclobber; _claim_payload claimed "$agent_id" > "$claimed" ) 2>/dev/null; then
    return 0
  fi
  return 1
}

_claim_owner_of() {
  # Best-effort agent_id read from a .claimed payload. Empty string on empty
  # file (SIGKILL between O_EXCL and printf — investigation §5).
  local f="$1"
  if [[ -s "$f" ]]; then
    awk -F= '/^agent_id=/ { print $2; exit }' "$f"
  fi
}

# ---- public API: claim ------------------------------------------------------

_claim_batch() {
  # _claim_batch <batch-size> <agent-id>
  if [[ $# -ne 2 ]]; then
    printf 'usage: claim-* <batch-size> <agent-id>\n' >&2
    return 2
  fi
  local batch_size="$1" agent_id="$2"
  if ! [[ "$batch_size" =~ ^[0-9]+$ ]] || [[ "$batch_size" -le 0 ]]; then
    printf 'claim-ctl: batch-size must be a positive integer (got %s)\n' "$batch_size" >&2
    return 2
  fi
  _claim_assert_root || return $?

  local ticker_dir won=0
  while IFS= read -r ticker_dir; do
    if [[ "$won" -ge "$batch_size" ]]; then
      break
    fi
    if _claim_one "$ticker_dir" "$agent_id"; then
      printf '%s\n' "${ticker_dir##*/}"
      won=$((won + 1))
    fi
  done < <(
    find "$CLAIM_ROOT" -mindepth 1 -maxdepth 1 -type d \
      ! -exec test -e '{}/.claimed' \; \
      ! -exec test -e '{}/.done' \; \
      -print | sort
  )
  return 0
}

# ---- public API: complete ---------------------------------------------------

_claim_complete() {
  # _claim_complete <ticker> [<ticker>...]
  # Multi-arg partial-failure: continue past failures, exit non-zero if any
  # ticker failed (investigation §7.2).
  if [[ $# -lt 1 ]]; then
    printf 'usage: complete-* <ticker> [<ticker>...]\n' >&2
    return 2
  fi
  _claim_assert_root || return $?

  local ticker any_failed=0
  for ticker in "$@"; do
    local ticker_dir="${CLAIM_ROOT}/${ticker}"
    local claimed="${ticker_dir}/.claimed"
    local done_file="${ticker_dir}/.done"
    local stock_file="${REPO_ROOT}/temp/research/stocks/${ticker}.md"

    if [[ ! -d "$ticker_dir" ]]; then
      printf 'claim-ctl: no such ticker dir: %s\n' "$ticker_dir" >&2
      any_failed=1
      continue
    fi
    if [[ ! -e "$claimed" ]]; then
      printf 'claim-ctl: %s has no .claimed (cannot complete an unclaimed ticker)\n' "$ticker" >&2
      any_failed=1
      continue
    fi
    if [[ -e "$done_file" ]]; then
      printf 'claim-ctl: %s already completed; skipping\n' "$ticker" >&2
      continue
    fi
    if [[ -n "${CLAIM_VALIDATOR:-}" ]]; then
      if ! "$CLAIM_VALIDATOR" "$stock_file"; then
        printf 'claim-ctl: %s failed completion validation (%s on %s)\n' \
          "$ticker" "$CLAIM_VALIDATOR" "$stock_file" >&2
        any_failed=1
        continue
      fi
    fi

    _claim_payload "done" "$(_claim_owner_of "$claimed")" > "$done_file"
  done

  return "$any_failed"
}

# ---- public API: progress ---------------------------------------------------

_claim_check_progress() {
  _claim_assert_root || return $?
  local stale_threshold="${1:-$CLAIM_STALE_MINUTES_DEFAULT}"
  local total=0 claimed=0 completed=0 stale=0 available
  local d
  while IFS= read -r d; do
    total=$((total + 1))
    if [[ -e "${d}/.done" ]]; then
      completed=$((completed + 1))
    elif [[ -e "${d}/.claimed" ]]; then
      claimed=$((claimed + 1))
      if [[ -n "$(find "${d}/.claimed" -mmin "+${stale_threshold}" 2>/dev/null)" ]]; then
        stale=$((stale + 1))
      fi
    fi
  done < <(find "$CLAIM_ROOT" -mindepth 1 -maxdepth 1 -type d)
  available=$((total - completed - claimed))
  printf 'total=%d available=%d claimed=%d completed=%d stale=%d\n' \
    "$total" "$available" "$claimed" "$completed" "$stale"
}

# ---- public API: reclaim stale ---------------------------------------------

_claim_reclaim_stale() {
  # _claim_reclaim_stale [<minutes>]
  local minutes="${1:-$CLAIM_STALE_MINUTES_DEFAULT}"
  if ! [[ "$minutes" =~ ^[0-9]+$ ]]; then
    printf 'claim-ctl: stale-minutes must be a non-negative integer (got %s)\n' "$minutes" >&2
    return 2
  fi
  _claim_assert_root || return $?
  # `-mmin +<n>` and `-delete` are supported on both BSD (macOS host) and GNU
  # (Debian container) find — investigation §1, §4.
  find "$CLAIM_ROOT" -mindepth 2 -maxdepth 2 -type f -name '.claimed' \
    -mmin "+${minutes}" -delete
}
