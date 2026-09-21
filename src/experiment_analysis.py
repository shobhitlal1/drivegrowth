"""DuckDB-backed experiment reporting, quality gates and reproducible decision records."""
from __future__ import annotations
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from src.config import DB_PATH
from src.database import connect
from src.experiment_designs import ExperimentDesign, Guardrail, ALPHA, FAMILY_SIZE, BOOTSTRAP_DRAWS
from src.experimentation import (binary_estimate, welch_estimate, financial_estimate,
    bootstrap_differences, financial_impact, planned_sample_per_arm, guardrail_result, decide, segment_effects)


def experiment_data(db_path: Path = DB_PATH) -> tuple[list[ExperimentDesign], pd.DataFrame, pd.Timestamp]:
    with connect(db_path) as con:
        registry = con.execute("SELECT * FROM experiment_registry ORDER BY start").fetchdf()
        frame = con.execute("SELECT * FROM experiments ORDER BY experiment_id, unit_id").fetchdf()
        snapshot = pd.Timestamp(con.execute("SELECT as_of FROM metadata").fetchone()[0])
    designs = []
    fields = ExperimentDesign.__dataclass_fields__
    for record in registry.to_dict("records"):
        record["guardrails"] = tuple(Guardrail(**g) for g in json.loads(record["guardrails"]))
        designs.append(ExperimentDesign(**{k: v for k, v in record.items() if k in fields}))
    return designs, frame, snapshot


def quality_checks(frame: pd.DataFrame, design: ExperimentDesign, snapshot: pd.Timestamp) -> list[dict]:
    counts = frame.variant.value_counts()
    nc, nt = int(counts.get("Control", 0)), int(counts.get("Treatment", 0))
    srm_p = float(stats.binomtest(nt, nc + nt, .5).pvalue) if nc + nt else 0.0
    required = [design.primary, "policy_purchased", "observed_contribution_30d", "modeled_policy_value_12m",
                "incentive_cost", "variable_cost", "net_value_12m", *[g.metric for g in design.guardrails]]
    observed = frame.loc[frame.outcome_observed]
    maturity_matches = frame.outcome_observed.eq(frame.outcome_window_end <= snapshot).all()
    expected_end = frame.assigned_date + pd.to_timedelta(design.observation_days, unit="D")
    return [
        {"name": "Unique randomized units", "passed": not frame.unit_id.duplicated().any(), "detail": f"{frame.unit_id.nunique():,} distinct units / {len(frame):,} assignments"},
        {"name": "Valid assignment", "passed": frame.variant.isin(["Control", "Treatment"]).all() and frame.assignment_probability.eq(.5).all(), "detail": "50:50 Bernoulli assignment before exposure"},
        {"name": "Sample-ratio mismatch", "passed": srm_p >= .001, "detail": f"Exact binomial p={srm_p:.4f}; failure threshold 0.001", "p_value": srm_p},
        {"name": "Fixed enrollment window", "passed": frame.assigned_date.between(design.start, design.end).all() and snapshot >= pd.Timestamp(design.end), "detail": f"{design.start} to {design.end}"},
        {"name": "Complete follow-up", "passed": maturity_matches and frame.outcome_window_end.eq(expected_end).all() and frame.outcome_observed.all(), "detail": f"{int(frame.outcome_observed.sum()):,}/{len(frame):,} units have {design.observation_days}-day outcomes"},
        {"name": "No missing mature outcomes", "passed": not observed[required].isna().any().any(), "detail": "Missing mature results block rollout; non-converters remain in the denominator"},
        {"name": "Financial reconciliation", "passed": np.allclose(observed.net_value_12m, observed.modeled_policy_value_12m - observed.incentive_cost - observed.variable_cost, atol=.00001), "detail": "Net unit value = gross policy value − incentives − variable cost"},
    ]


