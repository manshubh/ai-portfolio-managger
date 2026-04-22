# MCP tool selection, authority matrix, and coverage gaps

> **Canonical MCP authority for this project.** Combines (a) which MCP servers are selected and for what role, (b) a per-tool authority matrix mapping SPEC §18.2 + §6.2 requirements to the actual tool to call on the actual MCP, and (c) the cross-market coverage-gap log with bd follow-ups. Downstream consumers (M2, M3, M5, M9, M14) read this file to decide which tool to call for any given field and what to substitute when a gap bites.
>
> Produced by [M0.3](../plans/M0/M0.3-mcp-servers.md). Evidence: [`mcp-smoke-test-india.md`](./mcp-smoke-test-india.md) (24 cells) + [`mcp-smoke-test-us.md`](./mcp-smoke-test-us.md) (18 cells), both 2026-04-22. Operational config: [`config/mcp-servers.md`](../config/mcp-servers.md).
>
> **When to update:** (1) a new smoke session reveals a new gap, (2) an upstream MCP release changes a tool signature or fixes a gap (drop the row and note the version in which it was resolved), (3) a downstream milestone chooses a substitute path for a gap and the "resolution" column needs to reflect it. Any change is a single-commit edit — do not branch authority across multiple files.

## 1. Selected MCP servers

Three servers are registered project-wide (see `.mcp.json`, `.cursor/mcp.json`). Each has a narrow, non-redundant role:

| MCP | Version pin | Role | Status | Tools actually called | Ecosystem |
|---|---|---|---|---|---|
| `finstack-mcp` | 0.10.0 | **Primary fundamentals** (both markets) + SEC filings (US) + market-wide FII/DII (India) | PRIMARY | `company_profile`, `income_statement`, `balance_sheet`, `key_ratios`, `sec_filing`, `nse_fii_dii_data` | PyPI (`uvx`), MIT |
| `nsekit-mcp` | 0.0.22 | **India-specific price history + corporate actions** (fills gaps finstack does not cover for India) | SECONDARY | `equity_price_history`, `corporate_actions` | PyPI (`uvx`), **no license** — local-only per `config/mcp-servers.md` §5 |
| `nse-bse-mcp` | 0.1.5 | **India EOD live-quote fallback** (fast path when full history is overkill) | TERTIARY | `nse_equity_quote` | npm (`npx`, localhost:3000), MIT |

Servers **not selected** (considered and rejected at M0.3 investigation time, [`research/milestones/M0-investigation.md`](./milestones/M0-investigation.md)):

- None. All three candidates from the original investigation are kept. Redundancy is accepted at the server level because each fills a tool-level niche the others do not.

Note: `nsekit-mcp` exposes 117 tools, `finstack-mcp` 95, and `nse-bse-mcp` 59 (271 total surface); this project calls **9 tools total** (6 on finstack, 2 on nsekit, 1 on nse-bse) — a 3.3% utilization of the combined tool surface. Future phases may add more as needs emerge — new tool usage must be added to §2 below before it enters a skill. See §4 for the context-cost budget that this utilization implies and the stay/go signal per server.

## 2. Tool authority matrix (SPEC §18.2 + §6.2)

This is the single source of truth for "which tool on which MCP for which SPEC field". M9 (`fundamentals-fetch`) and M5 (`corp-actions-monitor`) must match this mapping; deviation is a bug. Fallback path applies when the primary tool returns `{}`, errors, or hits a row marked `gap: <id>` — fallback is Tier-B / Tier-C per SPEC §15.

### 2.1 Fundamentals and ratios

