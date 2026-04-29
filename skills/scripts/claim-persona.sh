#!/usr/bin/env bash
# claim-persona.sh — Phase 5 atomic ticker claim. SPEC §10.6, §18.8.
# Usage: claim-persona.sh <batch-size> <agent-id>
set -euo pipefail
# shellcheck source=./_claim-common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_claim-common.sh"
CLAIM_ROOT="${REPO_ROOT}/temp/research/persona-claims"
_claim_batch "$@"
