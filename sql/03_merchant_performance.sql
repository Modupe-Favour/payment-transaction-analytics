-- ==========================================================================
-- 03 — Merchant performance ranking
-- --------------------------------------------------------------------------
-- Identifies top-performing merchants by TPV, and flags underperformers
-- by success rate (defined as below the portfolio mean and bottom quartile).
-- Uses window functions + CTEs to compute percentile bands.
-- ==========================================================================

WITH merchant_kpis AS (
    SELECT
        m.merchant_id,
        m.merchant_name,
        m.segment,
        m.tier,
        m.country_code,
        COUNT(*)                                              AS transaction_count,
        SUM(t.amount_usd)                                     AS tpv_usd,
        AVG(t.amount_usd)                                     AS avg_ticket_usd,
        100.0 * SUM(CASE WHEN t.status = 'success' THEN 1 ELSE 0 END)
              / COUNT(*)                                      AS success_rate_pct
    FROM fact_transactions t
    JOIN dim_merchant m ON m.merchant_id = t.merchant_id
    GROUP BY 1, 2, 3, 4, 5
),
ranked AS (
    SELECT
        *,
        PERCENT_RANK() OVER (ORDER BY success_rate_pct) AS success_pctl,
        PERCENT_RANK() OVER (ORDER BY tpv_usd)          AS tpv_pctl,
        RANK()         OVER (ORDER BY tpv_usd DESC)     AS tpv_rank
    FROM merchant_kpis
)
SELECT
    merchant_id,
    merchant_name,
    segment,
    tier,
    country_code,
    transaction_count,
    ROUND(tpv_usd, 2)              AS tpv_usd,
    ROUND(avg_ticket_usd, 2)       AS avg_ticket_usd,
    ROUND(success_rate_pct, 2)     AS success_rate_pct,
    tpv_rank,
    ROUND(success_pctl * 100, 2)   AS success_percentile,
    ROUND(tpv_pctl    * 100, 2)    AS tpv_percentile,
    CASE
        WHEN success_rate_pct < 90 AND success_pctl < 0.25 THEN 'underperformer'
        WHEN success_rate_pct >= 95 AND tpv_pctl    >= 0.75 THEN 'star'
        WHEN tpv_pctl >= 0.75                              THEN 'high_volume'
        ELSE 'average'
    END AS performance_segment
FROM ranked
ORDER BY tpv_usd DESC;
