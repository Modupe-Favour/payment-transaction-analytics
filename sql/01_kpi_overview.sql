-- ==========================================================================
-- 01 — KPI Overview
-- --------------------------------------------------------------------------
-- Headline KPIs: TPV (USD), transaction count, avg ticket, success rate,
-- failure rate, p95 response time.
--
-- Designed to be the top-of-funnel metric for an executive dashboard.
-- ==========================================================================

WITH base AS (
    SELECT
        COUNT(*)                                       AS transaction_count,
        SUM(amount_usd)                                AS tpv_usd,
        AVG(amount_usd)                                AS avg_ticket_usd,
        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success_count,
        SUM(CASE WHEN status = 'failed'  THEN 1 ELSE 0 END) AS failure_count,
        COUNT(DISTINCT merchant_id)                    AS active_merchants,
        COUNT(DISTINCT country_code)                   AS active_countries,
        COUNT(DISTINCT payment_method)                 AS active_methods
    FROM fact_transactions
)
SELECT
    transaction_count,
    tpv_usd,
    avg_ticket_usd,
    success_count,
    failure_count,
    ROUND(100.0 * success_count / NULLIF(transaction_count, 0), 2) AS success_rate_pct,
    ROUND(100.0 * failure_count / NULLIF(transaction_count, 0), 2) AS failure_rate_pct,
    active_merchants,
    active_countries,
    active_methods
FROM base;
