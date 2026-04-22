# MCP smoke test — US

> Produced by [M0.3](../plans/M0/M0.3-mcp-servers.md). Evidence for the 18-cell US smoke matrix. Raw captures archived (gitignored) at `temp/mcp-smoke-raw-us.md`; this file is the authoritative, committed summary.
>
> Canonical tool-selection + gap authority: [`research/mcp-gaps.md`](./mcp-gaps.md). Operational config: [`config/mcp-servers.md`](../config/mcp-servers.md).

## 1. Run metadata

| Field | Value |
|---|---|
| Run date | 2026-04-22 |
| Session | Cursor (fresh window, separate from India session; project-scoped `.cursor/mcp.json`) |
| MCPs loaded | `finstack-mcp` 0.10.0, `nsekit-mcp` 0.0.22, `nse-bse-mcp` 0.1.5 (nsekit + nse-bse registered but uncalled — US matrix is finstack-only) |
| Tickers | `AAPL` / `JPM` / `MSFT` (no suffix needed) |
| Matrix size | 18 cells (6 tools × 3 tickers); SPEC §18.2 US Tier-1 coverage |
| `nse-bse-mcp` HTTP server | **not** required for this session |

### SPEC → actual tool mapping (verified this session)

| SPEC §18.2 name | Actual tool | Signature used |
|---|---|---|
| `get_fundamentals` | finstack `company_profile` | `company_profile(symbol)` |
| `get_income_statement` | finstack `income_statement` | `income_statement(symbol)` — annual default, 4 periods |
| `get_balance_sheet` | finstack `balance_sheet` | `balance_sheet(symbol)` — annual default, 4 periods |
| `get_ratios` | finstack `key_ratios` | `key_ratios(symbol)` |
| `get_sec_filing` (10-K) | finstack `sec_filing` | `sec_filing(symbol, filing_type="10-K", count=5)` — **matches SPEC §18.2 signature exactly** |
| `get_sec_filing` (10-Q) | finstack `sec_filing` | `sec_filing(symbol, filing_type="10-Q", count=5)` |

**Risk R4 in the parent plan ("finstack `get_sec_filing` might not expose the SPEC-assumed signature") is cleared** — the tool signature is `(symbol, filing_type, count)` exactly as SPEC §18.2 assumes. Separately, JPM exhibits a lookback-count gap (C14/C17); tracked as Gap G9.

## 2. Per-cell results

**18/18 cells returned a non-empty structured response with at least one SPEC-expected field.** Schema-shape gaps for the bank ticker are PASS at the cell level but escalated into [`research/mcp-gaps.md`](./mcp-gaps.md) — see §3.

