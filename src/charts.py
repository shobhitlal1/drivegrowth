"""Restrained Plotly styling, consistent scales, and readable business labels."""
from __future__ import annotations
import pandas as pd
import plotly.graph_objects as go

TEAL = "#098577"
INK = "#243B50"
MUTED = "#768797"
AMBER = "#C38C36"
SHORT_NAMES = {"Google Search": "Search", "Meta Ads": "Meta", "Affiliate Partners": "Affiliate",
               "Organic Search": "Organic", "Referral": "Referral", "Direct": "Direct",
               "TikTok / Social": "TikTok", "Comparison Websites": "Comparison"}


def base(fig: go.Figure, height: int = 280) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=55, r=22, t=32, b=42),
                      paper_bgcolor="white", plot_bgcolor="white",
                      font=dict(family="Arial, sans-serif", size=11, color=MUTED),
                      hoverlabel=dict(bgcolor=INK, font_color="white", font_size=12),
                      xaxis=dict(showgrid=False, zeroline=False, linecolor="#E6ECEF", tickfont_size=11, automargin=True),
                      yaxis=dict(gridcolor="#EFF2F5", zeroline=False, tickfont_size=11, automargin=True),
                      legend=dict(orientation="h", x=0, y=1.19, font_size=11),
                      hovermode="x unified", dragmode=False)
    return fig


def revenue_chart(data: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.month, y=data.revenue, name="Commission revenue", mode="lines",
                            line=dict(color=INK, width=2.5), hovertemplate="$%{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=data.month, y=data.contribution_margin, name="Pre-acquisition contribution", mode="lines",
                            line=dict(color=TEAL, width=2.5), fill="tozeroy", fillcolor="rgba(9,133,119,0.07)",
                            hovertemplate="$%{y:,.0f}<extra></extra>"))
    base(fig, 285)
    fig.update_xaxes(tickformat="%b", dtick="M1", title=None)
    fig.update_yaxes(tickprefix="$", tickformat="~s", rangemode="tozero")
    return fig


def channel_chart(data: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if not data.empty:
        display = data.dropna(subset=["cac", "ltv_cac"])
        max_policies = max(display.policies.max(), 1)
        for _, row in display.iterrows():
            fig.add_trace(go.Scatter(
                x=[row.cac], y=[row.ltv_cac], mode="markers+text",
                text=[SHORT_NAMES.get(row.channel, row.channel)],
                textposition={"Google Search": "top right", "Direct": "bottom center",
                              "Comparison Websites": "bottom left", "Meta Ads": "top left",
                              "TikTok / Social": "bottom right"}.get(row.channel, "top center"),
                textfont=dict(color=INK, size=10),
                marker=dict(size=12 + 19 * (row.policies / max_policies) ** .5,
                            color=TEAL if row.ltv_cac >= 3 else AMBER,
                            opacity=.8, line=dict(color="white", width=1.8)),
                customdata=[[row.channel, row.ltv, row.policies]], showlegend=False,
                hovertemplate="%{customdata[0]}<br>CAC: $%{x:.0f}<br>Modeled LTV/CAC: %{y:.1f}×<br>Policies: %{customdata[2]:,.0f}<extra></extra>"))
        fig.add_hline(y=3, line_width=1, line_dash="dot", line_color="#CFD8DF")
        max_x, max_y = max(display.cac.max(), 1), max(display.ltv_cac.max(), 1)
        base(fig, 285)
        fig.update_layout(hovermode="closest", margin=dict(l=62, r=30, t=25, b=52))
        fig.update_xaxes(title="Acquisition cost / policy →", tickprefix="$", range=[0, max_x * 1.22])
        fig.update_yaxes(title="Modeled LTV / CAC →", ticksuffix="×", range=[0, max_y * 1.22])
    return fig
