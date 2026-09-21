"""Generate a linked, censored synthetic marketplace with a fixed seed.

Run: python -m src.generate_data [--customers 500000] [--seed 20260921]
Customers represent registered website visitors, not ad impressions or policyholders.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import (
    RAW_DIR, SEED, N_CUSTOMERS, START_DATE, END_DATE, CHANNELS, CHANNEL_WEIGHTS,
    STATES, STATE_WEIGHTS, STATE_PREMIUM, CHANNEL_COST, START_RATE,
    COMPLETE_RATE, PURCHASE_RATE, MONTHLY_CHURN, RENEWAL_PROBABILITY, CARRIER_NAMES,
)


def generate_data(n: int = N_CUSTOMERS, seed: int = SEED,
                  output: Path = RAW_DIR) -> dict[str, int]:
    """Write Parquet source tables. All randomness uses one seeded generator."""
    if n < 1000:
        raise ValueError("Use at least 1,000 customers to populate all dimensions.")
    output.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    counts: dict[str, int] = {}

    def save(name: str, frame: pd.DataFrame) -> None:
        frame.to_parquet(output / f"{name}.parquet", index=False, compression="zstd")
        counts[name] = len(frame)
        print(f"  {name:26} {len(frame):>12,}", flush=True)

    cutoff = pd.Timestamp(END_DATE)
    days = pd.date_range(START_DATE, cutoff - pd.Timedelta(days=7))
    # Growth plus seasonality: new cohorts get more traffic, not independent dates.
    weights = np.linspace(.75, 1.30, len(days)) * (1 + .08 * np.sin(np.arange(len(days)) / 58))
    signup = pd.DatetimeIndex(rng.choice(days, n, p=weights / weights.sum()))
    ci = rng.choice(len(CHANNELS), n, p=CHANNEL_WEIGHTS)
    si = rng.choice(len(STATES), n, p=STATE_WEIGHTS)
    age = np.clip(rng.normal(38, 12, n).round(), 18, 78).astype("int16")
    age = np.where(ci == 6, np.maximum(18, age - 7), age)
    risk_score = rng.normal(size=n) + (age < 25) * .9 + np.isin(ci, [1, 6, 7]) * .40
    risk = np.select([risk_score > .9, risk_score > -.5], [2, 1], default=0)
    risk_label = np.array(["Low", "Standard", "High"])[risk]
    vehicle_age = np.clip(rng.gamma(3, 2.3, n), 0, 22).round().astype("int16")
    vehicle_value = np.round(np.clip(42000 * np.exp(-vehicle_age / 10) * rng.lognormal(0, .26, n), 3500, 85000), -2)
    mobile = rng.random(n) < np.where(np.isin(ci, [1, 6]), .88, .64)
    device = np.where(mobile, "Mobile", "Desktop")
    ids = np.arange(1, n + 1, dtype="int64")
    recent = np.asarray(signup >= "2026-04-01")
    segment = np.select(
        [risk == 2, ci == 4, np.isin(ci, [1, 6]), ci == 0, risk == 0],
        ["High-risk shoppers", "Referral customers", "Social-led shoppers", "High-intent search", "Low-risk households"],
        default="Everyday comparison shoppers",
    )
    customers = pd.DataFrame({
        "customer_id": ids, "signup_date": signup, "age": age,
        "state": np.array(STATES)[si], "vehicle_age": vehicle_age,
        "vehicle_value": vehicle_value,
        "credit_band": np.where(risk == 2, "Fair", np.where(risk == 0, "Excellent", "Good")),
        "risk_segment": risk_label, "acquisition_channel": np.array(CHANNELS)[ci],
        "device_type": device,
        "income_band": np.where(vehicle_value > 29000, "$100k+", np.where(vehicle_value > 15000, "$50k–100k", "Under $50k")),
        "customer_segment": segment,
    })
    save("customers", customers)

    carriers = pd.DataFrame({
        "carrier_id": np.arange(1, 6), "carrier_name": CARRIER_NAMES,
        "states_available": [",".join(STATES)] * 5,
        "commission_rate": [.155, .145, .165, .135, .16],
        "conversion_quality_score": [.86, .91, .82, .79, .88],
        "customer_satisfaction_score": [4.3, 4.6, 4.1, 3.9, 4.4],
    })
    save("carriers", carriers)
    carrier_idx = rng.choice(5, n, p=[.24, .22, .20, .17, .17])
    # Summit receives more high-risk shoppers, Juniper favors low-risk western traffic.
    carrier_idx = np.where((risk == 2) & (rng.random(n) < .32), 3, carrier_idx)
    carrier_idx = np.where((risk == 0) & np.isin(si, [0, 11]) & (rng.random(n) < .4), 1, carrier_idx)
    quoted_premium = np.round(
        1330 * np.array(STATE_PREMIUM)[si] * (1 + .33 * risk)
        * (1 + .26 * (age < 25)) * (0.82 + vehicle_value / 95000)
        * np.array([1, .98, 1.07, .91, 1.02])[carrier_idx]
        * rng.lognormal(0, .13, n), 2,
    )
    started = rng.random(n) < np.clip(np.array(START_RATE)[ci] - .035 * (risk == 2) + .012 * recent, 0, 1)
    completed = started & (rng.random(n) < np.clip(
        np.array(COMPLETE_RATE)[ci] - .115 * mobile - .045 * (risk == 2) + .022 * recent, 0, 1))
    matched = completed & (rng.random(n) < np.clip(
        .94 - .11 * (risk == 2) + .025 * (carrier_idx == 1) - .035 * ((si == 2) & (risk == 2)), 0, 1))
    purchased = matched & (rng.random(n) < np.clip(
        np.array(PURCHASE_RATE)[ci] - .045 * (risk == 2) - .025 * (si == 2)
        + .035 * (carrier_idx == 1) - .035 * (carrier_idx == 3), 0, 1))
    start_time = signup + pd.to_timedelta(rng.integers(8 * 60, 19 * 60, n), unit="m")
    completed_time = start_time + pd.to_timedelta(rng.integers(4, 22, n), unit="m")
    matched_time = completed_time + pd.Timedelta(minutes=1)
    purchase_time = matched_time + pd.to_timedelta(rng.integers(1, 7, n), unit="D")
    quote_ids = ids[started]
    quotes = pd.DataFrame({
        "quote_id": quote_ids, "customer_id": quote_ids,
        "quote_start_date": start_time[started],
        "quote_completion_date": pd.Series(completed_time).where(completed)[started].to_numpy(),
        "quoted_premium": np.where(completed[started], quoted_premium[started], np.nan),
        "carrier_id": carrier_idx[started] + 1, "carrier_matched": matched[started],
    })
    save("quotes", quotes)

    pi = np.flatnonzero(purchased)
    pn = len(pi)
    policy_start = purchase_time[pi].normalize()
    churn = np.clip(np.array(MONTHLY_CHURN)[ci[pi]] + .012 * (risk[pi] == 2) - .003 * (risk[pi] == 0), .003, .1)
    # Continuous cancellation and an additional discrete annual renewal decision.
    renewal_prob = np.clip(np.array(RENEWAL_PROBABILITY)[ci[pi]] - .10 * (risk[pi] == 2) + .025 * (carrier_idx[pi] == 1), 0, 1)
    renew_choice = rng.random(pn) < renewal_prob
    # Convert monthly survival to the mean continuous lifetime in days.
    days_until_exit = np.maximum(1, np.ceil(rng.exponential(30.4375 / -np.log1p(-churn), pn))).astype(int)
    days_until_exit = np.where(renew_choice, days_until_exit, np.minimum(days_until_exit, 365))
    exit_date = policy_start + pd.to_timedelta(days_until_exit, unit="D")
    observed_exit = pd.Series(exit_date).where(exit_date <= cutoff)
    renewal_eligible = ((policy_start + pd.Timedelta(days=365)) <= cutoff) & (days_until_exit >= 365)
    renewed = renewal_eligible & (days_until_exit > 365)
    commissions = np.array(carriers.commission_rate)[carrier_idx[pi]] - .028 * (risk[pi] == 2)
    service_cost = 3.6 + 3.4 * risk[pi] + .5 * (mobile[pi])
    claims = np.round(quoted_premium[pi] * np.array([.51, .68, .94])[risk[pi]], 2)
    policies = pd.DataFrame({
        "policy_id": np.arange(1, pn + 1), "customer_id": ids[pi],
        "carrier_id": carrier_idx[pi] + 1, "policy_start": policy_start,
        "premium": quoted_premium[pi], "commission_rate": commissions,
        "expected_claim_cost": claims, "monthly_service_cost": service_cost,
        "policy_status": np.where(exit_date <= cutoff, "Cancelled", "Active"),
        "renewal_eligible": renewal_eligible, "renewed": renewed,
        "cancellation_date": observed_exit.to_numpy(),
    })
    save("policies", policies)

    events = []
    for kind, mask, times in [
        ("website_visit", np.ones(n, dtype=bool), start_time - pd.Timedelta(minutes=3)),
        ("quote_started", started, start_time), ("quote_completed", completed, completed_time),
        ("carrier_matched", matched, matched_time), ("policy_purchased", purchased, purchase_time),
    ]:
        events.append(pd.DataFrame({"customer_id": ids[mask], "event_timestamp": times[mask],
                                    "event_type": kind, "device_type": device[mask],
                                    "session_id": ids[mask] * 10 + int(kind == "policy_purchased")}))
    events.append(pd.DataFrame({"customer_id": ids[pi][renewed],
                               "event_timestamp": policy_start[renewed] + pd.Timedelta(days=365),
                               "event_type": "policy_renewed", "device_type": device[pi][renewed],
                               "session_id": ids[pi][renewed] * 10 + 2}))
    save("funnel_events", pd.concat(events, ignore_index=True))

    spend = customers.groupby(["signup_date", "acquisition_channel"]).size().rename("clicks").reset_index()
    spend.columns = ["date", "channel", "clicks"]
    cost_map = dict(zip(CHANNELS, CHANNEL_COST))
    time_factor = 1 + .13 * ((spend.date - pd.Timestamp(START_DATE)).dt.days / 730)
    spend["spend"] = (spend.clicks * spend.channel.map(cost_map) * time_factor * rng.lognormal(0, .09, len(spend))).round(2)
    spend["impressions"] = np.ceil(spend.clicks / np.where(spend.channel.isin(["Meta Ads", "TikTok / Social"]), .015, .052)).astype(int)
    spend["campaign"] = spend.channel.str.lower().str.replace(" ", "_") + "_always_on"
    save("marketing_spend", spend)

    # Calendar-month ledger; prorate the first/last coverage months by covered days.
    ledgers = []
    for month in pd.date_range(pd.Timestamp(START_DATE).replace(day=1), cutoff, freq="MS"):
        next_month = month + pd.offsets.MonthBegin(1)
        active = (policy_start < next_month) & (exit_date > month)
        loc = np.flatnonzero(active)
        cover_start = np.maximum(policy_start[loc].to_numpy(), month.to_datetime64())
        cover_end = np.minimum(exit_date[loc].to_numpy(), next_month.to_datetime64())
        fraction = (cover_end - cover_start) / np.timedelta64(1, "D") / month.days_in_month
        premium = quoted_premium[pi][loc] / 12 * fraction
        commission = premium * commissions[loc]
        service = service_cost[loc] * fraction
        onboarding = ((policy_start[loc] >= month) & (policy_start[loc] < next_month)).astype(int) * 7.5
        ledgers.append(pd.DataFrame({
            "customer_id": ids[pi][loc], "policy_id": loc + 1, "month": month,
            "active_month_fraction": fraction,
            "premium_volume": premium.round(2), "commission_revenue": commission.round(2),
            "expected_claim_cost": (claims[loc] / 12 * fraction).round(2),
            "service_cost": service.round(2), "onboarding_cost": onboarding,
            "contribution_margin": (commission.round(2) - service.round(2) - onboarding).round(2),
        }))
    save("monthly_customer_value", pd.concat(ledgers, ignore_index=True))
    manifest = {"seed": seed, "customers": n, "as_of": END_DATE,
                "acquisition_start": START_DATE, "acquisition_end": str(days[-1].date()),
                "tables": counts, "synthetic": True, "schema_version": 1}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--customers", type=int, default=N_CUSTOMERS)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    generate_data(args.customers, args.seed)
