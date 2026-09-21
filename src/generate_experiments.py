"""Reproducible independent synthetic trial cohorts with pre-exposure assignment.

These separate trial ledgers do not rewrite the historical acquisition book.
Profile distributions and value assumptions use only records before each test.
Run after generating core data: python -m src.generate_experiments
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from src.config import RAW_DIR, END_DATE
from src.experiment_designs import DESIGNS, EXPERIMENT_SEED

SOURCE_TABLES = ["customers", "policies", "monthly_customer_value"]


def source_fingerprints(raw_dir: Path) -> dict[str, str]:
    return {name: hashlib.sha256((raw_dir / f"{name}.parquet").read_bytes()).hexdigest()
            for name in SOURCE_TABLES}


def historical_inputs(raw_dir: Path, before: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Derive economics using only exposure and ledger information before enrollment."""
    # A seeded row sampler also requires a stable source order and reduction order.
    with duckdb.connect(config={"threads": 1}) as con:
        for table in SOURCE_TABLES:
            con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_parquet(?)", [str(raw_dir / f"{table}.parquet")])
        # Value uses full months ending before the study starts; no future exits.
        cutoff = pd.Timestamp(before).replace(day=1)
        values = con.execute("""
            WITH exposure AS (
                SELECT c.acquisition_channel, c.risk_segment,
                       sum(CASE WHEN p.cancellation_date < ? THEN 1 ELSE 0 END) AS exits,
                       sum(date_diff('day', p.policy_start, least(coalesce(p.cancellation_date, ?), ?))) / 30.4375 AS months
                FROM policies p JOIN customers c USING(customer_id)
                WHERE p.policy_start < ? GROUP BY 1, 2
            ), margin AS (
                SELECT c.acquisition_channel, c.risk_segment,
                       sum(v.commission_revenue - v.service_cost) / nullif(sum(v.active_month_fraction), 0) AS monthly_margin
                FROM monthly_customer_value v JOIN customers c USING(customer_id)
                WHERE v.month < ? GROUP BY 1, 2
            ), combined AS (
                SELECT *, exp(-exits / nullif(months, 0)) AS survival
                FROM exposure JOIN margin USING(acquisition_channel, risk_segment)
            )
            SELECT acquisition_channel, risk_segment, monthly_margin,
                   monthly_margin * (1 - power(survival / power(1.08, 1.0/12), 12)) /
                   nullif(1 - survival / power(1.08, 1.0/12), 0) - 7.5 AS value_12m
            FROM combined ORDER BY acquisition_channel, risk_segment
        """, [cutoff] * 5).fetchdf()
        profiles = con.execute("""
            SELECT c.acquisition_channel, c.device_type, c.state, c.risk_segment,
                   p.policy_id IS NOT NULL AND (p.cancellation_date IS NULL OR p.cancellation_date >= ?) AS existing_member
            FROM customers c LEFT JOIN policies p ON c.customer_id = p.customer_id AND p.policy_start < ?
            WHERE c.signup_date < ? - INTERVAL 7 DAY
            ORDER BY c.customer_id
        """, [cutoff] * 3).fetchdf()
    return profiles, values


