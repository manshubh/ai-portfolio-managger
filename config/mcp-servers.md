# MCP servers — install, register, preflight

> Version pins verified **2026-04-22**: `finstack-mcp` 0.10.0, `nsekit-mcp` 0.0.22, `nse-bse-mcp` 0.1.5. See [THIRD_PARTY.md](../THIRD_PARTY.md) (M0.4) for the canonical pin list; this file is the operational doc. Upgrading any MCP is a separate `bd` ticket per [SPEC §19.14](../docs/SPEC.md).

## 1. What these MCPs are

Three Model Context Protocol servers serve as **Tier A** sources for the project's data-fetch skills per [SPEC §15.1–§15.3](../docs/SPEC.md). Together they cover Indian fundamentals/quotes (NSE + BSE), US fundamentals + SEC filings, and India corporate actions. SPEC §18.2 names the exact tool list consumed by the M2/M9 `fundamentals-fetch` aggregator and SPEC §6.2 names the corp-actions tool consumed by M5. When all three MCPs are unavailable or return no data, skills fall back to Tier B (direct HTTPS) and Tier C (web search) as defined in SPEC §15.

> **Canonical authority for tool selection and gaps:** [`research/mcp-gaps.md`](../research/mcp-gaps.md). That file is the single source of truth for "which MCP + which tool for which SPEC field, and what to substitute when a gap bites". This file (`config/mcp-servers.md`) is the operational / install doc; it mirrors the version pins but does **not** duplicate the authority matrix or the gap log.

## 2. Per-MCP table

| Name | Version pin | Install / run command | License | Tools used by this project | Known limits |
|---|---|---|---|---|---|
| `finstack-mcp` | **0.10.0** (PyPI) | `uvx finstack-mcp@0.10.0` (alt: `pipx install finstack-mcp==0.10.0`, then `python -m finstack.server`) | MIT | `get_fundamentals`, `get_income_statement`, `get_balance_sheet`, `get_ratios`, `get_fii_dii`, `get_sec_filing` | None known at pin time; SEC filing signature verified in smoke test. |
| `nsekit-mcp` | **0.0.22** (PyPI) | `uvx nsekit-mcp@0.0.22` | **None declared** — see §5 | `equity_history` (India MAs), `corporate_events` (M5) | Early-stage (0.0.x); NSE only; no BSE, no US. R1 in the plan. |
| `nse-bse-mcp` | **0.1.5** (npm) | `npx -y nse-bse-mcp@0.1.5` (runs HTTP server) + `npx -y mcp-remote@latest http://localhost:3000/mcp --allow-http` in client | MIT | `nse_equity_quote` (India live-quote fallback) | Requires a foreground server process — see §4. |

The finstack choice of `uvx` (not `python -m finstack.server`) pins the version **inside** the registration JSON and removes the pre-install step, matching the shape nsekit already uses.

## 3. Registration

Registration is project-scoped and checked into the repo at **two** files so the project works in either IDE without per-user fiddling:

- `.mcp.json` at the repo root — **Claude Code** project-scoped registration.
- `.cursor/mcp.json` — **Cursor** project-scoped registration.

Both files share the same JSON shape:

```json
{
  "mcpServers": {
    "finstack":  { "command": "uvx", "args": ["finstack-mcp@0.10.0"] },
    "nsekit":    { "command": "uvx", "args": ["nsekit-mcp@0.0.22"] },
    "nse-bse":   { "command": "npx", "args": ["-y", "mcp-remote@latest", "http://localhost:3000/mcp", "--allow-http"] }
  }
}
```

User-scoped alternatives `~/.claude.json` and `~/.cursor/mcp.json` also work, but the repo-scoped files take precedence and travel with the project — preferred.

> **Deviation from the bd issue wording.** The M0.3 bd description originally referenced `.claude/settings.json`. Current Claude Code MCP registration lives in `.mcp.json` at the repo root; `.claude/settings.json` is reserved for hooks and permissions and already holds bd's `PreCompact` / `SessionStart` hooks. We ship `.mcp.json` and leave the existing `.claude/settings.json` untouched. The bd close-note records this.

