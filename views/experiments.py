"""Experiment portfolio and decision reviews in the established product style."""
from __future__ import annotations
from html import escape
import json

import pandas as pd
import streamlit as st

from src.config import DB_PATH, DISCLAIMER
from src.database import connect
from src.experiment_analysis import portfolio, scenario, decision_record, json_default
from src.experiment_charts import conversion_chart, segment_chart, cumulative_chart
from src.experiment_designs import ALPHA, FAMILY_SIZE
from src.ui import html, number

DECISION_CLASSES = {"SHIP": "ship", "CONTINUE TESTING": "continue", "DO NOT SHIP": "stop"}
DIMENSIONS = {"Device": "device_type", "Acquisition channel": "acquisition_channel", "State": "state", "Risk segment": "risk_segment"}


def money(value: float, signed: bool = False) -> str:
    return ("−" if value < 0 else "+" if signed else "") + number(abs(value), "money")


def cash(value: float) -> str:
    """Use full dollar amounts in the financial bridge so rounded components reconcile."""
    return ("−" if value < 0 else "+" if value > 0 else "") + f"${abs(value):,.0f}"


def pvalue(value: float) -> str:
    return "<0.001" if value < .001 else f"{value:.3f}"


def pill(decision: str) -> str:
    return f'<span class="decision-pill {DECISION_CLASSES[decision]}">{escape(decision)}</span>'


def select_experiment(experiment_id: str) -> None:
    st.session_state["experiment_choice"] = experiment_id
    st.query_params["experiment"] = experiment_id


@st.cache_data(show_spinner=False)
def load_results(version: int) -> list[dict]:
    return portfolio()


def panel_title(title: str, subtitle: str = "", tag: str = "") -> None:
    html(f'<div class="panel-head"><div><div class="panel-title">{escape(title)}</div>'
         f'<div class="panel-subtitle">{escape(subtitle)}</div></div>'
         + (f'<span class="panel-tag">{escape(tag)}</span>' if tag else "") + '</div>')


