"""Focused experiment visuals using the existing palette and chart system."""
import pandas as pd
import plotly.graph_objects as go
from statsmodels.stats.proportion import proportion_confint
from src.charts import base, TEAL, INK


def conversion_chart(result: dict) -> go.Figure:
    p = result["primary"]
    fig = go.Figure()
    for label, mean, n, color in [("Control", p.control, p.control_n, INK), ("Treatment", p.treatment, p.treatment_n, TEAL)]:
        low, high = proportion_confint(round(mean * n), n, method="wilson")
        fig.add_trace(go.Bar(x=[label], y=[mean], name=label, width=.42,
                            marker_color=color, error_y=dict(type="data", array=[high-mean], arrayminus=[mean-low], color="#516777", thickness=1.4, width=7),
                            text=[f"{mean:.1%}"], textposition="outside", textfont=dict(size=14, color=INK),
                            hovertemplate=f"{label}: %{{y:.2%}}<br>n={n:,}<extra></extra>"))
    base(fig, 265)
    fig.update_layout(showlegend=False, margin=dict(l=52, r=18, t=28, b=34), hovermode="closest")
    fig.update_yaxes(tickformat=".0%", range=[0, min(1, max(p.control, p.treatment) * 1.26 + .02)])
    return fig


def segment_chart(frame: pd.DataFrame) -> go.Figure:
    frame = frame.sort_values("difference")
    fig = go.Figure(go.Scatter(
        x=frame.difference * 100, y=frame.segment, mode="markers",
        error_x=dict(type="data", array=(frame.ci_high-frame.difference)*100,
                     arrayminus=(frame.difference-frame.ci_low)*100, color="#9eafb8", thickness=1.7, width=4),
        marker=dict(size=10, color=[TEAL if h else INK for h in frame.heterogeneous]),
        customdata=frame[["control_n", "treatment_n", "interaction_q"]].to_numpy(),
        hovertemplate="%{y}<br>Lift: %{x:.2f} pp<br>Control: %{customdata[0]:,.0f} / Treatment: %{customdata[1]:,.0f}<br>Interaction q: %{customdata[2]:.3f}<extra></extra>",
    ))
    base(fig, max(250, len(frame) * 32 + 90))
    fig.update_layout(margin=dict(l=145, r=28, t=18, b=46), hovermode="closest")
    fig.add_vline(x=0, line_color="#CCD7DD", line_dash="dot")
    fig.update_xaxes(title="Treatment − control (percentage points)", showgrid=True, gridcolor="#EFF2F5")
    fig.update_yaxes(showgrid=False, automargin=True)
    return fig


def cumulative_chart(result: dict) -> go.Figure:
    frame = result["frame"]
    daily = frame.groupby(["assigned_date", "variant"])[result["design"].primary].agg(["sum", "count"]).reset_index()
    fig = go.Figure()
    for arm, color in [("Control", INK), ("Treatment", TEAL)]:
        part = daily[daily.variant == arm].sort_values("assigned_date")
        rate = part["sum"].cumsum() / part["count"].cumsum()
        fig.add_trace(go.Scatter(x=part.assigned_date, y=rate, name=arm, mode="lines", line=dict(color=color, width=2),
                                hovertemplate="%{x|%d %b}<br>%{y:.2%}<extra>%{fullData.name}</extra>"))
    base(fig, 260)
    fig.update_xaxes(tickformat="%d %b")
    fig.update_yaxes(tickformat=".0%")
    return fig
