-- Wealthfolio query fixture seeds.
-- Anchor date: 2026-04-30; valuation window: 2026-01-30..2026-04-30.
-- ID conventions: acct_* for accounts, asset_* for assets, quote_* for quotes.
-- This file contains seed INSERTs only. The schema is loaded from
-- research/wealthfolio-schema-v3.3.0.txt by build_fixture.sh.

BEGIN TRANSACTION;

INSERT INTO platforms (
    id, name, url, external_id, kind, website_url, logo_url
) VALUES
    (
        'platform_fixture_india',
        'Fixture India Broker',
        'https://fixture.example/india',
        'fixture-india',
        'BROKERAGE',
        'https://fixture.example/india',
        NULL
    ),
    (
        'platform_fixture_us',
        'Fixture US Broker',
        'https://fixture.example/us',
        'fixture-us',
        'BROKERAGE',
        'https://fixture.example/us',
        NULL
    );

INSERT INTO accounts (
    id, name, account_type, "group", currency, is_default, is_active,
    created_at, updated_at, platform_id, account_number, meta, provider,
    provider_account_id, tracking_mode, is_archived
) VALUES
    (
        'acct_in_broker',
        'Fixture India Brokerage',
        'SECURITIES',
        'India Brokerage',
        'INR',
        1,
        1,
        '2026-01-30T00:00:00.000Z',
        '2026-04-30T00:00:00.000Z',
        'platform_fixture_india',
        'IN-001',
        '{"fixture":true}',
        'fixture',
        'in-001',
        'AUTOMATED',
        0
    ),
    (
        'acct_in_pms',
        'Fixture India PMS',
        'SECURITIES',
        'India PMS',
        'INR',
        0,
        1,
        '2026-01-30T00:00:00.000Z',
        '2026-04-30T00:00:00.000Z',
        'platform_fixture_india',
        'IN-PMS-001',
        '{"fixture":true}',
        'fixture',
        'in-pms-001',
        'MANUAL',
        0
    ),
    (
        'acct_us_broker',
        'Fixture US Brokerage',
        'SECURITIES',
        'US Brokerage',
        'USD',
        0,
        1,
        '2026-01-30T00:00:00.000Z',
        '2026-04-30T00:00:00.000Z',
        'platform_fixture_us',
        'US-001',
        '{"fixture":true}',
        'fixture',
        'us-001',
        'AUTOMATED',
        0
    ),
    (
        'acct_archived_decoy',
        'Fixture Archived Decoy',
        'SECURITIES',
        'Archived',
        'USD',
        0,
        0,
        '2026-01-30T00:00:00.000Z',
        '2026-04-30T00:00:00.000Z',
        'platform_fixture_us',
        'US-OLD-001',
        '{"fixture":true,"decoy":true}',
        'fixture',
        'us-old-001',
        'MANUAL',
        1
    );

