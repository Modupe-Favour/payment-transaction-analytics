# 💳 Payment Transaction Analytics
Live Dashboard: https://payment-transaction-analytics-npx6oalqhercucdz8kaplt.streamlit.app/

> **End-to-end portfolio project** — analyse 1.2M+ payment transactions across five African markets, surface KPIs and failure diagnostics, and serve an interactive dashboard.
>
> **Stack:** Python · SQL (PostgreSQL / SQLite) · Streamlit · Plotly · pandas

![Status](https://img.shields.io/badge/status-active-success)
![Data](https://img.shields.io/badge/data-1.2M%20transactions-blue)
![Markets](https://img.shields.io/badge/markets-NG%20%7C%20KE%20%7C%20GH%20%7C%20ZA%20%7C%20EG-orange)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## 📌 Project summary

A production-grade analytics pipeline that ingests **1.2M synthetic payment transactions** across **Nigeria, Kenya, Ghana, South Africa, and Egypt**, models them in a star schema, and serves a multi-page Streamlit dashboard for monitoring TPV, success rates, failure diagnostics, and time-series trends.

The project demonstrates the full analytics workflow expected of a fintech analyst:

1. **Data engineering** — generate, validate, and load 1.2M transactions into a relational star schema.
2. **SQL analysis** — write idiomatic analytical SQL (CTEs, window functions, percentiles, conditional aggregation) to compute KPIs.
3. **Python analysis** — pandas-based post-processing, percentile enrichment, and cross-tabulation.
4. **Dashboard** — interactive Streamlit dashboard with Stripe-inspired visual design.
5. **Recommendations** — quantified TPV recovery opportunities by failure reason.

---

## 📊 Headline KPIs (12-month window)

| Metric | Value |
|---|---|
| Total Payment Volume (TPV) | **$41.5M** |
| Transaction volume | **1,200,000** |
| Average ticket size | **$34.59** |
| Success rate | **93.41%** |
| Active merchants | 220 |
| Active countries | 5 |
| Payment methods | 4 (Cards, Bank Transfer, Mobile Money, USSD) |
| Date range | Jan 1, 2025 – Dec 31, 2025 |

### Dashboard preview

![Overview](assets/dashboard_overview.png)

*More pages: [Merchants](assets/dashboard_merchants.png) · [Geography](assets/dashboard_geography.png) · [Payment Methods](assets/dashboard_methods.png) · [Failures](assets/dashboard_failures.png) · [Trends](assets/dashboard_trends.png)*

---

## 🏗️ Architecture

```
┌─────────────────────┐
│  data/generate_     │   Synthetic data generator
│  transactions.py    │   (deterministic, seed=42)
└──────────┬──────────┘
           │ writes
           ▼
   ┌──────────────┐
   │  Parquet     │  data/transactions.parquet (1.2M rows)
   │  + CSV       │  data/merchants.parquet   (220 rows)
   └──────┬───────┘
          │ loads via src/database.py
          ▼
   ┌──────────────────────────────────────┐
   │  Star Schema (SQLAlchemy backend)    │
   │  ┌─────────────┐  ┌──────────────┐   │
   │  │ dim_country │  │ dim_payment_ │   │
   │  │             │  │   method     │   │
   │  └─────────────┘  └──────────────┘   │
   │  ┌─────────────┐  ┌──────────────┐   │
   │  │ dim_merchant│  │ fact_trans-  │   │
   │  │             │  │   actions   │1.2M│
   │  └─────────────┘  └──────────────┘   │
   └────────────┬─────────────────────────┘
                │ SQL queries (/sql)
                ▼
   ┌──────────────────────────────────────┐
   │  Python analytics layer (src/)       │
   │  • queries.py — SQL loader + SQLite  │
   │    compatibility shim                 │
   │  • analytics.py — KPI functions      │
   │  • visualizations.py — Plotly charts │
   └────────────┬─────────────────────────┘
                │ serves
                ▼
   ┌──────────────────────────────────────┐
   │  Streamlit Dashboard                 │
   │  streamlit_app.py + 5 pages          │
   │  • Overview   • Geography            │
   │  • Merchants  • Payment Methods      │
   │  • Failures   • Trends               │
   └──────────────────────────────────────┘
```

**Backend flexibility:** the same code runs against SQLite (zero-setup, default) or PostgreSQL (production / Docker Compose). Switch via `DATABASE_URL`.

---

## 📁 Project structure

```
payment-transaction-analytics/
├── streamlit_app.py              # Dashboard entry point (Overview page)
├── pages/                        # Streamlit multi-page app
│   ├── 1_🏪_Merchants.py
│   ├── 2_🌍_Geography.py
│   ├── 3_💳_Payment_Methods.py
│   ├── 4_⚠️_Failures.py
│   └── 5_📈_Trends.py
├── data/
│   ├── generate_transactions.py  # 1.2M-row synthetic generator
│   ├── transactions.parquet      # Generated (gitignored)
│   ├── merchants.parquet         # Generated (gitignored)
│   └── transactions_sample.csv   # 1k-row preview (committed)
├── sql/
│   ├── 01_schema.sql             # PostgreSQL DDL (star schema)
│   ├── 02_indexes.sql            # Performance indexes
│   ├── 01_kpi_overview.sql
│   ├── 02_daily_kpi_trend.sql
│   ├── 03_merchant_performance.sql
│   ├── 04_country_analysis.sql
│   ├── 05_payment_method_analysis.sql
│   ├── 06_failure_reasons.sql
│   ├── 07_hourly_heatmap.sql
│   ├── 08_monthly_trend.sql
│   ├── 09_value_bands.sql
│   └── 10_recovery_opportunity.sql
├── src/
│   ├── database.py               # SQLAlchemy engine + loader
│   ├── queries.py                # SQL file loader + SQLite compat
│   ├── analytics.py              # KPI functions (pandas)
│   └── visualizations.py         # Plotly chart builders
├── notebooks/
│   └── 01_eda_payment_transactions.ipynb
├── .streamlit/config.toml        # Stripe-inspired theme
├── docker-compose.yml            # Local PostgreSQL
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## 🚀 Quickstart

### Option A — Zero-setup (SQLite, recommended for first run)

```bash
git clone <your-fork-url>
cd payment-transaction-analytics
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Generate 1.2M synthetic transactions (~12 seconds)
python data/generate_transactions.py --rows 1200000

# 2. Load into SQLite database (~30 seconds)
python -m src.database load

# 3. Launch the dashboard
streamlit run streamlit_app.py
```

Open <http://localhost:8501>.

### Option B — PostgreSQL via Docker

```bash
# Start Postgres 16 in a container
docker compose up -d

# Point the app at Postgres
cp .env.example .env
# Edit .env: DATABASE_URL=postgresql+psycopg2://analytics:analytics@localhost:5432/payments

# Generate + load + run
python data/generate_transactions.py --rows 1200000
python -m src.database load
streamlit run streamlit_app.py
```

### Option C — Streamlit Community Cloud

1. Push the repo to GitHub.
2. Go to <https://share.streamlit.io> and connect the repo.
3. Set the main file path to `streamlit_app.py`.
4. Add `DATABASE_URL` to Streamlit secrets (use [Neon](https://neon.tech) or [Supabase](https://supabase.com) free tier).
5. Deploy.

---

## 📐 KPI definitions

| KPI | Definition |
|---|---|
| **TPV (Total Payment Volume)** | Sum of `amount_usd` across all transactions in scope. |
| **Transaction volume** | Count of transactions (`COUNT(*)`). |
| **Avg ticket size** | `SUM(amount_usd) / COUNT(*)`. |
| **Success rate** | `100 * SUM(status='success') / COUNT(*)`. |
| **Failure rate** | `100 * SUM(status='failed')  / COUNT(*)`. |
| **Lost TPV** | `SUM(amount_usd WHERE status='failed')`. |
| **Recoverable TPV** | `Lost TPV × recoverable_pct` per failure reason (see `sql/10_recovery_opportunity.sql`). |
| **Avg response time** | `AVG(response_ms)` — proxy for payment latency. |
| **TPV share** | A segment's TPV divided by total TPV (window function). |
| **Performance segment** | `star` (high TPV + high success) · `high_volume` · `underperformer` (low success) · `average`. |

---

## 🔍 Analytical highlights

### Failure-reason diagnostic

The 1.2M-transaction dataset has a **6.59% failure rate** (79,054 failures). The top three failure reasons account for **68% of all failures**:

| Rank | Failure reason | Share | Lost TPV |
|---|---|---|---|
| 1 | Insufficient funds | 33.9% | $1.0M |
| 2 | Card declined | 18.0% | $0.5M |
| 3 | Network timeout | 16.0% | $0.5M |

### Recovery opportunity

Applying industry-benchmark recovery rates to each failure reason surfaces **~$950K of recoverable TPV** — a **2.3% portfolio uplift** if the top three fixable causes (network timeout, insufficient funds, card declines) are addressed.

See `sql/10_recovery_opportunity.sql` for the quantified model.

### Performance segment classification

Of 220 merchants:
- **5 stars** (high TPV + high success) — protect and scale
- **44 high-volume** (high TPV, mid success) — optimise routing
- **19 underperformers** (high TPV + low success) — urgent intervention
- **152 average** — monitor

---

## 🧪 Data generation methodology

The synthetic data generator (`data/generate_transactions.py`) produces realistic African fintech patterns:

- **Geographic weighting** — Nigeria 34% · Kenya 22% · South Africa 22% · Ghana 12% · Egypt 10%
- **Payment method mix** — Mobile Money 36% · Cards 32% · Bank Transfer 28% · USSD 4%
- **Time patterns** — Evening peak (18:00–21:00) at 1.35× baseline · Friday/Saturday peak at 1.20–1.25×
- **Success probability** — Per-transaction model based on:
  - Payment method base rate (mobile money 94.1% · bank transfer 95.2% · card 92.5% · USSD 91.8%)
  - Country infrastructure score (0.86–0.95)
  - Merchant segment boost (betting −3%, savings +2.5%)
  - Hour-of-day penalty (off-hours −0.8%, peak hours −0.4%)
  - High-value penalty (>$200 −1.5%)
  - New-customer penalty (−1%)
- **Failure-reason distribution** — Insufficient funds 34% · Card declined 18% · Network timeout 16% · Fraud 9% · Limit exceeded 8% · Invalid account 7% · Bank downtime 5% · Expired card 3%
- **Deterministic** — `--seed 42` produces identical output for reproducibility.

---

## 🛠️ Tech choices

| Decision | Choice | Why |
|---|---|---|
| ORM / DB layer | **SQLAlchemy 2.0** | DB-agnostic — same code runs on SQLite (local) and PostgreSQL (prod). |
| Default DB | **SQLite** | Zero-setup, portable, works on Streamlit Cloud free tier. |
| Prod DB | **PostgreSQL 16** | Standard fintech stack; supports window functions, `PERCENT_RANK`, `EXTRACT(ISODOW)`. |
| Dashboard | **Streamlit** | Rapid Python-native dashboards; easy Streamlit Cloud deploy. |
| Charts | **Plotly** | Interactive, professional look, exports to HTML. |
| Data format | **Parquet** | Columnar, compressed (1.2M rows = ~50MB), fast reads. |
| SQL files | **Plain `.sql`** | Reviewable in any IDE, version-controlled, no string escaping. |

---

## 📒 Notebooks

- **`notebooks/01_eda_payment_transactions.ipynb`** — exploratory data analysis: distributions, categorical breakdowns, success-rate analysis, time-series patterns, correlation matrix.

Run with:
```bash
jupyter lab notebooks/
```

---

## 🚦 Testing the pipeline

```bash
# Verify all SQL queries execute and return sensible results
python -c "
import sys; sys.path.insert(0, '.')
from src.analytics import (
    get_kpi_overview, get_merchant_performance, get_country_analysis,
    get_payment_method_analysis, get_failure_reasons, get_recovery_opportunity,
    get_hourly_heatmap, get_monthly_trend, get_value_bands, get_daily_kpi_trend
)
print('KPI:', get_kpi_overview().iloc[0]['tpv_usd'])
print('Merchants:', len(get_merchant_performance()))
print('Countries:', len(get_country_analysis()))
print('Methods:', len(get_payment_method_analysis()))
print('Failures:', len(get_failure_reasons()))
print('Recovery:', get_recovery_opportunity()['recoverable_tpv_usd'].sum())
print('Heatmap cells:', len(get_hourly_heatmap()))  # expect 168 (7*24)
print('Months:', len(get_monthly_trend()))           # expect 12
print('All queries OK')
"
```

---

## 📈 Sample insights you can reproduce

1. **Which country has the highest success rate?** → South Africa (94.5%), thanks to higher infrastructure score + card-heavy mix.
2. **Which payment method has the worst success rate?** → USSD (91.8%) — but only 4% of volume, so absolute impact is small.
3. **What's the largest TPV recovery opportunity?** → Network timeouts: 60% recoverable, ~$300K upside.
4. **Which merchants are bleeding TPV?** → See the "Underperformers" table on the Merchants page — 19 merchants with high TPV but <90% success rate.
5. **When do failures spike?** → Late-night hours (22:00–05:00) and on USSD channel during peak congestion.

---

## 📝 License

MIT — see `LICENSE`. Data is synthetic and may be reused freely.

---

## 🙋 About

Built as a portfolio project demonstrating end-to-end fintech analytics capability:
- **Data engineering:** schema design, ETL, indexing
- **SQL:** CTEs, window functions, percentiles, conditional aggregation
- **Python:** pandas, SQLAlchemy, Plotly
- **Dashboard:** multi-page Streamlit with custom theme
- **Communication:** KPI definitions, recommendations, methodology documentation

Feedback welcome via issues or pull requests.
