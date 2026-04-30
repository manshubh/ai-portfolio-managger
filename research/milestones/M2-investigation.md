# M2 — `wealthfolio-query` investigation

> **R** step of RPI for epic [ai-portfolio-manager-l74](../../.beads/). Snapshot of the finalized design decisions feeding M2 decomposition. The authoritative behavior lives in [`docs/SPEC.md §5.3, §5.4, §6.8, §7.1.1, §7.1.2, §17, §18.1, §19.2 invariants 11–14, 20`](../../docs/SPEC.md) and [`docs/implementation.md §M2`](../../docs/implementation.md).
>
> **Reference shorthand:** "M0.7" throughout this document refers to the M0 sub-task that landed the named-query skeleton at [`skills/sql/wealthfolio-queries.sql`](../../skills/sql/wealthfolio-queries.sql) with `-- name: <slug>` markers and `TODO(M2)` placeholders. M2 fills those placeholders.

## Goal recap

A read-only, named-parameter SQL wrapper is the single entry point for all reads against Wealthfolio's SQLite DB. Six subcommands (`export-snapshot`, `list-holdings`, `get-cash-balance`, `get-net-worth`, `get-avg-cost`, `get-portfolio-twr`) dispatch to versioned named queries in [`skills/sql/wealthfolio-queries.sql`](../../skills/sql/wealthfolio-queries.sql) (skeleton landed in M0.7). The wrapper enforces `sqlite3 -readonly`, merges `input/{market}/theses.yaml` into the Phase 1 snapshot CSV deterministically, and computes the TWR chained product in Python. Acceptance bar: `export-snapshot` produces a CSV whose header exactly matches [SPEC §7.1.1](../../docs/SPEC.md), every named query has a passing fixture test, and any write attempt fails because of `-readonly`.

---

## 1. Implementation shape — shell entrypoint, Python helpers

**Decision: Option B from the question round.** `skills/wealthfolio_query/query.sh` is the SPEC §17-named entrypoint and the only thing callers invoke. It dispatches to small Python helpers under the same directory for the two subcommands that need real post-processing:

- `query.sh` (bash, `set -euo pipefail`) — argument parsing, named-query lookup, scalar `sqlite3` invocations, JSON/CSV formatting for trivial cases.
- `query.py` — entry point reusable by Python helpers; exposes a `load_query(slug)` function that re-parses [`skills/sql/wealthfolio-queries.sql`](../../skills/sql/wealthfolio-queries.sql) and an `execute(slug, params)` helper using the stdlib `sqlite3` module with a `?ro=1` URI open.
- `export_snapshot.py` — runs `export-snapshot` SQL → reads `input/{market}/theses.yaml` → emits the [§7.1.1](../../docs/SPEC.md) CSV.
- `portfolio_twr.py` — runs `get-portfolio-twr` SQL → forward-fills gaps → computes the chained product → emits JSON.
- `__init__.py` — empty package marker so `python3 -m skills.wealthfolio_query.query …` resolves.

**Directory naming — underscore, not hyphen.** [SPEC §17](../../docs/SPEC.md) shows the directory as `skills/wealthfolio-query/` (hyphenated). We deviate to `skills/wealthfolio_query/` because Python module identifiers cannot contain hyphens, and we want `python3 -m skills.wealthfolio_query.query` to work without a parallel package shim. Implications, all handled in M2:

- M2 updates [SPEC §17](../../docs/SPEC.md) and [docs/implementation.md §M2 deliverables](../../docs/implementation.md) to reflect `skills/wealthfolio_query/` (the hyphen → underscore rename is the only change).
- Test directory follows the same convention: `tests/wealthfolio_query/`.
- The user-facing skill *name* and CLI subcommand names stay hyphenated (`wealthfolio-query export-snapshot ...`) — only the directory/Python-module identifier uses an underscore. This is the standard Python convention (`pip install foo-bar` ships module `foo_bar`).

Why not pure shell (option A): YAML merging via shell-out to a Python one-liner inside `query.sh` is harder to test and harder to read than a dedicated Python file. Why not Python-only (option C): the SPEC §17 layout names `query.sh` as the file, and shell is the simpler dispatch surface for the four scalar subcommands (`list-holdings`, `get-cash-balance`, `get-net-worth`, `get-avg-cost`) that are essentially "run SQL → format rows".

The two Python helpers are imported as modules, not invoked as subprocesses, so a single Python interpreter handles the whole call. `query.sh` `exec`s into Python via `python3 -m skills.wealthfolio_query.query <subcmd> ...` for `export-snapshot` and `get-portfolio-twr`; the other four subcommands stay in shell.

Both venues ([SPEC §17](../../docs/SPEC.md)) work:

