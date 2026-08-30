-- ==========================================================================
-- 10 — Lost TPV recovery opportunity (executive summary)
-- --------------------------------------------------------------------------
-- Quantifies how much TPV is lost to each failure reason and estimates the
-- upside if the top-3 fixable reasons were recovered to industry benchmark.
-- This is the "data-driven recommendation" query.
-- ==========================================================================

WITH portfolio AS (
    SELECT
        SUM(amount_usd)                       AS total_tpv,
        SUM(CASE WHEN status='success'
                 THEN amount_usd ELSE 0 END)  AS captured_tpv,
        SUM(CASE WHEN status='failed'
                 THEN amount_usd ELSE 0 END)  AS lost_tpv
    FROM fact_transactions
),
by_reason AS (
    SELECT
        failure_reason,
        COUNT(*)              AS failure_count,
        SUM(amount_usd)       AS lost_tpv_usd
    FROM fact_transactions
    WHERE status = 'failed'
    GROUP BY 1
),
benchmark AS (
    -- Realistic recovery targets per failure reason (industry experience)
    SELECT 'insufficient_funds' AS failure_reason, 0.15 AS recoverable_pct
    UNION ALL SELECT 'card_declined',      0.25
    UNION ALL SELECT 'network_timeout',    0.60
    UNION ALL SELECT 'fraud_suspected',    0.05
    UNION ALL SELECT 'limit_exceeded',     0.30
    UNION ALL SELECT 'invalid_account',    0.50
    UNION ALL SELECT 'bank_downtime',      0.70
    UNION ALL SELECT 'expired_card',       0.40
)
SELECT
    r.failure_reason,
    r.failure_count,
    ROUND(r.lost_tpv_usd, 2)                                   AS lost_tpv_usd,
    ROUND(100.0 * r.lost_tpv_usd / p.total_tpv, 2)            AS lost_tpv_share_pct,
    ROUND(100.0 * b.recoverable_pct, 2)                       AS recoverable_pct,
    ROUND(r.lost_tpv_usd * b.recoverable_pct, 2)              AS recoverable_tpv_usd,
    ROUND(100.0 * r.lost_tpv_usd * b.recoverable_pct
                / p.total_tpv, 2)                             AS incremental_tpv_pct
FROM by_reason r
JOIN benchmark b USING (failure_reason)
CROSS JOIN portfolio p
ORDER BY r.lost_tpv_usd * b.recoverable_pct DESC;
