# wealthfolio-query

Read-only wrapper around named SQL queries against the Wealthfolio SQLite database. Single entry point for every Wealthfolio read in the system ([SPEC §5.3, §6.8, §17, §18.1](../../docs/SPEC.md)).

Named queries live in [skills/sql/wealthfolio-queries.sql](../sql/wealthfolio-queries.sql), keyed by `-- name: <slug>` markers and pinned to Wealthfolio v3.2.1 via a `-- version:` header that the wrapper sanity-checks at startup.

## 1. Invocation

Two venues, identical behavior. Both rely on the `WEALTHFOLIO_DB` env var (see §6).

**Native** (host shell, requires `python3` and `sqlite3` on PATH):
```bash
WEALTHFOLIO_DB=/path/to/app.db \
  ./skills/wealthfolio_query/query.sh list-holdings --market india
```

**Container** (recommended; uses the bind mount from [docker-compose.yml](../../docker-compose.yml)):
```bash
bin/run-skill skills/wealthfolio_query/query.sh list-holdings --market india
```

`bin/run-skill` resolves `WEALTHFOLIO_DB` to `/wealthfolio/app.db` inside the container; the host directory is bound from `WEALTHFOLIO_DB_DIR` (see [config/wealthfolio.md](../../config/wealthfolio.md)).

## 2. Subcommands

Six subcommands per [SPEC §18.1](../../docs/SPEC.md). All open the DB read-only; missing-data outputs are silent (`0.0` or empty rows) unless `--strict-scope` is set (§3).

### `export-snapshot`
```
export-snapshot --market india|us \
                --scope-type market|account_group|account \
                --scope-value <value> \
                [--theses input/{market}/theses.yaml] \
                [--output <file>] \
                [--strict-scope]
```
**Output**: CSV with the 14 columns of [SPEC §7.1.1](../../docs/SPEC.md) (header byte-identical). When `--output` is set, the file is written silently and stdout stays empty (deliberate narrowing of [SPEC §6.8](../../docs/SPEC.md)). `--theses` defaults to `input/{market}/theses.yaml`; missing thesis = empty string.

### `list-holdings`
```
list-holdings [--market india|us|all] \
              [--scope-type ...] [--scope-value ...] \
              [--format json|csv] [--strict-scope]
```
**Output**: 13-column rows (same shape as `export-snapshot` minus `thesis`), default JSON. Deterministic `ORDER BY ticker, account` for byte-identical re-runs.

### `get-cash-balance`
```
get-cash-balance [--currency INR|USD|all] \
                 [--scope-type ...] [--scope-value ...] [--strict-scope]
```
**Output**: bare scalar (`1234567.89\n`). Reads `daily_account_valuation.cash_balance` from the latest valuation row per scoped account. Empty scope → `0.0` (silent).

### `get-net-worth`
```
get-net-worth [--market india|us|all] [--date <YYYY-MM-DD>] [--currency INR|USD]
```
**Output**: bare scalar in base currency unless `--currency` overrides the output denomination. `--date` defaults to the most recent `valuation_date <= today`.

### `get-avg-cost`
```
get-avg-cost <ticker>
```
**Output**: bare scalar — quantity-weighted average across all active lots in all active accounts holding the ticker. Ticker not held → exit 2 with stderr `ticker not in active holdings: <ticker>`.

### `get-portfolio-twr`
```
get-portfolio-twr --market india|us --start <YYYY-MM-DD> --end <YYYY-MM-DD>
```
**Output**: JSON object — `{"twr": <float>, "start": "...", "end": "...", "series": [{"date","V","C","r"}, ...]}`. Standard endpoint convention (`r[s]` is anchor, not part of the product). Forward-fills missing days as no-op factors of 1.

## 3. `--strict-scope`

Validates the scope pair *before* the main query runs. Exits 2 with `wealthfolio-query: scope <type>=<value> matches no active accounts` when no match is found. Without the flag, an unmatched scope is silent (empty rows / `0.0` / exit 0) — preserving callers that legitimately expect "no holdings here" as a valid result (e.g. cross-market reports).

