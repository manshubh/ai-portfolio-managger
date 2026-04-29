#!/usr/bin/env bash
# check-persona-progress.sh — Phase 5 single-line progress summary. SPEC §18.8.
# Usage: check-persona-progress.sh
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_claim-common.sh"
# shellcheck disable=SC2034  # consumed by _claim-common.sh
CLAIM_ROOT="${REPO_ROOT}/temp/research/persona-claims"
_claim_check_progress
