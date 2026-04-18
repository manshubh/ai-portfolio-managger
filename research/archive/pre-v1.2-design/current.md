# Portfolio Research Engine — Implementation Summary

> A self-contained description of this repository's current implementation. Written to be read **outside** the repo as research input for optimizing it into a complete portfolio manager.

---

## 1. What This Repository Is

A **weekly portfolio research engine** for equity markets (Indian NSE/BSE and US NYSE/NASDAQ) implemented entirely as **markdown instructions, prompt templates, and shell scripts** — no application code, no runtime, no dependencies, no API keys.

It is a *scaffolding* that an AI coding agent (Claude Code / Cursor / similar) executes turn-by-turn. The agent uses its own built-in tools (web search, file read/write, curl) to:

1. Fetch a user's live portfolio from a public Google Sheet
2. Research each holding (fundamentals, valuation, news, business story) with source-cited web searches
3. Score each stock on a fundamentals-first 0–11 composite system
4. Perform cross-stock portfolio-level gap analysis vs the user's written investment philosophy
5. Produce a dense, structured weekly research report and a rolling context ledger for the next run

It is **read-only research**: it never places trades, never touches a broker, never holds credentials. It outputs markdown reports.

### Current state in one sentence
A highly structured, multi-phase, parallelizable *research report generator* driven by AI agents that execute a prescriptive workflow defined by markdown files — not yet a "portfolio manager" in the transactional sense.

---

## 2. High-Level Architecture

### 2.1 Pipeline

```
Phase 1 (Setup)  →  Phase 2 (Research, parallel)  →  Phase 3 (Verification, optional)
                                                              ↓
                                      Phase 4 (Scoring, parallel)
                                                              ↓
                                      Phase 5 (Cross-Stock Synthesis)
                                                              ↓
                                      Phase 6 (Report Assembly)
                                                              ↓
                                  reports/{market}/YYYY-MM-DD-weekly-report.md
                                  context/{market}/last-run.md
```

Each phase is a separate agent session / prompt with a narrowly scoped responsibility. Phases communicate exclusively through files in `temp/research/` — the filesystem is the message bus.

### 2.2 Phase Responsibilities and Model Selection

| Phase | Responsibility | Suggested Model | Parallelizable |
|-------|----------------|-----------------|----------------|
| 1. Setup | Load prior context, fetch portfolio CSV, read philosophy, write manifest, create claim dirs | Haiku / Sonnet | No (single session) |
| 2. Research | Per-stock web research on fundamentals, valuation, news, business story; writes `{TICKER}.md` | Sonnet | **Yes** (batches of 10 via atomic claims) |
| 3. Verification (optional) | Read-only QA gate: completeness, format, recency, systematic data gaps | Haiku / Sonnet | No |
| 4. Scoring | Read research file, apply composite rubric, write `## Scoring` section with `[AI]` assessment | Sonnet / Opus | **Yes** (batches of 10 via separate claim dir) |
| 5. Synthesis | Full-portfolio gap analysis, action plan, executive summary | Opus | No (needs all stocks in context) |
| 6. Report Assembly | Mechanically assemble final report and context ledger — no new analysis | Sonnet | No |

### 2.3 Why This Shape

- **Separation of concerns** — each phase has one job; the scoring agent is forbidden from web searches, the synthesis agent is forbidden from re-scoring, the report agent is forbidden from generating new analysis.
- **Parallel fan-out for expensive steps** — Phases 2 and 4 (the token-heavy per-stock work) are sharded across multiple concurrent agent sessions using file-based atomic claims.
- **Token budget management** — the report is assembled in explicit batches of 12–15 stocks per tool call with a hard <300 line/call cap to avoid truncation.
- **Resumability** — an agent can crash mid-batch and any other session can reclaim abandoned work via `reclaim-*-stale.sh`.

---

## 3. Repository Layout

