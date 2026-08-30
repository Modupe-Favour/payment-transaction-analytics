-- ==========================================================================
-- 08 — Monthly trend with month-over-month (MoM) growth
-- --------------------------------------------------------------------------
-- Tracks portfolio evolution: month-by-month TPV, volume, success rate,
-- and the MoM % change in TPV + volume.
-- ==========================================================================

WITH monthly AS (
    SELECT
        DATE_TRUNC('month', timestamp)::date               AS month_start,
        TO_CHAR(timestamp, 'YYYY-MM')                       AS month_label,
        COUNT(*)                                            AS transaction_count,
        SUM(amount_usd)                                     AS tpv_usd,
        AVG(amount_usd)                                     AS avg_ticket_usd,
        100.0 * SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END)
              / COUNT(*)                                    AS success_rate_pct
    FROM fact_transactions
    GROUP BY 1, 2
)
SELECT
    month_start,
    month_label,
    transaction_count,
    ROUND(tpv_usd, 2)             AS tpv_usd,
    ROUND(avg_ticket_usd, 2)      AS avg_ticket_usd,
    ROUND(success_rate_pct, 2)    AS success_rate_pct,
    -- MoM growth using LAG window function
    ROUND(
        100.0 * (tpv_usd - LAG(tpv_usd) OVER (ORDER BY month_start))
              / NULLIF(LAG(tpv_usd) OVER (ORDER BY month_start), 0),
        2
    )                              AS tpv_mom_growth_pct,
    ROUND(
        100.0 * (transaction_count - LAG(transaction_count) OVER (ORDER BY month_start))
              / NULLIF(LAG(transaction_count) OVER (ORDER BY month_start), 0),
        2
    )                              AS volume_mom_growth_pct
FROM monthly
ORDER BY month_start;
