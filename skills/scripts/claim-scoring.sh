#!/usr/bin/env bash
# claim-scoring.sh — Phase 4 atomic ticker claim. SPEC §10.5, §18.8.
# Usage: claim-scoring.sh <batch-size> <agent-id>
set -euo pipefail
# shellcheck source=./_claim-common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_claim-common.sh"
CLAIM_ROOT="${REPO_ROOT}/temp/research/scoring-claims"
_claim_batch "$@"
