# Experiment decision review

Snapshot: August 31, 2026. Generated from the current DuckDB experiment ledger.

This project uses synthetically generated customer-level data designed to simulate realistic insurance marketplace behavior. It is not affiliated with or based on proprietary data from any insurance company.

| Experiment | Control → treatment | Lift (pp) | Adjusted p | Annualized modeled contribution | Recommendation |
|---|---|---|---|---|---|
| Shortened Quote Flow | 65.92% → 71.40% | +5.47 | <0.001 | $+1,676,862 | SHIP |
| Referral Incentive | 10.10% → 11.62% | +1.52 | <0.001 | $-206,168 | DO NOT SHIP |
| Carrier Ranking Algorithm | 39.53% → 40.63% | +1.09 | 0.666 | $+1,040,716 | CONTINUE TESTING |

## Shortened Quote Flow · SHIP

**What happened:** 13,894 control and 14,106 treatment units. Quote completion changed by +5.47 percentage points (95% interval +4.39 to +6.56).

**Why it matters:** Evidence, practical lift, financial downside, guardrails and planned sample size all pass the rollout rules.

**Financial impact:** At 30,438 eligible units per month, the model implies +757.3 incremental policies, $+145,981 gross modeled contribution, $0 incremental incentives, $1,826 variable cost and $1,500 monthly fixed cost. Annualized modeled net contribution is $+1,676,862, after $35,000 setup cost; its 95% sampling interval is $+903,570 to $+2,419,022.

**Guardrails:** Policy conversion — Pass (upper harm bound -1.47 pp vs 0.50 pp tolerance); Support contact rate — Pass (upper harm bound 0.62 pp vs 1.20 pp tolerance).

**Sample:** target 4,931 per arm; met. All 7 quality checks pass.

**Where to investigate first:** Mobile has +7.23 pp lift, with interaction q=1.905e-06 versus the remaining population. Confirm the exploratory difference in a pre-specified targeted follow-up before assuming differential economics.

## Referral Incentive · DO NOT SHIP

**What happened:** 19,918 control and 20,082 treatment units. Member → bound referral changed by +1.52 percentage points (95% interval +0.91 to +2.13).

**Why it matters:** Conversion evidence is positive, but the best estimate of modeled net contribution does not cover rollout costs. This is an economic decision, not proof that the true effect is negative.

**Financial impact:** At 43,482 eligible units per month, the model implies +659.2 incremental policies, $+75,514 gross modeled contribution, $88,956 incremental incentives, $1,739 variable cost and $1,000 monthly fixed cost. Annualized modeled net contribution is $-206,168, after $12,000 setup cost; its 95% sampling interval is $-595,390 to $+182,539.

**Guardrails:** Early cancellation / eligible member — Pass (upper harm bound 0.27 pp vs 0.60 pp tolerance); Support contact rate — Pass (upper harm bound 0.36 pp vs 1.00 pp tolerance).

**Sample:** target 13,778 per arm; met. All 7 quality checks pass.

## Carrier Ranking Algorithm · CONTINUE TESTING

**What happened:** 5,962 control and 6,038 treatment units. Quote → bound policy changed by +1.09 percentage points (95% interval -0.66 to +2.84).

**Why it matters:** At least one arm is below the pre-specified sample target. The primary improvement does not meet the family-adjusted evidence threshold. Safety within tolerance is not established for: Support contact rate.

**Financial impact:** At 17,393 eligible units per month, the model implies +190.0 incremental policies, $+99,078 gross modeled contribution, $0 incremental incentives, $2,435 variable cost and $4,500 monthly fixed cost. Annualized modeled net contribution is $+1,040,716, after $65,000 setup cost; its 95% sampling interval is $+258,717 to $+1,858,602.

**Guardrails:** Carrier match rate — Pass (upper harm bound 0.08 pp vs 1.50 pp tolerance); Support contact rate — Unclear (upper harm bound 1.65 pp vs 1.20 pp tolerance).

**Sample:** target 22,468 per arm; not met. All 7 quality checks pass.

## Interpreting the modeled value

Annualization values twelve new acquisition cohorts over twelve policy months each; it is not realized revenue or first-year recognized contribution. Financial intervals cover randomized-unit sampling only. Traffic, policy valuation, retention and cost assumptions remain uncertain. Referral rewards apply to all qualifying conversions. No real-company outcomes are claimed.

See [the experiment methodology](experimentation.md) and [machine-readable decision records](experiment_results.json). The optimizer has not been started.
