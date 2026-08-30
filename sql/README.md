# SQL Library

This folder contains the PostgreSQL schema, indexes, and analytical queries
used by the dashboard. Each query file is self-contained and can be run
directly against the database (e.g. via `psql` or DBeaver).

## Schema

| File | Purpose |
|---|---|
| `01_schema.sql` | Star schema DDL: `dim_country`, `dim_payment_method`, `dim_merchant`, `fact_transactions` |
| `02_indexes.sql` | Performance indexes (time, dimensions, composite, covering) |

## Analytical queries

| # | File | What it answers |
|---|---|---|
| 01 | `01_kpi_overview.sql` | Headline KPIs: TPV, volume, success rate, active dimensions |
| 02 | `02_daily_kpi_trend.sql` | Daily KPIs with 7-day rolling success rate (window function) |
| 03 | `03_merchant_performance.sql` | Merchant ranking + performance classification (PERCENT_RANK, CASE) |
| 04 | `04_country_analysis.sql` | Per-country KPIs + TPV share (window function) |
| 05 | `05_payment_method_analysis.sql` | Per-method KPIs + TPV share |
| 06 | `06_failure_reasons.sql` | Failure-reason breakdown: count, lost TPV, share |
| 07 | `07_hourly_heatmap.sql` | Hour-of-day × day-of-week heatmap source |
| 08 | `08_monthly_trend.sql` | Monthly KPIs with MoM growth (LAG window function) |
| 09 | `09_value_bands.sql` | Transaction value band analysis |
| 10 | `10_recovery_opportunity.sql` | Quantified TPV recovery opportunity per failure reason |

## Running

```bash
# From psql
psql "postgresql://analytics:analytics@localhost:5432/payments" \
  -f sql/01_kpi_overview.sql

# From Python
python -c "
import sys; sys.path.insert(0, '.')
from src.analytics import get_kpi_overview
print(get_kpi_overview())
"
```

## SQL style

- **CTEs over subqueries** for readability.
- **Window functions** for percentiles, rankings, MoM growth.
- **Conditional aggregation** (`SUM(CASE WHEN ...)`) for KPIs.
- **ISO standard SQL** where possible (portable across PostgreSQL + SQLite via the compat shim in `src/queries.py`).
- **Comments** at the top of each file explaining purpose and approach.
