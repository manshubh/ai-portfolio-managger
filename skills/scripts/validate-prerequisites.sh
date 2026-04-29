#!/usr/bin/env bash
# validate-prerequisites.sh — pre-Phase 4/5 stock-file gate. SPEC §18.8.
# Usage: validate-prerequisites.sh <phase-number>
#   phase=4 → every temp/research/stocks/*.md must contain [Fund] AND [Valu]
#   phase=5 → every temp/research/stocks/*.md must contain ## Scoring header
# Exit 1 on missing prerequisites (offending tickers on stderr).
# Exit 2 on usage errors (bad phase arg, missing stocks dir, no stock files).
set -euo pipefail

usage() {
  printf 'usage: %s <phase-number>  (valid: 4, 5)\n' "$0" >&2
  exit 2
}

[[ $# -eq 1 ]] || usage
phase="$1"

REPO_ROOT="${CLAIM_CTL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
STOCKS_DIR="${REPO_ROOT}/temp/research/stocks"

case "$phase" in
  4) patterns=('^\[Fund\]' '^\[Valu\]') ;;
  5) patterns=('^## Scoring[[:space:]]*$') ;;
  *) usage ;;
esac

if [[ ! -d "$STOCKS_DIR" ]]; then
  printf 'validate-prerequisites: stocks dir does not exist: %s\n' "$STOCKS_DIR" >&2
  exit 2
fi

failed=0
found=0
while IFS= read -r f; do
  found=1
  ticker="$(basename "$f" .md)"
  for pat in "${patterns[@]}"; do
    if ! grep -qE "$pat" "$f"; then
      printf '%s: missing %s\n' "$ticker" "$pat" >&2
      failed=1
    fi
  done
done < <(find "$STOCKS_DIR" -mindepth 1 -maxdepth 1 -type f -name '*.md' | sort)

if [[ "$found" -eq 0 ]]; then
  printf 'validate-prerequisites: no stock files in %s\n' "$STOCKS_DIR" >&2
  exit 2
fi

exit "$failed"