| Subcommand          | `--strict-scope`? |
|---------------------|-------------------|
| `export-snapshot`   | yes               |
| `list-holdings`     | yes               |
| `get-cash-balance`  | yes               |
| `get-net-worth`     | no — usage error  |
| `get-avg-cost`      | no — usage error  |
| `get-portfolio-twr` | no — usage error  |

Phase 1 ([M8](../../docs/implementation.md)) calls with `--strict-scope` so a typo'd `--scope-value` fails loud. Lower-level tooling that wants empty-result-OK omits the flag.

## 4. Failure modes

| Exit | Meaning                                                         |
|------|-----------------------------------------------------------------|
| 0    | Success (zero rows / `0.0` is valid output).                    |
| 1    | Usage error — bad flags, unknown subcommand, missing argument.  |
| 2    | DB / dependency / schema-version error, or `--strict-scope` miss. |
| 3    | Data-shape error (e.g. an unexpected JSON shape in `positions`). |

All errors print to stderr as `wealthfolio-query: <message>`. JSON-shaped error bodies are not used.

## 5. Environment

| Variable             | Where         | Purpose                                                  |
|----------------------|---------------|----------------------------------------------------------|
| `WEALTHFOLIO_DB`     | both venues   | Absolute path to `app.db`. Required.                     |
| `WEALTHFOLIO_DB_DIR` | host (compose) | Directory that gets bind-mounted to `/wealthfolio` (read-only). The container then resolves `WEALTHFOLIO_DB=/wealthfolio/app.db`. |

Path-discovery and quote-refresh discipline live in [config/wealthfolio.md](../../config/wealthfolio.md). Do not duplicate them here.

## 6. Read-only guarantees

Three layers of defense against accidental writes ([SPEC §19.2 invariant 11](../../docs/SPEC.md)):

1. **No DDL/DML in the SQL file.** [skills/sql/wealthfolio-queries.sql](../sql/wealthfolio-queries.sql) contains only `SELECT` / CTEs; verified by [tests/wealthfolio_query/test_readonly.sh](../../tests/wealthfolio_query/test_readonly.sh).
2. **Read-only open mode.** Shell paths use `sqlite3 -readonly`; Python paths use `mode=ro&immutable=1` URI ([query.py](query.py)). Either rejects DDL/DML at the SQLite layer.
3. **Parameterized binding only.** User-supplied flag values reach SQL through `:name` placeholders (`.parameter set` in shell, `sqlite3.Connection.execute(sql, dict)` in Python). The wrapper never `printf`s user input into a SQL body.

## 7. Concurrency

`sqlite3 -readonly` permits unlimited concurrent readers. The wrapper holds no caller-side locks — multiple agents can run subcommands in parallel against the same DB without coordination. Writes only ever come from the Wealthfolio GUI; the user is expected to quit the GUI before snapshots that need WAL-clean data per [config/wealthfolio.md §7](../../config/wealthfolio.md).

## 8. Schema-version pin

The SQL file opens with `-- version: wealthfolio v3.2.1 (build 20260301.1)`. The wrapper diffs this against the pin in [config/wealthfolio.md](../../config/wealthfolio.md) at startup; mismatch → exit 2 with a clear message ([SPEC §19.2 invariant 14](../../docs/SPEC.md)). The canonical schema dump lives at [research/wealthfolio-schema-v3.2.1.txt](../../research/wealthfolio-schema-v3.2.1.txt); test [test_schema.sh](../../tests/wealthfolio_query/test_schema.sh) diffs the fixture against it on every run.

## 9. Tests

Fixture-backed regression suite under [tests/wealthfolio_query/](../../tests/wealthfolio_query/). Run all of it with:

```bash
make test-wealthfolio-query
# or directly:
bash tests/wealthfolio_query/run-all.sh
```

The fixture rebuilds from [fixture.sql](../../tests/wealthfolio_query/fixture.sql) on every invocation — no committed `.db` to drift.