```
CLAUDE.md                            # Universal agent entry point (identity + quick start)
README.md                            # Human-facing documentation
agents.md                            # (referenced by README; same role as CLAUDE.md)

.agents/
├── workflows/
│   └── portfolio-research.md        # 6-phase overview with links to each phase file
└── portfolio-research/
    ├── phases/
    │   ├── phase-1-setup.md         # Fetch portfolio, build manifest, create claim dirs
    │   ├── phase-2-research.md      # Per-stock research agent instructions
    │   ├── phase-3-verification.md  # Optional QA gate
    │   ├── phase-4-scoring.md       # Per-stock scoring + AI assessment
    │   ├── phase-5-synthesis.md     # Portfolio-level gap analysis and action plan
    │   └── phase-6-report.md        # Report assembly + context ledger
    ├── frameworks/
    │   ├── research-methodology.md  # Search patterns, fallback chain, source tiers
    │   └── analysis-frameworks.md   # Fundamental checklist, scoring rubric, gap framework
    ├── guidelines/
    │   ├── rules.md                 # Mandatory rules for all phases
    │   └── quality-checklist.md     # Pre-publish validation gate
    ├── scripts/                     # Atomic claim system (shell)
    │   ├── claim-stocks.sh          # Phase 2 claim (noclobber)
    │   ├── complete-stock.sh        # Mark Phase 2 stock done
    │   ├── check-progress.sh        # Phase 2 progress monitor
    │   ├── reclaim-stale.sh         # Phase 2 crash recovery
    │   ├── claim-scoring.sh         # Phase 4 claim
    │   ├── complete-scoring.sh      # Mark Phase 4 stock done (validates `## Scoring` exists)
    │   ├── check-scoring-progress.sh
    │   ├── reclaim-scoring-stale.sh
    │   └── validate-prerequisites.sh
    └── templates/
        ├── weekly-report-template.md
        ├── stock-analysis-template.md
        ├── stock-research-output-template.md
        └── context-ledger-template.md

.claude/commands/                    # Slash command shims (phase1.md … phase6.md, progress.md)

config/
└── portfolio-url.md                 # Google Sheet URLs + CSV export URLs per market

input/
├── india/philosophy.md              # India investment philosophy (filled in)
└── us/philosophy.md                 # US philosophy (template with placeholders)

context/
├── india/last-run.md                # Rolling context ledger (auto-written by Phase 6)
└── us/last-run.md

reports/
├── india/YYYY-MM-DD-weekly-report.md
└── us/YYYY-MM-DD-weekly-report.md

