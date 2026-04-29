#!/usr/bin/env bash
# check-scoring-progress.sh — Phase 4 single-line progress summary. SPEC §18.8.
# Usage: check-scoring-progress.sh
set -euo pipefail
# shellcheck source=./_claim-common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_claim-common.sh"
CLAIM_ROOT="${REPO_ROOT}/temp/research/scoring-claims"
_claim_check_progress
