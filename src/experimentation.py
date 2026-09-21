"""Fixed-horizon intention-to-treat estimates and transparent rollout rules.

Every row is one independent randomized unit. Never condition primary inference
on completing a quote, sending a referral, purchasing, or another treatment outcome.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import confint_proportions_2indep, proportion_confint, proportions_ztest

from src.experiment_designs import ExperimentDesign, ALPHA, FAMILY_SIZE, POWER, BOOTSTRAP_DRAWS


@dataclass(frozen=True)
class Estimate:
    control_n: int
    treatment_n: int
    control: float
    treatment: float
    difference: float
    relative_lift: float | None
    ci_low: float
    ci_high: float
    p_value: float
    method: str


def _array(values) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("Inference requires at least two finite observations in each arm.")
    return values


def binary_estimate(control, treatment, alpha: float = ALPHA) -> Estimate:
    """Pooled two-proportion z-test; Newcombe/Wilson difference interval.

    Sparse observed cells use Fisher's exact test instead of a fragile normal test.
    All zero/all one arms retain a non-degenerate Newcombe interval and p=1.
    """
    c, t = _array(control), _array(treatment)
    if not np.isin(np.r_[c, t], [0, 1]).all():
        raise ValueError("Conversion observations must be binary.")
    nc, nt, sc, st = len(c), len(t), int(c.sum()), int(t.sum())
    pc, pt = sc / nc, st / nt
    low, high = confint_proportions_2indep(st, nt, sc, nc, method="newcomb", compare="diff", alpha=alpha)
    cells = [sc, nc - sc, st, nt - st]
    if min(cells) < 10:
        p = stats.fisher_exact([[st, nt - st], [sc, nc - sc]]).pvalue
        method = "Fisher exact p-value · Newcombe difference CI"
    else:
        _, p = proportions_ztest([st, sc], [nt, nc], alternative="two-sided")
        method = "Two-proportion z-test · Newcombe difference CI"
    return Estimate(nc, nt, pc, pt, pt - pc, (pt - pc) / pc if pc else None,
                    float(low), float(high), float(p), method)


def welch_estimate(control, treatment, alpha: float = ALPHA) -> Estimate:
    """Difference in means with unequal variances and Welch-Satterthwaite df."""
    c, t = _array(control), _array(treatment)
    diff = float(t.mean() - c.mean())
    vc, vt = c.var(ddof=1) / len(c), t.var(ddof=1) / len(t)
    se = math.sqrt(vc + vt)
    if se == 0:
        p, low, high = (1.0 if diff == 0 else 0.0), diff, diff
    else:
        df = (vc + vt) ** 2 / (vc**2 / (len(c) - 1) + vt**2 / (len(t) - 1))
        p = float(stats.ttest_ind(t, c, equal_var=False).pvalue)
        radius = stats.t.ppf(1 - alpha / 2, df) * se
        low, high = diff - radius, diff + radius
    return Estimate(len(c), len(t), float(c.mean()), float(t.mean()), diff,
                    diff / c.mean() if c.mean() else None, float(low), float(high), p, "Welch unequal-variance t-test")


def bootstrap_differences(control, treatment, draws: int = BOOTSTRAP_DRAWS,
                          seed: int = 314159) -> np.ndarray:
    """Resample whole randomized units within each arm; memory-bounded batches."""
    c, t = _array(control), _array(treatment)
    if draws < 200:
        raise ValueError("Use at least 200 bootstrap resamples.")
    rng = np.random.default_rng(seed)
    result = np.empty(draws)
    for start in range(0, draws, 64):
        n = min(64, draws - start)
        cm = c[rng.integers(0, len(c), (n, len(c)))].mean(axis=1)
        tm = t[rng.integers(0, len(t), (n, len(t)))].mean(axis=1)
        result[start:start + n] = tm - cm
    return result


def financial_estimate(control, treatment, draws: int = BOOTSTRAP_DRAWS,
                       seed: int = 314159) -> tuple[Estimate, np.ndarray]:
    """Welch p-value plus a percentile bootstrap interval for skewed unit values."""
    w = welch_estimate(control, treatment)
    samples = bootstrap_differences(control, treatment, draws, seed)
    low, high = np.quantile(samples, [.025, .975])
    return Estimate(w.control_n, w.treatment_n, w.control, w.treatment, w.difference,
                    w.relative_lift, float(low), float(high), w.p_value,
                    f"{draws:,} unit bootstrap draws (percentile CI) · Welch p-value"), samples


def planned_sample_per_arm(baseline: float, mde: float, alpha: float = ALPHA / FAMILY_SIZE,
                           power: float = POWER) -> int:
    """Normal-approximation two-arm sample plan, specified independently of outcomes."""
    if not 0 < baseline < baseline + mde < 1 or not 0 < alpha < 1 or not 0 < power < 1:
        raise ValueError("Invalid power-planning assumptions.")
    p1, p2 = baseline, baseline + mde
    average = (p1 + p2) / 2
    z_alpha, z_power = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    numerator = z_alpha * math.sqrt(2 * average * (1 - average)) + z_power * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    return math.ceil(numerator**2 / mde**2)


def incremental_policies(control_rate: float, treatment_rate: float, monthly_units: float) -> float:
    if min(control_rate, treatment_rate) < 0 or max(control_rate, treatment_rate) > 1 or monthly_units < 0:
        raise ValueError("Rates must be probabilities and eligible traffic cannot be negative.")
    return (treatment_rate - control_rate) * monthly_units


def financial_impact(control: pd.DataFrame, treatment: pd.DataFrame, monthly_units: float,
                     monthly_cost: float, setup_cost: float, bootstrap_net: np.ndarray,
                     value_multiplier: float = 1.0, bootstrap_gross: np.ndarray | None = None) -> dict:
    """Policy-volume + value-mix decomposition; rewards include baseline converters.

    Annualized value counts 12 new monthly cohorts valued over a 12-month policy
    horizon. It is not recognized first-calendar-year accounting contribution.
    """
    if min(monthly_units, monthly_cost, setup_cost, value_multiplier) < 0:
        raise ValueError("Volume, rollout costs and value multiplier must be nonnegative.")
    pc, pt = control.policy_purchased.mean(), treatment.policy_purchased.mean()
    gc, gt = control.modeled_policy_value_12m.mean(), treatment.modeled_policy_value_12m.mean()
    vc, vt = gc / pc if pc else 0, gt / pt if pt else 0
    policy_lift = incremental_policies(pc, pt, monthly_units)
    volume = policy_lift * vc * value_multiplier
    mix = monthly_units * pt * (vt - vc) * value_multiplier
    incentives = monthly_units * (treatment.incentive_cost.mean() - control.incentive_cost.mean())
    variable = monthly_units * (treatment.variable_cost.mean() - control.variable_cost.mean())
    gross = monthly_units * (gt - gc) * value_multiplier
    monthly = gross - incentives - variable - monthly_cost
    # Paired bootstrap gross/net draws preserve their covariance under sensitivity.
    draws = bootstrap_net.copy()
    if value_multiplier != 1:
        if bootstrap_gross is None:
            raise ValueError("Value sensitivity requires paired gross-value bootstrap draws.")
        draws += (value_multiplier - 1) * bootstrap_gross
    annual_draws = 12 * (draws * monthly_units - monthly_cost) - setup_cost
    low, high = np.quantile(annual_draws, [.025, .975])
    return {"monthly_units": monthly_units, "incremental_policies": policy_lift,
            "control_value_per_policy": vc * value_multiplier, "treatment_value_per_policy": vt * value_multiplier,
            "volume_contribution": volume, "value_mix_contribution": mix,
            "incremental_gross_contribution": gross, "incremental_incentives": incentives,
            "incremental_variable_cost": variable, "monthly_fixed_cost": monthly_cost,
            "monthly_net": monthly, "setup_cost": setup_cost, "annualized_net": 12 * monthly - setup_cost,
            "annual_ci_low": float(low), "annual_ci_high": float(high), "value_multiplier": value_multiplier}


def guardrail_result(control, treatment, direction: str, tolerance: float, family_size: int) -> dict:
    # alpha=.05/2 guards => a 97.5% one-sided safety bound (95% two-sided CI).
    estimate = binary_estimate(control, treatment, alpha=2 * ALPHA / family_size)
    harm_low, harm_high = ((estimate.ci_low, estimate.ci_high) if direction == "lower_good"
                           else (-estimate.ci_high, -estimate.ci_low))
    state = "Pass" if harm_high < tolerance else "Fail" if harm_low > tolerance else "Unclear"
    return {"estimate": estimate, "state": state, "harm_low": harm_low,
            "harm_high": harm_high, "tolerance": tolerance, "direction": direction}


def decide(primary: Estimate, adjusted_p: float, impact: dict, guardrails: list[dict],
           sufficient: bool, data_valid: bool, practical_effect: float) -> dict:
    """Experiment-agnostic decision policy; no branch checks an experiment ID."""
    reasons = []
    if not data_valid:
        return {"recommendation": "CONTINUE TESTING", "reasons": ["Resolve assignment, observation-window or data-quality failures before any rollout decision."]}
    failed = [g["label"] for g in guardrails if g["state"] == "Fail"]
    if failed:
        return {"recommendation": "DO NOT SHIP", "reasons": ["Evidence of guardrail harm beyond tolerance: " + ", ".join(failed) + "."]}
    if primary.ci_high < 0 or impact["annual_ci_high"] < 0:
        return {"recommendation": "DO NOT SHIP", "reasons": ["The interval supports primary-metric harm or negative modeled contribution at these rollout costs."]}
    if not sufficient:
        reasons.append("At least one arm is below the pre-specified sample target.")
    positive = adjusted_p < ALPHA and primary.ci_low > 0
    if not positive:
        reasons.append("The primary improvement does not meet the family-adjusted evidence threshold.")
    if primary.difference < practical_effect:
        reasons.append("The estimated primary lift is below the minimum practically useful effect.")
    if sufficient and positive and primary.difference >= practical_effect and impact["annualized_net"] <= 0:
        return {"recommendation": "DO NOT SHIP", "reasons": ["Conversion evidence is positive, but the best estimate of modeled net contribution does not cover rollout costs. This is an economic decision, not proof that the true effect is negative."]}
    if impact["annual_ci_low"] <= 0:
        reasons.append("The modeled financial interval still includes a non-positive rollout outcome.")
    uncertain = [g["label"] for g in guardrails if g["state"] == "Unclear"]
    if uncertain:
        reasons.append("Safety within tolerance is not established for: " + ", ".join(uncertain) + ".")
    if reasons:
        return {"recommendation": "CONTINUE TESTING", "reasons": reasons}
    return {"recommendation": "SHIP", "reasons": ["Evidence, practical lift, financial downside, guardrails and planned sample size all pass the rollout rules."]}


def segment_effects(frame: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Exploratory treatment-by-segment interaction vs the complementary population.

    BH correction covers all four dimensions together, not just the displayed one.
    Pointwise intervals are descriptive and do not authorize subgroup rollouts.
    """
    records = []
    for dim in ["acquisition_channel", "device_type", "state", "risk_segment"]:
        for name, sub in frame.groupby(dim):
            other = frame[frame[dim] != name]
            c, t = sub.loc[sub.variant == "Control", metric], sub.loc[sub.variant == "Treatment", metric]
            oc, ot = other.loc[other.variant == "Control", metric], other.loc[other.variant == "Treatment", metric]
            if min(len(c), len(t), len(oc), len(ot)) < 2:
                continue
            estimate = binary_estimate(c, t)
            other_effect = ot.mean() - oc.mean()
            variance = sum(x.var(ddof=1) / len(x) for x in [c, t, oc, ot])
            p = float(2 * stats.norm.sf(abs((estimate.difference - other_effect) / math.sqrt(variance)))) if variance else 1.0
            enough = min(len(c), len(t)) >= 200 and min(c.sum(), t.sum(), (1-c).sum(), (1-t).sum()) >= 10
            records.append({"dimension": dim, "segment": name, **asdict(estimate),
                            "interaction_p": p if enough else 1.0, "sufficient": bool(enough)})
    result = pd.DataFrame(records)
    if not result.empty:
        result["interaction_q"] = multipletests(result.interaction_p, method="fdr_bh")[1]
        result["heterogeneous"] = result.sufficient & (result.interaction_q < .05)
    return result
