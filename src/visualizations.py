"""
Visualization helpers — Stripe-inspired fintech palette + reusable chart
builders on top of Plotly.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# --------------------------------------------------------------------------- #
# Stripe-inspired palette                                                    #
# --------------------------------------------------------------------------- #

COLORS = {
    "navy":      "#0A2540",
    "navy_dark": "#061A30",
    "navy_soft": "#1E3A5F",
    "teal":      "#00D4B8",
    "teal_soft": "#5EEAD4",
    "coral":     "#FF6B6B",
    "amber":     "#FFB020",
    "violet":    "#7C5CFF",
    "grey_50":   "#F6F9FC",
    "grey_100":  "#E3E8EE",
    "grey_300":  "#ADBDCC",
    "grey_500":  "#697386",
    "grey_700":  "#3C4257",
    "white":     "#FFFFFF",
    "green":     "#16A34A",
    "red":       "#DC2626",
}

# Categorical palette for charts
CAT_PALETTE = [
    "#00D4B8", "#0A2540", "#7C5CFF", "#FF6B6B",
    "#FFB020", "#16A34A", "#1E3A5F", "#5EEAD4",
]

COUNTRY_COLORS = {
    "NG": "#00D4B8",
    "KE": "#7C5CFF",
    "GH": "#FFB020",
    "ZA": "#0A2540",
    "EG": "#FF6B6B",
}

METHOD_COLORS = {
    "card":           "#0A2540",
    "bank_transfer":  "#00D4B8",
    "mobile_money":   "#7C5CFF",
    "ussd":           "#FFB020",
}

STATUS_COLORS = {
    "success": "#16A34A",
    "failed":  "#DC2626",
}

# --------------------------------------------------------------------------- #
# Base layout                                                                #
# --------------------------------------------------------------------------- #

def _apply_fintech_layout(fig: go.Figure, title: str | None = None) -> go.Figure:
    """Apply consistent Stripe-style layout to a Plotly figure."""
    fig.update_layout(
        title=dict(
            text=title or "",
            font=dict(size=16, color=COLORS["navy"], family="Inter, sans-serif"),
            x=0.02,
        ),
        font=dict(family="Inter, system-ui, sans-serif", size=12, color=COLORS["grey_700"]),
        plot_bgcolor=COLORS["white"],
        paper_bgcolor=COLORS["white"],
        margin=dict(l=10, r=10, t=60, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11),
        ),
        hoverlabel=dict(
            bgcolor=COLORS["navy"],
            font_color=COLORS["white"],
            font_size=12,
        ),
    )
    fig.update_xaxes(
        showgrid=False,
        linecolor=COLORS["grey_100"],
        tickfont=dict(size=11, color=COLORS["grey_500"]),
        title_font=dict(size=12, color=COLORS["grey_700"]),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=COLORS["grey_50"],
        zeroline=False,
        tickfont=dict(size=11, color=COLORS["grey_500"]),
        title_font=dict(size=12, color=COLORS["grey_700"]),
    )
    return fig


# --------------------------------------------------------------------------- #
# Reusable chart builders                                                     #
# --------------------------------------------------------------------------- #

def line_chart(df: pd.DataFrame, x: str, y: str, name: str = "", color: str | None = None,
               title: str | None = None, dash: str = "solid") -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df[x], y=df[y],
        mode="lines",
        name=name or y,
        line=dict(color=color or COLORS["teal"], width=2.5, dash=dash),
        hovertemplate=f"<b>{name or y}</b><br>%{{x|%Y-%m-%d}}<br>%{{y:,.2f}}<extra></extra>",
    ))
    return _apply_fintech_layout(fig, title)


def multi_line_chart(df: pd.DataFrame, x: str, y: str, color_col: str,
                     title: str | None = None) -> go.Figure:
    fig = px.line(
        df, x=x, y=y, color=color_col,
        color_discrete_sequence=CAT_PALETTE,
    )
    return _apply_fintech_layout(fig, title)


def area_chart(df: pd.DataFrame, x: str, y: str, name: str = "", color: str | None = None,
               title: str | None = None) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df[x], y=df[y],
        mode="lines",
        name=name or y,
        line=dict(color=color or COLORS["teal"], width=2),
        fill="tozeroy",
        fillcolor=f"rgba(0, 212, 184, 0.12)",
        hovertemplate=f"<b>{name or y}</b><br>%{{x|%Y-%m-%d}}<br>%{{y:,.2f}}<extra></extra>",
    ))
    return _apply_fintech_layout(fig, title)


def bar_chart(df: pd.DataFrame, x: str, y: str, color: str | None = None,
              orientation: str = "v", text: str | None = None, title: str | None = None) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=df[x] if orientation == "v" else df[y],
        y=df[y] if orientation == "v" else df[x],
        orientation=orientation,
        marker_color=color or COLORS["teal"],
        text=df[text] if text else None,
        textposition="outside",
        hovertemplate="<b>%{label}</b><br>%{value:,.2f}<extra></extra>",
    ))
    return _apply_fintech_layout(fig, title)


def horizontal_bar_chart(df: pd.DataFrame, label_col: str, value_col: str,
                         color: str | None = None, title: str | None = None) -> go.Figure:
    fig = go.Figure(go.Bar(
        y=df[label_col],
        x=df[value_col],
        orientation="h",
        marker_color=color or COLORS["navy"],
        text=df[value_col].round(2) if df[value_col].dtype.kind in "iuf" else df[value_col],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x:,.2f}<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed")
    return _apply_fintech_layout(fig, title)


def heatmap(df_pivot: pd.DataFrame, title: str | None = None,
            colorscale: list | None = None) -> go.Figure:
    """Heatmap from a pivoted DataFrame (index=y, columns=x)."""
    fig = go.Figure(go.Heatmap(
        z=df_pivot.values,
        x=df_pivot.columns,
        y=df_pivot.index,
        colorscale=colorscale or [
            [0,   "#F6F9FC"],
            [0.5, "#5EEAD4"],
            [1,   "#0A2540"],
        ],
        hovertemplate="<b>%{y} / %{x}</b><br>%{z:,.0f}<extra></extra>",
    ))
    return _apply_fintech_layout(fig, title)


def donut_chart(df: pd.DataFrame, labels: str, values: str, title: str | None = None,
                colors: list | None = None) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=df[labels],
        values=df[values],
        hole=0.6,
        marker=dict(colors=colors or CAT_PALETTE[:len(df)]),
        textinfo="label+percent",
        textfont=dict(color=COLORS["navy"], size=11),
        hovertemplate="<b>%{label}</b><br>%{value:,.0f}<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        font=dict(family="Inter, system-ui, sans-serif", size=12, color=COLORS["grey_700"]),
        paper_bgcolor=COLORS["white"],
        plot_bgcolor=COLORS["white"],
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
    )
    if title:
        fig.update_layout(title=dict(text=title, x=0.02, font=dict(size=16, color=COLORS["navy"])))
    return fig


def scatter_chart(df: pd.DataFrame, x: str, y: str, size: str | None = None,
                  color_col: str | None = None, text: str | None = None,
                  title: str | None = None) -> go.Figure:
    fig = px.scatter(
        df, x=x, y=y, size=size, color=color_col, text=text,
        color_discrete_map=COUNTRY_COLORS if color_col == "country_code" else None,
        color_discrete_sequence=CAT_PALETTE,
    )
    return _apply_fintech_layout(fig, title)


# --------------------------------------------------------------------------- #
# Number formatters                                                          #
# --------------------------------------------------------------------------- #

def fmt_usd(v: float, compact: bool = False) -> str:
    if compact:
        if abs(v) >= 1e9: return f"${v/1e9:.2f}B"
        if abs(v) >= 1e6: return f"${v/1e6:.2f}M"
        if abs(v) >= 1e3: return f"${v/1e3:.1f}K"
    return f"${v:,.2f}"


def fmt_pct(v: float) -> str:
    return f"{v:.2f}%"


def fmt_int(v: float) -> str:
    return f"{int(v):,}"
