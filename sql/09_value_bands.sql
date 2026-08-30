-- ==========================================================================
-- 09 — Transaction value band analysis
-- --------------------------------------------------------------------------
-- Buckets transactions into value bands and compares:
--   - volume / TPV distribution
--   - success rate by band (high-value vs micro transactions)
-- ==========================================================================

WITH banded AS (
    SELECT
        *,
        CASE
            WHEN amount_usd <  5        THEN '01_micro (<$5)'
            WHEN amount_usd <  20       THEN '02_small ($5-$20)'
            WHEN amount_usd <  100      THEN '03_medium ($20-$100)'
            WHEN amount_usd <  500      THEN '04_large ($100-$500)'
            ELSE                             '05_premium ($500+)'
        END AS value_band
    FROM fact_transactions
)
SELECT
    value_band,
    COUNT(*)                                              AS transaction_count,
    ROUND(SUM(amount_usd), 2)                             AS tpv_usd,
    ROUND(AVG(amount_usd), 2)                             AS avg_ticket_usd,
    ROUND(100.0 * SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) / COUNT(*), 2)
                                                          AS success_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN status = 'failed'  THEN 1 ELSE 0 END) / COUNT(*), 2)
                                                          AS failure_rate_pct,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)    AS volume_share_pct,
    ROUND(100.0 * SUM(amount_usd) / SUM(SUM(amount_usd)) OVER (), 2)
                                                          AS tpv_share_pct
FROM banded
GROUP BY 1
ORDER BY 1;