INSERT INTO assets (
    id, kind, name, display_code, notes, metadata, is_active, quote_mode,
    quote_ccy, instrument_type, instrument_symbol, instrument_exchange_mic,
    provider_config, created_at, updated_at
) VALUES
    (
        'asset_reliance_xnse',
        'INVESTMENT',
        'Reliance Industries Limited',
        'RELIANCE.NS',
        'M2 fixture India XNSE equity',
        '{"fixture":true}',
        1,
        'MARKET',
        'INR',
        'EQUITY',
        'RELIANCE',
        'XNSE',
        '{"provider":"YAHOO"}',
        '2026-01-30T00:00:00.000Z',
        '2026-04-30T00:00:00.000Z'
    ),
    (
        'asset_tcs_xbom',
        'INVESTMENT',
        'Tata Consultancy Services Limited',
        'TCS.BO',
        'M2 fixture India XBOM equity',
        '{"fixture":true}',
        1,
        'MARKET',
        'INR',
        'EQUITY',
        'TCS',
        'XBOM',
        '{"provider":"YAHOO"}',
        '2026-01-30T00:00:00.000Z',
        '2026-04-30T00:00:00.000Z'
    ),
    (
        'asset_infosys_xnse',
        'INVESTMENT',
        'Infosys Limited',
        'INFY.NS',
        'M2 fixture second XNSE equity',
        '{"fixture":true}',
        1,
        'MARKET',
        'INR',
        'EQUITY',
        'INFY',
        'XNSE',
        '{"provider":"YAHOO"}',
        '2026-01-30T00:00:00.000Z',
        '2026-04-30T00:00:00.000Z'
    ),
    (
        'asset_niftybees_xnse',
        'INVESTMENT',
        'Nippon India ETF Nifty BeES',
        'NIFTYBEES.NS',
        'M2 fixture ETF taxonomy coverage',
        '{"fixture":true}',
        1,
        'MARKET',
        'INR',
        'EQUITY',
        'NIFTYBEES',
        'XNSE',
        '{"provider":"YAHOO"}',
        '2026-01-30T00:00:00.000Z',
        '2026-04-30T00:00:00.000Z'
    ),
    (
        'asset_pmscore_manual',
        'INVESTMENT',
        'Fixture PMS Core Basket',
        'PMSCORE.NS',
        'M2 fixture MIC-less display-code fallback',
        '{"fixture":true}',
        1,
        'MANUAL',
        'INR',
        'EQUITY',
        'PMSCORE',
        NULL,
        '{"provider":"MANUAL"}',
        '2026-01-30T00:00:00.000Z',
        '2026-04-30T00:00:00.000Z'
    ),
    (
        'asset_aapl_xnas',
        'INVESTMENT',
        'Apple Inc.',
        'AAPL',
        'M2 fixture US XNAS equity',
        '{"fixture":true}',
        1,
        'MARKET',
        'USD',
        'EQUITY',
        'AAPL',
        'XNAS',
        '{"provider":"YAHOO"}',
        '2026-01-30T00:00:00.000Z',
        '2026-04-30T00:00:00.000Z'
    ),
    (
        'asset_brkb_xnys',
        'INVESTMENT',
        'Berkshire Hathaway Inc. Class B',
        'BRK.B',
        'M2 fixture US XNYS equity',
        '{"fixture":true}',
        1,
        'MARKET',
        'USD',
        'EQUITY',
        'BRK.B',
        'XNYS',
        '{"provider":"YAHOO"}',
        '2026-01-30T00:00:00.000Z',
        '2026-04-30T00:00:00.000Z'
    ),
    (
        'asset_arkk_arcx',
        'INVESTMENT',
        'ARK Innovation ETF',
        'ARKK',
        'M2 fixture US ARCX security',
        '{"fixture":true}',
        1,
        'MARKET',
        'USD',
        'EQUITY',
        'ARKK',
        'ARCX',
        '{"provider":"YAHOO"}',
        '2026-01-30T00:00:00.000Z',
        '2026-04-30T00:00:00.000Z'
    ),
    (
        'asset_decoy_inactive',
        'INVESTMENT',
        'Archived Decoy Security',
        'DECOY',
        'Inactive fixture decoy',
        '{"fixture":true,"decoy":true}',
        0,
        'MARKET',
        'USD',
        'EQUITY',
        'DECOY',
        'XNAS',
        '{"provider":"YAHOO"}',
        '2026-01-30T00:00:00.000Z',
        '2026-04-30T00:00:00.000Z'
    );

INSERT INTO taxonomies (
    id, name, color, description, is_system, is_single_select, sort_order,
    created_at, updated_at
) VALUES
    (
        'instrument_type',
        'Instrument Type',
        '#8abceb',
        'Fixture taxonomy for ETF classification',
        1,
        1,
        10,
        '2026-01-30T00:00:00.000Z',
        '2026-04-30T00:00:00.000Z'
    );

INSERT INTO taxonomy_categories (
    id, taxonomy_id, parent_id, name, key, color, description, sort_order,
    created_at, updated_at
) VALUES
    (
        'ETP',
        'instrument_type',
        NULL,
        'Exchange Traded Product',
        'etp',
        '#4d9078',
        'Fixture parent category for ETPs',
        10,
        '2026-01-30T00:00:00.000Z',
        '2026-04-30T00:00:00.000Z'
    ),
    (
        'ETF',
        'instrument_type',
        'ETP',
        'Exchange Traded Fund',
        'etf',
        '#4d9078',
        'Fixture category for ETFs',
        20,
        '2026-01-30T00:00:00.000Z',
        '2026-04-30T00:00:00.000Z'
    );