- Native: `skills/wealthfolio_query/query.sh export-snapshot ...` against host APFS.
- Container: `bin/run-skill skills/wealthfolio_query/query.sh export-snapshot ...` reads the bind-mounted DB at `/wealthfolio/app.db` (after fix #7).

---

## 2. Named-query parser and parameter binding

The M0.7 file uses `-- name: <slug>` markers. The wrapper parses by:

1. Reading the entire `.sql` file as text.
2. Splitting on `^-- name: ` (multiline regex) — the first chunk is preamble, the rest are `(slug, body)` pairs where `slug` is the first token of the marker line.
3. Each `body` ends at the next `-- name:` or EOF; trailing semicolons preserved.

### Schema-version header

Per [implementation.md §M2 deliverables](../../docs/implementation.md) and [SPEC §19.2 invariant 14](../../docs/SPEC.md), the file opens with a `-- version: <wealthfolio-release>` line in its preamble (e.g. `-- version: wealthfolio-3.2.1`). The parser reads this on startup as a sanity check: if it doesn't match the value pinned in [`config/wealthfolio.md`](../../config/wealthfolio.md), the wrapper exits 2 with a clear message. This catches the case where a user upgrades Wealthfolio without updating the SQL file (the [SPEC §19.2 invariant 14](../../docs/SPEC.md) compatibility-layer contract).

Param binding goes through Python's `sqlite3.Connection.execute(sql, named_dict)` — first-class support for `:name` placeholders. The shell-only paths use `sqlite3 -cmd ".parameter set :name 'value'"`, but with **explicit single-quote escape** of `value` to avoid SQL-string injection through scope values. Callers always pass `--scope-value=user-input`; we never interpolate user input into the SQL body itself, only into `.parameter set`.

Read-only open:
- Python: `sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)`. `immutable=1` is correct here because the agent never writes; if the GUI is also writing, the `quit-before-scans` discipline ([config/wealthfolio.md §7](../../config/wealthfolio.md)) is the user's contract.
- Shell: `sqlite3 -readonly "$WEALTHFOLIO_DB" '...'`.

Both produce the same enforcement: any DDL/DML in the SQL body fails with `attempt to write a readonly database`.

---

## 3. Fixture DB strategy — committed `fixture.sql`

**Decision: Option (a).** `tests/wealthfolio_query/fixture.sql` contains DDL (a copy of the [pinned schema](../wealthfolio-schema-v3.2.1.txt)) plus INSERT statements that seed:

- 3 accounts: 1 INR-denominated India brokerage, 1 INR-denominated India "PMS" group, 1 USD US brokerage.
- 5 India + 3 US assets across `EQUITY` instrument types, with both `XNSE`/`XBOM` MICs and one MIC-less asset (to exercise the `display_code` fallback).
- 1 ETF (`NIFTYBEES.NS`) and 2 cash-only positions to exercise `get-cash-balance`.
- `holdings_snapshots` rows with realistic `positions` JSON (shape pinned per §4 below).
- `quotes` rows for every asset, current day plus a 60-day history for one ticker (so TWR has data to chain).
- `daily_account_valuation` rows covering at least 90 days for two of the three accounts so the M6 1m / 3m TWR fixtures have headroom.

`tests/wealthfolio_query/build_fixture.sh` runs `sqlite3 fixture.db < fixture.sql` from a clean slate; `make test-wealthfolio-query` cleans + rebuilds + tests. The fixture `.db` is **not** committed — only `fixture.sql` is. Tests rebuild the DB on every run (cheap; <100 ms) so there is no stale-fixture footgun.

Why not (b) Python builder: same content, more moving parts, no portability win since `sqlite3` is ubiquitous in our skill image.

Why not (c) anonymized real DB: leaks position sizes / cost basis even after symbol scrubbing, and the ground truth for assertions has to be hand-derived anyway. A fixture written from scratch is faster to read, audit, and extend.

### 3.1 Schema-dump gotcha: `sqlite_sequence`

The canonical dump at [`research/wealthfolio-schema-v3.2.1.txt`](../wealthfolio-schema-v3.2.1.txt) includes the line `CREATE TABLE sqlite_sequence(name,seq);`. SQLite **refuses direct user creation of this name** — it is reserved as an internal catalog created implicitly the first time any `INTEGER PRIMARY KEY AUTOINCREMENT` column exists. A naive `sqlite3 fixture.db ".read schema.txt"` therefore fails. The fixture builder works around it by replacing that line with a throwaway `CREATE TABLE … AUTOINCREMENT; DROP TABLE …;` pair, which forces SQLite to materialize `sqlite_sequence` itself. Any future schema upgrade under [SPEC §19.2 invariant 14](../../docs/SPEC.md) — whoever regenerates the dump must either keep the `sqlite_sequence` line and the workaround, or strip the line before committing. `test_schema.sh`'s `.schema` diff will enforce whichever choice is made, so drift fails loudly.

---

## 4. `holdings_snapshots.positions` JSON shape — read upstream Rust

The schema dump comment says `JSON HashMap<String, Position>`. The M0.7 skeleton placeholders are `$.quantity` and `$.avg_cost`, with the join `p.key = a.id` (assumed asset_id key). I confirmed the user's local `app.db` has 0 rows in `holdings_snapshots`, so I cannot introspect from live data right now.

**Decision: Option (a).** First implementation step in M2 is to read the `Position` struct definition in upstream `afadil/wealthfolio` at the Wealthfolio v3.2.1 release tag (Rust source under `src-core/` typically), pin the field names in [`skills/sql/wealthfolio-queries.sql`](../../skills/sql/wealthfolio-queries.sql), and remove the `TODO(M2)` markers. The exact JSON-path strings and the HashMap key (asset_id vs instrument_key vs display_code) get committed alongside a one-line comment citing the upstream commit.

Verification path (option b, deferred): once the user has populated Wealthfolio with at least one holding, M2 dumps a real `holdings_snapshots.positions` row and confirms the pinned paths match. **The user will be guided exactly when this verification is needed; M2 does not assume populated data is available before then.**

If upstream introspection turns up a surprise (e.g. nested struct, snake_case vs camelCase), this is a mini-R that gets recorded inline in the relevant `plans/M2/M2.x-*.md` and the `bd` close note, per the RPI exception clause in [CLAUDE.md §5](../../CLAUDE.md).

The MIC-value introspection (R3 from M0.7) follows the same path: M2 also adds `SELECT DISTINCT instrument_exchange_mic FROM assets` as a step in `tests/wealthfolio_query/test_queries.sh` so any drift from `XNSE`/`XBOM`/`XNAS`/`XNYS`/`ARCX` shows up as a failing test.

---

## 5. `get-portfolio-twr` chaining — endpoint convention, forward-fill

**Decision: standard endpoint convention.** `--start :s --end :e` reads as *"TWR from close of `:s` to close of `:e`"*:

- Daily returns produced: `r[s+1], r[s+2], …, r[e]` — total `(e − s)` returns.
- `V[s]` is the anchor; `r[s]` is **not** part of the product.
- `r[t] = (V[t] − V[t−1] − C[t]) / V[t−1]` where `C[t]` is the daily contribution delta computed from `cumulative_net_contribution_base[t] − cumulative_net_contribution_base[t−1]`.
- `TWR = ∏(1 + r[t]) − 1` over the window.
- `--start = --end` returns `TWR = 0.0` (zero-day window, no returns to chain).
- Caller-side: M6 "1m window ending today" → `--start = today − 30d, --end = today`. No off-by-one.

### `daily_account_valuation` columns the wrapper reads

Pinned for the v3.2.1 schema (see [`research/wealthfolio-schema-v3.2.1.txt`](../wealthfolio-schema-v3.2.1.txt)). The TWR query selects only:

- `account_id` — used for scope filtering against the `accounts` join.
- `valuation_date` — `TEXT` (`YYYY-MM-DD`); used as the chain index and `ORDER BY` key.
- `total_value_base` — `TEXT`, cast `AS REAL`; the `V[t]` series.
- `cumulative_net_contribution_base` — `TEXT`, cast `AS REAL`; differenced day-to-day to derive `C[t]`.

Cash-balance and net-worth queries also read `cash_balance_base` from the same table (see §9.1 below). No other columns are touched. If a future Wealthfolio release renames any of these, the schema-version header check (§2) catches it; the SQL file is the single point of update.

### Forward-fill rule

`daily_account_valuation` row population on non-trading days (weekends/Indian holidays for INR accounts, US market holidays for USD accounts) is **not yet known**. Two cases need handling:

- If Wealthfolio writes a row for every calendar day: trivial — chain through all rows in date order.
- If Wealthfolio skips non-trading days: forward-fill missing days with `V[prev]`, `C = 0`, which yields `r[gap] = 0` and a no-op factor of `1` in the product. Equivalent to "skip the day" mathematically but easier to reason about with an explicit fill.

**M2 verification step:** once the user has populated Wealthfolio with enough history, the wrapper queries `SELECT MIN(valuation_date), MAX(valuation_date), COUNT(*) FROM daily_account_valuation` and the wrapper plan compares row count vs calendar-day span. The forward-fill code is written defensively to handle both populations identically; it doesn't matter for correctness which one Wealthfolio actually does.

### Decimal precision

Wealthfolio stores all numerics as TEXT. `CAST(... AS REAL)` in SQL gives ~15 decimal digits of precision, which is well within tolerance for portfolio-scale math (a 100-crore INR portfolio still has 7 digits of headroom on the value, and TWR is a ratio that rounds cleanly). Python `Decimal` is not needed for v1. The benchmark acceptance test in M6 (`tests/benchmark/test_alpha.py`) targets 1bp tolerance — `REAL` clears that comfortably.

---

## 6. `--strict-scope` mode

**Decision: add the flag.** When `--strict-scope` is passed, the wrapper re-issues a small validation query before the main query and exits non-zero with a useful error if no rows match:

- `--scope-type market --scope-value <m>`: confirms `<m> ∈ {india, us}`.
- `--scope-type account_group --scope-value <g>`: confirms at least one active account has `accounts."group" = :g`.
- `--scope-type account --scope-value <n>`: confirms at least one active account has `accounts.name = :n`.

Without `--strict-scope`, the wrapper is silent on a bad scope value (queries return 0 rows, exit 0) — which preserves backward compatibility with callers that explicitly want "no holdings here" to be a valid result (e.g. asking for the US slice on an India-only portfolio).

### Subcommand applicability

`--strict-scope` is accepted only on subcommands that take a `--scope-type/--scope-value` pair, per [SPEC §18.1](../../docs/SPEC.md):

| Subcommand | Accepts `--strict-scope`? |
|---|---|
| `export-snapshot` | yes (always has scope) |
| `list-holdings` | yes |
| `get-cash-balance` | yes |
| `get-net-worth` | no — no scope params |
| `get-avg-cost` | no — keyed by ticker |
| `get-portfolio-twr` | no — keyed by `--market` only |

Passing `--strict-scope` to a non-scoped subcommand is a usage error (exit 1).

M8's Phase 1 prompt invokes `wealthfolio-query` with `--strict-scope` so a user typo (`--scope-value typoaccount`) fails loud. Lower-level tooling that legitimately wants empty results (e.g. cross-market reports) omits the flag.

---

## 7. Docker mount fix — fix in M2

[docker-compose.yml](../../docker-compose.yml) currently bind-mounts a single file at `~/Library/Application Support/Wealthfolio/ledger.db` to `/wealthfolio/ledger.db`. Three problems, all confirmed by inspection:

1. **Wrong path.** The real Wealthfolio app-support directory is `~/Library/Application Support/com.teymz.wealthfolio/`. The "Wealthfolio" path with `ledger.db` is a leftover from an early M0.9 draft that predates [config/wealthfolio.md](../../config/wealthfolio.md). I confirmed `sqlite3` cannot open the compose-mounted file, while `~/Library/Application Support/com.teymz.wealthfolio/app.db` (644K, has the expected tables) does open.
2. **File mount, not directory mount.** SQLite WAL needs `app.db-wal` and `app.db-shm` adjacent to `app.db`. A file-only mount silently returns stale or empty results when the GUI has uncheckpointed WAL writes.
3. **Env var name muddle.** Compose uses `WEALTHFOLIO_DB_PATH` (host) → exposes `WEALTHFOLIO_DB` (container). The config doc only ever names `WEALTHFOLIO_DB`. Two names = footgun.

**Fix in M2** (M2 is the first consumer that actually opens the DB; fixing it elsewhere would block M2 anyway):

```yaml
services:
  skills-env:
    build: .
    volumes:
      - .:/workspace
      - type: bind
        source: ${WEALTHFOLIO_DB_DIR:-${HOME}/Library/Application Support/com.teymz.wealthfolio}
        target: /wealthfolio
        read_only: true
    environment:
      - WEALTHFOLIO_DB=/wealthfolio/app.db
```

Notes:
- Single host-side env var: `WEALTHFOLIO_DB_DIR` (the directory on the host). Inside the container the canonical name `WEALTHFOLIO_DB` resolves to the file.
- Default uses `${HOME}` for portability instead of the hardcoded `/Users/mrihal/...`.
- `:ro` is preserved as `read_only: true` per [SPEC §19.2 invariant 11](../../docs/SPEC.md).

### Cross-milestone impact

[`docker-compose.yml`](../../docker-compose.yml) was an M0 deliverable ([implementation.md §M0](../../docs/implementation.md)), so this is M2 reaching back to fix an already-closed M0 artifact. Two parallel doc updates land in the same M2 subtask so the docs don't drift:

- [`config/wealthfolio.md`](../../config/wealthfolio.md) — record the new env-var contract (`WEALTHFOLIO_DB_DIR` host-side; `WEALTHFOLIO_DB` container-side, resolves to `/wealthfolio/app.db`). Update the macOS path-discovery guidance to point at `~/Library/Application Support/com.teymz.wealthfolio/`.
- [`README.md`](../../README.md) and any quick-start prose that references the old path.

The fix is a small subtask in the M2 decomposition; it lands before any test that needs the container.

---

## 8. Read-only enforcement — already covered by `sqlite3 -readonly`

M2 acceptance #2: "Attempting a write via the wrapper (e.g. injecting `UPDATE`) fails because of `-readonly`." Three layers of defense:

1. **The SQL file has no DDL/DML.** M0.7 verification confirmed `grep -cE '^\s*(CREATE|INSERT|UPDATE|DELETE|DROP|ALTER)\b'` returns 0; M2 keeps that property and adds the same check to `tests/wealthfolio_query/`.
2. **Open mode.** Both shell (`sqlite3 -readonly`) and Python (`mode=ro&immutable=1`) refuse writes at the SQLite layer. Test: `tests/wealthfolio_query/test_readonly.sh` directly invokes `sqlite3 -readonly "$FIXTURE_DB" "UPDATE accounts SET name='x'"` and asserts a non-zero exit + the literal "readonly" string in stderr.
3. **No string-formatted SQL.** Subcommand args go through `:name` parameter binding only. The wrapper never `printf`s user input into SQL bodies.

Together these mean even a malicious caller passing `--scope-value="x'; UPDATE accounts SET name='gone'; --"` cannot write — the value lands in `.parameter set` (escaped) and never reaches a query body.

---

## 9. Output format details

| Subcommand | Default format | `--format csv` allowed | `--format json` allowed | Scalar shape |
|---|---|---|---|---|
| `export-snapshot` | CSV (file or stdout) | yes | yes | n/a (rows) |
| `list-holdings` | JSON | yes | yes | n/a (rows) |
| `get-cash-balance` | JSON | yes | yes | bare number |
| `get-net-worth` | JSON | yes | yes | bare number |
| `get-avg-cost` | JSON | yes | yes | bare number |
| `get-portfolio-twr` | JSON | yes | yes | object with `twr`, `start`, `end`, `series` |

Decisions per the question round:

- **Scalar bare numbers.** `get-net-worth` returns `1234567.89\n` (followed by newline), not `{"net_worth_base": 1234567.89}`. Same for `get-cash-balance` and `get-avg-cost`. Bare numbers are easier to consume from shell (`NW=$(wealthfolio-query get-net-worth)`) and the SPEC §6.8 contract calls these "scalar" returns.
- **No preview echo — deliberate SPEC narrowing.** [SPEC §6.8](../../docs/SPEC.md) says the wrapper *may* echo preview rows when `--output <path>` is given. We deliberately narrow this to "must not" — when `--output` is set, the wrapper writes the file and exits silently. This is a recorded deviation from the SPEC text (the SPEC permission is "may", not "must"), motivated by parsing clarity for callers piping the output.
- **`--theses` default.** When `--theses` is omitted on `export-snapshot`, the wrapper auto-resolves to `input/{market}/theses.yaml` based on the `--market` value. If that file is missing the wrapper still runs (empty thesis column per [SPEC §19.2 invariant 13](../../docs/SPEC.md)) and emits a one-line stderr warning.
- **`--market all`.** On `list-holdings`, `--market all` is a wildcard: the market filter passes any row, and the scope filter still applies if `--scope-type` is set. `--market all --scope-type market --scope-value india` is interpreted as "all markets, scoped to the India market slice" — which collapses to the same as `--market india`. No error; the SQL handles it correctly.
- **Schema-version check.** Only in tests, not on every CLI invocation. `tests/wealthfolio_query/test_schema.sh` runs `sqlite3 -readonly $FIXTURE_DB '.schema'` and diffs against `research/wealthfolio-schema-v3.2.1.txt`. A drift fails the test, prompting a [SPEC §19.2 invariant 14](../../docs/SPEC.md) review. Production callers don't pay the latency.

### 9.1 Per-subcommand semantics

Pinning the semantics that [SPEC §6.8](../../docs/SPEC.md) and [SPEC §18.1](../../docs/SPEC.md) leave open:

**`export-snapshot`** — see §10 below for the column order, thesis merge, and row-order discipline.

**`list-holdings`**
- Output rows carry the same 13 columns as [§7.1.1](../../docs/SPEC.md) **minus** `thesis` (no theses merge here — `list-holdings` is for tooling that doesn't care about thesis text).
- Filters: `--market`, `--scope-type/--scope-value`. Both optional; defaults to all active accounts.
- Row order: `ORDER BY ticker, account` for byte-identical re-runs.

**`get-cash-balance`**
- Reads `daily_account_valuation.cash_balance_base` for the most recent `valuation_date` per scoped account, summed.
- `--currency`: `INR`, `USD`, or omitted.
  - Omitted → returns the base-currency sum directly (no conversion).
  - `INR`/`USD` → restricts the sum to accounts whose `accounts.currency = :ccy`. Does *not* apply FX conversion (Wealthfolio already normalizes to base; per-currency requests use the native-currency column path: `cash_balance` rather than `cash_balance_base`. The SQL named query handles the column choice.)
- Multi-currency-per-account expansion (the `holdings_snapshots.cash_balances` JSON HashMap fan-out) is **out of scope for v1** — see §14.
- Empty scope returns `0.0` (silent unless `--strict-scope`).

**`get-net-worth`**
- Reads `daily_account_valuation.total_value_base` summed across all active accounts in the requested market.
- `--date`: defaults to the most recent `valuation_date` available (not the calendar today, in case Wealthfolio hasn't snapshotted yet). When supplied, the wrapper picks the last `valuation_date <= :date`.
- `--currency`: same semantics as `get-cash-balance` — omitted = base; `INR`/`USD` selects a same-currency-account-only path.
- No `--scope-type` (per [SPEC §18.1](../../docs/SPEC.md)).

**`get-avg-cost <ticker>`**
- Quantity-weighted average across **all active lots in all active accounts** holding the ticker, computed from `holdings_snapshots.positions` as `SUM(qty * avg_cost) / SUM(qty)`.
- The specific JSON path inside `positions` depends on the upstream `Position` struct introspection (§4) — pinned in the SQL named query.
- Returns a single bare number. Multiple-account / multi-lot cases collapse to a single weighted figure; we accept this even though one user could plausibly want per-account breakdown — that variant is deferred.
- Ticker not held → exit 2 with a clear "ticker not in active holdings" message. (Distinct from cash-balance's "0.0 silent" because there's no meaningful zero-cost answer.)

**`get-portfolio-twr`** — see §5 above for the chained-product math and the `daily_account_valuation` columns it reads. Output object:

```json
{ "twr": 0.0421, "start": "2026-03-30", "end": "2026-04-30", "series": [ ... ] }
```

The `series` array carries `{date, V, C, r}` tuples for the chained window. M6's benchmark assembler consumes the scalar `twr`; `series` is for debug + verification fixtures.

---

## 10. CSV column order and `export-snapshot` thesis merge

The CSV column order must exactly match [SPEC §7.1.1](../../docs/SPEC.md):

```
ticker,name,market,currency,account,account_group,asset_type,quantity,avg_cost,snapshot_price,snapshot_market_value,allocation_pct,unrealized_pl_pct,thesis
```

The `export-snapshot` SQL emits the first 13 columns; `export_snapshot.py` reads `input/{market}/theses.yaml` and joins the `thesis` column on canonical Yahoo ticker. Missing thesis = empty string, never an error ([SPEC §19.2 invariant 13](../../docs/SPEC.md)). Order:

1. SQL → list of 13-column rows in memory (no file write yet). The named query ends with `ORDER BY ticker, account` so re-runs against the same DB state produce byte-identical output. This row-order discipline is what makes the [M9](../../docs/implementation.md) "snapshot byte-identical after Phase 2" assertion meaningful.
2. Read `input/{market}/theses.yaml` once.
3. For each row, look up `theses[ticker]`, default `""`.
4. Stream rows + thesis to `--output` path (or stdout) with `csv.writer` and `quoting=csv.QUOTE_MINIMAL`.

CSV escaping: thesis bodies may contain commas, quotes, or newlines. Standard `csv.writer` handles all three without configuration.

---

## 11. Operational contract details

### 11.1 Exit codes

- `0` — query ran, output emitted (zero rows is valid).
- `1` — usage error (bad args, missing required flag, unknown subcommand).
- `2` — DB error (cannot open `WEALTHFOLIO_DB`, schema mismatch surfaced by `--strict-scope` or test mode, write attempt blocked by `-readonly`).
- `3` — fixture/data-shape error (e.g. `positions` JSON path didn't resolve — escape hatch for the M0.7 TODO if upstream Rust check turned out wrong).

### 11.2 stderr

All errors print to stderr as `wealthfolio-query: <message>`. JSON-shaped error bodies are not used (these are CLI-tool errors, not API errors); stderr text is enough for the agent prompt to surface to the user.

### 11.3 `--help`

`query.sh --help` prints the SPEC §18.1 signature block. Each subcommand also accepts `--help` and prints its own one-section help.

### 11.4 Concurrency

Multiple parallel callers reading the DB are safe — `sqlite3 -readonly` permits unlimited concurrent readers. The wrapper holds no locks of its own.

### 11.5 Container vs native

Both venues read `WEALTHFOLIO_DB`. The wrapper does not branch on venue. Tests run inside the container by default (`bin/run-skill tests/wealthfolio_query/run-all.sh`) but the same scripts work natively if the env var is set on the host.

### 11.6 Logging

`query.sh` is silent on success. A `--verbose` flag (optional in M2) can echo the resolved query slug, parameter dict, and SQL fingerprint to stderr for debugging. Not required for acceptance.

---

## 12. Test coverage

`tests/wealthfolio_query/`:

- `fixture.sql` — schema + seeded data (5 IN + 3 US tickers, multi-account, multi-currency).
- `build_fixture.sh` — `rm -f fixture.db && sqlite3 fixture.db < fixture.sql`.
- `test_queries.sh` — every subcommand exercised against the fixture; assertions on output shape and known values. Includes a coverage assertion: every `-- name:` slug in [`skills/sql/wealthfolio-queries.sql`](../../skills/sql/wealthfolio-queries.sql) has a matching subcommand exercised at least once (per the [implementation.md §M2 acceptance criterion](../../docs/implementation.md)).
- `test_readonly.sh` — proves `UPDATE` against `-readonly` fails non-zero with stderr containing "readonly".
- `test_schema.sh` — diffs `.schema fixture.db` against `research/wealthfolio-schema-v3.2.1.txt` (less the row data); fails on schema drift.
- `test_export_snapshot.sh` — runs the full pipeline including `--theses input/india/theses.yaml.fixture`, asserts CSV header matches [SPEC §7.1.1](../../docs/SPEC.md) byte-for-byte, asserts row count and `allocation_pct` sums to ~1.0, and asserts byte-identical output across two consecutive runs (the row-order discipline from §10).
- `test_twr.sh` — fixture has known V/C series; assertion compares chained TWR to a hand-computed expected value within 1bp.
- `test_strict_scope.sh` — `--strict-scope --scope-value bogus` exits 2.
- `run-all.sh` — wrapper invoking the above in order; exits non-zero on any failure.

The fixture has fresh prices baked in, so quote-refresh staleness is **not** exercised at the M2 layer. The Phase 1 preflight check that surfaces stale quotes lives at the [M8 e2e level](../../docs/implementation.md), where the test harness can simulate user-skipped-refresh scenarios against a real Wealthfolio DB.

Concurrent-reader test is not part of M2 acceptance; M14 covers full-portfolio stress including parallel reads.

---

## 13. Final decisions / no remaining blockers

1. **Wrapper layout:** shell `query.sh` entrypoint; Python helpers (`query.py`, `export_snapshot.py`, `portfolio_twr.py`) for `export-snapshot` and `get-portfolio-twr`; the four scalar/list subcommands stay in shell.
2. **Directory naming:** `skills/wealthfolio_query/` (underscore) so `python3 -m skills.wealthfolio_query.query` resolves. M2 updates [SPEC §17](../../docs/SPEC.md) and [implementation.md §M2](../../docs/implementation.md) to reflect the rename. CLI subcommand names stay hyphenated.
3. **Named-query parsing:** regex split on `^-- name: `, dispatch by slug. SQLite named parameters (`:name`) bound via Python's `sqlite3` module or shell `.parameter set`. SQL file opens with a `-- version: <wealthfolio-release>` header that the wrapper sanity-checks against [`config/wealthfolio.md`](../../config/wealthfolio.md) at startup.
4. **Read-only:** `sqlite3 -readonly` (shell) and `mode=ro&immutable=1` (Python URI). No DDL/DML in the SQL file. No string-formatted SQL.
5. **Fixture:** committed `tests/wealthfolio_query/fixture.sql`; built fresh per test run; `.db` not committed.
6. **`positions` JSON shape:** pin from upstream `afadil/wealthfolio` Rust source at v3.2.1 tag as the first M2 implementation step. User-data verification deferred until populated; user will be guided when needed.
7. **TWR contract:** standard endpoint convention. `--start = --end` → TWR 0. Forward-fill missing days with `V[prev], C=0` (no-op for chained product). `daily_account_valuation` columns pinned in §5.
8. **Decimal precision:** `CAST(... AS REAL)` accepted; Python `Decimal` not needed for v1.
9. **`--strict-scope`:** add the flag, accepted only on `export-snapshot`, `list-holdings`, `get-cash-balance` (the three with scope params). M8 Phase 1 calls with the flag; lower-level tooling omits it for "empty result is fine" cases.
10. **Docker mount:** fix `docker-compose.yml` in M2 to bind-mount the directory `~/Library/Application Support/com.teymz.wealthfolio` to `/wealthfolio` and target `app.db`. Single host env var `WEALTHFOLIO_DB_DIR`; container exposes `WEALTHFOLIO_DB`. [`config/wealthfolio.md`](../../config/wealthfolio.md) updated in the same subtask.
11. **Output formats:** scalars → bare number; `--output <file>` → silent (deliberate narrowing of [SPEC §6.8](../../docs/SPEC.md)'s "may echo"); `--theses` → auto-resolve from `--market`; `--market all` → wildcard; schema check tests-only. Per-subcommand semantics pinned in §9.1.
12. **Row-order determinism:** `export-snapshot` SQL ends with `ORDER BY ticker, account` so re-runs are byte-identical (required by [M9](../../docs/implementation.md)'s snapshot-freeze assertion).
13. **Exit codes:** 0 success, 1 usage, 2 DB error, 3 data-shape error.

### 13.1 Deliverables checklist (input to `bd` decomposition)

Mapped from [implementation.md §M2 deliverables](../../docs/implementation.md). Every bullet here becomes one or more `bd` tasks under the M2 epic:

- [`skills/wealthfolio_query/query.sh`](../../skills/wealthfolio_query/) — shell entrypoint + four scalar/list subcommand paths.
- [`skills/wealthfolio_query/query.py`](../../skills/wealthfolio_query/) — named-query loader + parameterized executor.
- [`skills/wealthfolio_query/export_snapshot.py`](../../skills/wealthfolio_query/) — SQL → CSV with theses merge.
- [`skills/wealthfolio_query/portfolio_twr.py`](../../skills/wealthfolio_query/) — TWR chained-product computation.
- [`skills/wealthfolio_query/__init__.py`](../../skills/wealthfolio_query/) — package marker.
- [`skills/wealthfolio_query/README.md`](../../skills/wealthfolio_query/) — invocation, contract, failure modes, env-var setup.
- [`skills/sql/wealthfolio-queries.sql`](../../skills/sql/wealthfolio-queries.sql) — fill in M0.7 placeholders + `-- version:` header.
- [`tests/wealthfolio_query/`](../../tests/) — fixture + test scripts per §12.
- [`docker-compose.yml`](../../docker-compose.yml) — directory bind-mount + env-var fix per §7.
- [`config/wealthfolio.md`](../../config/wealthfolio.md) — updated env-var contract + path-discovery guidance.
- [`docs/SPEC.md`](../../docs/SPEC.md) §17 + [`docs/implementation.md`](../../docs/implementation.md) §M2 — `wealthfolio-query` → `wealthfolio_query` directory-name rename.

Nothing else blocks decomposition. The remaining details in §11 are implementation-level choices with clear defaults.

---

## 14. What's not in scope for M2

- **Multi-currency-per-account cash.** [`holdings_snapshots.cash_balances`](../wealthfolio-schema-v3.2.1.txt) JSON HashMap fan-out is deferred to a later milestone if real data shows users hold multiple currencies in one account. v1 reads single-currency cash from `daily_account_valuation`.
- **ADRs and cross-listed Yahoo-ticker mapping.** The MVP roster ([SPEC §8.3](../../docs/SPEC.md)) is NSE-listed + US majors. A lookup table is the escape hatch if M14's audit surfaces a gap; M2 does not pre-build it.
- **Snapshot freezing.** [SPEC §19.2 invariant 12](../../docs/SPEC.md) says Phase 1's `portfolio-snapshot.csv` is frozen for the run. M2 produces the file; the *invariant test* that mutating the file later breaks downstream lives in [M8](../../docs/implementation.md).
- **Quote-refresh preflight.** [SPEC §5.4](../../docs/SPEC.md) says the snapshot must reflect latest prices. If the pinned Wealthfolio release does not expose a quote-refresh CLI command, the user refreshes via the GUI before invoking us; M8 surfaces this as a Phase 1 preflight reminder. Not M2's problem.
- **Concurrent-reader stress.** Covered in M14.
- **`--verbose` debug flag.** Optional. Implement only if the test loop needs it.
- **Schema-drift auto-detect on every CLI call.** Tests-only per question 11.

---

## 15. Planning groups (P-step batching)

Only the six file-plan beads need `plans/M2/M2.x-<slug>.md` files; the other six (M2.1, M2.2, M2.9, M2.10, M2.11, M2.12) carry their plans inline in `bd --design`/`--notes`. The six file-plan beads cluster into **three planning sessions** based on shared decisions and layout coupling — planning each cluster in one go keeps cross-cutting conventions consistent, whereas splitting them risks drift on the shared surfaces.

### Group A — solo research: `l74.3` (M2.3)
- **Beads:** `ai-portfolio-manager-l74.3`
- **Plan file:** `plans/M2/M2.3-position-introspection.md`
- **Why alone:** Mini-R flow (read upstream Rust at v3.2.1, pin JSON paths, diff [`skills/sql/wealthfolio-queries.sql`](../../skills/sql/wealthfolio-queries.sql)). No shared layout or primitive decisions with any other file-plan bead. The output — pinned JSON paths and the HashMap-key choice — is an *input* to M2.6/M2.7 planning, not an overlapping concern. Produce this plan first so its findings land before the subcommand cluster is planned.

### Group B — primitives cluster: `l74.4` + `l74.5` (M2.4 + M2.5)
- **Beads:** `ai-portfolio-manager-l74.4`, `ai-portfolio-manager-l74.5`
- **Plan files:** `plans/M2/M2.4-wrapper-skeleton.md`, `plans/M2/M2.5-test-harness.md` (two files, one planning session)
- **Why together:** They share (1) the directory layout (`skills/wealthfolio_query/` ↔ `tests/wealthfolio_query/`), (2) the RO-open primitives (`test_readonly.sh` asserts the exact open-mode strings the wrapper uses), (3) the schema-version header contract (wrapper implements the check, `test_schema.sh` asserts it), (4) the fixture DB path conventions, (5) the exit-code matrix (wrapper emits, tests assert). Planning one without the other forces re-opening decisions when the second is written. M1 split skeleton and tests (M1.1 vs. M1.6) but M2's tests probe wrapper internals more directly, so they couple tighter.

### Group C — parallel subcommands: `l74.6` + `l74.7` + `l74.8` (M2.6 + M2.7 + M2.8)
- **Beads:** `ai-portfolio-manager-l74.6`, `ai-portfolio-manager-l74.7`, `ai-portfolio-manager-l74.8`
- **Plan files:** `plans/M2/M2.6-scalar-list-subcommands.md`, `plans/M2/M2.7-export-snapshot.md`, `plans/M2/M2.8-get-portfolio-twr.md` (three files, one planning session)
- **Why together:** They are structurally symmetric — each plan has the same shape (named-query wiring → helper/dispatcher → output format → fixture-backed test file). Planning them in one session keeps (1) the output-format table from §9 consistent (scalar bare numbers, JSON object, CSV with header byte-match), (2) the `ORDER BY ticker, account` determinism discipline applied everywhere row-order matters, (3) the per-subcommand exit-code semantics aligned (avg-cost exits 2 on unknown ticker; cash-balance exits 0 on empty scope), (4) the test-harness hook points uniform. They are *independent* once M2.5 lands (can be implemented in parallel by different agents), but the *planning* benefits from lockstep review because the conventions they establish cascade into M2.9 (strict-scope) and M2.11 (acceptance).

### Summary

| Planning session | Beads | Plan files produced |
|---|---|---|
| 1 | `l74.3` | 1 |
| 2 | `l74.4`, `l74.5` | 2 |
| 3 | `l74.6`, `l74.7`, `l74.8` | 3 |
| — (inline) | `l74.1`, `l74.2`, `l74.9`, `l74.10`, `l74.11`, `l74.12` | 0 (captured in `bd --design`/`--notes`) |

**Recommended order:** session 1 → session 2 → session 3. Session 1 is a pure prerequisite (fixes the SQL file's shape that the others assume); session 2 establishes primitives that session 3 consumes; session 3 is the last file-plan batch before acceptance/docs.
