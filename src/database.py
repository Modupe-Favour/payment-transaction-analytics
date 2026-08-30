"""
Database connection + data loading layer.

Uses SQLAlchemy so the same code runs against both SQLite (zero-setup local
development / Streamlit Cloud free tier) and PostgreSQL (production /
realistic fintech setup). Switch via DATABASE_URL env var (see .env.example).
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR     = PROJECT_ROOT / "data"
SQL_DIR      = PROJECT_ROOT / "sql"

DEFAULT_SQLITE_URL = f"sqlite:///{DATA_DIR}/payments.db"


def get_database_url() -> str:
    """Resolve DATABASE_URL from env, fall back to local SQLite.

    Only honors env vars that look like SQLAlchemy URLs (start with
    sqlite: / postgresql: / mysql: / ...). Anything else is ignored so
    unrelated env vars in the host environment don't break the app.
    """
    url = os.getenv("DATABASE_URL") or os.getenv("PAYMENTS_DATABASE_URL")
    valid_prefixes = ("sqlite:", "postgresql:", "postgres:", "mysql:", "mssql:", "oracle:")
    if url and url.lower().startswith(valid_prefixes):
        return url
    # Fall back to SQLite (auto-creates data/payments.db)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_SQLITE_URL


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return a cached SQLAlchemy engine."""
    url = get_database_url()
    # SQLite needs check_same_thread=False for Streamlit
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, future=True)
    return engine


# --------------------------------------------------------------------------- #
# Schema bootstrap                                                            #
# --------------------------------------------------------------------------- #