temp/research/                       # Inter-phase scratch space (created per run)
├── manifest.md                      # Written by Phase 1 (portfolio + philosophy reference + per-stock theses)
├── stocks/{TICKER}.md               # Written by Phase 2; ## Scoring appended by Phase 4
├── claims/{TICKER}/{.claimed,.done} # Phase 2 atomic locks
├── scoring-claims/{TICKER}/{.claimed,.done} # Phase 4 atomic locks
├── verification-notes.md            # Phase 3 output
└── portfolio-analysis.md            # Phase 5 output
```

---

## 4. Inputs

### 4.1 Portfolio (Google Sheet)

Configured in `config/portfolio-url.md`. One section per market with three fields:
- Sheet URL (for human reference)
- CSV export URL (`…/export?format=csv&gid=…`)
- Column layout

**India column layout:**
```
Company Name, Google Ticker, Sector, Market Cap, Qty, Avg Buy Price,
LTP (Live), Invested, Current, Allocation(%), P/L %, Philosophy
```

**US column layout:**
```
Company Name, Ticker Symbol, Sector, Market Cap, Shares, Avg Buy Price,
Current Price, Invested, Current Value, Allocation(%), P/L %
```

The optional `Philosophy` column carries a **per-stock investment thesis** written by the user. When present it is propagated through the manifest and into the `[Phil] Thesis:` field of each stock's research file — used by the scoring agent as conviction context.

The CSV is fetched with `curl -sL` in Phase 1, validated (must contain a CSV header, must not be HTML/404), and parsed directly by the agent (no scripts allowed — explicit rule).

### 4.2 Investment Philosophy

`input/{market}/philosophy.md` is the **single source of truth** for what "belongs" in the portfolio. Every scoring and synthesis decision references it.

Key sections codified in the India philosophy (filled in):

- **Investment Goals** — long-term wealth creation (10+ year horizon), beat Nifty 50 by 3–5% annually, no dividend dependence.
- **Investment Ideology** — Quality-at-reasonable-price (GARP), **fundamentals-first**, avoid high leverage, 1–3+ year holding period, short-term technicals explicitly rejected, long-term price context (50w/100w MAs, 5Y PE history) used only for *accumulation timing*.
- **Stock Selection Criteria** — two separate threshold tables:
  - **Non-financial:** ROE >12%, ROCE >12%, D/E <1.0, Promoter >40%, Pledge <10%, Rev/Profit 3Y CAGR >10%, FCF positive, MCap >5,000 Cr.
  - **Banking/NBFC:** ROA >1%, ROE >12%, Net NPA <1.5%, CAR >15%, CASA >30% (banks), NIM >3%, Profit Growth >10%, Promoter >30%, Pledge <10%, MCap >5,000 Cr.
- **Business Story Criteria** (qualitative) — Sector Growth Runway, Competitive Moat, Management Quality, Capacity Expansion, Market Share Trajectory, Corporate Governance.
- **Risk Tolerance** — moderate-aggressive, 30% max drawdown, small-caps capped at 20%, -20% price drop is a **review trigger** not an exit.
- **Sector Allocation Targets** — no hard targets in India version; overconcentration is the flag.
- **Position Sizing** — max 8% per stock, min 2%, average 3–5%, top-5 ≤35%.
- **Exit Rules** — explicit lists of **Fundamental Exit Triggers**, **Price Drop Review Trigger** (20% drop = deep review, not automatic sell), **Trim Signals**, **Hold Through** situations.
- **Transition Guidelines** — gradual rebalancing over 3–6 months, ≤2 sells/week, prefer SIP-style accumulation (3–4 chunks), ≥6 month minimum holding.

The US philosophy file currently contains only a **template with placeholders** (`[X]%`, `[X]B`, etc.). It is not yet filled in.

### 4.3 Prior Context

`context/{market}/last-run.md` — a rolling ≤100-line ledger written at the end of each run containing:
- Run summary + portfolio snapshot
- Concerning alerts (table of flagged stocks)
- Opportunities (table)
- Open action items (carried forward until the portfolio shows evidence of action)
- Price levels to watch (only within 5–10% of current price)
- Philosophy alignment score + top gaps

The next run reads this file first. Deleting it resets memory.

---

## 5. Outputs

### 5.1 Per-Stock Research File (Phase 2 output, enriched by Phase 4)

`temp/research/stocks/{TICKER}.md` — a **dense, single-line-per-tag** format:

```
# {STOCK_NAME} ({TICKER})
[Overview] Sector: … | MCap: … | Qty: … | Avg: ₹… | LTP: ₹… | P/L: …% | Inv: … | Val: … | Alloc: …%
[Fund]     Rev YoY: …% (Q3 FY26) | Rev QoQ: … | PAT YoY: … | PAT QoQ: … | D/E: … | Prom: …% (Pledge: …%)
           | ROE: …% | ROCE: …% | OPM: …% | NPM: …%
           { banking/NBFC only: | GNPA | NNPA | CASA | NIM | ROA | CAR }
[Valu]     PE: … (5Y: L–H, Med: M) vs Sec: … | PB: … | FII: …% (Δ) | DII: …% (Δ)
           | 100d: … | 200d: … | Supp: … | Res: … | 52w: … (H: … L: …)
[Biz]      Runway: … | Moat: … | Mgmt: … | CapEx: … | Shr: …
[News]     {date}: {headline} ({source}) | …
[Phil]     Thesis: {user thesis or "—"} | Meets: ROE(18.3%), ROCE(23.8%), D/E(~0)…
           | Fails: PATGr(8.2%<10%)…
