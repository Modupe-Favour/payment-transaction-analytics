-- ==========================================================================
-- 07 — Hour-of-day + day-of-week heat-map
-- --------------------------------------------------------------------------
-- Identifies peak and off-peak windows by transaction volume and success
-- rate. Output is suitable for a heatmap (dow x hour).
-- ==========================================================================

SELECT
    EXTRACT(ISODOW FROM timestamp)::INT                   AS day_of_week,  -- 1=Mon .. 7=Sun
    TO_CHAR(timestamp, 'Dy')                               AS day_name,
    EXTRACT(HOUR FROM timestamp)::INT                      AS hour_of_day,
    COUNT(*)                                               AS transaction_count,
    SUM(amount_usd)                                        AS tpv_usd,
    ROUND(
        100.0 * SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END)
              / COUNT(*),
        2
    )                                                      AS success_rate_pct
FROM fact_transactions
GROUP BY 1, 2, 3
ORDER BY 1, 3;