INSERT INTO asset_taxonomy_assignments (
    id, asset_id, taxonomy_id, category_id, weight, source, created_at,
    updated_at
) VALUES
    (
        'assign_niftybees_instrument_type_etf',
        'asset_niftybees_xnse',
        'instrument_type',
        'ETF',
        10000,
        'fixture',
        '2026-01-30T00:00:00.000Z',
        '2026-04-30T00:00:00.000Z'
    );

WITH RECURSIVE
dates(day, n) AS (
    VALUES ('2026-01-30', 0)
    UNION ALL
    SELECT date(day, '+1 day'), n + 1
    FROM dates
    WHERE day < '2026-04-30'
),
quote_seed(asset_id, currency, start_close, daily_step, start_volume) AS (
    VALUES
        ('asset_reliance_xnse', 'INR', 2450.00, 1.20, 1000000),
        ('asset_tcs_xbom', 'INR', 3800.00, 0.75, 900000),
        ('asset_infosys_xnse', 'INR', 1440.00, 0.35, 1100000),
        ('asset_niftybees_xnse', 'INR', 235.00, 0.05, 500000),
        ('asset_pmscore_manual', 'INR', 100.00, 0.10, 0),
        ('asset_aapl_xnas', 'USD', 180.00, 0.35, 70000000),
        ('asset_brkb_xnys', 'USD', 410.00, 0.70, 3000000),
        ('asset_arkk_arcx', 'USD', 48.00, 0.09, 12000000)
)
INSERT INTO quotes (
    id, asset_id, day, source, open, high, low, close, adjclose, volume,
    currency, notes, created_at, timestamp
)
SELECT
    'quote_' || replace(substr(qs.asset_id, 7), '.', '_') || '_' || replace(d.day, '-', '_'),
    qs.asset_id,
    d.day,
    CASE WHEN qs.asset_id = 'asset_pmscore_manual' THEN 'MANUAL' ELSE 'YAHOO' END,
    printf('%.2f', qs.start_close + (d.n * qs.daily_step) - 1.00),
    printf('%.2f', qs.start_close + (d.n * qs.daily_step) + 2.00),
    printf('%.2f', qs.start_close + (d.n * qs.daily_step) - 2.00),
    printf('%.2f', qs.start_close + (d.n * qs.daily_step)),
    printf('%.2f', qs.start_close + (d.n * qs.daily_step)),
    printf('%d', qs.start_volume + (d.n * 10)),
    qs.currency,
    'M2 fixture quote history',
    d.day || 'T16:00:00.000Z',
    d.day || 'T16:00:00.000Z'
FROM quote_seed qs
CROSS JOIN dates d;

INSERT INTO holdings_snapshots (
    id, account_id, snapshot_date, currency, positions, cash_balances,
    cost_basis, net_contribution, calculated_at, net_contribution_base,
    cash_total_account_currency, cash_total_base_currency, source
) VALUES
    (
        'hs_acct_in_broker_2026_04_30',
        'acct_in_broker',
        '2026-04-30',
        'INR',
        '{"asset_reliance_xnse":{"quantity":"100","averageCost":"2400.00"},"asset_tcs_xbom":{"quantity":"40","averageCost":"3600.00"},"asset_infosys_xnse":{"quantity":"80","averageCost":"1380.00"},"asset_niftybees_xnse":{"quantity":"500","averageCost":"220.00"}}',
        '{"INR":"125000.00"}',
        '604000.00',
        '700000.00',
        '2026-04-30T17:00:00.000Z',
        '700000.00',
        '125000.00',
        '125000.00',
        'CALCULATED'
    ),
    (
        'hs_acct_in_pms_2026_04_30',
        'acct_in_pms',
        '2026-04-30',
        'INR',
        '{"asset_pmscore_manual":{"quantity":"5000","averageCost":"95.00"},"asset_reliance_xnse":{"quantity":"80","averageCost":"2350.00"}}',
        '{"INR":"900000.00"}',
        '663000.00',
        '1500000.00',
        '2026-04-30T17:00:00.000Z',
        '1500000.00',
        '900000.00',
        '900000.00',
        'CALCULATED'
    ),
    (
        'hs_acct_us_broker_2026_04_30',
        'acct_us_broker',
        '2026-04-30',
        'USD',
        '{"asset_aapl_xnas":{"quantity":"200","averageCost":"170.00"},"asset_brkb_xnys":{"quantity":"50","averageCost":"390.00"},"asset_arkk_arcx":{"quantity":"250","averageCost":"45.00"}}',
        '{"USD":"42000.00"}',
        '64750.00',
        '100000.00',
        '2026-04-30T17:00:00.000Z',
        '8320000.00',
        '42000.00',
        '3494400.00',
        'CALCULATED'
    ),
    (
        'hs_acct_archived_decoy_2026_04_30',
        'acct_archived_decoy',
        '2026-04-30',
        'USD',
        '{"asset_decoy_inactive":{"quantity":"999","averageCost":"1.00"},"asset_aapl_xnas":{"quantity":"999","averageCost":"1.00"}}',
        '{"USD":"999999.00"}',
        '1998.00',
        '999999.00',
        '2026-04-30T17:00:00.000Z',
        '83199916.80',
        '999999.00',
        '83199916.80',
        'CALCULATED'
    );

