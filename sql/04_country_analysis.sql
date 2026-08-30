-- ==========================================================================
-- 04 — Country / geographic analysis
-- --------------------------------------------------------------------------
-- Per-country KPIs: TPV, volume, success rate, avg ticket, market share.
-- Also computes each country's share of total TPV (window function).
-- ==========================================================================

WITH country_kpis AS (
    SELECT
        t.country_code,
        c.country_name,
        c.currency_code,
        COUNT(*)                                              AS transaction_count,
        SUM(t.amount_usd)                                     AS tpv_usd,
        AVG(t.amount_usd)                                     AS avg_ticket_usd,
        100.0 * SUM(CASE WHEN t.status = 'success' THEN 1 ELSE 0 END)
              / COUNT(*)                                      AS success_rate_pct,
        100.0 * SUM(CASE WHEN t.status = 'failed'  THEN 1 ELSE 0 END)
              / COUNT(*)                                      AS failure_rate_pct,
        AVG(t.response_ms)                                    AS avg_response_ms
    FROM fact_transactions t
    JOIN dim_country c ON c.country_code = t.country_code
    GROUP BY 1, 2, 3
)
SELECT
    country_code,
    country_name,
    currency_code,
    transaction_count,
    ROUND(tpv_usd, 2)             AS tpv_usd,
    ROUND(avg_ticket_usd, 2)      AS avg_ticket_usd,
    ROUND(success_rate_pct, 2)    AS success_rate_pct,
    ROUND(failure_rate_pct, 2)    AS failure_rate_pct,
    ROUND(avg_response_ms, 0)     AS avg_response_ms,
    ROUND(100.0 * tpv_usd / SUM(tpv_usd) OVER (), 2) AS tpv_share_pct
FROM country_kpis
ORDER BY tpv_usd DESC;
