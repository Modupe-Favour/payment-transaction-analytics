-- ==========================================================================
-- Payment Transaction Analytics — PostgreSQL schema
-- --------------------------------------------------------------------------
-- Designed to run on PostgreSQL 13+ (also Docker container, see
-- docker-compose.yml). Compatible with most cloud Postgres offerings
-- (Neon, Supabase, RDS, AlloyDB).
--
-- Note: the same tables are created automatically in SQLite by the Python
-- loader (`src/database.py::load_data`) when running locally without
-- Postgres. SQL written here avoids Postgres-specific extensions where
-- possible so it remains portable.
-- ==========================================================================

BEGIN;

DROP TABLE IF EXISTS fact_transactions CASCADE;
DROP TABLE IF EXISTS dim_merchant CASCADE;
DROP TABLE IF EXISTS dim_country CASCADE;
DROP TABLE IF EXISTS dim_payment_method CASCADE;

-- ------------------------------------------------------------------------ --
-- Dimension: countries                                                     --
-- ------------------------------------------------------------------------ --
CREATE TABLE dim_country (
    country_code     CHAR(2)      PRIMARY KEY,
    country_name     VARCHAR(64)  NOT NULL,
    currency_code    CHAR(3)      NOT NULL,
    fx_to_usd        NUMERIC(12,6) NOT NULL,
    infra_score      NUMERIC(4,3) NOT NULL  -- 0..1 reliability index
);

-- ------------------------------------------------------------------------ --
-- Dimension: payment methods                                               --
-- ------------------------------------------------------------------------ --
CREATE TABLE dim_payment_method (
    method_key       VARCHAR(32)  PRIMARY KEY,
    method_label     VARCHAR(32)  NOT NULL,
    method_category  VARCHAR(32)  NOT NULL,  -- card | bank | wallet | ussd
    base_success_rate NUMERIC(5,4) NOT NULL
);

-- ------------------------------------------------------------------------ --
-- Dimension: merchants                                                     --
-- ------------------------------------------------------------------------ --
CREATE TABLE dim_merchant (
    merchant_id      VARCHAR(16)  PRIMARY KEY,
    merchant_name    VARCHAR(128) NOT NULL,
    segment          VARCHAR(32)  NOT NULL,  -- ecommerce, bill_pay, ...
    tier             VARCHAR(16)  NOT NULL,  -- enterprise | mid_market | smb
    country_code     CHAR(2)      NOT NULL REFERENCES dim_country(country_code),
    onboarded_at     TIMESTAMP    NOT NULL
);

-- ------------------------------------------------------------------------ --
-- Fact: transactions (1.2M+ rows)                                          --
-- ------------------------------------------------------------------------ --
CREATE TABLE fact_transactions (
    transaction_id        VARCHAR(20)  PRIMARY KEY,
    timestamp             TIMESTAMP    NOT NULL,
    merchant_id           VARCHAR(16)  NOT NULL REFERENCES dim_merchant(merchant_id),
    country_code          CHAR(2)      NOT NULL REFERENCES dim_country(country_code),
    currency_code         CHAR(3)      NOT NULL,
    payment_method        VARCHAR(32)  NOT NULL REFERENCES dim_payment_method(method_key),
    payment_method_label  VARCHAR(32)  NOT NULL,
    provider              VARCHAR(32)  NOT NULL,
    channel               VARCHAR(16)  NOT NULL,
    customer_type         VARCHAR(24)  NOT NULL,
    amount_local          NUMERIC(14,2) NOT NULL,
    amount_usd            NUMERIC(14,2) NOT NULL,
    status                VARCHAR(12)  NOT NULL,  -- success | failed
    failure_reason        VARCHAR(32),
    response_ms           INTEGER      NOT NULL,
    segment               VARCHAR(32)  NOT NULL,
    merchant_tier         VARCHAR(16)  NOT NULL
);

COMMIT;
