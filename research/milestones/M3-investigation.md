# M3 — `scoring-engine` investigation

> **R** step of RPI for epic [ai-portfolio-manager-vfq](../../.beads/). Snapshot of the design decisions feeding M3 decomposition. Authoritative behavior lives in [`docs/SPEC.md §6.3, §7.6, §8.2–§8.6, §9, §10.5, §10.6, §18.3, §19.2 inv. 15–16`](../../docs/SPEC.md) and [`docs/implementation.md §M3`](../../docs/implementation.md). Pin manifest at [`THIRD_PARTY.md §2.1`](../../THIRD_PARTY.md) (10 port targets at `virattt/ai-hedge-fund@0f6ac48`).
>
> **Reference shorthand:** "M0.5" refers to the M0 sub-task that landed [`input/india/philosophy.md`](../../input/india/philosophy.md) with the §7.6 YAML front-matter. "M0.4" landed [`THIRD_PARTY.md`](../../THIRD_PARTY.md). M3 flips the `Ported?` cells in §2.1.

## Goal recap

All deterministic scoring math — threshold pass/fail (§9.3), philosophy-fit graded score (§9.2 ladder), persona base scores (§9.4), and concentration sanity (§9.5) — is reproducible from JSON fixtures with zero LLM involvement. Output is JSON; the LLM consumes it in Phases 4/5/6 to compose narrative. Acceptance bar: the §9.3 INFY example is reproducible field-for-field; banking/NBFC scheme is exercised by an HDFCBANK fixture; the fundamentals-first invariant test passes (35/35 + 20/20 + 20/20 + 0/15 + 0/10 = 75 stays Conviction Hold); a 10-ticker `holdings.json` produces HHI + per-stock vol-adjusted limits + a top-5 correlation matrix.

The biggest contract surface change is **§4 below**: persona ports need multi-period line-item arrays that the current §18.2 `metrics.json` does not yet emit. M3 defines the extended shape; M9's `fundamentals-fetch` aggregator emits it.

---

## 1. Implementation shape — pure Python, single `engine.py`

`skills/scoring-engine/` ships as a Python package; there is no shell entrypoint (M2 needed `query.sh` because it dispatched to `sqlite3`; M3 has no shell-only surface).

- `skills/scoring_engine/engine.py` — `argparse` CLI dispatching the four subcommands from [SPEC §18.3](../../docs/SPEC.md): `check-thresholds`, `persona`, `concentration-check`, `full`.
- `skills/scoring_engine/my_philosophy.py` — greenfield primary scorer (see §3).
- `skills/scoring_engine/risk_manager.py` — port for `concentration-check` (see §6).
- `skills/scoring_engine/personas/{jhunjhunwala,buffett,munger,pabrai}.py` — MVP roster ports (see §5).
- `skills/scoring_engine/lib/line_items.py` — adapter between our extended `metrics.json` (see §4) and the upstream `analyze_*(line_items)` sub-functions.
- `skills/scoring_engine/__init__.py` — package marker.
- `skills/scoring_engine/requirements.txt` and `README.md`.

### Hyphen → underscore deviation

