# MCP smoke test — India

> Produced by [M0.3](../plans/M0/M0.3-mcp-servers.md). Evidence for the 24-cell India smoke matrix. Raw captures archived (gitignored) at `temp/mcp-smoke-raw-india.md`; this file is the authoritative, committed summary.
>
> Canonical tool-selection + gap authority: [`research/mcp-gaps.md`](./mcp-gaps.md). Operational config: [`config/mcp-servers.md`](../config/mcp-servers.md).

## 1. Run metadata

| Field | Value |
|---|---|
| Run date | 2026-04-22 |
| Session | Cursor (fresh window, project-scoped `.cursor/mcp.json`) |
| MCPs loaded | `finstack-mcp` 0.10.0, `nsekit-mcp` 0.0.22, `nse-bse-mcp` 0.1.5 |
| Tickers | `RELIANCE.NS` / `HDFCBANK.NS` / `INFY.NS` (tool calls use bare `RELIANCE` / `HDFCBANK` / `INFY`) |
| Matrix size | 24 cells (8 tools × 3 tickers); SPEC §18.2 + §6.2 coverage |
| `nse-bse-mcp` HTTP server | running on `localhost:3000` for duration of session |

### SPEC → actual tool mapping (verified this session)

| SPEC §18.2 name | MCP | Actual tool | Signature used |
|---|---|---|---|
| `get_fundamentals` | finstack | `company_profile` | `company_profile(symbol)` |
| `get_income_statement` | finstack | `income_statement` | `income_statement(symbol)` — annual default, 4 periods returned |
| `get_balance_sheet` | finstack | `balance_sheet` | `balance_sheet(symbol)` — annual default, 4 periods returned |
| `get_ratios` | finstack | `key_ratios` | `key_ratios(symbol)` |
| `get_fii_dii` | finstack | `nse_fii_dii_data` | `nse_fii_dii_data()` — **no args, market-wide** (not per-ticker) |
| `nse_equity_quote` | nse-bse | `nse_equity_quote` | `nse_equity_quote(symbol)` — EOD snapshot |
| `equity_history` (~1y) | nsekit | `equity_price_history` | `equity_price_history(symbol, period="1Y")` |
| `corporate_events` (±90d) | nsekit | `corporate_actions` | `corporate_actions(symbol, period="3M")` |

## 2. Per-cell results

