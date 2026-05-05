-- version: wealthfolio v3.3.0 (build 20260301.1)
-- schema-ref: research/wealthfolio-schema-v3.3.0.txt
-- mode: holdings-only (no reads from the `activities` table — see SPEC §5.2)
-- binding: SQLite named parameters (:param)
-- fidelity: Position JSON shape is pinned to Wealthfolio v3.2.1 (carried forward to v3.3.0;
--           v3.3.0 schema drift is confined to goals/goals_allocation/goal_plans/
--           sync_entity_metadata — none of which these queries read)
--           (commit 23bc088778898a499aab658694e2e2a8c1d208f1; see Position
--           provenance block below). Multi-currency-per-account cash and TWR
--           chaining are delegated to later M2 subtasks (M2.7, M2.8).
--
-- Named-query convention
--   Each query is introduced by `-- name: <slug>` on its own line and terminated
--   with a semicolon. The wrapper (M2) reads this file as text and dispatches by
--   slug. Blocks are otherwise standalone — CTEs are redefined per query so each
--   block runs in isolation.
--
-- Common idioms reused across queries
--   latest_snapshot / positions_flat:
--     Flattens the JSON `positions` HashMap from the most recent
--     holdings_snapshots row per account.
--   Market inference:
--     CASE on assets.instrument_exchange_mic, with accounts.currency fallback
--     when MIC is NULL. XNSE/XBOM -> india; XNAS/XNYS/ARCX -> us.
--   Yahoo-ticker normalization:
--     CASE on MIC: XNSE -> `<symbol>.NS`, XBOM -> `<symbol>.BO`,
--     XNAS/XNYS/ARCX -> `<symbol>`, else COALESCE(display_code, instrument_symbol).
--   Scope filter (SPEC §6.8 tri-mode):
--     scope_type IN ('market','account_group','account'); `accounts."group"` is
--     always quoted (reserved word in SQLite).
--   TOTAL pseudo-account rows:
--     holdings_snapshots and daily_account_valuation each carry a `TOTAL`
--     pseudo-account_id row alongside real-UUID rows (observed live in v3.3.0,
--     M2.14). Every query below JOINs accounts, which naturally drops TOTAL
--     because it won't match accounts.id. Any new query added here MUST JOIN
--     accounts or filter account_id != 'TOTAL' explicitly — otherwise aggregate
--     reads will double-count.
--
-- Position JSON shape pinned from Wealthfolio v3.2.1 commit 23bc0887:
-- AccountStateSnapshot.positions is asset_id -> Position; Position uses camelCase serde.
-- Source: crates/core/src/portfolio/snapshot/positions_model.rs and
--         crates/core/src/portfolio/snapshot/holdings_calculator.rs.
-- JSON paths used: $.quantity, $.averageCost (Decimal serialized via serde-float).
--
-- Invariants (SPEC §19.1)
--   Read-only. No DDL/DML below — enforced at the wrapper layer via
--   `sqlite3 -readonly` and statically by `grep` in this milestone's verification.


-- =============================================================================
-- get-net-worth — SPEC §5.3 / §6.8
-- =============================================================================
-- params:  :date      (YYYY-MM-DD; NULL selects the latest available valuation per account)
--          :market    (india|us|all)
--          :currency  (INR|USD|none; none emits base-currency total)
-- returns: base_total, fx_day
-- notes:   Sums total_value * fx_rate_to_base across the latest
--          daily_account_valuation row per active account on or before :date,
--          filtered by market. `fx_day` is emitted so the shell wrapper can
--          convert the base total to an output denomination without turning
--          `--currency` into an account filter.
--          Decimal fields are stored as TEXT in Wealthfolio; cast to REAL on read.
-- name: get-net-worth
WITH valuation_at_date AS (
    SELECT dav.*
    FROM daily_account_valuation dav
    JOIN (
        SELECT account_id, MAX(valuation_date) AS max_date
        FROM daily_account_valuation
        WHERE :date IS NULL OR valuation_date <= :date
        GROUP BY account_id
    ) m
      ON m.account_id = dav.account_id
     AND m.max_date   = dav.valuation_date
),
active_valuation AS (
    SELECT
        v.*,
        acc.currency AS account_currency
    FROM valuation_at_date v
    JOIN accounts acc ON acc.id = v.account_id
    WHERE acc.is_active   = 1
      AND acc.is_archived = 0
),
market_filtered AS (
    SELECT *
    FROM active_valuation
    WHERE :market = 'all'
       OR (:market = 'india' AND account_currency = 'INR')
       OR (:market = 'us'    AND account_currency = 'USD')
)
SELECT
    COALESCE(
        SUM(CAST(m.total_value AS REAL) * CAST(m.fx_rate_to_base AS REAL)),
        0.0
    ) AS base_total,
    (
        SELECT MAX(CAST(av.fx_rate_to_base AS REAL))
        FROM active_valuation av
        WHERE :currency != 'none'
          AND av.account_currency = :currency
    ) AS fx_day
