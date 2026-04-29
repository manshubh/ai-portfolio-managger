#!/usr/bin/env bash
# check-progress.sh — Phase 2 single-line progress summary. SPEC §18.8.
# Usage: check-progress.sh
set -euo pipefail
# shellcheck source=./_claim-common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_claim-common.sh"
CLAIM_ROOT="${REPO_ROOT}/temp/research/claims"
_claim_check_progress
