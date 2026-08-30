"""Trends page — time-based patterns: daily, monthly, hourly heatmap, value bands."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

from src.analytics import (
    get_daily_kpi_trend, get_monthly_trend, get_hourly_heatmap, get_value_bands,
)
from src.visualizations import (
    COLORS, _apply_fintech_layout, area_chart, line_chart, fmt_usd
)

st.set_page_config(page_title="Trends", page_icon="📈", layout="wide")

st.title("📈 Trends & Patterns")
st.caption("Time-series, monthly run-rate, hourly heatmap, value band distribution")

# --- Daily TPV + Volume ---
st.subheader("Daily TPV & Transaction Volume")
daily = get_daily_kpi_trend()

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=daily["tx_date"], y=daily["tpv_usd"],
    mode="lines", name="TPV (USD)",
    line=dict(color=COLORS["teal"], width=2),
    fill="tozeroy", fillcolor="rgba(0, 212, 184, 0.10)",
    yaxis="y",
    hovertemplate="<b>TPV</b><br>%{x|%Y-%m-%d}<br>$%{y:,.0f}<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=daily["tx_date"], y=daily["transaction_count"],
    mode="lines", name="Volume",
    line=dict(color=COLORS["navy"], width=2, dash="dot"),
    yaxis="y2",
    hovertemplate="<b>Volume</b><br>%{x|%Y-%m-%d}<br>%{y:,.0f}<extra></extra>",
))
fig.update_layout(
    yaxis=dict(title="TPV (USD)"),
    yaxis2=dict(title="Volume", overlaying="y", side="right"),
    height=420,
)
fig = _apply_fintech_layout(fig, "Daily TPV + Volume (12 months)")
st.plotly_chart(fig, width="stretch")

# --- Monthly trend with MoM growth ---
st.subheader("Monthly Run-Rate & MoM Growth")
monthly = get_monthly_trend()

cL, cR = st.columns([2, 1])
with cL:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly["month_label"], y=monthly["tpv_usd"],
        name="TPV",
        marker_color=COLORS["teal"],
        text=monthly["tpv_usd"].apply(lambda v: f"${v/1e6:.1f}M"),
        textposition="outside",
    ))
    fig = _apply_fintech_layout(fig, "Monthly TPV (USD)")
    fig.update_layout(height=400, yaxis_title="TPV (USD)")
    st.plotly_chart(fig, width="stretch")

with cR:
    fig = go.Figure()
    colors = [COLORS["green"] if v > 0 else COLORS["coral"] for v in monthly["tpv_mom_growth_pct"]]
    fig.add_trace(go.Bar(
        x=monthly["month_label"], y=monthly["tpv_mom_growth_pct"],
        marker_color=colors,
        text=monthly["tpv_mom_growth_pct"].apply(lambda v: f"{v:+.1f}%"),
        textposition="outside",
    ))
    fig = _apply_fintech_layout(fig, "MoM TPV Growth (%)")
    fig.update_layout(height=400, yaxis_title="MoM growth (%)")
    st.plotly_chart(fig, width="stretch")

# --- Hourly x DOW heatmap ---
st.subheader("Volume Heatmap — Hour of Day × Day of Week")
heat = get_hourly_heatmap()
pivot = heat.pivot(index="day_of_week", columns="hour_of_day", values="transaction_count").fillna(0)
day_labels = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
pivot.index = [day_labels.get(i, str(i)) for i in pivot.index]

fig = go.Figure(go.Heatmap(
    z=pivot.values,
    x=[f"{h:02d}" for h in pivot.columns],
    y=pivot.index,
    colorscale=[[0, "#F6F9FC"], [0.4, "#5EEAD4"], [1, COLORS["navy"]]],
    hovertemplate="<b>%{y} %{x}:00</b><br>%{z:,.0f} txns<extra></extra>",
))
fig = _apply_fintech_layout(fig, "Transaction Volume — Hour × Day")
fig.update_layout(height=360, xaxis_title="Hour of day", yaxis_title="Day of week")
st.plotly_chart(fig, width="stretch")

st.caption("🔴 Darker = higher volume. Evening peak (18:00–21:00) and Friday/Saturday are the busiest windows.")

# Heatmap of success rate
st.subheader("Success Rate Heatmap — Hour of Day × Day of Week")
pivot_s = heat.pivot(index="day_of_week", columns="hour_of_day", values="success_rate_pct").fillna(0)
pivot_s.index = [day_labels.get(i, str(i)) for i in pivot_s.index]

fig = go.Figure(go.Heatmap(
    z=pivot_s.values,
    x=[f"{h:02d}" for h in pivot_s.columns],
    y=pivot_s.index,
    colorscale=[[0, COLORS["coral"]], [0.5, "#FFB020"], [1, COLORS["teal"]]],
    hovertemplate="<b>%{y} %{x}:00</b><br>%{z:.2f}% success<extra></extra>",
    zmin=85, zmax=97,
))
fig = _apply_fintech_layout(fig, "Success Rate (%) — Hour × Day")
fig.update_layout(height=360, xaxis_title="Hour of day", yaxis_title="Day of week")
st.plotly_chart(fig, width="stretch")

st.caption("🔴 Red = lower success rate (peak hours tend to be worse due to congestion).")

# --- Value bands ---
st.subheader("Transaction Value Band Distribution")
bands = get_value_bands()

cL, cR = st.columns([1, 1])
with cL:
    fig = go.Figure(go.Bar(
        x=bands["value_band"].str.replace(r"^\d+_", "", regex=True),
        y=bands["transaction_count"],
        marker_color=COLORS["navy"],
        text=bands["transaction_count"].apply(lambda v: f"{int(v):,}"),
        textposition="outside",
    ))
    fig = _apply_fintech_layout(fig, "Volume by Value Band")
    fig.update_layout(height=380, xaxis_title="", yaxis_title="Transaction count")
    st.plotly_chart(fig, width="stretch")

with cR:
    fig = go.Figure(go.Bar(
        x=bands["value_band"].str.replace(r"^\d+_", "", regex=True),
        y=bands["tpv_usd"],
        marker_color=COLORS["teal"],
        text=bands["tpv_usd"].apply(lambda v: f"${v/1e6:.1f}M" if v >= 1e6 else f"${v/1e3:.0f}K"),
        textposition="outside",
    ))
    fig = _apply_fintech_layout(fig, "TPV by Value Band")
    fig.update_layout(height=380, xaxis_title="", yaxis_title="TPV (USD)")
    st.plotly_chart(fig, width="stretch")

st.caption("Note how premium transactions ($500+) are <1% of volume but contribute ~10% of TPV — high-value txn reliability matters disproportionately.")

# Value band table
st.subheader("Value Band KPIs")
disp = bands.copy()
disp["value_band"] = disp["value_band"].str.replace(r"^\d+_", "", regex=True)
disp["tpv_usd"] = disp["tpv_usd"].apply(lambda v: f"${v:,.0f}")
disp["avg_ticket_usd"] = disp["avg_ticket_usd"].apply(lambda v: f"${v:,.2f}")
disp["transaction_count"] = disp["transaction_count"].apply(lambda v: f"{int(v):,}")
disp["success_rate_pct"] = disp["success_rate_pct"].apply(lambda v: f"{v:.2f}%")
disp["failure_rate_pct"] = disp["failure_rate_pct"].apply(lambda v: f"{v:.2f}%")
disp["volume_share_pct"] = disp["volume_share_pct"].apply(lambda v: f"{v:.2f}%")
disp["tpv_share_pct"] = disp["tpv_share_pct"].apply(lambda v: f"{v:.2f}%")
disp = disp.rename(columns={
    "value_band": "Value Band", "transaction_count": "Txns",
    "tpv_usd": "TPV", "avg_ticket_usd": "Avg Ticket",
    "success_rate_pct": "Success", "failure_rate_pct": "Failure",
    "volume_share_pct": "Vol Share", "tpv_share_pct": "TPV Share",
})
st.dataframe(disp, width="stretch", hide_index=True)
