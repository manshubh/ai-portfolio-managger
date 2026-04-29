#!/usr/bin/env bash
# complete-scoring.sh — Phase 4 mark ticker(s) scoring-complete. SPEC §10.5, §18.8.
# Usage: complete-scoring.sh <ticker> [<ticker>...]
# Rejects (non-zero, no .done written) if the stock file lacks a `## Scoring` header.
set -euo pipefail
# shellcheck source=./_claim-common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_claim-common.sh"

_validate_scoring_header() {
  local stock_file="$1"
  grep -qE '^## Scoring[[:space:]]*$' "$stock_file"
}

CLAIM_ROOT="${REPO_ROOT}/temp/research/scoring-claims"
CLAIM_VALIDATOR=_validate_scoring_header
_claim_complete "$@"