**24/24 cells returned a non-empty structured response with at least one SPEC-expected field.** "PASS" below means the pass criterion in [M0.3 plan §Smoke-test matrix](../plans/M0/M0.3-mcp-servers.md#smoke-test-matrix) was met. A schema-shape gap (e.g. bank balance sheet without CASA) is still PASS at the cell level but is escalated into [`research/mcp-gaps.md`](./mcp-gaps.md) — see §3.

| # | Tool | Ticker | Status | First field observed | Notes |
|---|---|---|---|---|---|
| C01 | finstack `company_profile` | RELIANCE | PASS | `market_cap = 18.43T INR` | `exchange=NSI`, `currency=INR`. |
| C02 | finstack `company_profile` | HDFCBANK | PASS (bank shape thin) | `market_cap = 12.31T INR`, `industry="Banks - Regional"` | No CASA/GNPA/NIM/CAR/tier-1 in this tool; expected — see C08/C11 for the real bank-analytics cells. |
| C03 | finstack `company_profile` | INFY | PASS (ADR routing) | `market_cap = 55.56B USD`, `exchange=NYQ`, `currency=USD` | **finstack routes INFY to the NYSE ADR, not the NSE listing.** Gap G4. |
| C04 | finstack `income_statement` | RELIANCE | PASS | `total_revenue (FY2025) = 9,646,930,000,000 INR` | 4 annual periods, non-financial schema. |
| C05 | finstack `income_statement` | HDFCBANK | PASS | `net_interest_income (FY2025) = 1,404,485,600,000 INR`, `interest_income`, `interest_expense` | 4 annual periods, **banking-flavoured schema** (no `cost_of_revenue`/`gross_profit`). |
| C06 | finstack `income_statement` | INFY | PASS (ADR routing) | `total_revenue (FY2025) = 19,277,000,000 USD` | 4 annual, **USD via ADR**. Gap G4. |
| C07 | finstack `balance_sheet` | RELIANCE | PASS | `total_assets = 19,501,210,000,000 INR`, `long_term_debt`, `working_capital` | 4 annual periods, ~70 fields. |
| C08 | finstack `balance_sheet` | HDFCBANK | PASS (bank-shape gap) | `total_assets = 48,187,671,100,000 INR`, `cash_cash_equivalents_and_federal_funds_sold`, `trading_securities`, `available_for_sale_securities` | **Missing: `total_deposits`, `casa_ratio`, `tier_1_ratio`, `gnpa`, `nnpa`, `nim`, broken-out `advances`.** Generic US-GAAP-style bank balance sheet only. **Gap G1 — severity: high.** |
| C09 | finstack `balance_sheet` | INFY | PASS (ADR routing) | `total_assets = 17,419,000,000 USD` | 4 annual, USD via ADR. Gap G4. |
| C10 | finstack `key_ratios` | RELIANCE | PASS | `pe_trailing = 22.17`, `roe = null`, `debt_to_equity = 35.65` | Non-financial ratios populated; `roe`/`roa`/`current_ratio`/`quick_ratio`/`free_cash_flow` null (conglomerate quirks). |
| C11 | finstack `key_ratios` | HDFCBANK | PASS (bank-shape gap) | `pe_trailing = 17.85`, `roe = 0.1382`, `gross_margin = 0.0`, `ebitda_margin = 0.0`, `debt_to_equity = null`, `current_ratio = null`, `free_cash_flow = null` | Same shape as RELIANCE — **no NIM/CASA/GNPA/tier-1/CAR**. `gross_margin`/`ebitda_margin` meaningless for a bank. **Gap G1 — severity: high.** |
| C12 | finstack `key_ratios` | INFY | PASS (ADR routing) | `pe_trailing = 17.83`, currency=USD | USD via ADR. Gap G4. |
| C13 | finstack `nse_fii_dii_data` | (context: RELIANCE) | PASS | `FII/FPI netValue = -2078.36 cr (22-Apr-2026)` | **Tool is market-wide; takes no symbol.** Same response for C14/C15. Gap G2 — severity: low (broadcast downstream). |
| C14 | finstack `nse_fii_dii_data` | (context: HDFCBANK) | PASS | (identical to C13) | Same snapshot. |
| C15 | finstack `nse_fii_dii_data` | (context: INFY) | PASS | (identical to C13) | Same snapshot. |
| C16 | nse-bse `nse_equity_quote` | RELIANCE | PASS | `close = 1362.1 INR`, `date="22-Apr-2026 16:00:00"` | **EOD OHLCV snapshot** — no bid/ask/VWAP/delivery %. Gap G3 — severity: low. |
| C17 | nse-bse `nse_equity_quote` | HDFCBANK | PASS | `close = 799.9 INR` | EOD OHLCV. |
| C18 | nse-bse `nse_equity_quote` | INFY | PASS | `close = 1268.6 INR` | EOD OHLCV. Confirms nse-bse returns INR for INFY (contrast with finstack C03/C06/C09/C12 USD). |
| C19 | nsekit `equity_price_history` | RELIANCE | PASS | ~249 trading-day rows, first row `Date="22-Apr-2025" Close=1291.2`, last row matches C16 | Rich fields: Prev Close, Open, High, Low, Last, Close, VWAP, Total Traded Qty, Turnover, No. of Trades, Deliverable Qty, %Dly Qt. A few `Series: BL` block-deal rows interleaved. Gap G5 (minor). |
| C20 | nsekit `equity_price_history` | HDFCBANK | PASS | ~249 rows, **price discontinuity on 2025-08-26** (prev_close 1964.1 → open 979.5, ~2:1 split) | Consumers must apply split adjustment across this date. Gap G6 — severity: low. |
| C21 | nsekit `equity_price_history` | INFY | PASS | ~249 rows, INR prices ~1200–1690 range | **Confirms nsekit returns NSE INR for INFY** — viable fallback for INFY price data (finstack ADR-routes). Feeds gap G4's mitigation. |
| C22 | nsekit `corporate_actions` | RELIANCE | PASS (empty window) | `[]` for `period="3M"` | 1Y re-probe returned 1 event (RELIANCE dividend Rs 5.5, ex 14-Aug-2025) — tool works, 3M genuinely empty for RELIANCE. |
| C23 | nsekit `corporate_actions` | HDFCBANK | PASS (empty window, suspected under-report) | `[]` for `period="3M"` | **Price history C20 shows a large step on 19-Mar-2026 (prev 843 → open 770)** consistent with an ex-date; the 3M window did not surface it. **Gap G7 — severity: medium.** |
| C24 | nsekit `corporate_actions` | INFY | PASS (empty window) | `[]` for `period="3M"` | Empty. |

### Verbatim excerpts (first ~20 lines per cell, selective)

Full raw JSON for every cell lives in `temp/mcp-smoke-raw-india.md`. Representative excerpts — one per MCP, plus both banking cells:

**C01 · finstack `company_profile` · RELIANCE** (first 15 lines):

```json
{
  "symbol": "RELIANCE",
  "name": "Reliance Industries Limited",
  "sector": "Energy",
  "industry": "Oil & Gas Refining & Marketing",
  "country": "India",
  "city": "Mumbai",
  "website": "https://www.ril.com",
  "employees": 403303,
  "exchange": "NSI",
  "currency": "INR",
  "market_cap": 18432579862528,
  "market_cap_formatted": "$18.43T",
  "timestamp": "2026-04-22T20:37:45.081525"
}
```

**C08 · finstack `balance_sheet` · HDFCBANK** (first 20 lines, banking-shape gap visible — note absence of `total_deposits` / `tier_1_ratio` / `casa_ratio` / `gnpa`):

```json
{
  "symbol": "HDFCBANK",
  "type": "annual",
  "periods": 4,
  "currency": "INR",
  "data": [
    {
      "period": "2025-03-31",
      "total_assets": 48187671100000.0,
      "total_liabilities_net_minority_interest": 39564780100000.0,
      "stockholders_equity": 7676891400000.0,
      "minority_interest": 945999600000.0,
      "retained_earnings": 2099097200000.0,
      "long_term_debt": 5866163200000.0,
      "current_debt": 1306013100000.0,
      "total_debt": 7326106100000.0,
      "investments_and_advances": 6981246400000.0,
      "trading_securities": 625388500000.0,
      "cash_cash_equivalents_and_federal_funds_sold": 7576597900000.0,
      "available_for_sale_securities": 381931600000.0
    }
  ]
}
```

**C11 · finstack `key_ratios` · HDFCBANK** (first 20 lines, generic-ratio shape gap — `gross_margin`/`ebitda_margin` are 0, no NIM/CASA/GNPA/tier-1):

```json
{
  "symbol": "HDFCBANK",
  "currency": "INR",
  "valuation": {
    "pe_trailing": 17.850925,
    "pe_forward": 12.726996,
    "price_to_book": 2.1781278,
    "ev_to_ebitda": null,
    "ev_to_revenue": 5.466
  },
  "profitability": {
    "profit_margin": 0.26834,
    "operating_margin": 0.40539002,
    "gross_margin": 0.0,
    "ebitda_margin": 0.0,
    "roe": 0.13818,
    "roa": 0.01704
  }
}
```

**C16 · nse-bse `nse_equity_quote` · RELIANCE** (complete response; EOD shape only):

```json
{
  "date": "22-Apr-2026 16:00:00",
  "open": 1350.3,
  "high": 1366,
  "low": 1349.1,
  "close": 1362.1,
  "volume": 9525953
}
```

**C20 · nsekit `equity_price_history` · HDFCBANK** (split-day row, prev_close 1964.1 → open 979.5 on 2025-08-26):

```json
{"Symbol":"HDFCBANK","Series":"EQ","Date":"26-Aug-2025","Prev Close":1964.1,"Open Price":979.5,"High Price":985.7,"Low Price":968.0,"Last Price":972.3,"Close Price":973.4,"VWAP":973.26,"Total Traded Quantity":16917731,"Turnover ₹":16465410030.9,"No. of Trades":296302,"Deliverable Qty":11117324.0,"% Dly Qt to Traded Qty":65.71}
```

## 3. Summary

**24 / 24 cells pass** the per-cell criterion (non-empty structured response with ≥1 SPEC-expected field).

Mapping to SPEC §18.2 / §6.2 aggregator requirements:

| SPEC requirement | Status | Detail |
|---|---|---|
| Fundamentals for India non-bank (RELIANCE, INFY) | **Covered** with caveat | finstack `company_profile`/`income_statement`/`balance_sheet`/`key_ratios` work; **INFY routes to USD ADR → Gap G4**. |
| Fundamentals for India bank (HDFCBANK) | **Partial** | Income statement is bank-flavoured (interest_income, NII). Balance sheet + ratios return generic US-GAAP-style schema **without** CASA/GNPA/NIM/tier-1/CAR. **Gap G1 — severity: high**, blocks M3 `banking_nbfc` scheme fixture. |
| FII/DII | **Covered** (market-wide) | Single daily snapshot, broadcast downstream per ticker. Gap G2 — severity: low. |
| India live-quote | **Covered** (EOD) | nse-bse `nse_equity_quote` returns EOD OHLCV; intraday/bid-ask not exposed. Gap G3 — severity: low. |
| India historical MAs (100d / 200d) | **Covered** | nsekit `equity_price_history(..., period="1Y")` returns ~249 rows with full OHLCV+VWAP+delivery; enough for 100d/200d MAs. Filter `Series == "EQ"` downstream (Gap G5). |
| India corporate actions (±90d) | **Partial** | Tool reachable and works for 1Y windows; the `period="3M"` enum returned empty for all three tickers, and HDFCBANK price evidence suggests at least one event was under-reported. **Gap G7 — severity: medium**, M5 consumes. |

Banking-cell focus (per plan §"Banking-specific expectations"):

- **HDFCBANK + `get_balance_sheet` (C08)**: finstack returns a generic US-GAAP-style bank balance sheet missing `total_deposits`, `casa_ratio`, `tier_1_ratio`, `gnpa`, `nim`. **Gap G1.**
- **HDFCBANK + `get_ratios` (C11)**: same tool shape as non-bank tickers; no NIM / CASA / GNPA / tier-1 substitutes; `gross_margin` and `ebitda_margin` are 0. **Gap G1.**

Both are logged severity: high in `research/mcp-gaps.md` and have a bd follow-up filed before this subtask closes. M3 owns resolution per SPEC §15.3 (hand-curated fixture from Screener.in or equivalent, or a scraper skill).

## 4. Gaps

All gaps affecting India are catalogued in the canonical [`research/mcp-gaps.md`](./mcp-gaps.md). India-market rows (filter on `market = india`):

- **G1** — finstack bank shape (HDFCBANK) — severity: high — blocks M3.
- **G2** — finstack `nse_fii_dii_data` is market-wide — severity: low — M2/M9 broadcast handling.
- **G3** — nse-bse `nse_equity_quote` is EOD-only — severity: low — Phase 2 India live-quote fallback.
- **G4** — finstack ADR routing for Indian ADR-listed tickers (INFY) — severity: medium — M9 aggregator fallback (nsekit price + Tier-B fundamentals).
- **G5** — nsekit `equity_price_history` interleaves `Series: BL` rows — severity: low — consumer-side filter on `Series == "EQ"`.
- **G6** — nsekit price history is unadjusted across splits (HDFCBANK 2025-08-26) — severity: low — aggregator must apply adjustment.
- **G7** — nsekit `corporate_actions(..., period="3M")` under-reports (empty for HDFCBANK despite price-history evidence of an event) — severity: medium — M5 consumes.