[Prev]     {diff vs last run, or "> No prior context for this stock."}
[Sources]  Fund: … | Valu: … | Biz: … | News: …
```

Then Phase 4 **appends**:

```
---
## Scoring
Score: {0-11} {Rating} [{HIGH|MEDIUM|LOW}]
Sub: F:{f}/4 | BS:{b}/2 | V:{v}/2 | N:{n}/1 | PF:{p}/2
Rationale: {1-sentence per sub-score, pipe-delimited}
Action: {Hold | Accumulate | Trim | Exit | Hold-with-Conviction}
[AI] {2–5 line analytical synthesis bridging all dimensions}
Notes: {any fundamentals-first adjustments or verification flags}
```

Hard rules: no markdown tables in the data block, no bulleted lists, 10–15 lines total, every metric carries a period annotation ("Q3 FY26", "FY25" — **"Latest"/"Current"/"TTM" are explicitly forbidden**).

### 5.2 Portfolio Analysis (Phase 5 output)

`temp/research/portfolio-analysis.md` — executive summary, score-distribution table, sector-allocation gap table, position-sizing violations, stock-quality mismatches, risk-profile assessment, missing opportunities, and the tiered **action plan**:

| Priority | Horizon | When to use | Cap |
|----------|---------|-------------|-----|
| Immediate | This week | **Only** confirmed fundamental thesis breaks | **max 2 per report** |
| Short-term | 1–4 weeks | Tactical rebalance / trim / accumulate | — |
| Long-term | 1–3 months | Strategic shifts, new positions, gradual exits | — |
| Patience Required | No action | Fundamentally sound stocks in temporary weakness | — |

Each action must specify: *What, Which stock, Why (fundamental), Business-story status (Intact/Weakening/Broken), Valuation context*.

### 5.3 Weekly Report (Phase 6 output)

`reports/{market}/YYYY-MM-DD-weekly-report.md` — structured as:

1. **Header** (date, stock count, estimated value, prior run date, overall confidence)
2. **Changes Since Last Run** (only if prior context exists): Portfolio Changes, Follow-Up on Previous Alerts, Previous Action Items Status
3. **Executive Summary** (copied from portfolio-analysis.md)
4. **Stock-by-Stock Analysis** — each stock rendered as a `### {NAME} ({TICKER}) — {SCORE}/11 {RATING} [{CONFIDENCE}]` block with `[Overview] [Scores] [Rationale] [Fund] [Valu] [Biz] [News] [Phil] [Prev] [AI]` lines, **transferred verbatim** from the enriched stock file. ETFs get a single-paragraph short form.
5. **Portfolio Health Check** — sector allocation table, concentration risk, quality-score distribution
6. **Philosophy Alignment Gap Analysis** — current vs ideal, exit candidates table, underrepresented-sector entry candidates, position-sizing adjustments
7. **Action Plan** — four priority tables (Immediate / Short / Long / Patience Required)
8. **Watchlist / Flagged Stocks**
9. **Key Risks** (three)
10. **Confidence Summary** (HIGH / MEDIUM / LOW bucketed stock lists)

### 5.4 Context Ledger (Phase 6 secondary output)

`context/{market}/last-run.md` — ≤100 lines, overwritten each run (previous copied to `last-run-backup.md` first). Structure: Run Summary, Portfolio Snapshot, Key Alerts (Concerning + Opportunities), Open Action Items (carried forward if not acted on), Price Levels to Watch (only within 5–10% of current price), Philosophy Alignment.

---

## 6. The Scoring System (Fundamentals-First, 0–11)

Codified in `.agents/portfolio-research/frameworks/analysis-frameworks.md` and `phase-4-scoring.md`.

