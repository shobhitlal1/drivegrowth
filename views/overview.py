"""The original executive overview, preserved as a routed view."""
from html import escape
import pandas as pd
import streamlit as st
from src.analytics import Filters, dashboard_data
from src.charts import revenue_chart, channel_chart
from src.config import DB_PATH, CHANNELS, STATES, CARRIER_NAMES, DISCLAIMER
from src.executive_insights import observations
from src.ui import html, number, delta


def render_overview():
    months = list(pd.date_range("2024-09-01", "2026-07-01", freq="MS"))
    with st.sidebar:
        html('<a class="nav-link" href="#channel-economics">Channel economics ↗</a>'
             '<a class="nav-link" href="#funnel-health">Funnel health ↗</a>'
             '<div class="sidebar-divider"></div><div class="side-label">REPORTING WINDOW</div>')
        start = st.selectbox("From", months, index=len(months) - 3, format_func=lambda x: x.strftime("%B %Y"))
        end = st.selectbox("Through", months, index=len(months) - 1, format_func=lambda x: x.strftime("%B %Y"))
        html('<div class="side-label" style="margin-top:12px">PORTFOLIO FILTERS</div>')
        state = st.selectbox("State", ["All states", *sorted(STATES)])
        channel = st.selectbox("Acquisition channel", ["All channels", *CHANNELS])
        carrier = st.selectbox("Carrier", ["All carriers", *CARRIER_NAMES])
        segment = st.selectbox("Customer segment", ["All segments", "High-risk shoppers", "Referral customers", "Social-led shoppers",
                                                           "High-intent search", "Low-risk households", "Everyday comparison shoppers"])
        html('<div class="side-footer"><strong>PORTFOLIO PROJECT · CHECKPOINT 02</strong><br>'
             'Synthetic marketplace data<br>Snapshot · 31 Aug 2026<br>Python / SQL / DuckDB</div>')

    if start > end:
        st.warning("Choose a start month on or before the ending month.")
        st.stop()
    f = Filters(start.date(), (end + pd.offsets.MonthEnd()).date(), state, channel, carrier, segment)


    @st.cache_data(show_spinner=False)
    def load(filters: Filters, version: int) -> dict:
        return dashboard_data(filters)


    with st.spinner("Querying the portfolio…"):
        data = load(f, DB_PATH.stat().st_mtime_ns)
    k, prev = data["current"], data["previous"]
    channels = data["channels"]

    left, right = st.columns([.72, .28], vertical_alignment="center")
    with left:
        html('<div class="eyebrow">DRIVECO / GROWTH & OPERATIONS</div>'
             '<h1 class="page-title">Executive overview</h1>'
             '<p class="subtitle">Acquisition performance and the health of DriveCo’s insurance marketplace.</p>')
    with right:
        html('<div class="top-badges"><span class="badge synthetic">SYNTHETIC DATA</span><span class="badge">OVERVIEW / 01</span></div>')
        st.download_button("↓  Export channel snapshot", channels.to_csv(index=False),
                           file_name=f"drivegrowth_channels_{f.start}_{f.end}.csv", mime="text/csv", width="stretch")

    comparison = f"vs {f.previous().start:%d %b} – {f.previous().end:%d %b %Y}"
    html(f'<div class="date-bar"><strong>{f.start:%d %b} — {f.end:%d %b %Y} &nbsp; <span style="color:#9aa7af;font-weight:400">/ {comparison}</span></strong>'
         f'<span>{number(data["integrity"]["customers"])} customers in source · 12 states · 8 channels</span></div>')
    if f.previous().start < months[0].date():
        st.caption("Prior period extends before the dataset. Comparative changes are suppressed.")
        prev = {key: None for key in prev}
    if not k["customers"]:
        st.info("No acquired customers match this selection. Widen the reporting window or clear a portfolio filter.")
        st.stop()

    cards = [
        ("Commission revenue", "revenue", "money", "Active portfolio · in reporting period", False),
        ("Pre-acquisition contribution", "contribution_margin", "money", "Before acquisition costs · observed", False),
        ("Policies acquired", "policies", "count", "Policies from selected signup cohorts", False),
        ("Customer acquisition cost", "cac", "money", "Acquisition spend / policies acquired", True),
    ]
    markup = '<div class="kpi-grid">'
    for i, (label, key, fmt, foot, inverse) in enumerate(cards):
        markup += f'<div class="kpi {"accent" if i == 1 else ""}"><div class="kpi-label">{label}</div><div class="kpi-value">{number(k[key], fmt)}</div>{delta(k[key], prev[key], inverse)}<div class="kpi-foot">{foot}</div></div>'
    html(markup + "</div>")
    mini = [("Customers acquired", k["customers"], "count", "Website visits · identified cohort"),
            ("Quote → policy", k["conversion"], "pct", "Policies / quote starts"),
            ("Modeled 24mo LTV", k["ltv"], "money", "Contribution / acquired policy"),
            ("LTV / CAC", k["ltv_cac"], "ratio", "Modeled value / acquisition cost"),
            ("Renewal rate", k["renewal_rate"], "pct", f'{number(k["renewal_eligible"])} policies due for renewal')]
    html('<div class="kpi-strip">' + ''.join(f'<div class="mini-kpi"><div class="mini-label">{label}</div><div class="mini-value">{number(value, fmt)}</div><div class="mini-detail">{foot}</div></div>' for label, value, fmt, foot in mini) + '</div>')

    l, r = st.columns([1.17, 1], gap="medium")
    with l:
        with st.container(border=True, key="revenue_panel"):
            html('<div class="panel-head"><div><div class="panel-title">A growing book of business</div><div class="panel-subtitle">Monthly marketplace revenue and contribution · active portfolio</div></div><span class="panel-tag">12 MONTHS</span></div>')
            st.plotly_chart(revenue_chart(data["series"]), width="stretch", config={"displayModeBar": False}, theme=None)
            html('<div class="chart-note">Earned commission revenue. Premium volume and carrier claims are excluded from marketplace revenue.</div>')
    with r:
        with st.container(border=True, key="channel_panel"):
            html('<div id="channel-economics" class="panel-title">What does a dollar of acquisition buy?</div><div class="panel-subtitle">Channel economics · bubble size represents acquired policies</div>')
            st.plotly_chart(channel_chart(channels), width="stretch", config={"displayModeBar": False}, theme=None)
            html('<div class="chart-note">Upper left = more modeled value at lower CAC. Dotted line: illustrative 3× hurdle, not an investment recommendation.</div>')

    l, r = st.columns([1.17, 1], gap="medium")
    with l:
        with st.container(border=True, key="funnel_panel"):
            html('<div id="funnel-health" class="panel-head"><div><div class="panel-title">From first visit to first policy</div><div class="panel-subtitle">Selected acquisition cohorts · conversion from the preceding stage</div></div><span class="panel-tag">FUNNEL</span></div>')
            stages = [("Website visits", k["customers"]), ("Quote started", k["quote_starts"]), ("Quote completed", k["quote_completions"]),
                      ("Carrier matched", k["carrier_matches"]), ("Policy purchased", k["policies"])]
            rows = ""
            for i, (label, value) in enumerate(stages):
                rate = "100%" if i == 0 else number(value / stages[i - 1][1], "pct") if stages[i - 1][1] else "—"
                rows += f'<div class="funnel-row"><div class="funnel-label">{label}</div><div class="funnel-track"><div class="funnel-fill" style="width:{100 * value / k["customers"]:.2f}%"></div></div><div class="funnel-count">{number(value)}</div><div class="funnel-rate">{rate}</div></div>'
            html(rows)
            html(f'<div class="chart-note">{number(k["policies"] / k["customers"], "pct")} of website visits become policies. Aggregate impressions and renewal eligibility use different denominators.</div>')
    with r:
        with st.container(border=True, key="signals_panel"):
            html('<div class="panel-head"><div><div class="panel-title">Signals worth a closer look</div><div class="panel-subtitle">Calculated from this selection · observations, not causal claims</div></div><span class="panel-tag">BRIEFING</span></div>')
            items = observations(channels, data["devices"])
            if items:
                for item in items:
                    html(f'<div class="insight-row"><div class="insight-tag">{escape(item["tag"])}</div><div class="insight-title">{escape(item["title"])}</div><div class="insight-evidence">{escape(item["evidence"])}</div><div class="insight-action">{escape(item["action"])}</div></div>')
            else:
                st.caption("This selection has insufficient comparable groups for a reliable observation.")

    with st.container(border=True, key="table_panel"):
        html('<div class="panel-head"><div><div class="panel-title">Channel performance, beyond the headline</div><div class="panel-subtitle">A common acquisition window · modeled lifetime contribution alongside acquisition cost</div></div><span class="panel-tag">SORTED BY POLICIES</span></div>')
        table = '<div class="table-wrap"><table class="data-table"><thead><tr><th>Acquisition channel</th><th>Customers</th><th>Policies</th><th>Spend</th><th>Quote → policy</th><th>CAC</th><th>24mo LTV</th><th>LTV / CAC</th></tr></thead><tbody>'
        for row in channels.itertuples():
            table += f'<tr><td>{escape(row.channel)}</td><td>{number(row.customers)}</td><td>{number(row.policies)}</td><td>{number(row.spend, "money")}</td><td>{number(row.conversion, "pct")}</td><td>{number(row.cac, "money")}</td><td>{number(row.ltv, "money")}</td><td><span class="ratio-pill {"weak" if row.ltv_cac < 3 else ""}">{number(row.ltv_cac, "ratio")}</span></td></tr>'
        html(table + '</tbody></table></div>')

    with st.expander("How to read this overview · definitions, cohort scope and model assumptions"):
        st.markdown("""
    **Acquisition metrics** use customers whose signup date falls within the reporting months.
    Each synthetic visitor has at most one quote and one policy. Policy decisions occur within seven days.
    **Revenue and contribution** use the active policy book in the reporting months, including earlier acquisitions.
    Contribution equals earned commission minus service and onboarding costs, before acquisition spend.
    **CAC** divides acquisition spend by purchased policies. State, carrier and segment filters allocate daily channel spend
    in proportion to registered visitors; they do not measure directly observed segment advertising costs.
    A carrier filter attributes customers to the carrier selected at quote start and therefore excludes pre-quote visitors.
    **LTV** is 24 months of discounted expected contribution per acquired policy, using channel/risk-level margin
    and constant monthly survival estimated from the full history through 31 August 2026. It is a scenario estimate,
    not a validated predictive model or a historical backtest. Annual discount: 8%; onboarding cost: $7.50.
    **Renewal rate** is the share renewing among policies that survived to their first anniversary in the reporting months.
    Earlier cancellations are excluded from this conditional metric. **Comparisons** use the preceding equal number of calendar months.
    The final seven acquisition days of August are excluded to allow complete policy outcomes; July is the last selectable cohort month.
    """)
        st.caption(DISCLAIMER)

    html(f'<div class="bottom-note"><span>DRIVEGROWTH · Synthetic data / real analytical methods</span><span>Snapshot 31 Aug 2026 &nbsp; · &nbsp; {number(data["integrity"]["events"])} linked funnel events</span></div>')
