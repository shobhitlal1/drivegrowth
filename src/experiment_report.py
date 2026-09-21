"""Generate a readable decision memo and auditable JSON from live experiment analysis."""
import json
from src.config import ROOT, DISCLAIMER
from src.experiment_analysis import portfolio, decision_record, json_default


def write_experiment_report() -> list[dict]:
    results = portfolio()
    records = [decision_record(r) for r in results]
    (ROOT / "docs" / "experiment_results.json").write_text(json.dumps(records, default=json_default, indent=2) + "\n")
    rows = ["| Experiment | Control → treatment | Lift (pp) | Adjusted p | Annualized modeled contribution | Recommendation |",
            "|---|---|---|---|---|---|"]
    for r in results:
        p, i = r["primary"], r["impact"]
        pv = "<0.001" if r["adjusted_p"] < .001 else f"{r['adjusted_p']:.3f}"
        rows.append(f"| {r['design'].name} | {p.control:.2%} → {p.treatment:.2%} | {p.difference*100:+.2f} | {pv} | ${i['annualized_net']:+,.0f} | {r['decision']['recommendation']} |")
    body = "# Experiment decision review\n\nSnapshot: August 31, 2026. Generated from the current DuckDB experiment ledger.\n\n" + DISCLAIMER + "\n\n" + "\n".join(rows) + "\n\n"
    for r in results:
        d, p, i = r["design"], r["primary"], r["impact"]
        body += f"## {d.name} · {r['decision']['recommendation']}\n\n"
        body += f"**What happened:** {p.control_n:,} control and {p.treatment_n:,} treatment units. {d.primary_label} changed by {p.difference*100:+.2f} percentage points (95% interval {p.ci_low*100:+.2f} to {p.ci_high*100:+.2f}).\n\n"
        body += "**Why it matters:** " + " ".join(r["decision"]["reasons"]) + "\n\n"
        body += f"**Financial impact:** At {i['monthly_units']:,.0f} eligible units per month, the model implies {i['incremental_policies']:+,.1f} incremental policies, ${i['incremental_gross_contribution']:+,.0f} gross modeled contribution, ${i['incremental_incentives']:,.0f} incremental incentives, ${i['incremental_variable_cost']:,.0f} variable cost and ${i['monthly_fixed_cost']:,.0f} monthly fixed cost. Annualized modeled net contribution is ${i['annualized_net']:+,.0f}, after ${i['setup_cost']:,.0f} setup cost; its 95% sampling interval is ${i['annual_ci_low']:+,.0f} to ${i['annual_ci_high']:+,.0f}.\n\n"
        body += "**Guardrails:** " + "; ".join(f"{g['label']} — {g['state']} (upper harm bound {g['harm_high']*100:.2f} pp vs {g['tolerance']*100:.2f} pp tolerance)" for g in r["guardrails"]) + ".\n\n"
        body += f"**Sample:** target {r['target_per_arm']:,} per arm; {'met' if r['sufficient'] else 'not met'}. All {len(r['quality'])} quality checks {'pass' if r['data_valid'] else 'need review'}.\n\n"
        device = r["segments"][r["segments"].dimension == "device_type"]
        if device.heterogeneous.any():
            leading = device.sort_values("difference", ascending=False).iloc[0]
            body += f"**Where to investigate first:** {leading.segment} has {leading.difference*100:+.2f} pp lift, with interaction q={leading.interaction_q:.4g} versus the remaining population. Confirm the exploratory difference in a pre-specified targeted follow-up before assuming differential economics.\n\n"
    body += "## Interpreting the modeled value\n\nAnnualization values twelve new acquisition cohorts over twelve policy months each; it is not realized revenue or first-year recognized contribution. Financial intervals cover randomized-unit sampling only. Traffic, policy valuation, retention and cost assumptions remain uncertain. Referral rewards apply to all qualifying conversions. No real-company outcomes are claimed.\n\nSee [the experiment methodology](experimentation.md) and [machine-readable decision records](experiment_results.json). The optimizer has not been started.\n"
    (ROOT / "docs" / "experiment_review.md").write_text(body)
    print("Updated docs/experiment_review.md and docs/experiment_results.json from calculated results.")
    return results


if __name__ == "__main__":
    write_experiment_report()
