# Directory Contract

> Artifact mapping for `temp/research/*` files across the 7 runtime phases, enforcing I/O boundaries as specified in SPEC §2 principle 4 and §10.

| Artifact Path | Producer Phase(s) | Consumer Phase(s) | Authoritative Owner | Description |
|---|---|---|---|---|
| `temp/research/manifest.md` | Phase 1 | Phase 7 | Phase 1 (Setup) | Run metadata, snapshot summary, warning summary, highlights from previous runs. |
| `temp/research/portfolio-snapshot.csv` | Phase 1 | Phase 2, 6, 7 | Phase 1 (Setup) | Frozen copy of portfolio holdings to guarantee consistency across concurrent research processes. |
| `temp/research/warnings/corp-actions.md` | Phase 1 | Phase 7 | `corp-actions-monitor` | Informational feed of upcoming/recent corporate actions for the holdings. |
| `temp/research/claims/` | Phase 1, 2, 4, 5 | Phase 2, 4, 5 | `claim-ctl` | Lock directories ensuring atomic, partitionable processing for concurrent parallel agents. |
| `temp/research/stocks/{TICKER}.md` | Phase 2, 4, 5, 6 | Phase 3, 4, 5, 6, 7 | Phase Prompts (2-6) | Core stock file accumulating data through the pipeline: `[Tag]` data (Ph2) → `## Scoring` (Ph4) → `## Persona Cross-Check` (Ph5) → `## Debate` (Ph6). |
| `temp/research/verification-notes.md` | Phase 3 | Phase 7 | Phase 3 (Verification) | Log reporting any formatting, completeness, or rule violations found in the stock files. |
| `temp/research/debate-queue.md` | Phase 6 | Phase 6 | `select-debate.sh` | List of tickers flagged for selective debate based on the criteria in SPEC §11.2. |
| `temp/research/concentration-check.md` | Phase 6 | Phase 6, 7 | `scoring-engine` | Portfolio concentration metrics (HHI, volatility-adjusted limits, and top correlation pairs). |
| `temp/research/portfolio-analysis.md` | Phase 6 | Phase 7 | Phase 6 (Synthesis) | Executive summary, action plan, and synthesized insights across the portfolio. |
| `temp/research/report_data.json` | Phase 7 | `ledger-ctl` | Phase 7 (Report) | Structured JSON payload describing the analysis for secure append to the ledger without markdown parser brittleness. |
