#!/usr/bin/env bash
# run-all.sh - run every tests/wealthfolio_query/test_*.sh script,
# then assert every named-query slug in skills/sql/wealthfolio-queries.sql is
# referenced by at least one test or wrapper source (loose coverage check).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
REPO_ROOT="$(cd ../.. && pwd)"
SQL_FILE="$REPO_ROOT/skills/sql/wealthfolio-queries.sql"

failed=0
total=0
for t in test_*.sh; do
  [[ -e "$t" ]] || continue
  total=$((total + 1))
  printf '\n=== %s ===\n' "$t"
  if bash "./$t"; then
    :
  else
    failed=$((failed + 1))
  fi
done

# Slug coverage (loose): every `-- name: <slug>` must appear in at least one
# test_*.sh or wrapper source. Failure surface is an uncovered slug.
printf '\n=== slug-coverage ===\n'
total=$((total + 1))
slug_fail=0
slugs="$(grep -oE '^-- name: \S+' "$SQL_FILE" | awk '{print $3}')"
search_paths=(
  test_*.sh
  "$REPO_ROOT/skills/wealthfolio_query/query.sh"
  "$REPO_ROOT/skills/wealthfolio_query/query.py"
  "$REPO_ROOT/skills/wealthfolio_query/export_snapshot.py"
  "$REPO_ROOT/skills/wealthfolio_query/portfolio_twr.py"
)
for slug in $slugs; do
  if ! grep -qF "$slug" "${search_paths[@]}" 2>/dev/null; then
    printf 'FAIL  slug %q not referenced in any test or wrapper source\n' "$slug" >&2
    slug_fail=1
  fi
done
if [[ "$slug_fail" -eq 0 ]]; then
  printf 'PASS  slug coverage (%s slugs)\n' "$(echo "$slugs" | wc -w | tr -d ' ')"
else
  failed=$((failed + 1))
fi

printf '\n%d/%d test scripts passed\n' "$((total - failed))" "$total"
[[ "$failed" -eq 0 ]] || exit 1
