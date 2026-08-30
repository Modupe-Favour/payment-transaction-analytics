-- ==========================================================================
-- 05 — Payment method analysis
-- --------------------------------------------------------------------------
-- Compares cards, bank transfer, mobile money, USSD across:
--   - volume / TPV / share
--   - success rate, failure rate
--   - avg ticket size
--   - avg response time
-- ==========================================================================

WITH method_kpis AS (
    SELECT
        t.payment_method,
        t.payment_method_label,
        pm.method_category,
        COUNT(*)                                              AS transaction_count,
        SUM(t.amount_usd)                                     AS tpv_usd,
        AVG(t.amount_usd)                                     AS avg_ticket_usd,
        100.0 * SUM(CASE WHEN t.status = 'success' THEN 1 ELSE 0 END)
              / COUNT(*)                                      AS success_rate_pct,
        100.0 * SUM(CASE WHEN t.status = 'failed'  THEN 1 ELSE 0 END)
              / COUNT(*)                                      AS failure_rate_pct,
        AVG(t.response_ms)                                    AS avg_response_ms
    FROM fact_transactions t
    JOIN dim_payment_method pm ON pm.method_key = t.payment_method
    GROUP BY 1, 2, 3
)
SELECT
    payment_method,
    payment_method_label,
    method_category,
    transaction_count,
    ROUND(tpv_usd, 2)             AS tpv_usd,
    ROUND(avg_ticket_usd, 2)      AS avg_ticket_usd,
    ROUND(success_rate_pct, 2)    AS success_rate_pct,
    ROUND(failure_rate_pct, 2)    AS failure_rate_pct,
    ROUND(avg_response_ms, 0)     AS avg_response_ms,
    ROUND(100.0 * tpv_usd / SUM(tpv_usd) OVER (), 2) AS tpv_share_pct
FROM method_kpis
ORDER BY tpv_usd DESC;
