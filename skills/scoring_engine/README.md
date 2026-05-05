# scoring-engine

Deterministic scoring math for ai-portfolio-manager. All threshold pass/fail, philosophy-fit grading, persona base scores, and concentration sanity are reproducible from JSON fixtures with **zero LLM involvement**. Output is JSON; the LLM consumes it in Phases 4 / 5 / 6 to compose narrative.

Authoritative behavior lives in [`docs/SPEC.md §6.3, §7.6, §8.2–§8.6, §9, §10.5, §10.6, §18.3, §19.2 inv. 15–16`](../../docs/SPEC.md). M3 design decisions are recorded in [`research/milestones/M3-investigation.md`](../../research/milestones/M3-investigation.md). Upstream port pin manifest at [`THIRD_PARTY.md §2.1`](../../THIRD_PARTY.md) (10 targets at `virattt/ai-hedge-fund@0f6ac48`).

## Status

This skill is being built milestone-by-milestone. **M3.2 has shipped only the CLI shell** — every subcommand handler is currently a no-op that exits with code 2 and a `{"error":"not_implemented"}` JSON body on stderr. The argparse surface, `--help` strings, flags, and exit-code matrix are real and stable. Real handlers land in:

| Subtask | Lands |
|---|---|
| `check-thresholds`, `persona --persona my-philosophy` | M3.3 |
| `metrics.json` schema extension (`history.line_items[]`, governance/thesis flags) | M3.4 |
| `lib/line_items.py` adapter | M3.5 |
| `persona --persona {jhunjhunwala,buffett,munger,pabrai}` | M3.6 – M3.9 |
| `concentration-check` + `risk_manager.py` port + `prices.json` shape | M3.10 |
| `full` (combines `check-thresholds` + `my-philosophy`) | M3.11 |

## Hyphen → underscore directory note

[SPEC §17](../../docs/SPEC.md) shows the directory as `skills/scoring-engine/`. The actual directory is `skills/scoring_engine/` because Python module identifiers can't contain hyphens — same precedent as `skills/wealthfolio_query/`. The **skill name and CLI verbs stay hyphenated** (`scoring-engine check-thresholds …`); only the on-disk directory and Python package use the underscore. SPEC §17 is amended to reflect this in the same commit that lands this scaffold (M3.2).

## Invocation

```bash
python3 -m skills.scoring_engine.engine --help
python3 -m skills.scoring_engine.engine <subcommand> --help
```

The four subcommands match [SPEC §18.3](../../docs/SPEC.md):

### `check-thresholds`

```
python3 -m skills.scoring_engine.engine check-thresholds \
  --philosophy <path-to-philosophy.md> \
  --scheme {non_financial|banking_nbfc} \
  --metrics <path-to-metrics.json> \
  [--sector-exception <name>]
```

Runs the §9.3 pass/fail table and emits `philosophy_fit_graded` (PF/15: 0|8|15 per §9.2 ladder). Caller (Phase 4 prompt) supplies `--scheme` and optional `--sector-exception` (`it_mnc` / `psus` / `hospitals` / `foreign_sub` / `stock_exchanges`) inferred from `[Overview] Sector` per investigation §2 (Q3).

**Out of scope here**: F/35, BS/20, V/20, N/10. Those remain Phase 4 LLM judgments per [SPEC §10.5](../../docs/SPEC.md). `my_philosophy.py` only owns the PF/15 sub-score and the threshold pass/fail table — investigation §2 (Q1).

### `persona`

```
python3 -m skills.scoring_engine.engine persona \
  --persona {my-philosophy|jhunjhunwala|buffett|munger|pabrai} \
  --metrics <path-to-metrics.json> \
  [--price-context <path-to-context.json>]
```

Runs a single persona's deterministic base scoring (§9.4). Output is `{ticker, persona, sub_scores, weighted_score, max_score, signal, confidence, details}`. When required `history.line_items[]` periods are missing, the persona emits `{signal: "insufficient_data", missing_fields: [...], min_periods_required, min_periods_available}` with **exit code 0** — the caller decides whether to skip that row (investigation §5.2). `my-philosophy` is exempt from insufficient_data because it consumes only summary ratios from `fund.*`.