def analyze_experiment(frame: pd.DataFrame, design: ExperimentDesign, snapshot: pd.Timestamp,
                       draws: int = BOOTSTRAP_DRAWS) -> dict:
    frame = frame[frame.experiment_id == design.experiment_id].copy()
    checks = quality_checks(frame, design, snapshot)
    mature = frame[frame.outcome_observed].copy()
    c = mature[mature.variant == "Control"]
    t = mature[mature.variant == "Treatment"]
    primary = binary_estimate(c[design.primary], t[design.primary])
    adjusted_p = min(1.0, primary.p_value * FAMILY_SIZE)
    guardrails = []
    for g in design.guardrails:
        guardrails.append({"label": g.label, "metric": g.metric,
                           **guardrail_result(c[g.metric], t[g.metric], g.direction, g.tolerance, len(design.guardrails))})
    finance, bootstrap_net = financial_estimate(c.net_value_12m, t.net_value_12m, draws, seed=7117)
    # Reusing the seed and arm lengths resamples exactly the same randomized units.
    bootstrap_gross = bootstrap_differences(c.modeled_policy_value_12m, t.modeled_policy_value_12m, draws, seed=7117)
    observed, _ = financial_estimate(c.observed_contribution_30d, t.observed_contribution_30d, draws, seed=9019)
    days = (pd.Timestamp(design.end) - pd.Timestamp(design.start)).days + 1
    monthly_units = len(frame) / days * 30.4375
    impact = financial_impact(c, t, monthly_units, design.monthly_cost, design.setup_cost,
                              bootstrap_net, bootstrap_gross=bootstrap_gross)
    target = planned_sample_per_arm(design.planning_rate, design.mde)
    sufficient = min(len(c), len(t)) >= target
    valid = all(check["passed"] for check in checks)
    decision = decide(primary, adjusted_p, impact, guardrails, sufficient, valid, design.practical_effect)
    secondary = {}
    labels = {"policy_purchased": "Policy conversion", "carrier_matched": "Carrier match",
              "referral_sent": "Referral invitation sent", "quote_completed": "Quote completion"}
    columns = ["referral_sent"] if design.experiment_id == "referral" else ["quote_completed", "carrier_matched", "policy_purchased"]
    for col in columns:
        if col != design.primary:
            secondary[labels[col]] = binary_estimate(c[col], t[col])
    fingerprint = hashlib.sha256(pd.util.hash_pandas_object(frame, index=False).values.tobytes()).hexdigest()
    return {"design": design, "frame": mature, "control": c, "treatment": t,
            "primary": primary, "adjusted_p": adjusted_p, "guardrails": guardrails,
            "finance": finance, "observed_finance": observed,
            "premium": welch_estimate(c.premium, t.premium), "secondary": secondary,
            "impact": impact, "bootstrap_net": bootstrap_net, "bootstrap_gross": bootstrap_gross,
            "segments": segment_effects(mature, design.primary), "quality": checks,
            "target_per_arm": target, "sufficient": sufficient, "data_valid": valid,
            "decision": decision, "snapshot": str(snapshot.date()), "fingerprint": fingerprint,
            "status": "Analysis ready" if valid else "Follow-up / quality review",
            "assigned": len(frame), "mature": len(mature)}


def portfolio(db_path: Path = DB_PATH, draws: int = BOOTSTRAP_DRAWS) -> list[dict]:
    designs, frame, snapshot = experiment_data(db_path)
    return [analyze_experiment(frame, design, snapshot, draws) for design in designs]


def scenario(result: dict, monthly_units: float, value_multiplier: float, monthly_cost: float, setup_cost: float) -> dict:
    impact = financial_impact(result["control"], result["treatment"], monthly_units, monthly_cost,
                               setup_cost, result["bootstrap_net"], value_multiplier, result["bootstrap_gross"])
    decision = decide(result["primary"], result["adjusted_p"], impact, result["guardrails"],
                      result["sufficient"], result["data_valid"], result["design"].practical_effect)
    return {"impact": impact, "decision": decision}


def decision_record(result: dict) -> dict:
    """Portable auditable export; no bootstrap arrays or private local paths."""
    return {"experiment": result["design"].record(), "snapshot": result["snapshot"],
            "data_fingerprint_sha256": result["fingerprint"], "status": result["status"],
            "assigned": result["assigned"], "mature": result["mature"],
            "primary": asdict(result["primary"]), "primary_family_adjusted_p": result["adjusted_p"],
            "sample_target_per_arm": result["target_per_arm"], "sample_sufficient": result["sufficient"],
            "guardrails": [{**g, "estimate": asdict(g["estimate"])} for g in result["guardrails"]],
            "financial_estimate": asdict(result["finance"]), "impact": result["impact"],
            "segment_estimates": result["segments"].to_dict("records"),
            "decision": result["decision"], "quality_checks": result["quality"],
            "methodology": {"primary_family": FAMILY_SIZE, "family_alpha": ALPHA,
                            "primary_adjustment": "Bonferroni across three pre-specified primary hypotheses",
                            "guardrail_adjustment": "Bonferroni one-sided noninferiority bounds within experiment",
                            "segment_adjustment": "BH across all four exploratory dimensions",
                            "annualization": "12 acquisition cohorts, each valued over 12 policy months; not first-year recognized revenue",
                            "uncertainty": "Sampling only; excludes uncertainty in traffic, policy valuation and rollout costs"}}


def json_default(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Cannot serialize {type(value)}")


if __name__ == "__main__":
    from src.config import ROOT
    results = portfolio()
    output = ROOT / "docs" / "experiment_results.json"
    output.write_text(json.dumps([decision_record(r) for r in results], default=json_default, indent=2) + "\n")
    for r in results:
        p, impact = r["primary"], r["impact"]
        print(f"{r['design'].name}: {p.control:.2%} → {p.treatment:.2%}; adjusted p={r['adjusted_p']:.5f}; "
              f"annualized ${impact['annualized_net']:,.0f} [${impact['annual_ci_low']:,.0f}, ${impact['annual_ci_high']:,.0f}]; {r['decision']['recommendation']}")
        print("  " + " ".join(r["decision"]["reasons"]))
