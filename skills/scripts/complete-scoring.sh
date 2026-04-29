#!/usr/bin/env bash
# complete-scoring.sh — Phase 4 mark ticker(s) scoring-complete. SPEC §10.5, §18.8.
# Usage: complete-scoring.sh <ticker> [<ticker>...]
# Rejects (non-zero, no .done written) if the stock file lacks a `## Scoring` header.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_claim-common.sh"

_validate_scoring_header() {
  local stock_file="$1"
  grep -qE '^## Scoring[[:space:]]*$' "$stock_file"
}

# shellcheck disable=SC2034  # consumed by _claim-common.sh
CLAIM_ROOT="${REPO_ROOT}/temp/research/scoring-claims"
# shellcheck disable=SC2034  # consumed by _claim-common.sh
CLAIM_VALIDATOR=_validate_scoring_header
_claim_complete "$@"