FROM market_filtered m
;


-- =============================================================================
-- get-cash-balance — SPEC §6.8
-- =============================================================================
-- params:  :currency     (INR|USD|all)
--          :scope_type   (market|account_group|account)
--          :scope_value  (string; `all` with scope_type='market' passes all)
-- returns: cash_balance  (native when :currency is INR/USD; base currency when all)
-- notes:   v1 reads the per-account cash line from the latest daily_account_valuation
--          row. Accounts whose holdings_snapshots.cash_balances JSON holds multiple
--          currencies are out of scope for v1.
-- name: get-cash-balance
WITH latest_valuation AS (
    SELECT dav.*
    FROM daily_account_valuation dav
    JOIN (
        SELECT account_id, MAX(valuation_date) AS max_date
        FROM daily_account_valuation
        GROUP BY account_id
    ) m
      ON m.account_id = dav.account_id
     AND m.max_date   = dav.valuation_date
)
SELECT
    COALESCE(
        SUM(
            CASE
              WHEN :currency = 'all'
                THEN CAST(v.cash_balance AS REAL) * CAST(v.fx_rate_to_base AS REAL)
              ELSE CAST(v.cash_balance AS REAL)
            END
        ),
        0.0
    ) AS cash_balance
FROM latest_valuation v
JOIN accounts acc ON acc.id = v.account_id
WHERE acc.is_active   = 1
  AND acc.is_archived = 0
  AND (:currency = 'all' OR acc.currency = :currency)
  AND (
          (:scope_type = 'market' AND :scope_value = 'all')
       OR (:scope_type = 'market'
             AND ((:scope_value = 'india' AND acc.currency = 'INR')
               OR (:scope_value = 'us'    AND acc.currency = 'USD')))
       OR (:scope_type = 'account_group' AND acc."group" = :scope_value)
       OR (:scope_type = 'account'       AND acc.name    = :scope_value)
      )
;