| # | Tool | Ticker | Status | First field observed | Notes |
|---|---|---|---|---|---|
| C01 | finstack `company_profile` | AAPL | PASS | `market_cap = 4.00T USD`, `exchange=NMS` | Standard shape. |
| C02 | finstack `company_profile` | JPM | PASS (bank shape thin) | `market_cap = 844.28B USD`, `industry="Banks - Diversified"` | No tier-1/NIM/deposits/CAR in this tool — expected; see C08/C11. |
| C03 | finstack `company_profile` | MSFT | PASS | `market_cap = 3.20T USD`, `exchange=NMS` | Standard shape. |
| C04 | finstack `income_statement` | AAPL | PASS | `total_revenue (FY2025, Sep-ending) = 416,161,000,000 USD` | 4 annual periods, non-financial schema (`cost_of_revenue`, `gross_profit`, `ebitda`, `operating_income`). |
| C05 | finstack `income_statement` | JPM | PASS | `net_interest_income (FY2025) = 95,443,000,000 USD`, `interest_income`, `interest_expense` | 4 annual periods, **banking-flavoured** schema (no `cost_of_revenue`/`gross_profit`/`ebitda`/`operating_income`). Parallels India C05 HDFCBANK. |
| C06 | finstack `income_statement` | MSFT | PASS | `total_revenue (FY2025, Jun-ending) = 281,724,000,000 USD` | 4 annual periods. |
| C07 | finstack `balance_sheet` | AAPL | PASS | `total_assets = 359,241,000,000 USD`, `long_term_debt`, `inventory` | 4 annual periods, ~60 fields. |
| C08 | finstack `balance_sheet` | JPM | PASS (bank-shape gap) | `total_assets = 4,424,900,000,000 USD`, `held_to_maturity_securities`, `trading_securities`, `cash_cash_equivalents_and_federal_funds_sold`, `preferred_stock_equity` | **Missing: `total_deposits`, `tier_1_ratio` / `cet1_ratio`, `loans` / `allowance_for_loan_losses`, `nim`.** `current_liabilities` / `total_non_current_liabilities` also absent for banks. **Gap G1 — severity: high**, parallels India C08 HDFCBANK. |
| C09 | finstack `balance_sheet` | MSFT | PASS | `total_assets = 619,003,000,000 USD` | 4 annual periods. |
| C10 | finstack `key_ratios` | AAPL | PASS | `pe_trailing = 34.40`, `roe = 1.52`, `free_cash_flow = 106.3B` | Full non-financial ratio shape. |
| C11 | finstack `key_ratios` | JPM | PASS (bank-shape gap) | `pe_trailing = 14.99`, `roe = 0.1647`, `gross_margin = 0.0`, `ebitda_margin = 0.0`, `debt_to_equity = null`, `current_ratio = null`, `quick_ratio = null`, `free_cash_flow = null`, `ev_to_ebitda = null` | Same shape as AAPL/MSFT — **no NIM / tier-1 / CET-1 / CAR substitutes**. `gross_margin`/`ebitda_margin` meaningless for a bank. **Gap G1 — severity: high**, parallels India C11 HDFCBANK. |
| C12 | finstack `key_ratios` | MSFT | PASS (minor gap) | `pe_trailing = 26.97`, `roe = 0.3439`, `dividend_rate = null`, `dividend_yield = null`, `payout_ratio = null`, `ex_dividend_date = null` | MSFT does pay a dividend; `dividend` block nulled out. **Gap G8 — severity: low**, per-ticker. |
| C13 | finstack `sec_filing` | AAPL · 10-K | PASS | 5 filings returned (2021-10-29 → 2025-10-31) | Signature verified. |
| C14 | finstack `sec_filing` | JPM · 10-K | PASS (lookback gap) | **1 filing returned despite `count=5`** (only 2026-02-13 10-K) | Prior FY2024/2023/2022/2021 10-Ks exist on EDGAR but are not returned. **Gap G9 — severity: medium**, M9 multi-year diffing would need fallback. |
| C15 | finstack `sec_filing` | MSFT · 10-K | PASS | 5 filings returned (2021-07-29 → 2025-07-30) | Signature verified. |
| C16 | finstack `sec_filing` | AAPL · 10-Q | PASS | 5 filings returned (2024-08-02 → 2026-01-30) | Signature verified. |
| C17 | finstack `sec_filing` | JPM · 10-Q | PASS (lookback gap, corroborating) | **3 filings returned despite `count=5`** (only 2025 quarters) | Same pattern as C14 — confirms lookback gap is tool-wide on JPM, not 10-K-specific. Rolls into Gap G9. |
| C18 | finstack `sec_filing` | MSFT · 10-Q | PASS | 5 filings returned (2024-10-30 → 2026-01-28) | Signature verified. |

### Verbatim excerpts (selective; full raw JSON in `temp/mcp-smoke-raw-us.md`)

**C08 · finstack `balance_sheet` · JPM** (first 20 lines — bank-shape gap visible, no `total_deposits` / `tier_1_ratio` / `loans`):

```json
{
  "symbol": "JPM",
  "type": "annual",
  "periods": 4,
  "currency": "USD",
  "data": [
    {
      "period": "2025-12-31",
      "total_assets": 4424900000000.0,
      "total_liabilities_net_minority_interest": 4062462000000.0,
      "stockholders_equity": 362438000000.0,
      "preferred_stock_equity": 20045000000.0,
      "long_term_debt": 433970000000.0,
      "current_debt": 66012000000.0,
      "total_debt": 499982000000.0,
      "investments_and_advances": 1406543000000.0,
      "held_to_maturity_securities": 270134000000.0,
      "trading_securities": 636946000000.0,
      "cash_cash_equivalents_and_federal_funds_sold": 679764000000.0
    }
  ]
}
```

**C11 · finstack `key_ratios` · JPM** (bank-shape gap — generic ratios, nulls in place of bank substitutes):

```json
{
  "symbol": "JPM",
  "currency": "USD",
  "valuation": {
    "pe_trailing": 14.990662,
    "price_to_book": 2.4381135,
    "ev_to_ebitda": null,
    "ev_to_revenue": 1.765
  },
  "profitability": {
    "profit_margin": 0.33936,
    "operating_margin": 0.43052,
    "gross_margin": 0.0,
    "ebitda_margin": 0.0,
    "roe": 0.16465,
    "roa": 0.01272
  },
  "financial_health": {
    "debt_to_equity": null,
    "current_ratio": null,
    "quick_ratio": null,
    "total_debt": 1311809994752,
    "free_cash_flow": null
  }
}
```