| SPEC §18.2 name | MCP | Actual tool | Signature | Markets | Primary or fallback? | Known gap |
|---|---|---|---|---|---|---|
| `get_fundamentals` | finstack | `company_profile` | `company_profile(symbol)` | both | **primary** | G4 (ADR routing for Indian ADR-listed tickers) |
| `get_income_statement` | finstack | `income_statement` | `income_statement(symbol)` — annual default, 4 periods | both | **primary** | G4 (ADR routing); correctly switches to bank-flavoured schema for banks — no gap on banks here |
| `get_balance_sheet` | finstack | `balance_sheet` | `balance_sheet(symbol)` — annual default, 4 periods | both | **primary** for non-banks; **gap for banks** | G1 (no `total_deposits`/`tier_1_ratio`/`casa`/`gnpa`/`nim`/`loans` for banks), G4 |
| `get_ratios` | finstack | `key_ratios` | `key_ratios(symbol)` | both | **primary** for non-banks; **gap for banks** | G1 (no NIM/CASA/GNPA/tier-1 for banks), G4, G8 (MSFT dividend null) |

### 2.2 SEC filings (US Tier 1)

| SPEC §18.2 name | MCP | Actual tool | Signature | Markets | Primary or fallback? | Known gap |
|---|---|---|---|---|---|---|
| `get_sec_filing {ticker} {filing_type}` | finstack | `sec_filing` | `sec_filing(symbol, filing_type, count)` | us | **primary** for latest-filing queries; **fallback to EDGAR direct** for multi-year lookback on some tickers | G9 (JPM multi-year lookback returns fewer than requested) |

Risk R4 from the M0.3 plan (signature mismatch) is **cleared** — the `(symbol, filing_type, count)` signature matches SPEC §18.2 exactly. Only the per-ticker lookback depth is the issue.

### 2.3 India market data

