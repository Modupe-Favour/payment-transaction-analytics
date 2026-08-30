"""
Analytics layer — pandas-based post-processing on top of SQL query results.

Most heavy lifting is done in SQL; this module adds convenience wrappers,
percentile computations (SQLite compat), and helper series for the
Streamlit dashboard.
"""
from __future__ import annotations

import pandas as pd

from .queries import run_query


# --------------------------------------------------------------------------- #
# KPI helpers                                                                 #
# --------------------------------------------------------------------------- #

def get_kpi_overview() -> pd.DataFrame:
    """Headline KPIs."""
    return run_query("kpi_overview")


def get_daily_kpi_trend() -> pd.DataFrame:
    """Daily KPIs + 7-day rolling success rate."""
    df = run_query("daily_kpi_trend")
    df["tx_date"] = pd.to_datetime(df["tx_date"])
    return df


def get_monthly_trend() -> pd.DataFrame:
    df = run_query("monthly_trend")
    df["month_start"] = pd.to_datetime(df["month_start"])
    return df


# --------------------------------------------------------------------------- #
# Merchant performance — pandas-side percentile enrichment for SQLite        #
# --------------------------------------------------------------------------- #

def get_merchant_performance() -> pd.DataFrame:
    df = run_query("merchant_performance")
    # Recompute percentiles in pandas (works on both SQLite + Postgres results)
    if len(df) > 1:
        df["success_percentile"] = (df["success_rate_pct"].rank(pct=True) * 100).round(2)
        df["tpv_percentile"]     = (df["tpv_usd"].rank(pct=True) * 100).round(2)
        df["tpv_rank"]           = df["tpv_usd"].rank(ascending=False, method="min").astype(int)
        # Performance segment
        def _seg(row):
            if row["success_rate_pct"] < 90 and row["success_percentile"] < 25:
                return "underperformer"
            if row["success_rate_pct"] >= 95 and row["tpv_percentile"] >= 75:
                return "star"
            if row["tpv_percentile"] >= 75:
                return "high_volume"
            return "average"
        df["performance_segment"] = df.apply(_seg, axis=1)
    return df.sort_values("tpv_usd", ascending=False).reset_index(drop=True)


def get_country_analysis() -> pd.DataFrame:
    return run_query("country_analysis")


def get_payment_method_analysis() -> pd.DataFrame:
    return run_query("payment_method_analysis")


def get_failure_reasons() -> pd.DataFrame:
    return run_query("failure_reasons")


def get_hourly_heatmap() -> pd.DataFrame:
    df = run_query("hourly_heatmap")
    # Add day_name in pandas (SQLite path returns '' for day_name)
    _day_names = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
    if "day_name" in df.columns:
        df["day_name"] = df["day_of_week"].map(_day_names).fillna(df.get("day_name", ""))
    return df


def get_value_bands() -> pd.DataFrame:
    return run_query("value_bands")


def get_recovery_opportunity() -> pd.DataFrame:
    return run_query("recovery_opportunity")


# --------------------------------------------------------------------------- #
# Cross-tab helpers                                                           #
# --------------------------------------------------------------------------- #

def get_failure_by_method() -> pd.DataFrame:
    """Failure reason x payment method matrix."""
    from .database import get_engine
    from sqlalchemy import text
    eng = get_engine()
    sql = """
        SELECT payment_method, failure_reason,
               COUNT(*) AS failure_count,
               ROUND(SUM(amount_usd), 2) AS lost_tpv_usd
        FROM fact_transactions
        WHERE status = 'failed'
        GROUP BY payment_method, failure_reason
        ORDER BY payment_method, failure_count DESC
    """
    with eng.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    return df


def get_failure_by_country() -> pd.DataFrame:
    """Failure reason x country matrix."""
    from .database import get_engine
    from sqlalchemy import text
    eng = get_engine()
    sql = """
        SELECT country_code, failure_reason,
               COUNT(*) AS failure_count,
               ROUND(SUM(amount_usd), 2) AS lost_tpv_usd
        FROM fact_transactions
        WHERE status = 'failed'
        GROUP BY country_code, failure_reason
        ORDER BY country_code, failure_count DESC
    """
    with eng.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    return df


def get_daily_kpi_by_dimension(dim: str) -> pd.DataFrame:
    """Daily KPIs broken down by a single dimension (country_code,
    payment_method, segment, channel)."""
    from .database import get_engine
    from sqlalchemy import text
    eng = get_engine()
    if dim not in {"country_code", "payment_method", "segment", "channel", "merchant_tier"}:
        raise ValueError(f"Unsupported dimension: {dim}")
    sql = f"""
        SELECT
            date(timestamp)                              AS tx_date,
            {dim}                                        AS dim_value,
            COUNT(*)                                     AS transaction_count,
            SUM(amount_usd)                              AS tpv_usd,
            ROUND(100.0 * SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) / COUNT(*), 2)
                                                          AS success_rate_pct
        FROM fact_transactions
        GROUP BY 1, 2
        ORDER BY 1, 2
    """
    with eng.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    df["tx_date"] = pd.to_datetime(df["tx_date"])
    return df
