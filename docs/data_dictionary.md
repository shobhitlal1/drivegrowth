# Data dictionary

All customer-level records are synthetic. Dates are timezone-naive simulated dates/timestamps; USD amounts are nominal.

| Table | Grain / key | Meaning |
|---|---|---|
| `customers` | One registered visitor / `customer_id` | Signup, state, channel, device, vehicle, risk, credit, income and actionable segment |
| `marketing_spend` | Day × channel | Spend, campaign, aggregate impressions and registered visitor clicks |
| `funnel_events` | Customer × milestone | Chronological visit, quote start, completion, carrier match, policy purchase and first renewal |
| `quotes` | One started quote / `quote_id` | Completion timestamp is null when abandoned; premium is annual USD; carrier is recommendation at quote start |
| `policies` | One bound policy / `policy_id` | Annual premium, commission rate, annual carrier expected claims, monthly service cost, cancellation and first-renewal outcomes |
| `carriers` | Carrier / `carrier_id` | Fictional name, available states, commission and synthetic quality/satisfaction assumptions |
| `monthly_customer_value` | Policy × calendar month | Earned commission, premium volume, carrier expected claims, service, onboarding and contribution |
| `customer_facts` | Visitor / `customer_id` | Fan-out-safe joined acquisition mart with daily spend allocation and separate observed/model value |
| `ltv_assumptions` | Channel × risk | Observed exit/exposure estimates and current-snapshot 24-month LTV assumptions |
| `monthly_operating_performance` | Month × state × channel × carrier × segment | Active-book calendar financial aggregates |

## Metric contract

| Metric | Numerator / definition | Denominator / scope |
|---|---|---|
| Customers / traffic | Registered website visitors | Selected signup months; not all anonymous web sessions |
| Quote-start rate | Started quotes | Registered visitors |
| Quote-completion rate | Completed quotes | Started quotes |
| Carrier-match rate | Matched customers | Completed quotes |
| Quote → policy | Policies purchased | Started quotes |
| Visit → policy | Policies purchased | Registered visitors |
| CAC / policy CPA | Acquisition spend | Purchased policies in signup cohort |
| Revenue | Earned commission | Active policies in selected calendar months; excludes premium volume |
| Contribution margin | Commission − service − onboarding | Active policies in selected months; before acquisition spend |
| Modeled 24mo LTV | Discounted expected 24-month contribution − onboarding | Per acquired policy, channel/risk scenario |
| LTV/CAC | Policy-weighted modeled LTV | Acquisition cost per purchased policy |
| Renewal rate | Policies renewing at first anniversary | Policies surviving until anniversary during reporting period |
| 30/60/90/180/365-day retention | Policies still active strictly beyond the horizon | All original policies old enough to reach that horizon |
| Expected carrier loss ratio | Annual expected claim cost | Annual premium; not deducted from marketplace commission |
| Blended revenue/spend | Active-book earned commission | Current acquisition spend; not causal advertising ROAS |

Zero denominators return missing, rendered as an em dash. Customer counts are not policy counts. Missing renewal outcomes on immature policies are not failures. Monthly ledger contributions reconcile to rounded commission minus rounded service minus onboarding. A cancellation on date D ends coverage before D; a renewal failure at day 365 is not retained at the 365-day horizon.

The historical dashboard does not expose validated predictive LTV, payback, causal ROAS or optimized allocations. The Experiments section now exposes randomized treatment comparisons and modeled rollout economics in a separate trial ledger.

## Experiment tables

| Table | Grain | Purpose |
|---|---|---|
| `experiments` | Experiment × unique randomized unit | Pre-exposure assignment, covariates, fixed-window outcomes, costs and modeled value |
| `experiment_registry` | Experiment | Hypothesis, population, dates, primary metric, sample plan, guardrails, tolerances and rollout costs |
| `experiment_value_assumptions` | Experiment × channel × risk | 12-month contribution assumptions estimated from historical records before test enrollment |
| `experiment_arm_summary` | Experiment × arm | Assignment/maturity denominators, conversions, referral activity and unit economics |
| `experiment_daily_results` | Experiment × assignment date × arm | Mature fixed-window cumulative results, reconstructed at final snapshot |

`unit_id` is the independent randomized identity; historical customer identities are not reused. `policy_purchased` means a bound policy for quote/ranking units and a rewarded referred policy for referral-member units. `quote_completed` and `carrier_matched` are not instrumented for the referral trial and are missing there. `referral_sent` is applicable to the referral trial. Outcomes are missing until `outcome_window_end`; immaturity is never encoded as failure.

`premium` is annual premium volume per assigned unit, zero for non-converters. `observed_contribution_30d` is simulated 30-day marketplace contribution before referral incentives, with servicing and onboarding included. `modeled_policy_value_12m` is future 12-month pre-incentive contribution, zero for non-converters, incorporating early-cancellation assumptions. `net_value_12m = modeled_policy_value_12m − incentive_cost − variable_cost`. Fixed rollout costs are applied at scenario level, not repeated per unit.

Absolute lift is treatment minus control; percentage-point display multiplies by 100. Relative lift divides the absolute effect by control and is undefined at zero baseline. Annualized modeled contribution values twelve monthly acquisition cohorts, each over twelve policy months; it is not recognized first-year revenue. Guardrail harm, sample sufficiency, primary evidence and financial uncertainty independently affect the recommendation. Full definitions are in [experimentation.md](experimentation.md).