| Component | Max | Weight Philosophy |
|-----------|-----|-------------------|
| **Fundamental** | 4 | Primary driver — financial health, valuation, growth quality, balance sheet |
| **Business Story / Moat** | 2 | Qualitative conviction — moat, sector runway, management, capex visibility |
| **Valuation & Accumulation** | 2 | Accumulation context only — *never* reduces conviction on its own |
| **News/Sentiment** | 1 | Short-term informational — recent catalysts, analyst actions |
| **Philosophy Fit** | 2 | Graduated (0/1/2) check against the user's philosophy thresholds |
| **Total** | **11** | Fundamentals + Business Story = 6/11 (≈55%) |

### Rating bands

| Score | Label | Meaning |
|-------|-------|---------|
| 9–11 | Strong Conviction | Core holding, accumulate on dips |
| 7–8 | Conviction Hold | Fundamentals intact, hold with patience |
| 5–6 | Under Review | Mixed signals, monitor |
| 1–4 | Fundamental Concern | Thesis may be broken, deep review required |

### Key invariants

- **An expensive but fundamentally sound stock must not fall below "Conviction Hold."** A 4/4 + 2/2 + 2/2 + 0/2 + 0/1 = 8/11 is still Conviction Hold.
- **Philosophy Fit is graduated**:
  - 0 failures → 2
  - 1–2 non-dealbreaker failures → 1
  - 3+ failures OR any dealbreaker → 0
- **Dealbreakers (auto-zero Philosophy Fit)**:
  - Promoter holding = 0% (unless structurally promoter-less, e.g., MCX/BSE)
  - Confirmed fraud, SEBI action, severe governance crisis
  - User's per-stock Philosophy explicitly says "SELL" or "EXIT"
- **Structural sector exceptions** (documented in the framework): Hospital chains (Promoter >20%), IT MNCs (Promoter >10%), NBFCs (use banking criteria instead of D/E), PSUs (government holding >45% = pass), foreign MNC subsidiaries (parent >40% = pass), stock exchanges (exempt).
- **Confidence badge** — `[HIGH]` / `[MEDIUM]` / `[LOW]` attached to every stock based on source coverage.

### Action verbs
`Hold | Accumulate | Trim | Exit | Hold-with-Conviction` — the last one is specifically for fundamentally sound stocks in price weakness.

---

## 7. Research Methodology

Codified in `.agents/portfolio-research/frameworks/research-methodology.md`.

### 7.1 Source credibility tiers (India)

| Tier | Sources | Use |
|------|---------|-----|
| 1 | BSE/NSE filings, annual reports, SEBI/RBI disclosures | Official financials, shareholding |
| 2 | Screener.in, Trendlyne, Tickertape | Aggregated financials, ratios |
| 3 | Moneycontrol, Economic Times, LiveMint, Business Standard | News, analyst opinion |
| 4 | Blogs, Twitter, YouTube, ValuePickr | Sentiment only — **never** cite for financial data |

Rule: **Tier 3 is restricted to qualitative data.** Fundamentals must come from Tier 1–2.

### 7.2 Three-tier web fetch fallback chain

```
Tier 1: Direct URL fetch
  ↓ if blocked / empty / captcha / 403 / 429 / JS-only
Tier 2: Site-scoped web search ("… site:screener.in")
  ↓ if insufficient
Tier 3: Broad web search
```

Site-specific behaviors the framework documents:
- NSE/BSE India — almost always block, always search the web
- Screener.in — Tier 1 often works, Tier 2 fallback common
- Moneycontrol — URLs vary, always search
- **dhan.co** — reliable direct-fetch source used specifically for **split-adjusted 100-day and 200-day SMAs**
- Tickertape / Trendlyne — heavy JS, Tier 1 often fails
- Google Sheets — always curl in a terminal

### 7.3 Search query patterns