WITH RECURSIVE
dates(day, n) AS (
    VALUES ('2026-01-30', 0)
    UNION ALL
    SELECT date(day, '+1 day'), n + 1
    FROM dates
    WHERE day < '2026-04-30'
),
valuation_seed(
    account_id, account_currency, base_currency, fx_rate_to_base,
    start_cash, cash_step, start_investment, investment_step,
    start_cost_basis, cost_basis_step, start_net_contribution,
    net_contribution_step
) AS (
    VALUES
        (
            'acct_in_broker', 'INR', 'INR', 1.00,
            120500.00, 50.00, 615000.00, 388.8889,
            590000.00, 155.5556, 680000.00, 222.2222
        ),
        (
            'acct_us_broker', 'USD', 'INR', 83.20,
            39000.00, 33.3333, 75500.00, 50.00,
            63000.00, 19.4444, 95000.00, 55.5556
        )
)
INSERT INTO daily_account_valuation (
    id, account_id, valuation_date, account_currency, base_currency,
    fx_rate_to_base, cash_balance, investment_market_value, total_value,
    cost_basis, net_contribution, calculated_at
)
SELECT
    'dav_' || vs.account_id || '_' || replace(d.day, '-', '_'),
    vs.account_id,
    d.day,
    vs.account_currency,
    vs.base_currency,
    printf('%.4f', vs.fx_rate_to_base),
    printf('%.2f', vs.start_cash + (d.n * vs.cash_step)),
    printf('%.2f', vs.start_investment + (d.n * vs.investment_step)),
    printf(
        '%.2f',
        vs.start_cash + (d.n * vs.cash_step)
            + vs.start_investment + (d.n * vs.investment_step)
    ),
    printf('%.2f', vs.start_cost_basis + (d.n * vs.cost_basis_step)),
    printf('%.2f', vs.start_net_contribution + (d.n * vs.net_contribution_step)),
    d.day || 'T17:30:00.000Z'
FROM valuation_seed vs
CROSS JOIN dates d;

INSERT INTO daily_account_valuation (
    id, account_id, valuation_date, account_currency, base_currency,
    fx_rate_to_base, cash_balance, investment_market_value, total_value,
    cost_basis, net_contribution, calculated_at
) VALUES
    (
        'dav_acct_in_pms_2026_04_30',
        'acct_in_pms',
        '2026-04-30',
        'INR',
        'INR',
        '1.0000',
        '900000.00',
        '750000.00',
        '1650000.00',
        '663000.00',
        '1500000.00',
        '2026-04-30T17:30:00.000Z'
    ),
    (
        'dav_acct_archived_decoy_2026_04_30',
        'acct_archived_decoy',
        '2026-04-30',
        'USD',
        'INR',
        '83.2000',
        '999999.00',
        '1998.00',
        '1001997.00',
        '1998.00',
        '999999.00',
        '2026-04-30T17:30:00.000Z'
    );

COMMIT;
