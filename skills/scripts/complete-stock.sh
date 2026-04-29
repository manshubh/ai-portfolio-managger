#!/usr/bin/env bash
# complete-stock.sh — Phase 2 mark ticker(s) complete. SPEC §10.3, §18.8.
# Usage: complete-stock.sh <ticker> [<ticker>...]
set -euo pipefail
# shellcheck source=./_claim-common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_claim-common.sh"
CLAIM_ROOT="${REPO_ROOT}/temp/research/claims"
_claim_complete "$@"