**C14 · finstack `sec_filing` · JPM · 10-K · count=5** (only 1/5 returned — lookback gap):

```json
{
  "symbol": "JPM",
  "company": "JPMORGAN CHASE & CO",
  "cik": "0000019617",
  "filing_type": "10-K",
  "count": 1,
  "filings": [
    {"form": "10-K", "filing_date": "2026-02-13", "description": "10-K", "url": "https://www.sec.gov/Archives/edgar/data/0000019617/000162828026008131/jpm-20251231.htm"}
  ]
}
```

**C13 · finstack `sec_filing` · AAPL · 10-K · count=5** (full 5/5 — signature + lookback both healthy):

```json
{
  "symbol": "AAPL",
  "cik": "0000320193",
  "filing_type": "10-K",
  "count": 5,
  "filings": [
    {"form":"10-K","filing_date":"2025-10-31","url":"..."},
    {"form":"10-K","filing_date":"2024-11-01","url":"..."},
    {"form":"10-K","filing_date":"2023-11-03","url":"..."},
    {"form":"10-K","filing_date":"2022-10-28","url":"..."},
    {"form":"10-K","filing_date":"2021-10-29","url":"..."}
  ]
}
```

## 3. Summary

**18 / 18 cells pass** the per-cell criterion. No US ADR / cross-listing routing issues (contrast with India C03/C06/C09/C12 where INFY was routed to the NYSE ADR).

Mapping to SPEC §18.2 US Tier-1 requirements:

| SPEC requirement | Status | Detail |
|---|---|---|
| Fundamentals for US non-bank (AAPL, MSFT) | **Covered** | Full `company_profile` + `income_statement` + `balance_sheet` + `key_ratios` shape. |
| Fundamentals for US bank (JPM) | **Partial** | Income statement is bank-flavoured (interest_income / NII / occupancy expense). Balance sheet + ratios return generic US-GAAP-style schema **without** `total_deposits` / `tier_1_ratio` / `loans` / `nim` / CAR / CET-1. **Gap G1 — severity: high**, parallels HDFCBANK (India C08/C11), confirming cross-market finstack banking-schema issue. |
| SEC 10-K / 10-Q filings | **Covered** with one ticker-specific exception | Signature confirmed; AAPL and MSFT return `count=5` for both filing types. **JPM returns only 1/5 on 10-K and 3/5 on 10-Q.** **Gap G9 — severity: medium**; M9 multi-year diff would need an EDGAR direct-call fallback on JPM (and possibly other financials). Latest filing is returned in all cases so Phase 2 US Tier-1 for the most-recent 10-K/10-Q is not blocked. |
| MSFT dividend data | **Partial** | `dividend` block nulled on MSFT despite MSFT paying a dividend. **Gap G8 — severity: low**; AAPL and JPM dividend fields populate. |

Banking-cell focus (per plan §"Banking-specific expectations"):

- **JPM + `get_balance_sheet` (C08)**: missing `total_deposits`, `tier_1_ratio` / `cet1_ratio`, `loans`, `allowance_for_loan_losses`, `nim`. **Gap G1.**
- **JPM + `get_ratios` (C11)**: generic-ratio shape, no NIM / tier-1 / CAR / CET-1 substitutes; `gross_margin`/`ebitda_margin` = 0 (meaningless), many health fields null. **Gap G1.**

Both parallel the HDFCBANK gap on the India side, confirming the finstack banking-shape issue is cross-market (not India-specific). This reinforces that M3's `banking_nbfc` scheme cannot be fixture-sourced from finstack alone; SPEC §15.3 fixture fallback is authoritative.

## 4. Gaps

All gaps affecting US are catalogued in the canonical [`research/mcp-gaps.md`](./mcp-gaps.md). US-market rows (filter on `market = us`):

- **G1** — finstack bank shape (JPM) — severity: high — blocks M3 `banking_nbfc` fixture + Phase 2 US Tier-1 bank analytics.
- **G8** — finstack `key_ratios` dividend block nulled for MSFT — severity: low — M2/M9 per-ticker handling.
- **G9** — finstack `sec_filing` multi-year lookback for JPM returns `count=1` on 10-K, `count=3` on 10-Q despite `count=5` arg — severity: medium — M9 multi-year diff fallback to EDGAR direct call.
