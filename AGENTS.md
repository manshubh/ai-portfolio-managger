# AI Portfolio Manager — Agent Constitution

Runtime rules for the portfolio research agent. Every session touching this repo must follow these invariants. Full text in [docs/SPEC.md §19](docs/SPEC.md).

## Critical Invariants (must never be violated)

1. **Never write the Wealthfolio DB.** Read-only via `skills/wealthfolio-query/query.sh`. Writes go through the Wealthfolio UI. (SPEC §19 inv 11)
2. **Phase 1 snapshot is frozen.** `temp/research/portfolio-snapshot.csv` is authoritative for the run — later phases add context but never rewrite it. (SPEC §19 inv 12)
3. **Deterministic math, LLM narrative.** Scores, HHI, alpha, and persona sub-scores come from `scoring-engine`. The LLM writes rationale referencing those values; it never re-derives them. (SPEC §19 inv 15)
4. **Immediate actions capped at 2 per report.** Reserved for confirmed thesis breaks only. (SPEC §19 inv 10)
5. **Never fabricate data.** Missing → "N/A" or "Data not found", always with a source citation. (SPEC §19 inv 1)

## Remaining Invariants

Enforced by phase prompts — referenced by number, not duplicated here.

- **Inv 2** Always cite sources: ticker, access date, tier (1=filings, 2=aggregators, 3=news, 4=social).
- **Inv 3** Follow the MCP fallback chain (§15.2) fully before giving up.
- **Inv 4** Report serves the user's philosophy, not generic advice.
- **Inv 5** Context ledger ≤100 lines — continuity, not a second report.
- **Inv 6** Filesystem is the inter-phase bridge (`temp/research/`). No live re-fetching after Phase 1.
- **Inv 7** Dense `[Tag]` output format — no tables or bullets inside data lines.
- **Inv 8** Fundamentals-first — valuation informs accumulation pace, not conviction.
- **Inv 9** Price drops are review triggers, not sell signals.
- **Inv 13** Missing thesis in `theses.yaml` is empty string, not an error.
- **Inv 14** SQL queries versioned with Wealthfolio release; upgrades require explicit review.
- **Inv 16** `my-philosophy` is always the first persona; rotating personas are sparring partners.
- **Inv 17** Debate is selective — trigger rules (§11.2) are mandatory; universal debate is forbidden.
- **Inv 18** Corp-actions feed is informational and non-blocking.
- **Inv 19** Ledger is append-only — rows are never updated or deleted.
- **Inv 20** Philosophy hash tracked per run; changes prompt re-baselining confirmation.
- **Inv 21** MCP staleness triggers fallback to Tier B before accepting stale data.

## Directory Layout

See [.agents/directory-contract.md](.agents/directory-contract.md) for the canonical artifact-to-phase mapping.

## Phase Commands

| Command | Phase | Key output |
|---------|-------|------------|
| `/phase1` | Setup | `portfolio-snapshot.csv`, manifest, corp-actions |
| `/phase2` | Research | `temp/research/stocks/{TICKER}.md` |
| `/phase3` | Verification | `verification-notes.md` |
| `/phase4` | Scoring | `## Scoring` block per stock |
| `/phase5` | Persona Cross-Check | `## Persona Cross-Check` block per stock |
| `/phase6` | Synthesis + Debate | `portfolio-analysis.md` |
| `/phase7` | Report + Ledger | `reports/{market}/YYYY-MM-DD-weekly-report.md` |
