"""Geography page — country-level KPIs and comparison."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import plotly.graph_objects as go

from src.analytics import get_country_analysis, get_daily_kpi_by_dimension
from src.visualizations import (
    COLORS, COUNTRY_COLORS, _apply_fintech_layout,
    fmt_usd, fmt_pct, fmt_int
)

st.set_page_config(page_title="Geography", page_icon="🌍", layout="wide")

st.title("🌍 Geographic Analysis")
st.caption("5 African markets: Nigeria · Kenya · Ghana · South Africa · Egypt")

df = get_country_analysis()

# Top KPIs
c1, c2, c3, c4, c5 = st.columns(5)
for i, (_, r) in enumerate(df.iterrows()):
    with [c1, c2, c3, c4, c5][i]:
        st.metric(
            f"{r['country_name']}",
            fmt_usd(r["tpv_usd"], compact=True),
            delta=f"{r['success_rate_pct']:.1f}% success",
        )

st.markdown("")

# TPV share donut
cL, cR = st.columns([1, 2])
with cL:
    st.subheader("TPV Share")
    fig = go.Figure(go.Pie(
        labels=df["country_name"],
        values=df["tpv_usd"],
        hole=0.55,
        marker=dict(colors=[COUNTRY_COLORS[c] for c in df["country_code"]]),
        textinfo="label+percent",
        textfont=dict(color=COLORS["navy"], size=11),
    ))
    fig.update_layout(
        height=380, showlegend=False, paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig, width="stretch")

with cR:
    st.subheader("KPI Comparison")
    # Grouped bar — Success rate + Avg ticket
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["country_name"], y=df["success_rate_pct"],
        name="Success rate (%)",
        marker_color=[COUNTRY_COLORS[c] for c in df["country_code"]],
        text=df["success_rate_pct"].round(2),
        textposition="outside",
    ))
    fig.update_layout(
        yaxis=dict(range=[80, 100], title="Success rate (%)"),
        height=380, barmode="group",
    )
    fig = _apply_fintech_layout(fig)
    st.plotly_chart(fig, width="stretch")

# Volume trend by country
st.subheader("Daily TPV Trend by Country")
trend = get_daily_kpi_by_dimension("country_code")
fig = go.Figure()
for cc in sorted(trend["dim_value"].unique()):
    sub = trend[trend["dim_value"] == cc]
    fig.add_trace(go.Scatter(
        x=sub["tx_date"], y=sub["tpv_usd"],
        mode="lines",
        name=cc,
        line=dict(color=COUNTRY_COLORS.get(cc, "#999"), width=1.6),
        hovertemplate=f"<b>{cc}</b><br>%{{x|%Y-%m-%d}}<br>$%{{y:,.0f}}<extra></extra>",
    ))
fig = _apply_fintech_layout(fig, "Daily TPV by Country")
fig.update_layout(yaxis_title="TPV (USD)", height=420)
st.plotly_chart(fig, width="stretch")

# Full table
st.subheader("Country KPI Table")
disp = df.copy()
disp["tpv_usd"] = disp["tpv_usd"].apply(lambda v: f"${v:,.0f}")
disp["avg_ticket_usd"] = disp["avg_ticket_usd"].apply(lambda v: f"${v:,.2f}")
disp["avg_response_ms"] = disp["avg_response_ms"].apply(lambda v: f"{int(v)} ms")
disp["transaction_count"] = disp["transaction_count"].apply(lambda v: f"{int(v):,}")
disp["success_rate_pct"] = disp["success_rate_pct"].apply(lambda v: f"{v:.2f}%")
disp["failure_rate_pct"] = disp["failure_rate_pct"].apply(lambda v: f"{v:.2f}%")
disp["tpv_share_pct"] = disp["tpv_share_pct"].apply(lambda v: f"{v:.2f}%")
disp = disp.rename(columns={
    "country_code": "Code", "country_name": "Country", "currency_code": "Currency",
    "transaction_count": "Txns", "tpv_usd": "TPV", "avg_ticket_usd": "Avg Ticket",
    "success_rate_pct": "Success", "failure_rate_pct": "Failure",
    "avg_response_ms": "Latency", "tpv_share_pct": "TPV Share",
})
st.dataframe(disp, width="stretch", hide_index=True)