### Prerequisite toolchain

| Tool | Purpose | Check |
|---|---|---|
| `uv` (and `uvx`) | Launches `finstack-mcp` and `nsekit-mcp` without pre-install | `uvx --version` |
| Node / `npx` | Launches `nse-bse-mcp` server + `mcp-remote` client bridge | `npx --version` |

If either is missing: `brew install uv node`.

## 4. `nse-bse-mcp` preflight

`nse-bse-mcp` is an **HTTP server** — the MCP client does not spawn it. Before any Cursor/Claude session that needs BSE/NSE quote data, start the server in a dedicated terminal:

```bash
npx -y nse-bse-mcp@0.1.5
# stays foreground; leaves http://localhost:3000/mcp listening
```

Leave that terminal open for the duration of the session. Stop it with Ctrl-C when done. If the server is not running, every `nse-bse` tool call fails with a connection error — this is expected and **not** a bug.

The US session documented in §6 does not need this server running (no `nse-bse` tools are called for US tickers).

## 5. NseKit license posture

`NseKit-MCP` at 0.0.22 ships with **no LICENSE file, no license declared in `pyproject.toml`, and the GitHub API's repository license field is `null`.** Proceed with risk awareness: do not redistribute; confine use to local tool invocation. Revisit if usage extends beyond local Phase 1 corp-actions queries. (M0.4 copies this language verbatim into `THIRD_PARTY.md`.)

Verified 2026-04-22:

- `GET https://pypi.org/pypi/nsekit-mcp/0.0.22/json` → `info.license` = `null`, no `License ::` classifier.
- `GET https://api.github.com/repos/Prasad1612/NseKit-MCP` → `license` = `null`.
- `GET https://api.github.com/repos/Prasad1612/NseKit-MCP/contents/LICENSE` → `404`.

If NseKit becomes a distribution blocker later (e.g., the repo is published as a product), a fork-or-replace bd ticket gets filed and this file is updated. Until then, local invocation is acceptable.

## 6. Smoke-test references

The smoke protocol (M0.3 plan §"Smoke-test matrix") exercises every tool named in SPEC §18.2 plus `corporate_events` (§6.2) across three tickers per market, in **two separate sessions** (India + US) run in fresh Cursor/Claude windows. Total: **42 cells** (24 India + 18 US).

The user runs both sessions — the agent cannot, because this agent has none of the three MCPs registered in its own session. Paste-ready prompts live in `plans/M0/M0.3-smoke-script-{india,us}.md`; raw outputs are captured to `temp/mcp-smoke-raw-{india,us}.md` (gitignored scratch); final evidence is written to:

- [`research/mcp-smoke-test-india.md`](../research/mcp-smoke-test-india.md) — 24 cells (RELIANCE.NS, HDFCBANK.NS, INFY.NS).
- [`research/mcp-smoke-test-us.md`](../research/mcp-smoke-test-us.md) — 18 cells (AAPL, JPM, MSFT).

## 7. Tool selection, authority matrix, and coverage gaps

All three live in the single canonical [`research/mcp-gaps.md`](../research/mcp-gaps.md):

- **§1 Selected MCP servers** — which of the three is PRIMARY / SECONDARY / TERTIARY and which tools are actually called.
- **§2 Tool authority matrix** — for each SPEC §18.2 / §6.2 requirement, the actual MCP + tool + signature, including fallback paths.
- **§3 Gap log** — cross-market rows (`market` column), each with severity, downstream phase, bd follow-up, and resolution path.
- **§4 Consumer pointers** — explicit per-milestone read-this instructions (M2, M3, M5, M9, M14).

M0.3 seeded the file with 9 gaps (1 high, 3 medium, 5 low) and 4 bd follow-ups from the 42-cell smoke. Downstream milestones update it in place — do not branch authority across additional files.