def render_experiments() -> None:
    with connect() as con:
        ready = bool(con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='experiments'").fetchone()[0])
    if not ready:
        st.info("Generate the trial cohorts to open Experiments.")
        st.code("python -m src.generate_experiments\npython -m src.database")
        return
    try:
        with st.spinner("Calculating experiment evidence, financial intervals and rollout rules…"):
            results = load_results(DB_PATH.stat().st_mtime_ns)
    except ValueError as error:
        st.error(f"Experiment analysis is blocked by invalid or insufficient observations: {error}")
        st.caption("Repair the source data and rebuild the database before interpreting treatment effects.")
        return
    lookup = {r["design"].experiment_id: r for r in results}
    choices = ["portfolio", *lookup]
    requested = st.query_params.get("experiment", "portfolio")
    with st.sidebar:
        html('<div class="sidebar-divider"></div><div class="side-label">EXPERIMENT LIBRARY</div>')
        selected = st.selectbox("Review", choices, index=choices.index(requested) if requested in choices else 0,
                                format_func=lambda x: "All experiments" if x == "portfolio" else lookup[x]["design"].name,
                                key="experiment_choice")
        st.query_params["experiment"] = selected
        html('<div class="side-context"><div class="side-label">DECISION STANDARD</div>'
             '<p>Evidence + economics<br>+ guardrails + sample sufficiency</p>'
             '<div class="side-label">ANALYSIS SCOPE</div><p>Full randomized population<br>30-day outcome window<br>Fixed-horizon analysis</p></div>'
             '<div class="side-footer"><strong>PORTFOLIO PROJECT · CHECKPOINT 02</strong><br>'
             'Synthetic randomized trials<br>Snapshot · 31 Aug 2026<br>SQL / inference / decisions</div>')
    if selected == "portfolio":
        render_portfolio(results)
    else:
        render_detail(lookup[selected])
    html('<div class="bottom-note"><span>DRIVEGROWTH · Synthetic trials / real analytical methods</span><span>Snapshot · 31 Aug 2026</span></div>')


def render_portfolio(results: list[dict]) -> None:
    html('<div class="eyebrow">DRIVECO / PRODUCT & GROWTH EXPERIMENTS</div>'
         '<h1 class="page-title">Which changes deserve a rollout?</h1>'
         '<p class="subtitle">A decision portfolio connecting customer behavior, financial value and downside risk.</p>'
         '<div class="exp-badges"><span class="badge synthetic">SYNTHETIC TRIALS</span><span class="badge">FIXED HORIZON · 30-DAY OUTCOMES</span></div>')
    candidates = [r for r in results if r["decision"]["recommendation"] == "SHIP"]
    modeled_value = sum(r["impact"]["annualized_net"] for r in candidates)
    cards = [("Experiments reviewed", str(len(results)), "Three pre-specified primary hypotheses"),
             ("Randomized units", number(sum(r["assigned"] for r in results)), "Shoppers or eligible referral members"),
             ("Rollout candidates", str(len(candidates)), "Pass all evidence and business gates"),
             ("Candidate modeled value", money(modeled_value), "Annualized cohort value · assumptions apply")]
    html('<div class="kpi-grid">' + ''.join(f'<div class="kpi {"accent" if i == 3 else ""}"><div class="kpi-label">{a}</div><div class="kpi-value">{b}</div><div class="kpi-foot">{c}</div></div>' for i, (a,b,c) in enumerate(cards)) + '</div>')
    html('<div class="section-intro">THE EXPERIMENT PORTFOLIO <span>Decisions computed from unit-level outcomes</span></div>')
    for r in results:
        d, p, impact = r["design"], r["primary"], r["impact"]
        with st.container(border=True, key=f"exp_panel_portfolio_{d.experiment_id}"):
            html(f'<div class="panel-head"><div><div class="experiment-name">{escape(d.name)}</div><div class="panel-subtitle">{escape(d.control)} → {escape(d.treatment)}</div></div>{pill(r["decision"]["recommendation"])}</div>'
                 f'<div class="trial-status">{escape(r["status"])} · {r["assigned"]:,} assigned · {r["mature"]:,} mature · {pd.Timestamp(d.start):%d %b}–{pd.Timestamp(d.end):%d %b %Y}</div>'
                 f'<div class="experiment-metric-label">PRIMARY · {escape(d.primary_label)}</div>'
                 '<div class="experiment-stat-grid">'
                 f'<div><span>Control → treatment</span><strong>{p.control:.2%} → {p.treatment:.2%}</strong></div>'
                 f'<div><span>Absolute / relative lift</span><strong>{p.difference * 100:+.2f} pp <em>/ {number(p.relative_lift,"pct")}</em></strong></div>'
                 f'<div><span>Annualized modeled contribution</span><strong>{money(impact["annualized_net"], True)}</strong></div></div>'
                 f'<div class="experiment-evidence">95% lift CI: {p.ci_low*100:+.2f} to {p.ci_high*100:+.2f} pp &nbsp; · &nbsp; Family-adjusted p {pvalue(r["adjusted_p"])}<br>'
                 f'95% modeled value interval: {money(impact["annual_ci_low"])} to {money(impact["annual_ci_high"])}</div>'
                 f'<div class="decision-reason">{escape(r["decision"]["reasons"][0])}</div>')
            st.button("Review experiment →", key=f"open_{d.experiment_id}", on_click=select_experiment, args=(d.experiment_id,))
    with st.container(border=True, key="exp_panel_portfolio_signals"):
        panel_title("Signals worth a closer look", "The difference between a metric win and a business win", "BRIEFING")
        for r in results:
            p, impact, d = r["primary"], r["impact"], r["design"]
            if r["adjusted_p"] < .05 and p.difference > 0 and impact["annualized_net"] <= 0:
                title = f"{d.name}: conversion improves, economics do not clear the hurdle"
                detail = f"{p.difference*100:+.2f} pp primary lift, but {money(impact['annualized_net'], True)} modeled contribution after incentives and rollout costs."
            elif r["decision"]["recommendation"] == "SHIP":
                title = f"{d.name} clears the rollout rules"
                detail = f"All guardrails pass; modeled financial downside is {money(impact['annual_ci_low'], True)} at the lower 95% sampling bound. Start with a staged rollout and a holdout."
            else:
                title = f"{d.name}: the decision needs more evidence"
                detail = " ".join(r["decision"]["reasons"])
            html(f'<div class="insight-row"><div class="insight-title">{escape(title)}</div><div class="insight-evidence">{escape(detail)}</div></div>')
    st.caption("Modeled value uses 12 months of future contribution for each of 12 monthly acquisition cohorts. It is not realized revenue or first-year recognized contribution. The trial cohorts are separate from the historical acquisition book.")


def render_detail(r: dict) -> None:
    d, p, impact = r["design"], r["primary"], r["impact"]
    st.button("← All experiments", on_click=select_experiment, args=("portfolio",), key="back_to_portfolio")
    html('<div class="eyebrow">EXPERIMENTS / DECISION REVIEW</div>'
         f'<h1 class="page-title">{escape(d.name)}</h1><p class="subtitle">{escape(d.control)} → {escape(d.treatment)}</p>')
    with st.container(border=True, key="exp_panel_design"):
        panel_title("The question we set out to answer", tag="PRE-SPECIFIED DESIGN")
        html(f'<div class="hypothesis">{escape(d.hypothesis)}</div><div class="design-grid">'
             f'<div><span>PRIMARY METRIC</span><p>{escape(d.primary_label)}</p></div>'
             f'<div><span>GUARDRAILS</span><p>{escape(" · ".join(g.label for g in d.guardrails))}</p></div>'
             f'<div><span>POPULATION / RANDOMIZATION UNIT</span><p>{escape(d.population)}</p></div>'
             f'<div><span>TEST PERIOD / FOLLOW-UP</span><p>{pd.Timestamp(d.start):%d %b}–{pd.Timestamp(d.end):%d %b %Y} · {d.observation_days}-day outcomes</p></div>'
             f'<div><span>SAMPLE / STATUS</span><p>{p.control_n:,} control · {p.treatment_n:,} treatment<br>{r["status"]}</p></div>'
             f'<div><span>PRE-SPECIFIED SAMPLE TARGET</span><p>{r["target_per_arm"]:,} / arm · 80% power at {d.mde*100:.1f} pp MDE</p></div></div>')
    render_decision(r, impact, r["decision"])
    tabs = st.tabs(["Decision review", "Segment differences", "Evidence & methods"])
    with tabs[0]:
        render_results(r)
        render_impact(r)
        render_guardrails(r)
    with tabs[1]:
        render_segments(r)
    with tabs[2]:
        render_methods(r)


def render_decision(r: dict, impact: dict, decision: dict) -> None:
    p = r["primary"]
    relative = f"{p.relative_lift:+.1%} relative" if p.relative_lift is not None else "relative lift undefined at zero baseline"
    action = {"SHIP": "Begin a staged rollout with a persistent randomized holdout. Monitor the pre-specified guardrails and revalidate contribution assumptions before full exposure.",
              "DO NOT SHIP": "Keep the current experience. Address the failed economic or guardrail condition, then register a new test before considering rollout.",
              "CONTINUE TESTING": "Keep the control as the default. Register an adequately powered follow-up or a valid sequential design; do not extend this fixed-horizon test until significance appears."}[decision["recommendation"]]
    html(f'<div class="decision-banner {DECISION_CLASSES[decision["recommendation"]]}"><div class="panel-head"><div class="panel-title">The rollout decision</div>{pill(decision["recommendation"])}</div>'
         f'<div class="decision-grid"><div><span>WHAT HAPPENED</span><p>{escape(r["design"].primary_label)} moved from {p.control:.2%} to {p.treatment:.2%}: {p.difference*100:+.2f} pp, {relative}.</p></div>'
         f'<div><span>WHY IT MATTERS</span><p>{escape(" ".join(decision["reasons"]))}</p></div>'
         f'<div><span>FINANCIAL IMPACT</span><p>{money(impact["annualized_net"], True)} annualized modeled contribution. 95% sampling interval: {money(impact["annual_ci_low"])} to {money(impact["annual_ci_high"])}.</p></div>'
         f'<div><span>RISKS / GUARDRAILS</span><p>{escape(" · ".join(g["label"] + ": " + g["state"].lower() for g in r["guardrails"]))}. Value, traffic and implementation costs remain assumptions.</p></div></div>'
         f'<div class="decision-action"><span>RECOMMENDED NEXT ACTION</span><p>{action}</p></div></div>')


def render_results(r: dict) -> None:
    p = r["primary"]
    left, right = st.columns([1, 1.12], gap="medium")
    with left:
        with st.container(border=True, key="exp_panel_primary_chart"):
            panel_title("What changed?", r["design"].primary_label + " · all randomized units", "95% ARM CIs")
            st.plotly_chart(conversion_chart(r), width="stretch", config={"displayModeBar": False}, theme=None)
            html('<div class="chart-note">Wilson intervals for each arm. The treatment-effect interval is calculated separately; overlap of arm intervals is not the decision rule.</div>')
    with right:
        with st.container(border=True, key="exp_panel_primary_stats"):
            panel_title("How strong is the evidence?", "Treatment minus control · intention to treat")
            html(f'<div class="effect-headline">{p.difference*100:+.2f}<span> percentage points</span></div>'
                 f'<div class="effect-interval">95% CI: {p.ci_low*100:+.2f} to {p.ci_high*100:+.2f} pp</div>'
                 f'<div class="evidence-pair"><span>Relative lift</span><strong>{number(p.relative_lift,"pct")}</strong></div>'
                 f'<div class="evidence-pair"><span>Raw two-sided p-value</span><strong>{pvalue(p.p_value)}</strong></div>'
                 f'<div class="evidence-pair"><span>Family-adjusted p-value</span><strong>{pvalue(r["adjusted_p"])}</strong></div>'
                 f'<div class="evidence-pair"><span>Minimum practical lift</span><strong>{r["design"].practical_effect*100:.2f} pp</strong></div>'
                 f'<div class="chart-note">{escape(p.method)}. Bonferroni adjustment covers the three primary hypotheses. A p-value is not the probability that the treatment works.</div>')
    with st.container(border=True, key="exp_panel_secondary"):
        panel_title("Did the rest of the customer journey improve?", "Secondary results are diagnostic; the pre-specified primary metric determines evidence for rollout")
        rows = []
        for label, estimate in r["secondary"].items():
            rows.append((label, estimate, "pct"))
        rows.extend([("Premium volume / randomized unit", r["premium"], "money"),
                     ("30-day pre-incentive contribution / unit", r["observed_finance"], "money"),
                     ("Modeled 12-month net value / unit", r["finance"], "money")])
        metric_table(rows)
        html('<div class="chart-note">All amounts include zeros for non-converters. Premium volume is not DriveCo revenue. Financial intervals use a unit bootstrap; continuous premium uses Welch’s unequal-variance test. Secondary p-values are unadjusted.</div>')


def metric_table(rows: list) -> None:
    table = '<div class="table-wrap"><table class="data-table"><thead><tr><th>Metric</th><th>Control</th><th>Treatment</th><th>Difference / 95% CI</th><th>p-value</th></tr></thead><tbody>'
    for label, e, fmt in rows:
        if fmt == "pct":
            cv, tv = f"{e.control:.2%}", f"{e.treatment:.2%}"
            diff = f"{e.difference*100:+.2f} pp"
            interval = f"{e.ci_low*100:+.2f} to {e.ci_high*100:+.2f} pp"
        else:
            cv, tv = f"${e.control:,.2f}", f"${e.treatment:,.2f}"
            diff = f"${e.difference:+,.2f}"
            interval = f"${e.ci_low:+,.2f} to ${e.ci_high:+,.2f}"
        table += f'<tr><td>{escape(label)}</td><td>{cv}</td><td>{tv}</td><td>{diff}<br><span class="table-sub">{interval}</span></td><td>{pvalue(e.p_value)}</td></tr>'
    html(table + '</tbody></table></div>')


def render_impact(r: dict) -> None:
    impact = r["impact"]
    with st.container(border=True, key="exp_panel_impact"):
        panel_title("Does the economics support rollout?", "From incremental policies to contribution after incentive and rollout costs", "MODELED IMPACT")
        html(f'<div class="impact-hero"><div><span>ANNUALIZED MODELED CONTRIBUTION</span><strong>{money(impact["annualized_net"], True)}</strong><p>95% sampling interval · {money(impact["annual_ci_low"])} to {money(impact["annual_ci_high"])}</p></div>'
             f'<div><span>ELIGIBLE UNITS / MONTH</span><strong>{impact["monthly_units"]:,.0f}</strong><p>Observed enrollment pace, extrapolated to 30.44 days</p></div></div>')
        bridge = [
            ("Incremental policies / month", f'{impact["incremental_policies"]:+,.1f}', "Policy-conversion difference × eligible monthly units"),
            ("Contribution from extra policies", cash(impact["volume_contribution"]), f'Incremental policies × ${impact["control_value_per_policy"]:,.2f} control value / policy'),
            ("Change in value mix", cash(impact["value_mix_contribution"]), "Treatment policy volume × change in conditional policy value"),
            ("Incremental incentive cost", cash(-impact["incremental_incentives"]), "Treatment reward cost − control reward cost, across all conversions"),
            ("Incremental variable cost", cash(-impact["incremental_variable_cost"]), "Per-assigned-unit treatment delivery costs"),
            ("Monthly rollout operating cost", cash(-impact["monthly_fixed_cost"]), "Explicit implementation assumption"),
            ("Net value / monthly acquisition cohort", cash(impact["monthly_net"]), "Gross contribution − incentives − variable and fixed costs"),
            ("One-time implementation cost", cash(-impact["setup_cost"]), "Deducted once from the annualized estimate"),
        ]
        table = '<div class="table-wrap"><table class="data-table impact-table"><thead><tr><th>Bridge</th><th>Amount</th><th>Calculation</th></tr></thead><tbody>'
        for label, amount, explanation in bridge:
            table += f'<tr><td>{escape(label)}</td><td>{amount}</td><td>{escape(explanation)}</td></tr>'
        html(table + '</tbody></table></div>')
        html('<div class="chart-note">Annualized estimate = 12 × monthly cohort net value − one-time implementation cost. Each acquired policy carries 12-month modeled value. This is not realized revenue or first-calendar-year recognized contribution. The interval covers experiment sampling uncertainty, not valuation or traffic uncertainty.</div>')
        with st.expander("What could change the decision? · rollout sensitivity"):
            st.caption("Change operating assumptions without changing the measured experiment. The portfolio decision retains the registered default scenario.")
            a, b = st.columns(2)
            with a:
                traffic = st.number_input("Eligible units per month", min_value=0.0, value=float(round(impact["monthly_units"])), step=1000.0, key="scenario_traffic_"+r["design"].experiment_id)
                multiplier = st.slider("Policy-value multiplier", .25, 1.50, 1.0, .05, key="scenario_value_"+r["design"].experiment_id)
            with b:
                recurring = st.number_input("Monthly rollout cost ($)", min_value=0.0, value=float(r["design"].monthly_cost), step=500.0, key="scenario_recurring_"+r["design"].experiment_id)
                setup = st.number_input("One-time implementation cost ($)", min_value=0.0, value=float(r["design"].setup_cost), step=5000.0, key="scenario_setup_"+r["design"].experiment_id)
            changed = scenario(r, traffic, multiplier, recurring, setup)
            ci = changed["impact"]
            html(f'<div class="scenario-result">{pill(changed["decision"]["recommendation"])} <strong>{money(ci["annualized_net"], True)}</strong> annualized modeled contribution<br><span>95% sampling interval: {money(ci["annual_ci_low"])} to {money(ci["annual_ci_high"])}</span></div>')
            st.caption(" ".join(changed["decision"]["reasons"]))


def render_guardrails(r: dict) -> None:
    with st.container(border=True, key="exp_panel_guardrails"):
        panel_title("What could go wrong with a rollout?", "Safety must be supported by a noninferiority bound, not a non-significant p-value")
        for g in r["guardrails"]:
            e = g["estimate"]
            direction = "increase" if g["direction"] == "lower_good" else "decrease"
            cls = "ship" if g["state"] == "Pass" else "stop" if g["state"] == "Fail" else "continue"
            html(f'<div class="guardrail-row"><div><strong>{escape(g["label"])}</strong><p>{e.control:.2%} control → {e.treatment:.2%} treatment · {e.difference*100:+.2f} pp</p>'
                 f'<p>Allowed harm: {g["tolerance"]*100:.2f} pp {direction}. Upper harm bound: {g["harm_high"]*100:.2f} pp.</p></div><span class="decision-pill {cls}">{g["state"].upper()}</span></div>')
        html('<div class="chart-note">One-sided bounds control the guardrail family at 5% within this experiment. An unclear result blocks SHIP. A demonstrated breach triggers DO NOT SHIP.</div>')


def render_segments(r: dict) -> None:
    with st.container(border=True, key="exp_panel_segments"):
        panel_title("Where does the treatment work best?", "Randomized treatment comparisons within pre-exposure segments · exploratory")
        dim = st.selectbox("Compare treatment effects by", list(DIMENSIONS), key="effect_dimension")
        part = r["segments"][r["segments"].dimension == DIMENSIONS[dim]]
        if part.empty:
            st.info("Too few units for this breakdown.")
            return
        st.plotly_chart(segment_chart(part), width="stretch", config={"displayModeBar": False}, theme=None)
        html('<div class="chart-note">Intervals are pointwise 95% treatment effects. Teal indicates an interaction detected after BH correction across all four dimensions; it is not an automatic segment rollout recommendation.</div>')
        significant = part[part.heterogeneous]
        panel_title("Signals worth a closer look")
        if len(significant):
            best = significant.sort_values("difference", ascending=False).iloc[0]
            html(f'<div class="insight-row"><div class="insight-title">The treatment effect varies across {escape(dim.lower())} segments</div><div class="insight-evidence">'
                 f'{escape(str(best.segment))}: {best.difference*100:+.2f} pp (95% CI {best.ci_low*100:+.2f} to {best.ci_high*100:+.2f}); interaction q {pvalue(best.interaction_q)} versus the complementary population. '
                 'Confirm this pattern in a pre-specified follow-up before targeting a rollout.</div></div>')
        else:
            html('<div class="insight-row"><div class="insight-title">No reliable difference between these segment effects is detected</div><div class="insight-evidence">Different point estimates alone are not evidence of heterogeneous treatment effects. This analysis may still lack power for small segments.</div></div>')
        rows = '<div class="table-wrap"><table class="data-table"><thead><tr><th>Segment</th><th>Control / treatment n</th><th>Lift / 95% CI (pp)</th><th>Interaction q</th></tr></thead><tbody>'
        for x in part.sort_values("difference", ascending=False).itertuples():
            rows += f'<tr><td>{escape(str(x.segment))}</td><td>{x.control_n:,} / {x.treatment_n:,}</td><td>{x.difference*100:+.2f}<br><span class="table-sub">{x.ci_low*100:+.2f} to {x.ci_high*100:+.2f}</span></td><td>{pvalue(x.interaction_q)}<br><span class="table-sub">{"Exploratory" if x.sufficient else "Small sample"}</span></td></tr>'
        html(rows + '</tbody></table></div>')
    st.caption("No cross-channel or cross-state causal claims are made. Effects compare randomized treatment and control inside the same segment. Interactions compare that effect with the remaining population. Correlated and overlapping segment tests are exploratory.")


def render_methods(r: dict) -> None:
    with st.container(border=True, key="exp_panel_timeline"):
        panel_title("Did the result stabilize as enrollment accumulated?", "Retrospective cumulative 30-day outcomes, grouped by assignment date")
        st.plotly_chart(cumulative_chart(r), width="stretch", config={"displayModeBar": False}, theme=None)
        html('<div class="chart-note">This reconstructs fully matured cohorts at the final snapshot; it is not the information available in real time. No interim stopping or repeated significance testing is used.</div>')
    with st.container(border=True, key="exp_panel_quality"):
        panel_title("Can we trust the comparison?", "Assignment and observation checks gate every recommendation")
        for check in r["quality"]:
            html(f'<div class="evidence-pair"><span><strong>{escape(check["name"])}</strong><br><span class="table-sub">{escape(check["detail"])}</span></span><span class="check-label">{"PASS" if check["passed"] else "REVIEW"}</span></div>')
    with st.expander("The decision contract · methods and explicit thresholds", expanded=True):
        st.markdown(f"""
**Primary inference:** {r['primary'].method}. Report a two-sided 95% difference interval and raw p-value.
Use Bonferroni-adjusted p-values across {FAMILY_SIZE} registered primary hypotheses; the decision threshold is {ALPHA:.0%}.

**Sample plan:** {r['target_per_arm']:,} units per arm, at 80% power, {r['design'].planning_rate:.0%} planning baseline,
and {r['design'].mde*100:.1f} pp minimum detectable effect. The separate practical-lift threshold is {r['design'].practical_effect*100:.2f} pp.

**Financial inference:** {r['finance'].method}. Resample randomized units within arms, retaining zeros,
with paired gross/net draws for sensitivity analysis. Future policy value uses pre-test channel/risk history,
a 12-month horizon and 8% annual discount. Traffic defaults to observed enrollment pace.

**Guardrails:** one-sided Newcombe noninferiority bounds, Bonferroni-adjusted within this experiment.
PASS means the upper bound on harm is below the configured tolerance. FAIL means the lower bound exceeds tolerance.
Otherwise the result is unclear and cannot support SHIP.

**SHIP** requires valid data, mature outcomes, planned sample in both arms, positive family-adjusted primary evidence,
practical lift, a positive lower financial bound and all guardrails passing.
**DO NOT SHIP** follows demonstrated guardrail harm, a negative primary or financial interval, or sufficient positive
conversion evidence with a non-positive best estimate of rollout contribution. Otherwise **CONTINUE TESTING**.

**Segments:** treatment-effect interactions versus the complementary population; BH correction over all four dimensions.
Cells require at least 200 units per arm and ten successes/failures for a heterogeneity flag. Segment results remain exploratory.

**Limitations:** separate synthetic trial populations; no production telemetry. Referral design allows one invitation and
one rewarded conversion per member, with no network spillovers. No sequential stopping rule, long-run retention validation,
or uncertainty in financial assumptions is modeled. A closed inconclusive test needs a registered follow-up, not significance hunting.
""")
        st.caption(DISCLAIMER)
    st.download_button("↓ Export decision record", json.dumps(decision_record(r), default=json_default, indent=2),
                       file_name=r["design"].experiment_id + "_decision.json", mime="application/json")
