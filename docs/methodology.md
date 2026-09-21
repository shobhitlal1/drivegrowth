# Methodology · historical operating book and experiment workspace

All relationships below are simulation assumptions, not empirical insurance-market estimates.
Fixed seed: `20260921`. Coverage: September 2024–August 2026. Snapshot: August 31, 2026.
The last seven acquisition days are withheld to observe every policy decision; July is the last complete selectable acquisition month.

## Generative process

1. Draw 500,000 registered visitors over a growing, seasonal daily arrival curve across eight channels and twelve states.
2. Condition age and device on channel. Derive risk from a latent score correlated with younger age and social/comparison acquisition. Derive vehicle value from age and lognormal variation.
3. Draw a nested funnel: visit → quote start → quote completion → match → purchase. Later events require all earlier events. Mobile completion has an 11.5-point structural penalty; risk, state, carrier, and recent-cohort effects also influence conversion.
4. Route quotes to five fictional carriers. Routing depends on risk and state; carrier choice influences premium and purchase probability.
5. Compute annual premiums using state, age, risk, vehicle value, carrier and noise. Higher risk reduces commission rate and raises service cost. Expected claims are a separate carrier-level economic estimate.
6. Simulate continuous cancellation using monthly survival and an extra discrete renewal decision at 365 days. Referral survival is stronger; social/comparison survival is weaker. Only exits observed by the snapshot are exposed in source data.
7. Prorate premium volume, commissions and service costs by active days in each calendar month. Apply $7.50 onboarding once. Keep cents-consistent ledger identities.

Acquisition costs per registered visitor are configured in `src/config.py`: Search $25; Meta $7; Affiliate $15; Organic $8; Referral $9.50; Direct $6.50; TikTok $4.50; Comparison $18. Time inflation and daily lognormal variation modify those base assumptions. Organic, direct and referral include program/content/brand costs; none are treated as free. Referral costs incorporate program incentives as aggregate acquisition spend, rather than deducting them again from operating margin. Impressions are anonymous aggregate exposures, not invented identified customer events.

The generator was calibrated once during this checkpoint after the first run revealed implausibly low acquisition-cost assumptions. Published screenshots, reports and the database use the final configuration above. These figures are illustrative inputs, not external benchmarks.

## LTV scenario

Estimate exit intensity as observed cancellations / total policy exposure months for each channel × risk cell, including nonrenewals. Right-censor exposure at the snapshot. Set monthly survival `s = exp(-exit intensity)` and monthly contribution `m = sum(commission − service) / sum(active-month fractions)`.

`LTV_24 = Σ[t=0..23] m × s^t / 1.08^(t/12) − 7.50`

This approximates 24 months of contribution for a newly acquired policy. It does not include acquisition costs. The full snapshot supplies these descriptive assumptions even when viewing earlier acquisition cohorts; this is not a point-in-time backtest. Constant survival smooths the annual renewal discontinuity. It does not establish predictive accuracy, causal lift, or diminishing returns. A held-out predictive model belongs in the next phase.

## Attribution and comparisons

CAC uses all modeled acquisition costs divided by purchased policies in a signup cohort. A filtered state/carrier/segment receives daily channel spend in proportion to its visitor count. This allocation conserves total spend but does not establish the actual marginal cost of acquiring that segment.

Carrier filters select the recommendation at quote start, excluding visitors with no quote. Segment rules prioritize high risk, then referral, social, high-intent search, low-risk households and a residual comparison segment. These descriptive labels do not establish causal segment effects.

Financial KPIs include all active policies in reporting months; acquisition KPIs use signup cohorts. They answer different operating questions and are labeled accordingly. Prior comparisons cover the same number of calendar months, without seasonal adjustment. Renewal rate is conditional on reaching the renewal anniversary; 365-day retention in SQL includes earlier cancellations.

## Limitations

One registered visitor, one quote, one carrier recommendation and at most one policy per customer; no multi-touch attribution, repeat shopping, observed claim settlements, or second renewal. All carriers support all simulated states. Credit and income bands are simplified synthetic correlates. No real customer data, production integration, or real-world business impact is claimed. Source volume is deliberately below a distributed-systems workload; local DuckDB is sufficient.

## Experiment workspace · checkpoint 02

The experiment workspace adds separate randomized trial cohorts and preserves the historical overview's layout. It uses intention-to-treat denominators, fixed follow-up, multiplicity-adjusted primary tests, explicit guardrail noninferiority bounds, randomized-unit bootstrap intervals, and a financial bridge including incentives on baseline converters. All displayed decisions are derived from calculated data and registered thresholds.

Read [the experiment design and decision methodology](experimentation.md) and the [generated experiment review](experiment_review.md). The original operating dataset and the experimental trial population are separate simulations; trial effects are not retroactively added to historical revenue. The historical chart is smoother because it aggregates earned revenue across the active book. Experiment data adds day-level variation, temporary deterioration, segment differences and uncertain/mixed outcomes without cosmetically altering the historical ledger.
