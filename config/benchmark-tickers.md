---
benchmarks:
  india:
    ticker: ^NSEI
    name: Nifty 50
    return_type: price-return
    label: "price-return (no dividend reinvestment)"
    source: yfinance
    alternatives:
      total_return: ^NSEI.TRI  # NSE Total Return Index — not on yfinance; prefer NIFTYBEES (NAV-based) if needed
  us:
    ticker: ^GSPC
    name: S&P 500
    return_type: price-return
    label: "price-return (no dividend reinvestment)"
    source: yfinance
    alternatives:
      total_return: ^SP500TR   # available on yfinance; use if dividends matter to alpha comparison
---

### § 1 — What this file is

This file declares the default benchmark ticker for each market. `skills/benchmark/benchmark.py` (M6) reads the YAML front-matter at runtime. The `--benchmark-ticker` CLI flag (SPEC §18.5) overrides the default for a single run.

### § 2 — Default benchmarks

| Market | Ticker | Index name | Return type | yfinance available |
|---|---|---|---|---|
| `india` | `^NSEI` | Nifty 50 | Price-return | Yes |
| `us` | `^GSPC` | S&P 500 | Price-return | Yes |

### § 3 — Override for a single run

```bash
benchmark \
  --market india \
  --benchmark-ticker ^NSEI \
  --windows 1w,1m,3m,1y,3y,inception
```

When `--benchmark-ticker` is given, `config/benchmark-tickers.md` is not read. To change the **permanent default**, edit the `ticker` field in the YAML front-matter of this file.

### § 4 — Price-return limitation

Both `^NSEI` and `^GSPC` are **price-return** benchmarks on Yahoo Finance: they track index price only, excluding dividend reinvestment. This understates the total return of either index, so the alpha vs. a total-return benchmark would be lower. Weekly reports stamp the `label` field from the YAML front-matter adjacent to each market's alpha rows (SPEC §14.3 mandates this explicitly for `^NSEI`; the US report mirrors the treatment).

Alternatives:
- India total-return: `^NSEI.TRI` (NSE Total Return Index) is not on yfinance at MVP; `NIFTYBEES` (NAV-adjusted) is the practical substitute.
- US total-return: `^SP500TR` is available on yfinance and can be used as a drop-in.

To switch, edit `ticker` in the YAML and confirm yfinance resolves the new symbol before closing.

### § 5 — Wealthfolio "Beat the Market?" (SPEC §14.4)

Wealthfolio has a built-in "Beat the Market?" panel that natively compares account performance to S&P 500 or any configurable ETF. That comparison is transaction-derived and is the **primary visual benchmark** at MVP. The number this `benchmark` skill produces is derived from `daily_account_valuation` snapshots and is intended for programmatic weekly-report inclusion and ledger storage — the two will differ and that is expected.

### § 6 — Version / upgrade policy

If a default ticker changes (e.g., migrating to a total-return variant), bump `version` in the YAML, update this file, and file a `bd` ticket before changing production runs — stale `benchmark_alpha_*` ledger rows computed against the old ticker become non-comparable.