The framework prescribes specific query patterns per data class:
- Growth metrics → `"{COMPANY}" INDmoney quarterly results YoY QoQ`
- Static ratios → `"{COMPANY}" screener.in financial ratios`
- Shareholding → `"{TICKER}" shareholding pattern moneycontrol` / `… FII DII trendlyne`
- Daily MAs → fetch `https://dhan.co/stocks/{company-slug}-share-price/`
- Sector PE → **look up once per sector from Trendlyne**, cache, reuse across all stocks in that sector (documented Nifty-sectoral-index mapping: IT, Bank, FMCG, Pharma, Financial Services, Auto, Healthcare)
- Banking additionals → `"{COMPANY}" Q3 FY26 results NPA CASA NIM ROA CAR`
- News → always append current year and month; use `-site:screener.in` to exclude BSE filings masquerading as news

### 7.4 Quality standards (mandatory)

- **Recency verification** — every fundamental metric carries a quarter/period; "Latest"/"Current"/"TTM" forbidden; news must be ≤2–4 weeks old
- **Citations mandatory** — `[N] Source — "Title" — URL — Accessed {DATE} — Tier {N}`
- **Source diversity** — each stock must cite ≥2 unique source domains
- **No fabrication** — "N/A" / "Data not found" is the only acceptable substitute for a missing value
- **No speculation** — never extrapolate between quarters

---

## 8. Parallel Execution via Atomic File Claims

Phases 2 and 4 are designed for multiple concurrent agent sessions. The coordination primitive is **per-stock lock directories** containing two sentinel files:

```
temp/research/claims/{TICKER}/
    ├── .claimed   # written when an agent takes the stock
    └── .done      # written when the agent finishes
```

### 8.1 Claim script (`claim-stocks.sh`, mirrored by `claim-scoring.sh`)

The critical line:

```bash
if (set -o noclobber; echo "$AGENT_ID $(date +%s)" > "$CLAIMED_FILE") 2>/dev/null; then
  echo "$TICKER"
  CLAIMED_LIST+=("$TICKER")
fi
```

`set -o noclobber` makes `>` fail atomically if the file already exists. Two concurrent agents racing for the same ticker — exactly one succeeds; the other silently moves on. No shared mutable state, no locks, no database.

### 8.2 Complete + crash recovery

- `complete-stock.sh TICKER [TICKER …]` — writes `.done`. `complete-scoring.sh` additionally validates that a `## Scoring` section actually exists in the stock file before marking done.
- `check-progress.sh` / `check-scoring-progress.sh` — counts total / claimed / completed
- `reclaim-stale.sh [minutes]` / `reclaim-scoring-stale.sh` — deletes `.claimed` files older than N minutes (default 30) so crashed / abandoned stocks become reclaimable by any session
- `validate-prerequisites.sh` — pre-flight checks before Phase 5/6

Each agent session claims exactly one batch (10), processes it, then **must stop** ("Batch complete. Start a new conversation to process the next batch"). The agent is explicitly forbidden from looping.

---

## 9. Rules That Apply to Every Phase

From `guidelines/rules.md` and reinforced in each phase file:

1. **Never fabricate data.** Missing → "N/A" / "Data not found".
2. **Always cite sources.** Every number needs a source and access date.
3. **Follow the fallback chain.** Don't abandon a stock after one failed fetch.
4. **Respect the philosophy.** The report serves the user's written philosophy, not generic advice.
5. **Keep context brief.** The ledger is for continuity, not a second report.
6. **Filesystem is the bridge.** All inter-phase communication happens through `temp/research/`.
7. **Dense output format.** `[Tag] Metric: Value | Metric: Value` — no tables, no bullets in data lines.
8. **Fundamentals-first.** Valuation informs accumulation timing, not conviction. An expensive stock with strong fundamentals is still a conviction hold.
9. **Price drops are review triggers, not sell signals.** −20% from buy price triggers a **deep fundamental review**, never an automatic exit.
10. **Immediate actions capped at 2 per report** — reserved for fundamental thesis breaks only.

---

## 10. Invocation Surface

Users run the workflow as slash commands (shimmed in `.claude/commands/`):

