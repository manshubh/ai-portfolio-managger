#!/usr/bin/env bash
# reclaim-stale.sh — Phase 2 release stale claims. SPEC §10.3, §18.8.
# Usage: reclaim-stale.sh [<minutes>]   # default 30
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_claim-common.sh"
# shellcheck disable=SC2034  # consumed by _claim-common.sh
CLAIM_ROOT="${REPO_ROOT}/temp/research/claims"
_claim_reclaim_stale "$@"
