"""Payment Methods page — comparison across cards, bank transfer, mobile money, USSD."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from src.analytics import get_payment_method_analysis, get_daily_kpi_by_dimension
from src.visualizations import (
    COLORS, METHOD_COLORS, _apply_fintech_layout,
    fmt_usd, fmt_pct, fmt_int
)

st.set_page_config(page_title="Payment Methods", page_icon="💳", layout="wide")

st.title("💳 Payment Method Analysis")
st.caption("Cards · Bank Transfer · Mobile Money · USSD — performance comparison")

df = get_payment_method_analysis()

# KPI cards
for _, r in df.iterrows():
    c = st.columns(4)
    color = METHOD_COLORS.get(r["payment_method"], "#999")
    idx = ["card", "bank_transfer", "mobile_money", "ussd"].index(r["payment_method"])
    with c[idx]:
        st.markdown(
            f"""
            <div style="border-left: 4px solid {color}; padding: 12px 16px; background: {COLORS['grey_50']}; border-radius: 6px;">
                <div style="font-size: 14px; font-weight: 600; color: {COLORS['navy']};">{r['payment_method_label']}</div>
                <div style="font-size: 11px; color: {COLORS['grey_500']}; margin-top: 4px;">{r['method_category'].title()}</div>
                <div style="font-size: 22px; font-weight: 700; color: {COLORS['navy']}; margin-top: 8px;">{r['success_rate_pct']:.2f}%</div>
                <div style="font-size: 11px; color: {COLORS['grey_500']};">{int(r['transaction_count']):,} txns · {fmt_usd(r['tpv_usd'], compact=True)} TPV</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("")

# TPV vs Volume share
cL, cR = st.columns(2)
with cL:
    st.subheader("TPV Share by Method")
    fig = go.Figure(go.Pie(
        labels=df["payment_method_label"],
        values=df["tpv_usd"],
        hole=0.55,
        marker=dict(colors=[METHOD_COLORS.get(m, "#999") for m in df["payment_method"]]),
        textinfo="label+percent",
        textfont=dict(color=COLORS["navy"], size=11),
    ))
    fig.update_layout(height=380, showlegend=False, paper_bgcolor="white", plot_bgcolor="white",
                      margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, width="stretch")

with cR:
    st.subheader("Volume vs TPV Share")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["payment_method_label"], y=df["transaction_count"],
        name="Volume",
        marker_color=[METHOD_COLORS.get(m, "#999") for m in df["payment_method"]],
        opacity=0.7,
    ))
    # Add TPV as secondary y
    fig.add_trace(go.Scatter(
        x=df["payment_method_label"], y=df["tpv_usd"],
        mode="lines+markers",
        name="TPV (USD)",
        line=dict(color=COLORS["coral"], width=2.5),
        yaxis="y2",
    ))
    fig.update_layout(
        yaxis=dict(title="Transaction count"),
        yaxis2=dict(title="TPV (USD)", overlaying="y", side="right"),
        height=380,
    )
    fig = _apply_fintech_layout(fig)
    st.plotly_chart(fig, width="stretch")

# Daily success rate trend
st.subheader("Daily Success Rate Trend by Method")
trend = get_daily_kpi_by_dimension("payment_method")
fig = go.Figure()
for m in sorted(trend["dim_value"].unique()):
    sub = trend[trend["dim_value"] == m]
    fig.add_trace(go.Scatter(
        x=sub["tx_date"], y=sub["success_rate_pct"],
        mode="lines",
        name=m.replace("_", " ").title(),
        line=dict(color=METHOD_COLORS.get(m, "#999"), width=1.5),
        hovertemplate=f"<b>{m}</b><br>%{{x|%Y-%m-%d}}<br>%{{y:.2f}}%<extra></extra>",
    ))
fig = _apply_fintech_layout(fig, "Daily Success Rate by Payment Method")
fig.update_layout(yaxis_title="Success rate (%)", yaxis_range=[80, 100], height=420)
st.plotly_chart(fig, width="stretch")

# Avg ticket + latency comparison
cL, cR = st.columns(2)
with cL:
    st.subheader("Average Ticket Size (USD)")
    fig = go.Figure(go.Bar(
        x=df["payment_method_label"],
        y=df["avg_ticket_usd"],
        marker_color=[METHOD_COLORS.get(m, "#999") for m in df["payment_method"]],
        text=df["avg_ticket_usd"].round(2),
        textposition="outside",
    ))
    fig = _apply_fintech_layout(fig)
    fig.update_layout(yaxis_title="Avg ticket (USD)", height=360)
    st.plotly_chart(fig, width="stretch")

with cR:
    st.subheader("Avg Response Time (ms)")
    fig = go.Figure(go.Bar(
        x=df["payment_method_label"],
        y=df["avg_response_ms"],
        marker_color=[METHOD_COLORS.get(m, "#999") for m in df["payment_method"]],
        text=df["avg_response_ms"].round(0).astype(int),
        textposition="outside",
    ))
    fig = _apply_fintech_layout(fig)
    fig.update_layout(yaxis_title="Latency (ms)", height=360)
    st.plotly_chart(fig, width="stretch")

# Full table
st.subheader("Method KPI Table")
disp = df.copy()
disp["tpv_usd"] = disp["tpv_usd"].apply(lambda v: f"${v:,.0f}")
disp["avg_ticket_usd"] = disp["avg_ticket_usd"].apply(lambda v: f"${v:,.2f}")
disp["avg_response_ms"] = disp["avg_response_ms"].apply(lambda v: f"{int(v)} ms")
disp["transaction_count"] = disp["transaction_count"].apply(lambda v: f"{int(v):,}")
disp["success_rate_pct"] = disp["success_rate_pct"].apply(lambda v: f"{v:.2f}%")
disp["failure_rate_pct"] = disp["failure_rate_pct"].apply(lambda v: f"{v:.2f}%")
disp["tpv_share_pct"] = disp["tpv_share_pct"].apply(lambda v: f"{v:.2f}%")
disp = disp.rename(columns={
    "payment_method": "Method", "payment_method_label": "Label",
    "method_category": "Category", "transaction_count": "Txns",
    "tpv_usd": "TPV", "avg_ticket_usd": "Avg Ticket",
    "success_rate_pct": "Success", "failure_rate_pct": "Failure",
    "avg_response_ms": "Latency", "tpv_share_pct": "TPV Share",
})
st.dataframe(disp, width="stretch", hide_index=True)