def generate_experiments(raw_dir: Path = RAW_DIR, seed: int = EXPERIMENT_SEED,
                         scale: float = 1.0) -> dict:
    if not 0 < scale <= 1:
        raise ValueError("scale must be in (0, 1].")
    frames, registry, value_tables = [], [], []
    for ix, design in enumerate(DESIGNS):
        rng = np.random.default_rng(seed + ix * 1009)
        profiles, values = historical_inputs(raw_dir, design.start)
        profiles = profiles[profiles.existing_member if design.experiment_id == "referral" else ~profiles.existing_member]
        n = max(200, int(design.sample * scale))
        # Donor profiles describe covariate distributions, not reused identities.
        frame = profiles.iloc[rng.integers(0, len(profiles), n)].drop(columns="existing_member").reset_index(drop=True)
        frame = frame.merge(values, on=["acquisition_channel", "risk_segment"], how="left", validate="many_to_one")
        if frame.value_12m.isna().any():
            raise ValueError("Insufficient pre-test history to value all experiment profiles.")
        days = pd.date_range(design.start, design.end)
        # Weekday traffic and a measured enrollment ramp, with genuine day-to-day variation.
        weights = np.where(days.dayofweek < 5, 1.12, .73) * rng.lognormal(0, .16, len(days))
        frame["assigned_date"] = rng.choice(days, n, p=weights / weights.sum())
        treatment = rng.random(n) < .5  # fixed 50:50 Bernoulli assignment, independent of outcomes
        frame["variant"] = np.where(treatment, "Treatment", "Control")
        frame["unit_id"] = [f"{design.experiment_id}:{i:07d}" for i in range(n)]
        frame["experiment_id"] = design.experiment_id
        frame["assignment_probability"] = .5
        frame["outcome_window_end"] = frame.assigned_date + pd.Timedelta(days=design.observation_days)
        frame["outcome_observed"] = frame.outcome_window_end <= pd.Timestamp(END_DATE)
        mobile = frame.device_type.eq("Mobile").to_numpy()
        high_risk = frame.risk_segment.eq("High").to_numpy()
        low_risk = frame.risk_segment.eq("Low").to_numpy()
        social = frame.acquisition_channel.isin(["Meta Ads", "TikTok / Social"]).to_numpy()
        progress = (frame.assigned_date - pd.Timestamp(design.start)).dt.days.to_numpy()
        daily_noise = rng.normal(0, .012, len(days))[progress]
        weekend = (frame.assigned_date.dt.dayofweek >= 5).to_numpy()
        common = daily_noise - .015 * weekend - .03 * high_risk
        sent = np.zeros(n, dtype=bool)
        if design.experiment_id == "quote_flow":
            completion_p = .79 - .135 * mobile - .05 * social + common
            completion_p += treatment * np.where(mobile, .075, .006)
            # A temporary performance regression affects both arms mid-enrollment.
            completion_p -= .035 * ((progress >= 13) & (progress <= 16))
            completed = rng.random(n) < np.clip(completion_p, .01, .99)
            matched = completed & (rng.random(n) < .94 - .07 * high_risk)
            bought = matched & (rng.random(n) < .43 - .06 * social - .03 * high_risk)
            support_p = .027 + .012 * high_risk + treatment * (.001 + .003 * high_risk)
            incentive = np.zeros(n)
            variable = treatment.astype(float) * .06
            mix_factor = np.ones(n)
        elif design.experiment_id == "referral":
            sent = rng.random(n) < np.clip(.39 + treatment * .043 + .025 * low_risk + common, .01, .99)
            bought = sent & (rng.random(n) < .27 + treatment * .002 - .025 * high_risk)
            completed = sent
            matched = sent
            support_p = .017 + .01 * high_risk + treatment * .001
            incentive = bought * np.where(treatment, 35.0, 20.0)
            variable = treatment.astype(float) * .04
            # Referral policy economics are valued at a conservative share of member profiles.
            mix_factor = np.full(n, .70)
        else:
            completed = np.ones(n, dtype=bool)
            matched = rng.random(n) < np.clip(.925 - .065 * high_risk + treatment * .007 + daily_noise, .01, .99)
            bought = matched & (rng.random(n) < np.clip(.44 - .04 * high_risk + treatment * (.015 - .025 * high_risk) + daily_noise, .01, .99))
            support_p = .029 + .012 * high_risk + treatment * (.003 + .016 * high_risk)
            incentive = np.zeros(n)
            variable = treatment.astype(float) * .14
            mix_factor = 1 + treatment * (.06 - .07 * high_risk)
        support = rng.random(n) < support_p
        early_cancel = bought & (rng.random(n) < .045 + .025 * high_risk + treatment * .003)
        # Right-skewed policy values, with zero value for non-converters.
        value_per_policy = frame.value_12m.to_numpy() * mix_factor * rng.lognormal(-.5 * .55**2, .55, n)
        projected_cm = bought * value_per_policy * np.where(early_cancel, .12, 1)
        observed_cm = bought * (frame.monthly_margin.to_numpy() * rng.lognormal(-.5 * .4**2, .4, n) * np.where(early_cancel, .4, 1) - 7.5)
        frame["quote_completed"] = completed.astype(int)
        frame["carrier_matched"] = matched.astype(int)
        if design.experiment_id == "referral":
            # The referral trial does not instrument a member's own quote workflow.
            frame[["quote_completed", "carrier_matched"]] = np.nan
        frame["policy_purchased"] = bought.astype(int)
        frame["referral_sent"] = sent.astype(int)
        frame["support_contact"] = support.astype(int)
        frame["early_cancel"] = early_cancel.astype(int)
        frame["premium"] = (bought * rng.lognormal(np.log(1950 + 430 * high_risk), .28, n)).round(2)
        frame["observed_contribution_30d"] = observed_cm.round(2)
        frame["modeled_policy_value_12m"] = projected_cm.round(2)
        frame["incentive_cost"] = incentive.round(2)
        frame["variable_cost"] = variable.round(2)
        frame["net_value_12m"] = (frame.modeled_policy_value_12m - frame.incentive_cost - frame.variable_cost).round(2)
        # Store immature outcomes as missing, not as observed failures.
        outcome_columns = ["quote_completed", "carrier_matched", "policy_purchased", "referral_sent",
                           "support_contact", "early_cancel", "premium", "observed_contribution_30d",
                           "modeled_policy_value_12m", "incentive_cost", "variable_cost", "net_value_12m"]
        frame.loc[~frame.outcome_observed, outcome_columns] = np.nan
        frames.append(frame.drop(columns=["value_12m", "monthly_margin"]))
        row = design.record()
        row["guardrails"] = json.dumps(row["guardrails"])
        row["seed"] = seed + ix * 1009
        registry.append(row)
        value_tables.append(values.assign(experiment_id=design.experiment_id, fit_before=pd.Timestamp(design.start).replace(day=1)))
        print(f"  {design.name:30} {n:>8,} randomized units", flush=True)
    pd.concat(frames, ignore_index=True).to_parquet(raw_dir / "experiments.parquet", index=False, compression="zstd")
    pd.DataFrame(registry).to_parquet(raw_dir / "experiment_registry.parquet", index=False)
    pd.concat(value_tables, ignore_index=True).to_parquet(raw_dir / "experiment_value_assumptions.parquet", index=False)
    manifest = {"seed": seed, "as_of": END_DATE, "units": sum(len(f) for f in frames), "scale": scale,
                "schema_version": 1, "separate_synthetic_trial_cohorts": True,
                "source_fingerprints": source_fingerprints(raw_dir)}
    (raw_dir / "experiment_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=EXPERIMENT_SEED)
    args = parser.parse_args()
    generate_experiments(seed=args.seed)
