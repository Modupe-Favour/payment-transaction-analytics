-- ==========================================================================
-- 06 — Failure reason diagnostic
-- --------------------------------------------------------------------------
-- Breakdown of failure reasons by:
--   - overall frequency
--   - payment method (which methods drive which failures)
--   - country
-- Helps answer: "Where is the lost TPV, and what's causing it?"
-- ==========================================================================

-- 6a. Overall failure reason share
WITH failures AS (
    SELECT failure_reason, payment_method, country_code, amount_usd
    FROM fact_transactions
    WHERE status = 'failed'
),
reason_totals AS (
    SELECT
        failure_reason,
        COUNT(*)              AS failure_count,
        SUM(amount_usd)       AS lost_tpv_usd
    FROM failures
    GROUP BY 1
)
SELECT
    failure_reason,
    failure_count,
    ROUND(lost_tpv_usd, 2)                                AS lost_tpv_usd,
    ROUND(100.0 * failure_count / SUM(failure_count) OVER (), 2) AS failure_share_pct,
    ROUND(100.0 * lost_tpv_usd   / SUM(lost_tpv_usd)   OVER (), 2) AS lost_tpv_share_pct
FROM reason_totals
ORDER BY failure_count DESC;

-- 6b. Failure reason x payment method (run separately)
-- ====================================================
-- SELECT
--     payment_method,
--     failure_reason,
--     COUNT(*)        AS failure_count,
--     ROUND(SUM(amount_usd), 2) AS lost_tpv_usd
-- FROM fact_transactions
-- WHERE status = 'failed'
-- GROUP BY 1, 2
-- ORDER BY payment_method, failure_count DESC;

-- 6c. Failure reason x country (run separately)
-- ====================================================
-- SELECT
--     country_code,
--     failure_reason,
--     COUNT(*)        AS failure_count,
--     ROUND(SUM(amount_usd), 2) AS lost_tpv_usd
-- FROM fact_transactions
-- WHERE status = 'failed'
-- GROUP BY 1, 2
-- ORDER BY country_code, failure_count DESC;
