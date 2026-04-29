#!/usr/bin/env bash
# run-all.sh — run every tests/claim-ctl/*.sh except _* and itself.
# Exit non-zero if any single test script exits non-zero.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

failed=0
total=0
for t in *.sh; do
  case "$t" in
    _*|run-all.sh) continue ;;
  esac
  total=$((total + 1))
  printf '\n=== %s ===\n' "$t"
  if bash "./$t"; then
    :
  else
    failed=$((failed + 1))
  fi
done

printf '\n%d/%d test scripts passed\n' "$((total - failed))" "$total"
[[ "$failed" -eq 0 ]] || exit 1