-- =============================================================================
-- list-holdings — SPEC §5.3
-- =============================================================================
-- params:  :market       (india|us|all)
--          :scope_type   (market|account_group|account)
--          :scope_value  (string matching the scope axis)
-- returns: ticker, name, market, currency, account, account_group, asset_type,
--          quantity, avg_cost, snapshot_price, snapshot_market_value,
--          allocation_pct, unrealized_pl_pct
-- notes:   Mirrors export-snapshot's normalized row shape except for the thesis
--          column, which is merged only by the export-snapshot wrapper.
-- name: list-holdings
WITH latest_snapshot AS (
    SELECT hs.*
    FROM holdings_snapshots hs
    JOIN (
        SELECT account_id, MAX(snapshot_date) AS max_date
        FROM holdings_snapshots
        GROUP BY account_id
    ) m
      ON m.account_id = hs.account_id
     AND m.max_date   = hs.snapshot_date
),
positions_flat AS (
    SELECT
        hs.account_id,
        p.key                                  AS position_key,
        json_extract(p.value, '$.quantity')    AS quantity,
        json_extract(p.value, '$.averageCost') AS avg_cost
    FROM latest_snapshot hs,
         json_each(hs.positions) p
),
latest_quote AS (
    SELECT q.*
    FROM quotes q
    JOIN (
        SELECT asset_id, MAX(day) AS max_day
        FROM quotes
        GROUP BY asset_id
    ) m
      ON m.asset_id = q.asset_id
     AND m.max_day  = q.day
),
asset_type_map AS (
    SELECT
        ata.asset_id,
        MAX(CASE
              WHEN tc.id = 'ETF' OR tc.parent_id = 'ETP' THEN 1
              ELSE 0
            END) AS is_etf
    FROM asset_taxonomy_assignments ata
    JOIN taxonomy_categories tc
      ON tc.taxonomy_id = ata.taxonomy_id
     AND tc.id          = ata.category_id
    WHERE ata.taxonomy_id = 'instrument_type'
    GROUP BY ata.asset_id
),
scoped AS (
    SELECT
        CASE
          WHEN a.instrument_exchange_mic = 'XNSE' THEN a.instrument_symbol || '.NS'
          WHEN a.instrument_exchange_mic = 'XBOM' THEN a.instrument_symbol || '.BO'
          WHEN a.instrument_exchange_mic IN ('XNAS','XNYS','ARCX') THEN a.instrument_symbol
          ELSE COALESCE(a.display_code, a.instrument_symbol)
        END AS ticker,
        a.name AS name,
        CASE
          WHEN a.instrument_exchange_mic IN ('XNSE','XBOM') THEN 'india'
          WHEN a.instrument_exchange_mic IN ('XNAS','XNYS','ARCX') THEN 'us'
          WHEN a.instrument_exchange_mic IS NULL AND acc.currency = 'INR' THEN 'india'
          WHEN a.instrument_exchange_mic IS NULL AND acc.currency = 'USD' THEN 'us'
          ELSE 'unknown'
        END AS market,
        a.quote_ccy AS currency,
        acc.name    AS account,
        acc."group" AS account_group,
        CASE
          WHEN COALESCE(atm.is_etf, 0) = 1 THEN 'ETF'
          ELSE 'stock'
        END AS asset_type,
        CAST(pf.quantity AS REAL)                          AS quantity,
        CAST(pf.avg_cost AS REAL)                          AS avg_cost,
        CAST(lq.close    AS REAL)                          AS snapshot_price,
        CAST(pf.quantity AS REAL) * CAST(lq.close AS REAL) AS snapshot_market_value
    FROM positions_flat pf
    JOIN accounts acc           ON acc.id     = pf.account_id
    JOIN assets   a             ON a.id       = pf.position_key
    LEFT JOIN latest_quote   lq  ON lq.asset_id = a.id
    LEFT JOIN asset_type_map atm ON atm.asset_id = a.id
    WHERE acc.is_active   = 1
      AND acc.is_archived = 0
),
filtered AS (
    SELECT *
    FROM scoped
    WHERE (:market = 'all' OR market = :market)
      AND (
              (:scope_type = 'market' AND :scope_value = 'all')
           OR (:scope_type = 'market'        AND market        = :scope_value)
           OR (:scope_type = 'account_group' AND account_group = :scope_value)
           OR (:scope_type = 'account'       AND account       = :scope_value)
          )
)
SELECT
    ticker,
    name,
    market,
    currency,
    account,
    account_group,
    asset_type,
    quantity,
    avg_cost,
    snapshot_price,
    snapshot_market_value,
    snapshot_market_value * 1.0 / NULLIF(SUM(snapshot_market_value) OVER (), 0) AS allocation_pct,
    CASE
      WHEN avg_cost IS NULL OR avg_cost = 0 THEN NULL
      ELSE (snapshot_price - avg_cost) * 1.0 / avg_cost
    END AS unrealized_pl_pct
FROM filtered
ORDER BY ticker, account
;


