# Data

This folder contains the synthetic data generator and the generated datasets.

## Files

| File | Description | Size | Gitignored? |
|---|---|---|---|
| `generate_transactions.py` | Synthetic data generator — 1.2M transactions | — | No (committed) |
| `transactions.parquet` | Full 1.2M-row transaction dataset | ~50 MB | Yes |
| `merchants.parquet` | 220-merchant dimension table | <1 MB | Yes |
| `transactions_sample.csv` | 1k-row CSV preview | <1 MB | No (committed) |
| `merchants.csv` | Merchants as CSV | <1 MB | No (committed) |
| `payments.db` | SQLite database (auto-created on first load) | ~120 MB | Yes |

## Regenerating the data

```bash
# Default: 1.2M transactions, seed=42, Jan-Dec 2025
python data/generate_transactions.py

# Custom: 500k transactions
python data/generate_transactions.py --rows 500000

# Custom date range
python data/generate_transactions.py --start 2024-01-01 --end 2024-12-31

# Different seed (different patterns)
python data/generate_transactions.py --seed 99
```

## Loading into the database

After generating, load the parquet files into the database:

```bash
# SQLite (default)
python -m src.database load

# PostgreSQL (set DATABASE_URL first)
DATABASE_URL=postgresql+psycopg2://analytics:analytics@localhost:5432/payments \
  python -m src.database load
```

## Data schema

See `sql/01_schema.sql` for the canonical PostgreSQL DDL. The Python loader
auto-creates an equivalent SQLite schema when running locally.

### fact_transactions (1.2M rows)

| Column | Type | Description |
|---|---|---|
| transaction_id | VARCHAR(20) PK | TX2025XXXXXXXXX |
| timestamp | TIMESTAMP | Transaction time |
| merchant_id | VARCHAR(16) FK | → dim_merchant |
| country_code | CHAR(2) FK | → dim_country |
| currency_code | CHAR(3) | NGN, KES, GHS, ZAR, EGP |
| payment_method | VARCHAR(32) FK | → dim_payment_method |
| payment_method_label | VARCHAR(32) | Display label |
| provider | VARCHAR(32) | Visa, MTN MoMo, NIBSS, etc. |
| channel | VARCHAR(16) | web, mobile_app, ussd, pos, api |
| customer_type | VARCHAR(24) | new, returning, repeat_high_value |
| amount_local | NUMERIC(14,2) | Amount in local currency |
| amount_usd | NUMERIC(14,2) | Amount in USD |
| status | VARCHAR(12) | success, failed |
| failure_reason | VARCHAR(32) | NULL for successful txns |
| response_ms | INTEGER | Response time in ms |
| segment | VARCHAR(32) | Merchant segment |
| merchant_tier | VARCHAR(16) | enterprise, mid_market, smb |

## Reproducibility

All data is deterministic given the same `--seed`. The default seed is 42.
