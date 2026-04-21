# M0 Research — Foundations & Audit

> Investigation notes for M0 subtasks. Conducted 2026-04-18.

---

## M0.1: Wealthfolio

- **Latest release:** v3.2.1 (April 3, 2026)
- **Install:** `brew install --cask wealthfolio` (macOS, Intel + Apple Silicon)
- **DB path (macOS):** `~/Library/Application Support/com.teymz.wealthfolio/app.db`
- **Override:** `WF_DB_PATH` env var
- **Schema:** 28 tables via Diesel ORM (Rust) + 28 migrations
- **Core tables for us:** `accounts`, `activities`, `assets`, `quotes`, `daily_account_valuation`, `holdings_snapshots`, `platforms`
- **Source:** https://github.com/afadil/wealthfolio

### Key tables (relevant to SPEC §5.3 queries)

| Table | Purpose |
|-------|---------|
| `accounts` | Brokerage accounts (id, name, account_type, group, currency, platform_id) |
| `activities` | Transactions (account_id, asset_id, activity_type, activity_date, quantity, unit_price, amount, fee, currency, fx_rate) |
| `assets` | Securities (id, kind, name, display_code, instrument_type, instrument_symbol, instrument_exchange_mic) |
| `quotes` | Price history (asset_id, day, open, high, low, close, adjclose, volume, currency) |
| `daily_account_valuation` | Daily snapshots (account_id, valuation_date, cash_balance, investment_market_value, total_value, cost_basis, net_contribution) |
| `holdings_snapshots` | Point-in-time positions (account_id, snapshot_date, positions JSON, cash_balances, cost_basis) |

---

## M0.2: virattt/ai-hedge-fund

> **Resolved 2026-04-21.** Pin decision and license posture are final; authoritative record is [`research/ai-hedge-fund-pin-0f6ac48.md`](../ai-hedge-fund-pin-0f6ac48.md). Consumed by M0.4 (`THIRD_PARTY.md`) and M3 (scoring-engine port). The notes below are the pre-plan investigation context.

- **Latest commit SHA:** `0f6ac487986f7eb80749ed42bd26fb8330c450db`
- **License:** README claims MIT, but **no LICENSE file exists** in the repo. GitHub API returns `license: null`.
- **Source:** https://github.com/virattt/ai-hedge-fund

### Personas available (22 files in `src/agents/`)

**Needed for SPEC §8.3 (MVP roster):**
- `rakesh_jhunjhunwala.py` — India legend
- `warren_buffett.py` — Moat investor
- `charlie_munger.py` — Quality + inversion
- `mohnish_pabrai.py` — Deep value
- `ben_graham.py` — Margin of safety
- `phil_fisher.py` — Growth + quality
- `aswath_damodaran.py` — Valuation + story
- `peter_lynch.py` — GARP

**Functional agents (also needed for M3):**
- `fundamentals.py` — Rule-based scoring (ROE, margins, growth, valuation)
- `risk_manager.py` — Volatility, correlation, position limits
- `phil_fisher.py` — Hybrid (rule-based + LLM narrative)

**Extras (not in our MVP):**
- `bill_ackman.py`, `cathie_wood.py`, `michael_burry.py`, `nassim_taleb.py`, `stanley_druckenmiller.py`
- `growth_agent.py`, `news_sentiment.py`, `portfolio_manager.py`, `sentiment.py`, `technicals.py`, `valuation.py`

### License risk

The README states: "This project is licensed under the MIT License - see the LICENSE file for details."
However, the LICENSE file is missing from the repository. This is a discrepancy worth noting in THIRD_PARTY.md.

---

## M0.3: MCP Servers

All three servers named in the SPEC exist and are installable.

### finstack-mcp (PRIMARY)

| Field | Value |
|-------|-------|
| Package | `finstack-mcp` (PyPI) |
| Version | 0.10.0 (April 9, 2026) |
| License | MIT |
| GitHub | https://github.com/finstacklabs/finstack-mcp |
| Tools | ~95 |
| Coverage | India (NSE+BSE) + US + crypto + forex + SEC EDGAR |
| API key | Not required for base |

**Key capabilities:** fundamental data, income statement, balance sheet, cash flow, key ratios, company profile, dividend history, SEC filings (10-K, 10-Q, 8-K), promoter shareholding, pledge data, FII/DII flows, corporate actions, NSE/BSE live quotes, options chain.

**Config:**
```json
{
  "mcpServers": {
    "finstack": {
      "command": "python",
      "args": ["-m", "finstack.server"]
    }
  }
}
```

### NseKit-MCP

| Field | Value |
|-------|-------|
| Package | `nsekit-mcp` (PyPI) |
| Version | 0.0.22 (March 25, 2026) |
| License | **None specified** |
| GitHub | https://github.com/Prasad1612/NseKit-MCP |
| Tools | 100+ |
| Coverage | NSE only (no BSE, no US) |

**Config:**
```json
{
  "mcpServers": {
    "NseKit-MCP": {
      "command": "uvx",
      "args": ["nsekit-mcp@latest"]
    }
  }
}
```

**Risk:** No license, 0 GitHub stars, NSE-only, early stage (v0.0.22).

### nse-bse-mcp

| Field | Value |
|-------|-------|
| Package | `nse-bse-mcp` (npm) |
| Version | 0.1.5 |
| License | MIT |
| GitHub | https://github.com/bshada/nse-bse-mcp |
| Tools | 60 |
| Coverage | NSE + BSE (India only, no US) |

**Config:**
```json
{
  "mcpServers": {
    "nse-bse-mcp": {
      "command": "npx",
      "args": ["-y", "mcp-remote@latest", "http://localhost:3000/mcp", "--allow-http"]
    }
  }
}
```

### Comparison

| Feature | finstack-mcp | NseKit-MCP | nse-bse-mcp |
|---------|-------------|------------|-------------|
| India (NSE) | Yes | Yes | Yes |
| India (BSE) | Yes | No | Yes |
| US markets | **Yes** | No | No |
| SEC filings | **Yes** | No | No |
| Fundamentals | **Yes** | No | No |
| License | MIT | **None** | MIT |
| Maturity | Active | Early | Stable |

### Recommendation

finstack-mcp is the clear primary. It covers India + US in one server with fundamentals, SEC, and no API key. nse-bse-mcp adds raw exchange data (bhavcopy, scrip-level BSE). NseKit-MCP is redundant and has license risk.

---

## Open Questions (for user)

1. Is Wealthfolio already installed, or should M0.1 just document the process?
2. ~~ai-hedge-fund has no LICENSE file despite claiming MIT — proceed noting the discrepancy?~~ **Resolved:** proceed with the pin, capture standard MIT template with reconstructed copyright line, disclose the discrepancy in `THIRD_PARTY.md`. See [`research/ai-hedge-fund-pin-0f6ac48.md §5`](../ai-hedge-fund-pin-0f6ac48.md).
3. MCP selection: keep all three per SPEC, or trim to finstack-mcp + nse-bse-mcp (dropping the unlicensed NseKit-MCP)?