-- =============================================================================
-- export-snapshot — SPEC §5.4 / §7.1.1
-- =============================================================================
-- params:  :market       (india|us)
--          :scope_type   (market|account_group|account)
--          :scope_value  (string matching the scope axis)
-- returns: ticker, name, market, currency, account, account_group, asset_type,
--          quantity, avg_cost, snapshot_price, snapshot_market_value,
--          allocation_pct, unrealized_pl_pct
-- notes:   Phase 1 frozen-snapshot columns MINUS `thesis`. The wrapper (M2) merges
--          input/{market}/theses.yaml before writing portfolio-snapshot.csv
--          (SPEC §5.4). allocation_pct is computed AFTER the scope filter so it
--          reflects the chosen slice, not the full portfolio.
--
--          asset_type ∈ {stock, ETF} (SPEC §7.1.1) is derived from the
--          `instrument_type` taxonomy: any asset whose category id is `ETF` or whose
--          category sits under `ETP` is an ETF; everything else (incl. unassigned
--          assets) falls back to `stock`. assets.instrument_type alone is too coarse
--          because upstream lumps stocks/ETFs/funds into the same provider-routing
--          enum (`EQUITY`).
--
--          Final ORDER BY ticker, account makes consecutive runs against the same
--          DB state byte-identical (required by the M9 snapshot-freeze invariant
--          and M2.7's byte-identical re-run test).
-- name: export-snapshot
WITH latest_snapshot AS (
    SELECT hs.*
    FROM holdings_snapshots hs
    JOIN (
        SELECT account_id, MAX(snapshot_date) AS max_date
        FROM holdings_snapshots
        GROUP BY account_id
    ) m
      ON m.account_id = hs.account_id
     AND m.max_date   = hs.snapshot_date
),
positions_flat AS (
    SELECT
        hs.account_id,
        p.key                                  AS position_key,
        json_extract(p.value, '$.quantity')    AS quantity,
        json_extract(p.value, '$.averageCost') AS avg_cost
    FROM latest_snapshot hs,
         json_each(hs.positions) p
),
latest_quote AS (
    SELECT q.*
    FROM quotes q
    JOIN (
        SELECT asset_id, MAX(day) AS max_day
        FROM quotes
        GROUP BY asset_id
    ) m
      ON m.asset_id = q.asset_id
     AND m.max_day  = q.day
),
asset_type_map AS (
    SELECT
        ata.asset_id,
        MAX(CASE
              WHEN tc.id = 'ETF' OR tc.parent_id = 'ETP' THEN 1
              ELSE 0
            END) AS is_etf
    FROM asset_taxonomy_assignments ata
    JOIN taxonomy_categories tc
      ON tc.taxonomy_id = ata.taxonomy_id
     AND tc.id          = ata.category_id
    WHERE ata.taxonomy_id = 'instrument_type'
    GROUP BY ata.asset_id
),
scoped AS (
    SELECT
        CASE
          WHEN a.instrument_exchange_mic = 'XNSE' THEN a.instrument_symbol || '.NS'
          WHEN a.instrument_exchange_mic = 'XBOM' THEN a.instrument_symbol || '.BO'
          WHEN a.instrument_exchange_mic IN ('XNAS','XNYS','ARCX') THEN a.instrument_symbol
          ELSE COALESCE(a.display_code, a.instrument_symbol)
        END AS ticker,
        a.name AS name,
        CASE
          WHEN a.instrument_exchange_mic IN ('XNSE','XBOM') THEN 'india'
          WHEN a.instrument_exchange_mic IN ('XNAS','XNYS','ARCX') THEN 'us'
          WHEN a.instrument_exchange_mic IS NULL AND acc.currency = 'INR' THEN 'india'
          WHEN a.instrument_exchange_mic IS NULL AND acc.currency = 'USD' THEN 'us'
          ELSE 'unknown'
        END AS market,
        a.quote_ccy    AS currency,
        acc.name       AS account,
        acc."group"    AS account_group,
        CASE
          WHEN COALESCE(atm.is_etf, 0) = 1 THEN 'ETF'
          ELSE 'stock'
        END AS asset_type,
        CAST(pf.quantity AS REAL)                              AS quantity,
        CAST(pf.avg_cost AS REAL)                              AS avg_cost,
        CAST(lq.close    AS REAL)                              AS snapshot_price,
        CAST(pf.quantity AS REAL) * CAST(lq.close AS REAL)     AS snapshot_market_value
    FROM positions_flat pf
    JOIN accounts acc          ON acc.id     = pf.account_id
    JOIN assets   a            ON a.id       = pf.position_key
    LEFT JOIN latest_quote   lq  ON lq.asset_id = a.id
    LEFT JOIN asset_type_map atm ON atm.asset_id = a.id
    WHERE acc.is_active   = 1
      AND acc.is_archived = 0
),
filtered AS (
    SELECT *
    FROM scoped
    WHERE market = :market
      AND (
              (:scope_type = 'market'        AND market        = :scope_value)
           OR (:scope_type = 'account_group' AND account_group = :scope_value)
           OR (:scope_type = 'account'       AND account       = :scope_value)
          )
)
SELECT
    ticker,
    name,
    market,
    currency,
    account,
    account_group,
    asset_type,
    quantity,
    avg_cost,
    snapshot_price,
    snapshot_market_value,
    snapshot_market_value * 1.0 / NULLIF(SUM(snapshot_market_value) OVER (), 0) AS allocation_pct,
    CASE
      WHEN avg_cost IS NULL OR avg_cost = 0 THEN NULL
      ELSE (snapshot_price - avg_cost) * 1.0 / avg_cost
    END AS unrealized_pl_pct
FROM filtered
ORDER BY ticker, account
;


-- =============================================================================
-- get-avg-cost — SPEC §6.8
-- =============================================================================
-- params:  :ticker  (Yahoo-canonical, e.g. 'RELIANCE.NS' or 'AAPL')
-- returns: avg_cost (quantity-weighted across accounts holding the ticker)
-- notes:   In holdings-only mode, avg cost lives inside the positions JSON — not in
--          activities. Reverse-maps :ticker via instrument_symbol + MIC, falling
--          back to display_code for MIC-less assets. ADR / cross-listed reverse
--          lookups are out of scope for v1.
-- name: get-avg-cost
WITH latest_snapshot AS (
    SELECT hs.*
    FROM holdings_snapshots hs
    JOIN (
        SELECT account_id, MAX(snapshot_date) AS max_date
        FROM holdings_snapshots
        GROUP BY account_id
    ) m
      ON m.account_id = hs.account_id
     AND m.max_date   = hs.snapshot_date
),
positions_flat AS (
    SELECT
        hs.account_id,
        p.key                                  AS position_key,
        json_extract(p.value, '$.quantity')    AS quantity,
        json_extract(p.value, '$.averageCost') AS avg_cost
    FROM latest_snapshot hs,
         json_each(hs.positions) p
),
matched AS (
    SELECT
        CAST(pf.quantity AS REAL) AS quantity,
        CAST(pf.avg_cost AS REAL) AS avg_cost
    FROM positions_flat pf
    JOIN accounts acc ON acc.id = pf.account_id
    JOIN assets   a   ON a.id   = pf.position_key
    WHERE acc.is_active   = 1
      AND acc.is_archived = 0
      AND (
              (a.instrument_exchange_mic = 'XNSE' AND (a.instrument_symbol || '.NS') = :ticker)
           OR (a.instrument_exchange_mic = 'XBOM' AND (a.instrument_symbol || '.BO') = :ticker)
           OR (a.instrument_exchange_mic IN ('XNAS','XNYS','ARCX')
               AND a.instrument_symbol = :ticker)
           OR (a.instrument_exchange_mic IS NULL
               AND COALESCE(a.display_code, a.instrument_symbol) = :ticker)
          )
)
SELECT
    SUM(quantity * avg_cost) / NULLIF(SUM(quantity), 0) AS avg_cost
FROM matched
;


-- =============================================================================
-- Validation queries (used by --strict-scope; see SPEC §6.8 + M2 investigation §6)
-- =============================================================================
-- name: validate-scope-account-group
SELECT 1
FROM accounts
WHERE is_active   = 1
  AND is_archived = 0
  AND "group"     = :scope_value
LIMIT 1
;


-- name: validate-scope-account
SELECT 1
FROM accounts
WHERE is_active   = 1
  AND is_archived = 0
  AND name        = :scope_value
LIMIT 1
;


-- =============================================================================
-- get-portfolio-twr — SPEC §6.8
-- =============================================================================
-- params:  :market  (india|us)
--          :start   (YYYY-MM-DD, inclusive)
--          :end     (YYYY-MM-DD, inclusive)
-- returns: date, portfolio_value_base, cumulative_net_contribution_base
-- notes:   v1 emits per-day aggregates. The wrapper (M2) converts the cumulative
--          contribution series into per-day deltas and computes the chained product:
--            C[t] = cumulative[t] - cumulative[t-1]
--            TWR  = PROD(1 + ((V[t] - V[t-1] - C[t]) / V[t-1])) - 1  over [:start, :end]
--          SQL-side recursion is possible but fragile given TEXT-stored decimals;
--          Python-side math is cleaner.
--
--          Market filter uses accounts.currency (INR↔india, USD↔us). This is coarser
--          than the holdings-level MIC inference but daily_account_valuation does not
--          carry per-asset data.
-- name: get-portfolio-twr
SELECT
    dav.valuation_date AS date,
    SUM(CAST(dav.total_value AS REAL)
        * CAST(dav.fx_rate_to_base AS REAL))      AS portfolio_value_base,
    SUM(CAST(dav.net_contribution AS REAL)
        * CAST(dav.fx_rate_to_base AS REAL))      AS cumulative_net_contribution_base
FROM daily_account_valuation dav
JOIN accounts acc ON acc.id = dav.account_id
WHERE dav.valuation_date BETWEEN :start AND :end
  AND acc.is_active   = 1
  AND acc.is_archived = 0
  AND (
          (:market = 'india' AND acc.currency = 'INR')
       OR (:market = 'us'    AND acc.currency = 'USD')
      )
GROUP BY dav.valuation_date
ORDER BY dav.valuation_date
;