```
/phase1 market=india
/phase2 market=india     # run multiple sessions in parallel
/phase3 market=india     # optional
/phase4 market=india     # run multiple sessions in parallel
/phase5 market=india
/phase6 market=india
/progress                # checks Phase 2 and Phase 4 claim state
```

`market=us` swaps the market. If the market parameter is absent, every phase errors with `"Market parameter required. Use market=india or market=us"`.

Alternatively, the user can paste the prompt from `prompts/weekly-analysis.md` (referenced in README but not present in the current file tree) or simply invoke the phases via agents.md/CLAUDE.md.

---

## 11. What the System Currently Does Well

1. **Clear separation of concerns** — each agent has one job, which makes prompts tight and results predictable.
2. **Deterministic, parallel-safe coordination** — the `noclobber` claim mechanism is simple, correct, and language-agnostic.
3. **Dense, machine-readable stock-file format** — the `[Tag]` blocks are trivially parseable and force the agent to commit to specific metrics rather than narrative.
4. **Philosophy-driven scoring** — explicit thresholds for non-financial vs banking/NBFC, sector-structural exceptions, dealbreaker rules, and a conservative "fundamentals-first" tiebreaker make scoring auditable and consistent.
5. **Conservative action philosophy** — the 2-immediate-actions cap and the explicit "Patience Required" tier resist the typical LLM tendency to manufacture urgency.
6. **Context continuity** — the ≤100-line ledger gives each run memory without consuming a lot of token budget.
7. **Source-citation rigor** — Tier 1–4 framework, access-date citations, and source-diversity requirements make reports auditable.
8. **Crash-tolerant** — any agent can be killed and any other session can pick up the remaining work via `reclaim-stale.sh`.
9. **Two-market support** — India (filled in) and US (template) with per-market portfolio, philosophy, reports, and context.

---

## 12. Current Limitations & Gaps (relative to a "complete portfolio manager")

This is research scaffolding, not portfolio management. Observed gaps:

### 12.1 It is output-only
- **No position-level actions executed** — the report recommends; the user must manually place trades.
- **No broker integration** — no Zerodha/Kite, no Upstox, no IBKR connector.
- **No transaction history ingestion** — the "Portfolio" is a point-in-time snapshot from a Google Sheet; realized P/L, tax lots, holding periods, corporate-action-adjusted cost basis are not tracked.
- **No cash position** — the system only sees holdings, not cash available to deploy.

### 12.2 Data quality is best-effort
- **Web-search-first** — every quantitative metric is scraped from search snippets and public aggregators, with an explicit 3-tier fallback because sources frequently block or go stale. No persisted price/fundamentals database.
- **Sector PE caching is single-run** — recomputed each time, no historical series kept.
- **No real-time prices** — LTP comes from the user's sheet, which they update manually. The system cannot fetch live quotes reliably.
- **Banking/NBFC schema is bolted on** — metrics live inside the same `[Fund]` line conditionally. No structured type system.
- **No benchmarking** — rating labels are absolute thresholds; there is no Nifty-relative or sector-relative performance attribution.

### 12.3 Workflow ergonomics
- **Agent-session batching is manual** — the user must start multiple Phase 2 / Phase 4 conversations themselves; there is no orchestrator that fans them out.
- **No single-command end-to-end run** — each phase is a separate invocation.
- **Temp directory is manual** — not auto-cleaned between runs (quality checklist mentions cleanup but it is not enforced).
- **US philosophy is an unfilled template** — running `market=us` today against a placeholder philosophy produces generic output.
- **No UI** — purely markdown + terminal + agent chat.