[SPEC §17](../../docs/SPEC.md) shows the directory as `skills/scoring-engine/`; we deviate to `skills/scoring_engine/` because Python module identifiers can't contain hyphens. This is the same hyphen→underscore rename M2 did for `wealthfolio_query`. The CLI command and skill **name** stay hyphenated (`scoring-engine check-thresholds …`); only the directory and Python package use the underscore. M3 amends [SPEC §17](../../docs/SPEC.md) and [`docs/implementation.md §M3`](../../docs/implementation.md) in the same commit that lands the package, mirroring M2's precedent (recorded in M2's investigation §1).

### Invocation

```
python3 -m skills.scoring_engine.engine check-thresholds --philosophy <p> --scheme non_financial --metrics <m.json>
```

Match [SPEC §18.3](../../docs/SPEC.md)'s public surface: `--help` produces the contract; failures return non-zero with a JSON error on stderr. Exit code matrix is small — 0 on success, 1 on bad input (missing required field, schema mismatch), 2 on internal error. Insufficient-data persona output is **exit 0** (see §5.2 below).

---

## 2. Rubric ownership — `my_philosophy.py` grades PF/15 only

**Decision: Q1 = (a).** `my_philosophy.py` deterministically computes the §9.3 pass/fail table and the §9.2 graded `philosophy_fit` sub-score (PF: 0 / 8 / 15). It does **not** compute F/35, BS/20, V/20, or N/10. The Phase 4 LLM judges those four against the qualitative `[Biz]`/`[News]` content per [SPEC §10.5](../../docs/SPEC.md), then writes the `## Scoring` block citing the deterministic PF and threshold-table values.

This resolves a real wording conflict: [`docs/implementation.md §M3 Deliverables`](../../docs/implementation.md) says `my_philosophy.py` is the *"exclusive source of truth for the portfolio score"*, which contradicts §9.6 (Business Story) calling itself analyst judgment and §10.5 prose putting the LLM in charge of composing F/BS/V/N. **M3 amends [`docs/implementation.md §M3`](../../docs/implementation.md)** to say:

> `my_philosophy.py` is the exclusive source of truth for the philosophy-fit (PF/15) sub-score and the §9.3 threshold pass/fail table. The Fundamental, Business Story, Valuation, and News sub-scores remain Phase 4 LLM judgments per [SPEC §10.5](docs/SPEC.md), composed using the deterministic table as evidence.

This amendment is one of M3's first deliverables (alongside the M2 hyphen-rename precedent).

### Output of `check-thresholds` (§9.3 contract, unchanged)

```json
{ "ticker": "...", "scheme": "...", "checks": [ ... ], "pass_count": N, "fail_count": M,
  "dealbreakers_triggered": [...], "philosophy_fit_graded": 0|8|15 }
```

`philosophy_fit_graded` is the deterministic PF that the LLM quotes verbatim. The graded ladder (§9.2):
- 0 dealbreakers, 0 non-dealbreaker fails → **15**
- 0 dealbreakers, 1–2 non-dealbreaker fails → **8**
- 0 dealbreakers, 3+ non-dealbreaker fails → **0**
- ≥1 dealbreaker triggered → **0** (overrides any pass count)

Dealbreakers per §9.2: zero promoter (unless `sector_exceptions.{name}.exempt: true`), confirmed fraud / SEBI/SEC action (caller signals via a `metrics.governance_red_flag: true` boolean), and `[Phil] Thesis: SELL|EXIT` (caller signals via `metrics.user_thesis_exit: true`). The engine doesn't web-search; it consumes booleans the agent provides.

### Sector-exception application

Decision: Q3 = caller-decides. The CLI takes `--sector-exception <name>` as an optional flag. Phase 4's prompt is responsible for inferring `it_mnc` / `psus` / `hospitals` / `foreign_sub` / `stock_exchanges` from the `[Overview] Sector` line and passing the flag. The engine looks up the named entry under `sector_exceptions:` in the philosophy YAML, applies its keys to the relevant threshold rows, and emits `effective_threshold` + `pass_with_exception: true` exactly per the §9.3 INFY example. `stock_exchanges.exempt: true` short-circuits the zero-promoter dealbreaker.

`--scheme {non_financial|banking_nbfc}` is also caller-supplied — same principle. Phase 4 detects banking/NBFC from sector and passes the flag.

---

## 3. Extended `metrics.json` — adds `line_items[]` arrays

**Decision: Q2 = (B1).** We extend the §18.2 contract to include multi-period line-item arrays alongside the existing summary ratios. This adds shape complexity in `fundamentals-fetch` but preserves upstream persona logic intact (the SPEC §8.3 "retain native internal math scales" guidance), keeps M3 from doing lossy re-derivations, and lines up naturally with what `finstack-mcp get_income_statement` / `get_cash_flow` already return.

### New `metrics.json` fields (additive — existing keys unchanged)

```jsonc
{
  "ticker": "INFY", "as_of": "2026-04-17",
  "fund": { /* existing summary ratios — single-period */ },
  "valu": { /* existing valuation/price block — single-period */ },
  "history": {
    "period_type": "annual",        // "annual" or "ttm" — agent picks per-persona need
    "periods": ["FY26","FY25","FY24","FY23","FY22","FY21","FY20","FY19"],   // newest-first
    "line_items": [                  // one entry per period (same length & order as `periods`)
      {
        "revenue":                       12345,
        "gross_profit":                   4567,
        "gross_margin":                   0.37,
        "operating_income":               2345,
        "operating_margin":               0.19,
        "net_income":                     1890,
        "earnings_per_share":             45.2,
        "ebit":                           2345,
        "free_cash_flow":                 1670,
        "total_debt":                      230,
        "cash_and_equivalents":           4500,
        "current_assets":                 8900,
        "current_liabilities":            3400,
        "total_assets":                  21000,
        "total_liabilities":              5800,
        "shareholders_equity":           15200,
        "capital_expenditure":             400,
        "depreciation_and_amortization":   180,
        "outstanding_shares":             4150,
        "dividends_and_other_cash_distributions": 720,
        "issuance_or_purchase_of_equity_shares":   0,
        "return_on_equity":               0.287,
        "return_on_invested_capital":     0.330
      },
      ...
    ]
  },
  "governance_red_flag": false,         // boolean — set by Phase 2 agent if confirmed fraud / SEBI action
  "user_thesis_exit":    false,         // boolean — set by Phase 2 from [Phil] Thesis line
  "sources": [...], "missing_fields": [...]
}
```

### Field selection rationale

The line-item attribute names exactly mirror upstream's `search_line_items()` keys so the ported `analyze_*` functions read them with no rename. The union covers what the four MVP personas need (verified by reading upstream heads of `mohnish_pabrai.py`, `rakesh_jhunjhunwala.py`, `warren_buffett.py`, `charlie_munger.py` at SHA `0f6ac48`). Currency: native ledger currency (₹ Cr for India) — consistent with `fund.mcap_cr`. INR/USD distinction stays in the per-market caller; the engine does not convert.

### Period semantics

- `period_type: annual` is the default. We pick annual because Indian filings are annually-reported for many of these line items (capex, dividends, depreciation), and 8 annual periods is what Pabrai's upstream call uses (`limit=8`). Personas that originally called with `period="ttm", limit=5` (Jhunjhunwala) consume the latest 5 entries of the annual array — documented as a deliberate simplification in the persona's port-header comment.
- `periods` is newest-first, so `line_items[0]` is the most recent period. Upstream code conventions vary; the line-items adapter (§1's `lib/line_items.py`) normalizes to newest-first regardless of upstream order.
- Missing periods: when fewer than the requested N are available, the array is shorter. Personas that require a minimum (e.g. growth analysis needs ≥3 periods) emit `signal: insufficient_data` with the missing-period count cited (see §5.2).

### Coordination with M9

The extended shape is M3's contract. M9 implements the fundamentals-fetch aggregator that **emits** it. M3 hand-writes fixtures (`infy.json`, `hdfcbank.json`) matching this shape so persona porting and `my_philosophy` testing are not blocked on M9. M3 files a `bd` follow-up onto the M9 epic referencing this section so M9 doesn't drift.

The §18.2 schema in [`docs/SPEC.md`](../../docs/SPEC.md) gets amended in the same M3 commit that lands the contract — additive only (existing keys unchanged), so backward-compatible with anything already reading just summary ratios.

---

## 4. Port scope — 4 MVP personas, 6 deferred

**Decision: Q6 = MVP roster only.** M3 ports `jhunjhunwala`, `buffett`, `munger`, `pabrai`. The 6 non-MVP targets in [`THIRD_PARTY.md §2.1`](../../THIRD_PARTY.md) (`fundamentals.py`, `phil_fisher.py`, `ben_graham.py`, `aswath_damodaran.py`, `peter_lynch.py`, plus the upstream `risk_manager.py` which IS ported but for `concentration-check`, not as a persona) split as:

- **`risk_manager.py`** — ported in M3 (§6 below) for `concentration-check`. Not a persona.
- **`fundamentals.py`** — *referenced* by §6.3, but its threshold-counting pattern is what `my_philosophy.py` re-implements against our YAML. **Not ported** as code; the upstream-attribution header is captured in `my_philosophy.py` to honor MIT (we copied its *idea*; we did not copy its source).
- **`phil_fisher.py`** — its weight pattern is referenced by §6.3 ("our Phase 4 uses its weight pattern already"). The pattern is documented in `my_philosophy.py`'s comments; the file itself is **not ported** in M3. Listed in §8.3 as "available but not in MVP default".
- **`ben_graham.py`, `aswath_damodaran.py`, `peter_lynch.py`** — opt-in personas per §8.3. **Deferred** to a follow-up `bd` issue (e.g. M3.x-deferred-persona-ports) filed on milestone close, not a blocker for M3 acceptance.

### THIRD_PARTY.md ports table updates at M3 close

For the 4 MVP files: flip `Ported?` `pending` → `ported <commit-sha>`. For the 6 deferred files: leave `pending` in §2.1 and add a note pointing at the follow-up `bd` issue. The pinned SHA does not change.

---

## 5. Persona port mechanics

### 5.1 Upstream-stripping scope (Q8)

Each ported file at SHA `0f6ac48` imports `langchain_core`, `pydantic`, `src.graph.state`, `src.tools.api`, `src.utils.llm`, `src.utils.progress`. Strip:

- The top-level `<persona>_agent(state, agent_id)` entrypoint (uses `state` graph, `progress` tracker, `call_llm`).
- The `BaseModel` Pydantic signal class (we emit dicts, not Pydantic).
- Calls to `get_financial_metrics()`, `search_line_items()`, `get_market_cap()` — replaced with reads from the dict our adapter produces from `metrics.json`.
- `langchain_core.prompts.ChatPromptTemplate`, `HumanMessage`, `call_llm` — gone entirely. The LLM rationale is generated in Phase 5 by the agent reading our `signal`/`sub_scores`/`weighted_score`, not by the engine.

Keep:

- The math sub-functions: `analyze_growth(...)`, `analyze_downside_protection(...)`, `analyze_pabrai_valuation(...)`, etc. These read line-item arrays and return numeric scores plus brief detail strings — pure Python, no I/O.
- The threshold tables embedded in those functions (per §8.3 "retain native internal math scales").
- The combination weights (e.g. Pabrai: `downside*0.45 + valuation*0.35 + …`).

Each ported file's header comment retains:

```python
# Ported from virattt/ai-hedge-fund src/agents/<file>.py
# at commit 0f6ac487986f7eb80749ed42bd26fb8330c450db (THIRD_PARTY.md §2.1)
# Stripped: langchain LLM call, Pydantic signal model, src.graph.state plumbing.
# Adapted: data input now flows from skills.scoring_engine.lib.line_items.
```

### 5.2 Output contract — deterministic core, optional graceful-degradation (Q6 follow-up)

Every persona CLI emits:

```json
{ "ticker": "INFY", "persona": "jhunjhunwala",
  "sub_scores": { "management_quality": 8.5, "secular_growth": 7.0, "valuation": 5.5, "technical_context": 6.0 },
  "weighted_score": 72, "max_score": 100,
  "signal": "bullish", "confidence": 0.72,
  "details": { "<sub_score_name>": "<one-line cited detail string>", ... } }
```

When required line-items are missing — e.g. Pabrai needs ≥3 years of `free_cash_flow` and `total_debt` for downside protection, Jhunjhunwala needs ≥3 years of revenue & EPS for growth — the persona emits the **insufficient-data** payload instead:

```json
{ "ticker": "INFY", "persona": "jhunjhunwala",
  "signal": "insufficient_data", "confidence": 0.0,
  "missing_fields": ["history.line_items[2].revenue", "history.line_items[3].free_cash_flow"],
  "min_periods_required": 3, "min_periods_available": 1 }
```

Exit code is **0** in both cases — the caller (Phase 5 prompt, M11) decides whether to skip that persona's row in the `## Persona Cross-Check` block. `my-philosophy` is **exempt from insufficient-data** because it consumes only summary ratios from `fund.*` and the YAML thresholds, both guaranteed present by Phase 1+2. This gives "make personas optional" two layers:

- Per-persona automatic graceful degradation when data is incomplete (M3's contribution).
- Run-level skip via `personas_enabled: []` in YAML or a Phase-5 CLI flag (M11's contribution; out of M3 scope).

### 5.3 Determinism

Two runs on identical inputs must produce identical `sub_scores`, `weighted_score`, and `signal`. No `random.*`, no wall-clock, no `dict` ordering surprises (sub_scores emitted in fixed declared order). Each persona has a regression test asserting byte-equal repeated output.

---

## 6. `concentration-check` — `risk_manager.py` port + price-history shape (Q4)

`risk_manager.py` is ported intact (math-only stripped of `state`/`progress`). It produces:

- **HHI** = Σ(weight_i²) across holdings, where `weight_i = market_value_i / total_market_value`.
- **Per-stock vol-adjusted limit** = `calculate_volatility_adjusted_limit(prices_i, base_limit_pct)` — base_limit_pct comes from `position_sizing.max_per_stock_pct` in the YAML.
- **Correlation matrix** — pairwise Pearson correlations of daily returns over the lookback window; output is the top-5 correlation pairs by absolute value.

### Inputs

```
scoring-engine concentration-check \
  --holdings <holdings.json> \
  --price-history <prices.json> \
  --philosophy <philosophy.md>
```

`holdings.json` is straightforward (ticker, market_value, allocation_pct, sector — derivable from `temp/research/portfolio-snapshot.csv`).

`prices.json` shape — defined here, fetched elsewhere:

```jsonc
{
  "as_of": "2026-04-17",
  "lookback_days": 252,
  "tickers": {
    "RELIANCE.NS": { "dates": ["2025-04-18", ...], "closes": [2840.5, ...] },
    "INFY.NS":     { "dates": ["2025-04-18", ...], "closes": [1455.0, ...] },
    ...
  }
}
```

Daily closes, base-currency unnecessary (correlation is scale-invariant; vol uses log-returns). Missing days are simply omitted; the correlation pair-up uses the intersection of available dates per pair (documented in `risk_manager.py`'s docstring).

### Where the fetch happens — M8, not M3

**Decision: Q4 yes.** M3 defines the contract and ships a small fetcher stub at `skills/scoring_engine/lib/fetch_prices.py` that **only reads from a path** (no network) — for testing, the path points at a fixture; for real use, M8's Phase 1 prompt fetches the history (via NseKit / yfinance per the per-market source-tier rules in §15) and writes `temp/research/prices.json` once per run. This aligns with invariant 12 (Phase 1 snapshot is frozen) — price history is a Phase 1 artifact, not re-fetched downstream.

M3 files a follow-up `bd` issue on the M8 epic: "Phase 1 emits temp/research/prices.json per scoring-engine concentration-check contract".

---

## 7. `scoring-engine full` semantics (Q5)

`full --ticker T --metrics m.json --philosophy p.md` returns:

```json
{ "thresholds": { /* check-thresholds output */ },
  "my_philosophy": { /* my-philosophy persona output */ } }
```

**No rotating personas.** The agent calls `persona --persona <name>` separately for each rotation pick in Phase 5. `full` is the single-call convenience for Phase 4 (which wants threshold table + the user's own persona verdict in one shot). This matches [SPEC §18.3](../../docs/SPEC.md): *"combined output (thresholds + my-philosophy persona)"*.

---

## 8. Fixtures and test plan

### Fundamentals-engine fixtures (`tests/scoring-engine/`)

| Fixture | Scheme | Purpose |
|---|---|---|
| `infy.json` | non_financial | Reproduces SPEC §9.3 example field-for-field; exercises `it_mnc` sector exception (promoter 14.5% with `effective_threshold: 10`, `pass_with_exception: true`) |
| `hdfcbank.json` | banking_nbfc | GNPA / NNPA / CASA / NIM / ROA / CAR thresholds; PF graded path |
| `coalindia.json` | non_financial | `psus` exception (promoter ≥45% government check) |
| `bse.json` | non_financial | `stock_exchanges.exempt: true` short-circuits zero-promoter dealbreaker |
| `fundamentals_first.json` | non_financial | Synthetic — strong fund + strong moat + rich PE → asserts `philosophy_fit_graded ≥ 8` and that no LLM-side composition could push the result below Conviction Hold (asserted in a wrapper test that calls into `my_philosophy` only) |
| `dealbreaker_zero_promoter.json` | non_financial | Promoter = 0% non-exempt → `dealbreakers_triggered: ["zero_promoter"]`, PF=0 |
| `dealbreaker_thesis_sell.json` | non_financial | `user_thesis_exit: true` → PF=0 regardless of pass count |

Each fixture includes the new `history.line_items[]` array (≥8 periods) so persona ports can be exercised against the same files without a separate fixture set.

### Persona-engine fixtures

For each of the 4 MVP personas: one regression fixture that asserts `sub_scores`, `weighted_score`, and `signal` are stable across two runs. Plus one `insufficient_data` fixture per persona (truncated history) asserting the graceful-degradation payload shape and exit 0.

### Concentration-engine fixture

One 10-ticker `holdings.json` + matching `prices.json` (252 trading days × 10 tickers, hand-stubbed). Asserts HHI within 0.001 of expected, vol-adjusted limit per stock within 0.5pp, top-5 correlation pairs match expected (ranked by abs value).

### Linting

`ruff` on every Python file (matches M2's `requirements.txt` style); `python -m pytest tests/scoring-engine/` is the runner. No `shellcheck` (no shell files).

---

## 9. Doc-hygiene artifacts (M3 closes)

- **[`docs/implementation.md §M3`](../../docs/implementation.md)** — amend the deliverable line about `my_philosophy.py` per §2 above (PF-only ownership, not full rubric).
- **[`docs/SPEC.md §17`](../../docs/SPEC.md)** — rename `scoring-engine` directory cell to `scoring_engine` (hyphen→underscore, M2 precedent).
- **[`docs/SPEC.md §18.2`](../../docs/SPEC.md)** — additive amendment for the `history.line_items[]` and `governance_red_flag` / `user_thesis_exit` fields per §3 above.
- **[`THIRD_PARTY.md §2.1`](../../THIRD_PARTY.md)** — flip 4 `Ported?` cells; note 6 deferred targets and link to follow-up `bd` issue.
- **§7 revision log** in `THIRD_PARTY.md` — one new row dated M3 close.

---

## 10. Resolved questions log

| # | Question | Decision |
|---|---|---|
| Q1 | Rubric ownership: deterministic vs LLM | **(a)** `my_philosophy.py` deterministic for §9.3 table + PF/15 only. F/BS/V/N stay LLM. impl.md §M3 wording amended (§2). |
| Q2 | Persona input shape | **(B1)** Extend `metrics.json` with `history.line_items[]` arrays, mirroring upstream's `search_line_items()` keys (§3). |
| Q3 | Sector-exception + scheme dispatch | Caller (Phase 4 agent) decides; engine applies. CLI flags `--sector-exception` and `--scheme` (§2). |
| Q4 | `concentration-check --price-history` source | M3 defines `prices.json` shape; M8 Phase 1 fetches and writes it (§6). |
| Q5 | `scoring-engine full` semantics | `check-thresholds` + `my-philosophy` only; rotating personas called separately (§7). |
| Q6 | Port scope | 4 MVP personas (jhun/buffett/munger/pabrai) + risk_manager. 6 deferred behind a follow-up `bd` issue. **Plus**: per-persona `insufficient_data` graceful degradation (§5.2). |
| Q7 | CLI shape | Single `engine.py` Python entry, no shell shim, hyphen→underscore directory deviation (§1). |
| Q8 | Upstream-stripping scope | Strip langchain / pydantic signal / state plumbing / upstream API fetchers; keep math sub-functions and threshold tables (§5.1). |

No open questions remain. Decomposition can proceed.

---

## 11. Decomposition preview

Suggested `bd` subtasks under epic `ai-portfolio-manager-vfq`. Numbering follows M2's pattern; final structure pinned in the planning session (not here).

| # | Title | Notes |
|---|---|---|
| M3.1 | Investigation file landed | This file. Closes when committed. |
| M3.2 | Skill scaffold + `engine.py` CLI shell + README + requirements.txt | Argparse subcommands, `--help`, exit-code matrix, no-op handlers. Doc amendments to SPEC §17 + impl.md §M3 wording (Q1) ride along. |
| M3.3 | `my_philosophy.py` + §9.3 pass/fail + PF/15 graded ladder + sector-exception application + dealbreaker logic | Fixtures: `infy.json`, `hdfcbank.json`, `coalindia.json`, `bse.json`, `dealbreaker_zero_promoter.json`, `dealbreaker_thesis_sell.json`. |
| M3.4 | `metrics.json` schema extension — line_items + governance/thesis flags | SPEC §18.2 amendment. Coordinates with M9 via a follow-up bd issue on M9 epic. |
| M3.5 | `lib/line_items.py` adapter — normalizes our `metrics.json.history` to upstream-shaped list-of-dicts | Used by all 4 personas. |
| M3.6 | Port `personas/jhunjhunwala.py` | Strip per §5.1; fixtures: regression + insufficient_data. |
| M3.7 | Port `personas/buffett.py` | Same shape as M3.6. |
| M3.8 | Port `personas/munger.py` | Same shape as M3.6. |
| M3.9 | Port `personas/pabrai.py` | Same shape as M3.6. |
| M3.10 | `risk_manager.py` port + `concentration-check` subcommand + `prices.json` shape + `lib/fetch_prices.py` stub | 10-ticker fixture; follow-up bd on M8 for the actual Phase 1 fetch. |
| M3.11 | `scoring-engine full` wiring | Composes M3.3 + my-philosophy persona output. Fundamentals-first invariant test. |
| M3.12 | THIRD_PARTY.md flips + deferred-persona follow-up bd issue + acceptance walkthrough | Closes M3. |

M3.6–M3.9 are structurally symmetric (each: strip → adapter wiring → fixture → regression test) and can be planned in one batch and implemented in parallel by different agents, mirroring M2.6/M2.7/M2.8 in M2's investigation §11 Group C.