def _sqlite_ddl() -> list[str]:
    """Return SQLite-compatible DDL statements (subset of Postgres schema)."""
    return [
        """
        CREATE TABLE IF NOT EXISTS dim_country (
            country_code     TEXT PRIMARY KEY,
            country_name     TEXT NOT NULL,
            currency_code    TEXT NOT NULL,
            fx_to_usd        REAL NOT NULL,
            infra_score      REAL NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS dim_payment_method (
            method_key        TEXT PRIMARY KEY,
            method_label      TEXT NOT NULL,
            method_category   TEXT NOT NULL,
            base_success_rate REAL NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS dim_merchant (
            merchant_id      TEXT PRIMARY KEY,
            merchant_name    TEXT NOT NULL,
            segment          TEXT NOT NULL,
            tier             TEXT NOT NULL,
            country_code     TEXT NOT NULL,
            onboarded_at     TEXT NOT NULL,
            FOREIGN KEY (country_code) REFERENCES dim_country(country_code)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS fact_transactions (
            transaction_id        TEXT PRIMARY KEY,
            timestamp             TEXT NOT NULL,
            merchant_id           TEXT NOT NULL,
            country_code          TEXT NOT NULL,
            currency_code         TEXT NOT NULL,
            payment_method        TEXT NOT NULL,
            payment_method_label  TEXT NOT NULL,
            provider              TEXT NOT NULL,
            channel               TEXT NOT NULL,
            customer_type         TEXT NOT NULL,
            amount_local          REAL NOT NULL,
            amount_usd            REAL NOT NULL,
            status                TEXT NOT NULL,
            failure_reason        TEXT,
            response_ms           INTEGER NOT NULL,
            segment               TEXT NOT NULL,
            merchant_tier         TEXT NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_fact_tx_ts        ON fact_transactions(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_fact_tx_merchant   ON fact_transactions(merchant_id)",
        "CREATE INDEX IF NOT EXISTS idx_fact_tx_country    ON fact_transactions(country_code)",
        "CREATE INDEX IF NOT EXISTS idx_fact_tx_method     ON fact_transactions(payment_method)",
        "CREATE INDEX IF NOT EXISTS idx_fact_tx_status     ON fact_transactions(status)",
        "CREATE INDEX IF NOT EXISTS idx_fact_tx_failure    ON fact_transactions(failure_reason)",
        "CREATE INDEX IF NOT EXISTS idx_fact_tx_segment    ON fact_transactions(segment)",
    ]


def init_schema(engine: Engine | None = None) -> None:
    """Create tables if missing. Uses SQLite DDL when on SQLite; otherwise
    runs the canonical PostgreSQL schema from sql/01_schema.sql."""
    engine = engine or get_engine()
    if engine.url.get_backend_name() == "sqlite":
        with engine.begin() as conn:
            for stmt in _sqlite_ddl():
                conn.execute(text(stmt))
    else:
        schema_sql = (SQL_DIR / "01_schema.sql").read_text()
        # Naive splitter on ';' — fine for our DDL (no triggers / functions)
        statements = [s.strip() for s in schema_sql.split(";") if s.strip()]
        with engine.begin() as conn:
            for stmt in statements:
                # Skip transaction-control statements that psql handles but
                # SQLAlchemy Connection.execute does not allow in a begin block
                if stmt.upper().startswith(("BEGIN", "COMMIT", "ROLLBACK")):
                    continue
                conn.execute(text(stmt))


# --------------------------------------------------------------------------- #
# Reference data seeding                                                      #
# --------------------------------------------------------------------------- #

# Mirrored from data/generate_transactions.py — kept here so the loader is
# self-contained for dimension seeding.
_REF_COUNTRIES = {
    "NG": {"name": "Nigeria",       "currency": "NGN", "fx_to_usd": 0.00065, "infra_score": 0.86},
    "KE": {"name": "Kenya",         "currency": "KES", "fx_to_usd": 0.0072,  "infra_score": 0.91},
    "GH": {"name": "Ghana",         "currency": "GHS", "fx_to_usd": 0.072,   "infra_score": 0.88},
    "ZA": {"name": "South Africa",  "currency": "ZAR", "fx_to_usd": 0.054,   "infra_score": 0.95},
    "EG": {"name": "Egypt",         "currency": "EGP", "fx_to_usd": 0.021,   "infra_score": 0.89},
}

_REF_METHODS = {
    "card":           {"label": "Card",           "category": "card",   "base_success": 0.925},
    "bank_transfer":  {"label": "Bank Transfer",  "category": "bank",   "base_success": 0.952},
    "mobile_money":   {"label": "Mobile Money",   "category": "wallet", "base_success": 0.941},
    "ussd":           {"label": "USSD",            "category": "ussd",   "base_success": 0.918},
}


def _seed_reference_data(engine: Engine) -> None:
    """Insert countries + payment methods into dimension tables."""
    countries_df = pd.DataFrame([
        {"country_code": k, "country_name": v["name"], "currency_code": v["currency"],
         "fx_to_usd": v["fx_to_usd"], "infra_score": v["infra_score"]}
        for k, v in _REF_COUNTRIES.items()
    ])
    methods_df = pd.DataFrame([
        {"method_key": k, "method_label": v["label"], "method_category": v["category"],
         "base_success_rate": v["base_success"]}
        for k, v in _REF_METHODS.items()
    ])
    with engine.begin() as conn:
        countries_df.to_sql("dim_country", conn, if_exists="replace", index=False)
        methods_df.to_sql("dim_payment_method", conn, if_exists="replace", index=False)


# --------------------------------------------------------------------------- #
# Data loading                                                                #
# --------------------------------------------------------------------------- #

def load_parquet_to_db(parquet_path: Path | None = None,
                       merchants_path: Path | None = None,
                       engine: Engine | None = None,
                       chunksize: int = 50_000) -> tuple[int, int]:
    """Load transactions + merchants parquet files into the database.

    Returns (n_transactions, n_merchants).
    """
    engine = engine or get_engine()
    init_schema(engine)
    _seed_reference_data(engine)

    parquet_path = parquet_path or (DATA_DIR / "transactions.parquet")
    merchants_path = merchants_path or (DATA_DIR / "merchants.parquet")

    if not parquet_path.exists():
        raise FileNotFoundError(
            f"Transactions parquet not found at {parquet_path}. "
            "Run `python data/generate_transactions.py` first."
        )

    # Merchants (small)
    merchants_df = pd.read_parquet(merchants_path)
    # Align column names with the SQL schema
    merchants_df = merchants_df.rename(columns={"country": "country_code"})
    # Convert datetime to ISO string for SQLite compat
    merchants_df["onboarded_at"] = merchants_df["onboarded_at"].astype(str)
    with engine.begin() as conn:
        merchants_df.to_sql("dim_merchant", conn, if_exists="replace", index=False)

    # Transactions — chunked write to keep memory bounded
    total = 0
    df = pd.read_parquet(parquet_path)
    # Align column names with the SQL schema
    df = df.rename(columns={
        "country":  "country_code",
        "currency": "currency_code",
    })
    df["timestamp"] = df["timestamp"].astype(str)
    with engine.begin() as conn:
        # Replace to keep idempotent
        conn.execute(text("DELETE FROM fact_transactions"))
        # Write in chunks
        for i in range(0, len(df), chunksize):
            chunk = df.iloc[i:i + chunksize]
            chunk.to_sql("fact_transactions", conn, if_exists="append", index=False)
            total += len(chunk)
            print(f"  ...loaded {total:,} / {len(df):,} rows")

    return total, len(merchants_df)


def is_loaded(engine: Engine | None = None) -> bool:
    """Check whether fact_transactions has any rows."""
    engine = engine or get_engine()
    try:
        with engine.connect() as conn:
            n = conn.execute(text("SELECT COUNT(*) FROM fact_transactions")).scalar()
        return bool(n)
    except Exception:
        return False


def row_count(engine: Engine | None = None) -> int:
    engine = engine or get_engine()
    with engine.connect() as conn:
        return int(conn.execute(text("SELECT COUNT(*) FROM fact_transactions")).scalar() or 0)


if __name__ == "__main__":
    # CLI entry: python -m src.database load
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "load":
        n_tx, n_m = load_parquet_to_db()
        print(f"\nLoaded {n_tx:,} transactions + {n_m} merchants into {get_database_url()}")
    elif cmd == "status":
        url = get_database_url()
        print(f"DATABASE_URL = {url}")
        print(f"Loaded: {is_loaded()}  Rows: {row_count()}")
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python -m src.database [load|status]")
