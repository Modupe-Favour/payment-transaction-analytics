"""Failures page — diagnostic on failure reasons + recovery opportunity."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.analytics import (
    get_failure_reasons, get_failure_by_method, get_failure_by_country,
    get_recovery_opportunity,
)
from src.visualizations import (
    COLORS, METHOD_COLORS, COUNTRY_COLORS, _apply_fintech_layout, fmt_usd
)

st.set_page_config(page_title="Failures", page_icon="⚠️", layout="wide")

st.title("⚠️ Failure Analysis")
st.caption("Diagnose where TPV is leaking and how much is recoverable")

failures = get_failure_reasons()
recovery = get_recovery_opportunity()

# Headline KPIs
total_lost = failures["lost_tpv_usd"].sum()
top_reason = failures.iloc[0]
recoverable = recovery["recoverable_tpv_usd"].sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Lost TPV", fmt_usd(total_lost, compact=True),
          delta=f"{failures['failure_count'].sum():,} failed txns",
          delta_color="inverse")
c2.metric("Top Failure Reason", top_reason["failure_reason"].replace("_", " ").title(),
          delta=f"{top_reason['failure_share_pct']:.1f}% of all failures")
c3.metric("Recoverable TPV", fmt_usd(recoverable, compact=True),
          delta=f"{recoverable/total_lost*100:.1f}% of lost")
c4.metric("Incremental TPV Uplift", f"+{recoverable/41_511_714*100:.2f}%",
          delta="of portfolio TPV", delta_color="off")

st.markdown("")

# Failure reason breakdown
cL, cR = st.columns([1, 1])
with cL:
    st.subheader("Failure Count by Reason")
    fig = go.Figure(go.Bar(
        y=failures["failure_reason"].str.replace("_", " ").str.title(),
        x=failures["failure_count"],
        orientation="h",
        marker_color=COLORS["coral"],
        text=failures["failure_count"],
        textposition="outside",
    ))
    fig.update_yaxes(autorange="reversed")
    fig = _apply_fintech_layout(fig)
    fig.update_layout(xaxis_title="Failure count", height=380)
    st.plotly_chart(fig, width="stretch")

with cR:
    st.subheader("Lost TPV by Reason")
    fig = go.Figure(go.Bar(
        y=failures["failure_reason"].str.replace("_", " ").str.title(),
        x=failures["lost_tpv_usd"],
        orientation="h",
        marker_color=COLORS["navy"],
        text=failures["lost_tpv_usd"].apply(lambda v: f"${v:,.0f}"),
        textposition="outside",
    ))
    fig.update_yaxes(autorange="reversed")
    fig = _apply_fintech_layout(fig)
    fig.update_layout(xaxis_title="Lost TPV (USD)", height=380)
    st.plotly_chart(fig, width="stretch")

# Recovery opportunity
st.subheader("🎯 Recovery Opportunity (Data-Driven Recommendations)")
st.caption("Estimated recoverable TPV by addressing each failure reason to industry benchmark")

disp = recovery.copy()
disp["failure_reason"] = disp["failure_reason"].str.replace("_", " ").str.title()
disp["lost_tpv_usd"] = disp["lost_tpv_usd"].apply(lambda v: f"${v:,.0f}")
disp["recoverable_tpv_usd"] = disp["recoverable_tpv_usd"].apply(lambda v: f"${v:,.0f}")
disp["failure_count"] = disp["failure_count"].apply(lambda v: f"{int(v):,}")
disp["lost_tpv_share_pct"] = disp["lost_tpv_share_pct"].apply(lambda v: f"{v:.2f}%")
disp["recoverable_pct"] = disp["recoverable_pct"].apply(lambda v: f"{v:.0f}%")
disp["incremental_tpv_pct"] = disp["incremental_tpv_pct"].apply(lambda v: f"+{v:.2f}%")
disp = disp.rename(columns={
    "failure_reason": "Failure Reason",
    "failure_count": "Failure Count",
    "lost_tpv_usd": "Lost TPV",
    "lost_tpv_share_pct": "Lost Share",
    "recoverable_pct": "Recovery Target",
    "recoverable_tpv_usd": "Recoverable TPV",
    "incremental_tpv_pct": "Incremental Uplift",
})
disp = disp[["Failure Reason", "Failure Count", "Lost TPV", "Lost Share",
             "Recovery Target", "Recoverable TPV", "Incremental Uplift"]]
st.dataframe(disp, width="stretch", hide_index=True)

# Failure by method
st.subheader("Failure Reasons by Payment Method")
fbm = get_failure_by_method()
pivot = fbm.pivot(index="failure_reason", columns="payment_method", values="failure_count").fillna(0)
pivot.index = pivot.index.str.replace("_", " ").str.title()
pivot = pivot.reindex(failures["failure_reason"].str.replace("_", " ").str.title())

fig = go.Figure(go.Heatmap(
    z=pivot.values,
    x=pivot.columns,
    y=pivot.index,
    colorscale=[[0, "#F6F9FC"], [0.5, "#FFB020"], [1, "#DC2626"]],
    hovertemplate="<b>%{y} / %{x}</b><br>%{z:,.0f} failures<extra></extra>",
))
fig = _apply_fintech_layout(fig, "Failure Count: Reason × Method")
fig.update_layout(height=380)
st.plotly_chart(fig, width="stretch")

# Failure by country
st.subheader("Failure Reasons by Country")
fbc = get_failure_by_country()
pivot_c = fbc.pivot(index="failure_reason", columns="country_code", values="failure_count").fillna(0)
pivot_c.index = pivot_c.index.str.replace("_", " ").str.title()
pivot_c = pivot_c.reindex(failures["failure_reason"].str.replace("_", " ").str.title())

fig = go.Figure(go.Heatmap(
    z=pivot_c.values,
    x=pivot_c.columns,
    y=pivot_c.index,
    colorscale=[[0, "#F6F9FC"], [0.5, "#5EEAD4"], [1, COLORS["navy"]]],
    hovertemplate="<b>%{y} / %{x}</b><br>%{z:,.0f} failures<extra></extra>",
))
fig = _apply_fintech_layout(fig, "Failure Count: Reason × Country")
fig.update_layout(height=380)
st.plotly_chart(fig, width="stretch")

# Recommendations
st.subheader("📋 Recommended Actions")
st.markdown(f"""
Based on the analysis above, the following interventions would yield the largest TPV uplift:

