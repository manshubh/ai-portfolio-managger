#!/usr/bin/env bash
# reclaim-persona-stale.sh — Phase 5 release stale persona claims. SPEC §10.6, §18.8.
# Usage: reclaim-persona-stale.sh [<minutes>]   # default 30
set -euo pipefail
# shellcheck source=./_claim-common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_claim-common.sh"
CLAIM_ROOT="${REPO_ROOT}/temp/research/persona-claims"
_claim_reclaim_stale "$@"