The four rotating personas are ports of `virattt/ai-hedge-fund@0f6ac48` with langchain / Pydantic / state-graph plumbing stripped. Math sub-functions, weight patterns, and embedded threshold tables are kept verbatim (investigation §5.1 / SPEC §8.3 "retain native internal math scales"). Six other upstream targets (`fundamentals.py`, `phil_fisher.py`, `ben_graham.py`, `aswath_damodaran.py`, `peter_lynch.py`, plus a `risk_manager.py` not used as a persona) are **deferred** past M3 — see investigation §4 and the follow-up bd issue.

### `concentration-check`

```
python3 -m skills.scoring_engine.engine concentration-check \
  --holdings <path-to-holdings.json> \
  --price-history <path-to-prices.json> \
  --philosophy <path-to-philosophy.md>
```

Portfolio-level sanity per §9.5. Emits HHI = Σ(weight_i²), per-stock volatility-adjusted position limit (base from `position_sizing.max_per_stock_pct` in the philosophy YAML), and the top-5 correlation pairs by absolute Pearson correlation over the lookback window. `prices.json` shape is fixed in investigation §6 (per-ticker dates + closes, lookback ≥ 252 trading days). The actual price-history fetch is a Phase-1 artifact (M8), not this skill — `lib/fetch_prices.py` only reads from a path.

### `full`

```
python3 -m skills.scoring_engine.engine full \
  --ticker <T> \
  --metrics <path-to-metrics.json> \
  --philosophy <path-to-philosophy.md>
```

Convenience wrapper for Phase 4 that composes `check-thresholds` and `persona --persona my-philosophy` into `{thresholds: {...}, my_philosophy: {...}}` in a single invocation. Rotating personas are still called separately by Phase 5 (investigation §7).

## Exit-code matrix

| Code | Meaning | Examples |
|---|---|---|
| **0** | Success. Includes the deterministic-base success case **and** the `signal: "insufficient_data"` graceful-degradation case for rotating personas. | Normal output written to stdout. |
| **1** | Bad input — schema mismatch, missing required field, malformed JSON. | Caller bug; fix the input. |
| **2** | Internal error — un-handled exception, not-yet-implemented stub (M3.2 state). | Engine bug; file a `bd` issue. |

All errors emit a structured JSON body on stderr with at minimum `{"error": "<kind>", "message": "..."}`.

## Determinism

Two runs on byte-identical inputs MUST produce byte-identical stdout. No `random.*`, no wall-clock, no `dict` ordering surprises (sub_scores are emitted in the persona's declared order). Each persona has a regression test asserting byte-equal repeated output (investigation §5.3).

## Layout

```
skills/scoring_engine/
├── __init__.py
├── engine.py                     # CLI entry — this file's argparse layer
├── my_philosophy.py              # M3.3 — PF/15 + §9.3 table + dealbreaker logic
├── risk_manager.py               # M3.10 — concentration math (port)
├── personas/
│   ├── jhunjhunwala.py           # M3.6
│   ├── buffett.py                # M3.7
│   ├── munger.py                 # M3.8
│   └── pabrai.py                 # M3.9
├── lib/
│   ├── line_items.py             # M3.5 — metrics.json.history → upstream-shaped dicts
│   └── fetch_prices.py           # M3.10 — path-only stub (no network)
├── requirements.txt
└── README.md
```

Most of those files do not exist yet — see the **Status** table above.

## Upstream attribution

Files ported from `virattt/ai-hedge-fund` carry a header comment naming the upstream path and the pinned commit SHA `0f6ac487986f7eb80749ed42bd26fb8330c450db`. Stripped: langchain LLM call, Pydantic signal model, state-graph plumbing, upstream API fetchers. Adapted: data input flows from `skills.scoring_engine.lib.line_items`. MIT license text and the running ports table are in [`THIRD_PARTY.md §2.1`](../../THIRD_PARTY.md).
