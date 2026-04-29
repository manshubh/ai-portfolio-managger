#!/usr/bin/env bash
# complete-persona.sh — Phase 5 mark ticker(s) persona-cross-check-complete. SPEC §10.6, §18.8.
# Usage: complete-persona.sh <ticker> [<ticker>...]
# Rejects (non-zero, no .done written) if the stock file lacks a `## Persona Cross-Check` header.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_claim-common.sh"

_validate_persona_header() {
  local stock_file="$1"
  grep -qE '^## Persona Cross-Check[[:space:]]*$' "$stock_file"
}

# shellcheck disable=SC2034  # consumed by _claim-common.sh
CLAIM_ROOT="${REPO_ROOT}/temp/research/persona-claims"
# shellcheck disable=SC2034  # consumed by _claim-common.sh
CLAIM_VALIDATOR=_validate_persona_header
_claim_complete "$@"
