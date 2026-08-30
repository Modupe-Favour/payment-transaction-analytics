"""Merchants page — segment ranking, top/bottom performers."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.analytics import get_merchant_performance
from src.visualizations import (
    COLORS, METHOD_COLORS, scatter_chart, horizontal_bar_chart, _apply_fintech_layout,
    fmt_usd, fmt_pct, fmt_int
)

st.set_page_config(page_title="Merchants", page_icon="🏪", layout="wide")

st.title("🏪 Merchant Performance")
st.caption("Ranking, segment analysis, and performance classification across 220 merchants")

df = get_merchant_performance()

# Filters
c1, c2, c3 = st.columns(3)
with c1:
    segment_filter = st.multiselect("Segment", options=sorted(df["segment"].unique()),
                                    default=[])
with c2:
    tier_filter = st.multiselect("Tier", options=sorted(df["tier"].unique()),
                                 default=[])
with c3:
    perf_filter = st.multiselect("Performance Segment",
                                 options=sorted(df["performance_segment"].unique()),
                                 default=[])

mask = pd.Series([True] * len(df))
if segment_filter:
    mask &= df["segment"].isin(segment_filter)
if tier_filter:
    mask &= df["tier"].isin(tier_filter)
if perf_filter:
    mask &= df["performance_segment"].isin(perf_filter)

fdf = df[mask].copy()

# KPI cards
c1, c2, c3, c4 = st.columns(4)
c1.metric("Merchants in view", f"{len(fdf):,}")
c2.metric("Combined TPV", fmt_usd(fdf["tpv_usd"].sum(), compact=True))
c3.metric("Avg success rate", f"{fdf['success_rate_pct'].mean():.2f}%" if len(fdf) else "—")
underperformers = (fdf["performance_segment"] == "underperformer").sum()
c4.metric("Underperformers", f"{underperformers}", delta=f"{underperformers} need attention",
          delta_color="inverse")

st.markdown("")

# Scatter: TPV vs Success Rate
st.subheader("TPV vs Success Rate — Performance Quadrant")
fig = go.Figure()
seg_colors = {"star": COLORS["teal"], "high_volume": COLORS["navy"],
              "average": COLORS["grey_500"], "underperformer": COLORS["coral"]}
for seg, color in seg_colors.items():
    sub = fdf[fdf["performance_segment"] == seg]
    if len(sub):
        fig.add_trace(go.Scatter(
            x=sub["tpv_usd"], y=sub["success_rate_pct"],
            mode="markers",
            marker=dict(size=10, color=color, opacity=0.7,
                        line=dict(width=1, color="white")),
            name=seg.replace("_", " ").title(),
            text=sub["merchant_name"],
            hovertemplate=f"<b>{{text}}</b><br>TPV: ${{x:,.0f}}<br>Success: {{y:.2f}}%<extra></extra>",
        ))
# Reference lines
mean_success = fdf["success_rate_pct"].mean()
mean_tpv = fdf["tpv_usd"].median()
fig.add_hline(y=mean_success, line_dash="dash", line_color=COLORS["grey_300"],
              annotation_text=f"avg success {mean_success:.1f}%")
fig.add_vline(x=mean_tpv, line_dash="dash", line_color=COLORS["grey_300"],
              annotation_text=f"median TPV ${mean_tpv:,.0f}")
fig = _apply_fintech_layout(fig)
fig.update_layout(xaxis_title="TPV (USD)", yaxis_title="Success Rate (%)",
                  yaxis_range=[80, 100], height=460)
st.plotly_chart(fig, width="stretch")

st.caption("Stars (teal) = high TPV + high success · Underperformers (coral) = high TPV + low success — top recovery priority")

# Top / Bottom tables
cL, cR = st.columns(2)
with cL:
    st.subheader("🏆 Top 15 by TPV")
    top = fdf.nlargest(15, "tpv_usd")[
        ["merchant_name", "segment", "tier", "country_code", "tpv_usd",
         "transaction_count", "success_rate_pct", "performance_segment"]
    ]
    top["tpv_usd"] = top["tpv_usd"].apply(lambda v: f"${v:,.0f}")
    top["success_rate_pct"] = top["success_rate_pct"].apply(lambda v: f"{v:.2f}%")
    top["transaction_count"] = top["transaction_count"].apply(lambda v: f"{int(v):,}")
    top = top.rename(columns={
        "merchant_name": "Merchant", "segment": "Segment", "tier": "Tier",
        "country_code": "Country", "tpv_usd": "TPV",
        "transaction_count": "Txns", "success_rate_pct": "Success",
        "performance_segment": "Bucket",
    })
    st.dataframe(top, width="stretch", hide_index=True)

with cR:
    st.subheader("⚠️ Bottom 15 by Success Rate")
    bot = fdf.nsmallest(15, "success_rate_pct")[
        ["merchant_name", "segment", "tier", "country_code", "tpv_usd",
         "transaction_count", "success_rate_pct", "performance_segment"]
    ]
    bot["tpv_usd"] = bot["tpv_usd"].apply(lambda v: f"${v:,.0f}")
    bot["success_rate_pct"] = bot["success_rate_pct"].apply(lambda v: f"{v:.2f}%")
    bot["transaction_count"] = bot["transaction_count"].apply(lambda v: f"{int(v):,}")
    bot = bot.rename(columns={
        "merchant_name": "Merchant", "segment": "Segment", "tier": "Tier",
        "country_code": "Country", "tpv_usd": "TPV",
        "transaction_count": "Txns", "success_rate_pct": "Success",
        "performance_segment": "Bucket",
    })
    st.dataframe(bot, width="stretch", hide_index=True)

# Segment summary
st.subheader("📊 Segment Summary")
seg_summary = (fdf.groupby("segment")
               .agg(merchants=("merchant_id", "count"),
                    tpv_usd=("tpv_usd", "sum"),
                    avg_success=("success_rate_pct", "mean"),
                    avg_ticket=("avg_ticket_usd", "mean"))
               .round(2)
               .reset_index()
               .sort_values("tpv_usd", ascending=False))
seg_summary["tpv_usd"] = seg_summary["tpv_usd"].apply(lambda v: f"${v:,.0f}")
seg_summary["avg_success"] = seg_summary["avg_success"].apply(lambda v: f"{v:.2f}%")
seg_summary["avg_ticket"] = seg_summary["avg_ticket"].apply(lambda v: f"${v:,.2f}")
seg_summary = seg_summary.rename(columns={
    "segment": "Segment", "merchants": "Merchants", "tpv_usd": "Total TPV",
    "avg_success": "Avg Success", "avg_ticket": "Avg Ticket",
})
st.dataframe(seg_summary, width="stretch", hide_index=True)