| SPEC §18.2 name | MCP | Actual tool | Signature | Market | Primary or fallback? | Known gap |
|---|---|---|---|---|---|---|
| `get_fii_dii` | finstack | `nse_fii_dii_data` | `nse_fii_dii_data()` — **no args, market-wide** | india | **primary** | G2 (market-wide — broadcast one snapshot to all tickers' context, do not attempt per-ticker FII/DII) |
| `nse_equity_quote` | nse-bse | `nse_equity_quote` | `nse_equity_quote(symbol)` — EOD snapshot | india | **primary** for Phase 2 live-quote fallback | G3 (EOD-only; no bid/ask/VWAP/delivery-pct — use nsekit `equity_price_history` if microstructure is needed) |
| `equity_history` (~1y, for 100d/200d MAs) | nsekit | `equity_price_history` | `equity_price_history(symbol, period="1Y")` | india | **primary** | G5 (filter `Series == "EQ"` to drop block-deal `BL` rows), G6 (unadjusted across splits — aggregator must apply adjustment from `corporate_actions` output) |
| `equity_history` (INR price for ADR-listed India names) | nsekit | `equity_price_history` | same | india | **fallback path for G4** — when finstack company_profile returns `exchange=NYQ` for an Indian ticker, price data must come from nsekit | — |

### 2.4 Corporate actions (SPEC §6.2, M5)

| SPEC §6.2 name | MCP | Actual tool | Signature | Market | Primary or fallback? | Known gap |
|---|---|---|---|---|---|---|
| `corporate_events` (±90d) | nsekit | `corporate_actions` | `corporate_actions(symbol, period="3M")` OR `corporate_actions(symbol, start_date, end_date)` | india | **primary** (with `start_date`/`end_date` preferred over `period` enum) | G7 (`period="3M"` under-reports — use explicit date range; Yahoo `actions` is the authoritative fallback per SPEC §6.2) |
| `corporate_events` (US) | — | (none; Yahoo `actions`) | — | us | **no MCP** — Yahoo is the primary per SPEC §6.2 | — |

## 3. Gap log

One row per discovered issue. Severity: `high` (blocks a specific downstream milestone), `medium` (requires a fallback path but does not block), `low` (informational / handled by aggregator normalization). Resolution column states the accepted path; bd follow-up links to the ticket where the downstream milestone owns execution.

| ID | Market | Tool | MCP | Ticker(s) | Observation | Severity | Downstream phase | bd follow-up | Resolution path |
|---|---|---|---|---|---|---|---|---|---|
| G1 | india + us | `balance_sheet`, `key_ratios` | finstack | HDFCBANK, JPM | No `total_deposits` / `tier_1_ratio` / `casa_ratio` / `gnpa` / `nim` / `loans` fields for bank tickers; generic US-GAAP shape only. `gross_margin`/`ebitda_margin` = 0, `debt_to_equity`/`current_ratio`/`free_cash_flow` null. | **high** | M3 (`banking_nbfc` scheme fixture), M9 (Phase 2 bank analytics) | [`ai-portfolio-manager-7ol`](../.beads/) | M3 sources the `banking_nbfc` fixture from Screener.in or equivalent per SPEC §15.3. Phase 2 bank analytics degrades: income_statement's bank-flavoured fields (NII, interest_income, interest_expense) ARE available and used; CASA/GNPA/tier-1 fields come from the M3 fixture, not from finstack. |
| G2 | india | `nse_fii_dii_data` | finstack | market-wide | Tool takes no symbol; returns one market-wide daily snapshot. | low | M2/M9 aggregator | — (accepted) | Call once per run; broadcast the same snapshot into each ticker's `valu.fii_*` / `valu.dii_*` context. Do not pretend this is per-ticker. |
| G3 | india | `nse_equity_quote` | nse-bse | RELIANCE, HDFCBANK, INFY | EOD OHLCV only; no bid/ask/VWAP/delivery %. | low | M9 Phase 2 live-quote | — (accepted) | Use nsekit `equity_price_history` if VWAP or delivery % is needed; otherwise accept EOD shape. |
| G4 | india | `company_profile`, `income_statement`, `balance_sheet`, `key_ratios` | finstack | INFY (and other ADR-listed India names: WIT, HDB, IBN, RDY, TTM) | finstack routes Indian ADR-listed tickers to the US ADR: `exchange="NYQ"`, `currency="USD"`. Returns US ADR financials, not NSE standalone/consolidated in INR. | medium | M9 aggregator | [`ai-portfolio-manager-v2b`](../.beads/) | M9 detects ADR routing (`company_profile.exchange == "NYQ" and country == "India"`) and falls back to Tier-B (Yahoo) or Tier-C (web) for fundamentals; uses nsekit `equity_price_history` for INR price data. Sources are attributed per SPEC §18.2 `sources[]`. |
| G5 | india | `equity_price_history` | nsekit | all India tickers | Series column interleaves `EQ` (normal trades) with `BL` (block deals). | low | M9 aggregator | — (accepted) | Consumer-side filter: `Series == "EQ"` for MA/price-trend calcs. `BL` rows are auditable delivery-book data, not price-series data. |
| G6 | india | `equity_price_history` | nsekit | HDFCBANK (and any split/bonus across the 1Y window) | Raw prices are **unadjusted** across corporate actions. HDFCBANK shows a ~2:1 step on 2025-08-26 (prev_close 1964.1 → open 979.5). | low | M9 aggregator | — (accepted) | Aggregator applies split/bonus adjustment using `corporate_actions` output for the same ticker. Alternatively, use finstack `company_profile` + Yahoo `history` (which returns split-adjusted closes) as a second source for MA calcs and cross-check. |
| G7 | india | `corporate_actions` | nsekit | HDFCBANK (and likely others) | `period="3M"` returned empty for all 3 tickers; HDFCBANK price history indicates at least one event within the window. Tool works for `period="1Y"`. | medium | M5 `corp-actions-monitor` | [`ai-portfolio-manager-nh7`](../.beads/) | M5 calls with explicit `start_date=today-90d, end_date=today+14d` rather than the `period` enum. If still empty, fall back to Yahoo `actions` per SPEC §6.2 and flag `source: Yahoo fallback`. Holdings-only semantics (ap0) already allow informational-only output. |
| G8 | us | `key_ratios` | finstack | MSFT | `dividend_rate`, `dividend_yield`, `payout_ratio`, `ex_dividend_date` all null despite MSFT paying a dividend. AAPL and JPM populate correctly. | low | M9 aggregator | [`ai-portfolio-manager-ine`](../.beads/) | Per-ticker: fall back to Yahoo `info.dividendRate` / `info.dividendYield` when finstack's dividend block is null. This is the happy path of the SPEC §18.2 `missing_fields[]` + `sources[]` normalization. |
| G9 | us | `sec_filing` | finstack | JPM (and possibly other large banks — untested) | `count=5` returned `count=1` on 10-K and `count=3` on 10-Q. Latest filing IS returned; historical back-fill is not. AAPL and MSFT unaffected. | medium | M9 (multi-year 10-K diff) | [`ai-portfolio-manager-8df`](../.beads/) | M9 Phase 2 US Tier-1 **latest-filing flow is not blocked** (latest 10-K/10-Q is returned). For multi-year diffing, M9 falls back to a direct EDGAR `browse-edgar?CIK=<cik>&type=10-K` call to enumerate prior filings when `response.count < count_arg`. |

## 4. Context cost per MCP (selection factor)

Context cost was not considered at M0.3 selection time but is a first-class factor for keeping a server on the authority list. Cursor mounts these MCPs under the **FileSystem model** — tool descriptors live at `~/.cursor/projects/Users-mrihal-workspace-ai-portfolio-manager/mcps/<server>/tools/*.json` and are read on demand, not injected into the system prompt. That is the session we actually run in. But a project that wants to stay portable must also bound the **classic-mode injection cost** — the surface that would land in the system prompt if the same `.mcp.json` were consumed by Claude Desktop, LangChain's MCP adapter, or any client that auto-registers every tool at startup.

Measurements taken 2026-04-22 by `wc -c` over the descriptor files Cursor's MCP FileSystem writes after discovery (`~/.cursor/projects/.../mcps/<server>/tools/`):

| MCP | Tools on server | Tools actually called | Total descriptor surface | Avg chars / tool | Sum of USED-tool descriptors | Classic-mode injection cost¹ |
|---|---|---|---|---|---|---|
| finstack | 95 | 6 | 102 KB | ~1,075 | 6,568 chars (~1,640 tok) | ~25,500 tok |
| nsekit | 117 | 2 | 59 KB | ~500 | 2,669 chars (~670 tok) | ~14,700 tok |
| nse-bse | 59 | 1 | 47 KB | ~800 | 327 chars (~80 tok) | ~11,800 tok |
| **Total** | **271** | **9** | **208 KB** | — | **9,564 chars (~2,390 tok)** | **~52,000 tok** |

¹ Characters ÷ 4 chars-per-token (conservative for dense JSON). This is the upper bound — what the project would pay in a non-Cursor client that injects every tool at session start.

Under the Cursor FileSystem mode we actually pay (a) ~180 tok for the `<mcp_file_system_servers>` registration (all three combined, trivial), plus (b) ~270 tok per unique tool descriptor read during a workflow. Per-call output tokens (e.g. a 1Y `equity_price_history` response ≈ 8 KB JSON) are the same regardless of MCP choice, so they do not factor in here.

### Stay/go signal per server

- **finstack — KEEP (primary, best utilization).** 6 of the 9 called tools. Per-workflow descriptor cost ~1,640 tok; the full 25.5 K-tok injection bound is tolerable for a primary data source. No plausible replacement at this price point for US fundamentals + SEC filings + India market-wide FII/DII in a single pinned MCP.

- **nsekit — KEEP with caveat.** 2 tools used out of 117 — a 1.7% utilization of the largest surface of the three. Under Cursor FileSystem mode the steady-state cost is only ~670 tok, but the **classic-mode injection cost is ~14.7 K tok** — the single largest amortization risk in the project. Combined with the existing license gap (§5 of `config/mcp-servers.md`), this server is the first thing to shim if a non-Cursor client ever enters the stack. Action: if portability to Claude Desktop, LangChain, or CI becomes a requirement, wrap nsekit behind a thin local HTTP adapter that exposes only `equity_price_history` and `corporate_actions`; keep the upstream MCP local-only per existing policy. No action needed for M9 / M5 today.

- **nse-bse — CANDIDATE TO DROP at M9 kickoff.** TERTIARY status, 1 tool used out of 59 (1.7% utilization), 47 KB server-side surface, and the `nse_equity_quote` call is **semantically subsumed by nsekit's `equity_price_history(symbol, period="1D")`** (see §2.3 and Gap G3). We are paying a 59-tool classic-mode cost (~11.8 K tok) and running a persistent `npx mcp-remote` process on `localhost:3000` for a convenience path that has a one-line substitute on an MCP we already keep. Unless Phase 2 live-quote latency benchmarking shows nse-bse materially faster than nsekit's 1D call (unmeasured today), drop nse-bse at the start of M9 and re-point §2.3 row `nse_equity_quote` at nsekit. A bd follow-up will be filed if the server survives M9 kickoff without a latency justification.

### What is explicitly NOT a cost concern

- `<mcp_file_system_servers>` registration overhead (~180 tok total) — trivial next to the SPEC doc itself.
- Discovery-time `ls` of tool folders — per-session, not amortized, and bounded by the 271-file surface.
- Tool-call output size — orthogonal to MCP selection; any equivalent upstream (Yahoo, EDGAR, Screener) would return the same shape.

## 5. Consumer pointers

Each downstream milestone reads this file; this section tells them exactly what to look at.

- **M2 (`wealthfolio-query`)** — independent of MCPs. No action here. Listed for completeness.
- **M3 (`scoring-engine`, banking_nbfc scheme)** — read §3 Gap G1. Do **not** rely on finstack for CASA/NIM/tier-1/GNPA. Source `tests/scoring-engine/hdfcbank.json` (and analogous for any US bank fixture) from Screener.in or equivalent per SPEC §15.3. bd: [`ai-portfolio-manager-7ol`](../.beads/).
- **M5 (`corp-actions-monitor`)** — read §2.4 and Gap G7. Call `corporate_actions` with explicit `start_date`/`end_date`, not the `period` enum. On empty / error, fall back to Yahoo per SPEC §6.2. bd: [`ai-portfolio-manager-nh7`](../.beads/).
- **M9 (`fundamentals-fetch` aggregator)** — read §2.1, §2.2, §2.3 top-to-bottom for the tool authority mapping. Read §3 Gaps G1 / G4 / G8 / G9 for the fallback paths. Implement ADR-detection (G4) and SEC multi-year fallback (G9) as part of the aggregator skill, not as per-ticker workarounds. bd: [`ai-portfolio-manager-v2b`](../.beads/) (G4), [`ai-portfolio-manager-8df`](../.beads/) (G9), [`ai-portfolio-manager-ine`](../.beads/) (G8).
- **M14 (full-portfolio stress test)** — re-run the smoke matrix against the live portfolio once M9 lands. If any new gap surfaces, append a row here (not a new file) and file a bd ticket.

## 6. Revision log

| Date | Change |
|---|---|
| 2026-04-22 | Initial write. 9 gaps logged (1 high, 3 medium, 5 low) from the 42-cell India + US smoke test. 4 bd follow-ups filed. |
| 2026-04-22 | Added §4 context-cost analysis. Measured descriptor surface (271 tools, 208 KB, 3.3% utilization). Flagged `nse-bse-mcp` as drop-candidate at M9 kickoff (1/59 tools used, subsumed by nsekit `equity_price_history(period="1D")`). Flagged `nsekit-mcp` as the largest classic-mode injection risk (~14.7 K tok) for non-Cursor clients. `finstack-mcp` retained as primary without reservation. |