### 12.4 Analytical gaps
- **No portfolio optimization** — no mean-variance, no risk parity, no factor tilt analysis.
- **No scenario / what-if** — cannot answer "what happens if I trim INFY by 50% and add HDFCBANK?".
- **No correlation / covariance tracking** — concentration risk is evaluated only by name and sector weights, not by return correlations.
- **No drawdown / volatility tracking** — the philosophy specifies a 30% max drawdown but the system cannot measure actual drawdown.
- **No backtesting of rules** — e.g., "if I had followed every Immediate action over 12 months, what would P/L be?"
- **Sector targets are soft in India philosophy** — no numeric targets means gap analysis is qualitative ("too concentrated" vs "+15% overweight").
- **Watchlist is in-report only** — there's no persisted candidate-list of stocks being considered for entry.
- **No dividend / corporate-action tracking.**
- **No tax-lot optimization** for trim recommendations (philosophy mentions LTCG considerations but the system has no visibility into lots).

### 12.5 Governance of the engine itself
- **No tests / fixtures** — quality depends entirely on the agent following prompt rules.
- **No schema validation** — `[Tag]` lines are enforced by prose rules, not a parser. Phase 3 (optional) spot-checks format.
- **No metrics on the engine** — no tracking of "how often did Phase 2 fall to Tier 3?", "what % of stocks got `[LOW]`?".
- **Previous context is trusted** — the ledger is written by the same agent that will read it; there is no external validation of claims carried forward.

---

## 13. Extension Points (Where a "Complete Portfolio Manager" Would Plug In)

Natural integration seams for someone optimizing this into a full manager:

| Want to add | Where it plugs in |
|-------------|-------------------|
| Live prices / fundamentals API (e.g., Alpha Vantage, Polygon, Tijori) | Replace/augment the Phase 2 web-search layer; cache in a persisted `data/` folder |
| Broker / execution | New Phase 7 post-report that takes the Action Plan and submits orders (with confirmations) |
| Transaction history & tax lots | Replace the Google Sheet snapshot with a ledger file; `Invested` / `P/L %` become derived |
| Portfolio optimizer | New framework `frameworks/optimization.md` and a Phase 5b that proposes target weights |
| Backtest engine | Offline runner that replays `reports/{market}/*.md` to measure the system's recommendations |
| Schema / parser | Typed schema (JSON Schema / Pydantic) for the `[Tag]` format + a linter used by Phase 3 |
| Orchestrator | Script that spawns the 5 parallel Phase 2 / Phase 4 sessions automatically |
| UI | Web app reading `reports/` and `context/` (both are markdown — easy to render) |
| Alerts | Cron job + `check-progress.sh` + webhook on new report |
| Multi-market consolidation | New phase that merges India + US into a single consolidated view |
| Benchmarking | Nifty/S&P historical series alongside context ledger for relative attribution |

---

## 14. Glossary

- **Manifest** — `temp/research/manifest.md`, the portfolio + philosophy + per-stock-theses document written by Phase 1 that every subsequent phase reads.
- **Enriched stock file** — a `temp/research/stocks/{TICKER}.md` that has had its `## Scoring` section appended by Phase 4. Phases 5 and 6 read only enriched files.
- **Claim** — a `.claimed` sentinel file inside a per-ticker lock directory. Writing it atomically (via `noclobber`) is how an agent reserves a stock for its batch.
- **Context ledger** — the ≤100-line rolling memory file at `context/{market}/last-run.md`.
- **Dealbreaker** — a Philosophy Fit criterion whose failure auto-scores 0/2 (e.g., promoter 0%, fraud, user-marked EXIT).
- **Structural exception** — a documented case where a philosophy threshold is waived for a specific sector/structure (e.g., global IT MNCs get a 10% promoter threshold).
- **Patience Required** — the action tier reserved for fundamentally sound stocks in temporary weakness — explicitly "no action needed".
- **Hold-with-Conviction** — an action verb used when a stock is down but the fundamental and business-story theses remain intact.
- **Fundamentals-first** — the scoring invariant that valuation alone cannot push a stock below Conviction Hold.
- **`[Tag]` format** — the single-line-per-tag, pipe-delimited stock data format (`[Overview]`, `[Fund]`, `[Valu]`, `[Biz]`, `[News]`, `[Phil]`, `[Prev]`, `[Sources]`, `[Scores]`, `[Rationale]`, `[AI]`).