1. **Address network timeouts first** — Estimated recoverable: **{fmt_usd(recovery.iloc[0]['recoverable_tpv_usd'], compact=True)}**
   Network timeouts represent {failures[failures['failure_reason']=='network_timeout'].iloc[0]['failure_share_pct']:.1f}% of failures but have a 60% recovery rate.
   Invest in retry logic + idempotency keys + alternative routing for bank transfer failures.

2. **Reduce insufficient funds rejections** — Estimated recoverable: **{fmt_usd(recovery[recovery['failure_reason']=='insufficient_funds'].iloc[0]['recoverable_tpv_usd'], compact=True)}**
   The #1 failure reason by volume. Implement balance pre-check APIs, partial-payment options,
   and 'save card + retry on payday' flows for repeat customers.

3. **Fix bank downtime** — Estimated recoverable: **{fmt_usd(recovery[recovery['failure_reason']=='bank_downtime'].iloc[0]['recoverable_tpv_usd'], compact=True)}**
   Bank downtime has the highest recovery rate (70%) because it's structural.
   Add multi-bank failover and real-time bank status monitoring.

4. **Smart retry for card declines** — Estimated recoverable: **{fmt_usd(recovery[recovery['failure_reason']=='card_declined'].iloc[0]['recoverable_tpv_usd'], compact=True)}**
   Implement adaptive retry with backoff for soft declines (do not retry hard declines / fraud).

5. **Clean up invalid accounts** — Estimated recoverable: **{fmt_usd(recovery[recovery['failure_reason']=='invalid_account'].iloc[0]['recoverable_tpv_usd'], compact=True)}**
   Build account-validation step before transaction submission.

**Total potential uplift:** ~{fmt_usd(recoverable, compact=True)} (~{recoverable/41_511_714*100:.2f}% of current TPV).
""")
