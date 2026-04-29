#!/usr/bin/env bash
# reclaim-scoring-stale.sh — Phase 4 release stale scoring claims. SPEC §10.5, §18.8.
# Usage: reclaim-scoring-stale.sh [<minutes>]   # default 30
set -euo pipefail
# shellcheck source=./_claim-common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_claim-common.sh"
CLAIM_ROOT="${REPO_ROOT}/temp/research/scoring-claims"
_claim_reclaim_stale "$@"
