-- ==========================================================================
-- Payment Transaction Analytics — performance indexes
-- --------------------------------------------------------------------------
-- Indexes that the analytical queries in this repo benefit from.
-- Apply after data load to keep insert performance reasonable.
-- ==========================================================================

BEGIN;

-- Time-based analytics (trend, daily KPIs)
CREATE INDEX IF NOT EXISTS idx_fact_tx_timestamp       ON fact_transactions (timestamp);
CREATE INDEX IF NOT EXISTS idx_fact_tx_date            ON fact_transactions ((timestamp::date));
CREATE INDEX IF NOT EXISTS idx_fact_tx_hour            ON fact_transactions (EXTRACT(HOUR FROM timestamp));

-- Slice + dice by dimensions
CREATE INDEX IF NOT EXISTS idx_fact_tx_merchant        ON fact_transactions (merchant_id);
CREATE INDEX IF NOT EXISTS idx_fact_tx_country         ON fact_transactions (country_code);
CREATE INDEX IF NOT EXISTS idx_fact_tx_method          ON fact_transactions (payment_method);
CREATE INDEX IF NOT EXISTS idx_fact_tx_status          ON fact_transactions (status);
CREATE INDEX IF NOT EXISTS idx_fact_tx_segment         ON fact_transactions (segment);
CREATE INDEX IF NOT EXISTS idx_fact_tx_failure_reason  ON fact_transactions (failure_reason);

-- Composite indexes for the most common dashboard filters
CREATE INDEX IF NOT EXISTS idx_fact_tx_country_ts      ON fact_transactions (country_code, timestamp);
CREATE INDEX IF NOT EXISTS idx_fact_tx_method_ts       ON fact_transactions (payment_method, timestamp);
CREATE INDEX IF NOT EXISTS idx_fact_tx_merchant_ts     ON fact_transactions (merchant_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_fact_tx_status_ts       ON fact_transactions (status, timestamp);

-- Covering index for the overview KPI query
CREATE INDEX IF NOT EXISTS idx_fact_tx_kpi_cover       ON fact_transactions (timestamp, status, amount_usd);

COMMIT;
