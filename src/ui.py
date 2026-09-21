"""Shared presentation helpers for the established DriveGrowth visual language."""
import math
import streamlit as st
from src.metrics import relative_change


def html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def number(value: float | None, kind: str = "count") -> str:
    if value is None or not math.isfinite(float(value)):
        return "—"
    if kind == "money":
        return f"${value / 1e6:.2f}m" if abs(value) >= 1e6 else (f"${value / 1000:,.0f}k" if abs(value) >= 1000 else f"${value:,.0f}")
    if kind == "pct":
        return f"{value:.1%}"
    if kind == "ratio":
        return f"{value:.1f}×"
    return f"{value:,.0f}"


def delta(current: float, previous: float, lower_better: bool = False) -> str:
    change = relative_change(current, previous) if current is not None and previous is not None else None
    if change is None:
        return '<span class="delta neutral">No comparable prior period</span>'
    good = change <= 0 if lower_better else change >= 0
    return f'<span class="delta {"" if good else "down"}">{"↑" if change >= 0 else "↓"} {abs(change):.1%}</span> <span class="kpi-foot">vs prior period</span>'

