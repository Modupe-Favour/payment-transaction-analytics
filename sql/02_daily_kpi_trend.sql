-- ==========================================================================
-- 02 — Daily KPI trend (volume, TPV, success rate)
-- --------------------------------------------------------------------------
-- Powers the main time-series charts. Uses a CTE + window functions to
-- compute a 7-day rolling success rate for smoothing.
-- ==========================================================================

WITH daily AS (
    SELECT
        timestamp::date                                AS tx_date,
        COUNT(*)                                       AS transaction_count,
        SUM(amount_usd)                                AS tpv_usd,
        AVG(amount_usd)                                AS avg_ticket_usd,
        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success_count,
        SUM(CASE WHEN status = 'failed'  THEN 1 ELSE 0 END) AS failure_count
    FROM fact_transactions
    GROUP BY 1
)
SELECT
    tx_date,
    transaction_count,
    tpv_usd,
    avg_ticket_usd,
    ROUND(100.0 * success_count / NULLIF(transaction_count, 0), 2) AS success_rate_pct,
    ROUND(100.0 * failure_count / NULLIF(transaction_count, 0), 2) AS failure_rate_pct,
    -- 7-day rolling success rate
    ROUND(
        100.0 * SUM(success_count) OVER w
              / NULLIF(SUM(transaction_count) OVER w, 0),
        2
    ) AS success_rate_7d_rolling_pct
FROM daily
WINDOW w AS (ORDER BY tx_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
ORDER BY tx_date;
