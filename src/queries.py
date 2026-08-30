"""
SQL query loader.

Reads .sql files from /sql and exposes them as Python functions.
Keeps SQL in .sql files for reviewability + IDE support.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

import pandas as pd

from .database import get_engine, SQL_DIR

# Map of friendly names -> filenames
QUERY_FILES = {
    "kpi_overview":             "01_kpi_overview.sql",
    "daily_kpi_trend":          "02_daily_kpi_trend.sql",
    "merchant_performance":     "03_merchant_performance.sql",
    "country_analysis":         "04_country_analysis.sql",
    "payment_method_analysis":  "05_payment_method_analysis.sql",
    "failure_reasons":          "06_failure_reasons.sql",
    "hourly_heatmap":           "07_hourly_heatmap.sql",
    "monthly_trend":            "08_monthly_trend.sql",
    "value_bands":              "09_value_bands.sql",
    "recovery_opportunity":     "10_recovery_opportunity.sql",
}


@lru_cache(maxsize=None)
def load_query(name: str) -> str:
    """Read a .sql file by friendly name. Cached."""
    if name not in QUERY_FILES:
        raise KeyError(f"Unknown query '{name}'. Available: {list(QUERY_FILES)}")
    return (SQL_DIR / QUERY_FILES[name]).read_text()


def run_query(name: str, engine: Engine | None = None, params: dict | None = None) -> pd.DataFrame:
    """Execute a named query and return a pandas DataFrame.

    SQLite doesn't support all Postgres functions (PERCENT_RANK, EXTRACT(ISODOW), etc.)
    so for SQLite we have inline equivalents defined here.
    """
    engine = engine or get_engine()
    backend = engine.url.get_backend_name()
    sql = _sqlite_compat(name) if backend == "sqlite" else load_query(name)
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params or {})
    return df


# --------------------------------------------------------------------------- #
# SQLite-compatible query variants                                            #
# --------------------------------------------------------------------------- #

def _sqlite_compat(name: str) -> str:
    """Return SQLite-friendly version of a query.

    SQLite lacks PERCENT_RANK (use percentile approximation via window),
    EXTRACT(ISODOW), DATE_TRUNC, TO_CHAR — we substitute equivalents.
    """
    raw = load_query(name)
    # Apply common substitutions
    out = raw
    # DATE_TRUNC('month', ts)::date -> date(substr(ts,1,7) || '-01')
    out = out.replace(
        "DATE_TRUNC('month', timestamp)::date",
        "date(substr(timestamp,1,7) || '-01')"
    )
    # TO_CHAR(timestamp, 'YYYY-MM') -> substr(timestamp,1,7)
    out = out.replace("TO_CHAR(timestamp, 'YYYY-MM')", "substr(timestamp,1,7)")
    # Drop TO_CHAR(... 'Dy') AS day_name entirely (we'll add it via pandas later)
    import re
    out = re.sub(
        r"TO_CHAR\(\s*timestamp\s*,\s*'Dy'\s*\)\s+AS\s+day_name,?",
        "'' AS day_name,",
        out,
    )
    # EXTRACT(ISODOW FROM ts)::INT -> strftime('%w', ts) + adjustments
    # SQLite %w: 0=Sun..6=Sat ; ISO: 1=Mon..7=Sun
    out = out.replace(
        "EXTRACT(ISODOW FROM timestamp)::INT",
        "CASE cast(strftime('%w', timestamp) AS INT) WHEN 0 THEN 7 ELSE cast(strftime('%w', timestamp) AS INT) END"
    )
    # EXTRACT(HOUR FROM ts)::INT -> cast(strftime('%H', ts) AS INT)
    out = out.replace(
        "EXTRACT(HOUR FROM timestamp)::INT",
        "cast(strftime('%H', timestamp) AS INT)"
    )
    # timestamp::date -> date(timestamp)
    out = out.replace("timestamp::date", "date(timestamp)")
    # PERCENT_RANK() OVER (ORDER BY x) -> 0.5 placeholder (pandas re-computes proper percentiles)
    if "PERCENT_RANK()" in out:
        out = re.sub(
            r"PERCENT_RANK\(\)\s+OVER\s+\(\s*ORDER BY\s+success_rate_pct\s*\)\s+AS\s+\w+",
            "0.5 AS success_pctl",
            out,
        )
        out = re.sub(
            r"PERCENT_RANK\(\)\s+OVER\s+\(\s*ORDER BY\s+tpv_usd\s*\)\s+AS\s+\w+",
            "0.5 AS tpv_pctl",
            out,
        )
    return out


def list_queries() -> list[str]:
    return list(QUERY_FILES)
