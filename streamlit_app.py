"""
Payment Transaction Analytics — Streamlit app entry point.

Run locally:
    streamlit run streamlit_app.py

Deploy to Streamlit Community Cloud:
    1. Push this repo to GitHub
    2. Connect the repo on https://share.streamlit.io
    3. Set the main file path to `streamlit_app.py`
    4. (Optional) Set DATABASE_URL in secrets for cloud Postgres
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make the local `src` package importable when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st
from src.database import is_loaded, get_database_url, row_count
from src.analytics import get_kpi_overview
from src.visualizations import COLORS

st.set_page_config(
    page_title="Payment Transaction Analytics",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------- #
# Inject Stripe-style CSS                                                     #
# --------------------------------------------------------------------------- #

st.markdown(
    f"""
    <style>
    /* App-wide typography */
    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    /* Header */
    .main-header {{
        background: linear-gradient(135deg, {COLORS['navy']} 0%, {COLORS['navy_soft']} 100%);
        color: {COLORS['white']};
        padding: 28px 36px;
        border-radius: 12px;
        margin-bottom: 24px;
    }}
    .main-header h1 {{
        font-size: 28px;
        font-weight: 700;
        margin: 0 0 6px 0;
        letter-spacing: -0.02em;
    }}
    .main-header p {{
        font-size: 14px;
        margin: 0;
        opacity: 0.85;
    }}

    /* KPI card */
    .kpi-card {{
        background: {COLORS['white']};
        border: 1px solid {COLORS['grey_100']};
        border-radius: 12px;
        padding: 20px 22px;
        height: 100%;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }}
    .kpi-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(10, 37, 64, 0.08);
    }}
    .kpi-card .label {{
        font-size: 12px;
        color: {COLORS['grey_500']};
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin: 0 0 8px 0;
        font-weight: 500;
    }}
    .kpi-card .value {{
        font-size: 28px;
        font-weight: 700;
        color: {COLORS['navy']};
        margin: 0;
        letter-spacing: -0.02em;
    }}
    .kpi-card .delta {{
        font-size: 12px;
        margin-top: 6px;
        color: {COLORS['grey_500']};
    }}
    .kpi-card .delta.up {{ color: {COLORS['green']}; }}
    .kpi-card .delta.down {{ color: {COLORS['red']}; }}

    /* Section title */
    .section-title {{
        font-size: 18px;
        font-weight: 600;
        color: {COLORS['navy']};
        margin: 24px 0 12px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid {COLORS['teal_soft']};
    }}

    /* Sidebar */
    .sidebar-info {{
        background: {COLORS['grey_50']};
        padding: 12px 14px;
        border-radius: 8px;
        font-size: 12px;
        color: {COLORS['grey_700']};
        margin-top: 16px;
    }}

    /* Footer */
    .footer {{
        margin-top: 48px;
        padding: 18px 24px;
        border-top: 1px solid {COLORS['grey_100']};
        color: {COLORS['grey_500']};
        font-size: 12px;
        text-align: center;
    }}

    /* Reduce default Streamlit padding */
    .block-container {{
        padding-top: 24px;
        padding-bottom: 0;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


def render_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="main-header">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(label: str, value: str, delta: str | None = None,
                    delta_direction: str = "neutral") -> None:
    delta_html = ""
    if delta:
        cls = "up" if delta_direction == "up" else ("down" if delta_direction == "down" else "")
        delta_html = f'<p class="delta {cls}">{delta}</p>'
    st.markdown(
        f"""
        <div class="kpi-card">
            <p class="label">{label}</p>
            <p class="value">{value}</p>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_title(title: str) -> None:
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Sidebar                                                                     #
# --------------------------------------------------------------------------- #

with st.sidebar:
    st.markdown("### 💳 Payment Analytics")
    st.caption("Africa-focused payment KPIs")
    st.divider()

    # DB status
    loaded = is_loaded()
    if loaded:
        n_rows = row_count()
        st.success(f"✓ Database loaded\n\n**{n_rows:,} transactions**")
    else:
        st.warning("⚠ Database not loaded")
        if st.button("Load data into DB", width="stretch"):
            from pathlib import Path
            from src.database import DATA_DIR, load_parquet_to_db

            transactions_path = DATA_DIR / "transactions.parquet"
            merchants_path = DATA_DIR / "merchants.parquet"

            if not transactions_path.exists() or not merchants_path.exists():
                with st.spinner("First run: generating 1.2M synthetic transactions (~30-60s)..."):
                    from data.generate_transactions import generate
                    df, merchants = generate(rows=1_200_000, start="2025-01-01", end="2025-12-31", seed=42)
                    DATA_DIR.mkdir(parents=True, exist_ok=True)
                    df.to_parquet(transactions_path, index=False)
                    merchants.to_parquet(merchants_path, index=False)

            with st.spinner("Loading transactions into DB..."):
                load_parquet_to_db()
            st.rerun()

    db_url = get_database_url()
    backend = "PostgreSQL" if db_url.startswith(("postgres", "postgresql")) else "SQLite"
    st.markdown(
        f"""
        <div class="sidebar-info">
            <strong>Backend:</strong> {backend}<br>
            <strong>Schema:</strong> star (fact_transactions + 3 dims)<br>
            <strong>Period:</strong> Jan–Dec 2025
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    st.markdown("#### Pages")
    st.markdown("""
    - 📊 **Overview** — headline KPIs
    - 🏪 **Merchants** — segment ranking
    - 🌍 **Geography** — country analysis
    - 💳 **Payment Methods** — method comparison
    - ⚠️ **Failures** — diagnostic
    - 📈 **Trends** — time series
    """)


# --------------------------------------------------------------------------- #
# Body — Overview page (this file). Other pages live in /pages                #
# --------------------------------------------------------------------------- #

render_header(
    "Payment Transaction Analytics",
    "1.2M+ transactions across 5 African markets · 12 months · 4 payment methods · 220 merchants"
)

if not is_loaded():
    st.info("👈 Load data from the sidebar to begin.")
    st.stop()

kpi = get_kpi_overview().iloc[0]

# Top KPI row
c1, c2, c3, c4 = st.columns(4)
with c1:
    render_kpi_card("Total Payment Volume", f"${kpi['tpv_usd']:,.0f}",
                    delta=f"avg ${kpi['avg_ticket_usd']:.2f}/tx")
with c2:
    render_kpi_card("Transactions", f"{int(kpi['transaction_count']):,}",
                    delta=f"{int(kpi['active_merchants'])} active merchants")
with c3:
    render_kpi_card("Success Rate", f"{kpi['success_rate_pct']:.2f}%",
                    delta=f"{int(kpi['failure_count']):,} failures",
                    delta_direction="down")
with c4:
    render_kpi_card("Active Countries", f"{int(kpi['active_countries'])}",
                    delta=f"{int(kpi['active_methods'])} payment methods")

st.markdown("")

# Daily trend chart
render_section_title("Daily KPI Trend (TPV & Volume)")
from src.analytics import get_daily_kpi_trend
from src.visualizations import area_chart, line_chart, COLORS

daily = get_daily_kpi_trend()
cL, cR = st.columns([2, 1])
with cL:
    fig = area_chart(daily, "tx_date", "tpv_usd", name="TPV (USD)",
                     color=COLORS["teal"], title="Daily TPV (USD)")
    fig.update_layout(height=320)
    st.plotly_chart(fig, width="stretch")
with cR:
    fig = line_chart(daily, "tx_date", "success_rate_pct", name="Success rate",
                     color=COLORS["navy"], title="Daily Success Rate (%)")
    # Add 7-day rolling
    fig.add_scatter(x=daily["tx_date"], y=daily["success_rate_7d_rolling_pct"],
                    mode="lines", name="7-day rolling",
                    line=dict(color=COLORS["teal"], width=2, dash="dot"))
    fig.update_layout(height=320)
    st.plotly_chart(fig, width="stretch")

# Method breakdown
render_section_title("Payment Method Mix")
from src.analytics import get_payment_method_analysis
from src.visualizations import donut_chart, bar_chart, METHOD_COLORS

methods = get_payment_method_analysis()
cL, cR = st.columns([1, 2])
with cL:
    colors = [METHOD_COLORS.get(m, "#999") for m in methods["payment_method"]]
    fig = donut_chart(methods, labels="payment_method_label", values="transaction_count",
                      title="Volume Share", colors=colors)
    fig.update_layout(height=320)
    st.plotly_chart(fig, width="stretch")
with cR:
    # Success rate by method — horizontal bar
    import plotly.graph_objects as go
    fig = go.Figure()
    for _, r in methods.iterrows():
        c = METHOD_COLORS.get(r["payment_method"], "#999")
        fig.add_trace(go.Bar(
            y=[r["payment_method_label"]],
            x=[r["success_rate_pct"]],
            orientation="h",
            marker_color=c,
            text=f"{r['success_rate_pct']:.2f}%",
            textposition="outside",
            hovertemplate=f"<b>{r['payment_method_label']}</b><br>Success: {r['success_rate_pct']:.2f}%<extra></extra>",
        ))
    fig.update_layout(
        title="Success Rate by Method",
        height=320,
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=50, b=20),
        xaxis=dict(range=[80, 100], gridcolor="#F6F9FC"),
        yaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig, width="stretch")

# Footer
st.markdown(
    """
    <div class="footer">
        Payment Transaction Analytics · Built with Python · SQL · Streamlit · Plotly<br>
        Data is synthetic and reproducible via <code>python data/generate_transactions.py --seed 42</code>
    </div>
    """,
    unsafe_allow_html=True,
)
