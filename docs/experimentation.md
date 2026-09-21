# From an experiment result to an operating decision

DriveGrowth's experiment workspace answers five questions: what changed, whether the change is useful, whether it pays for itself, where the effect varies, and what evidence could change the decision. The interface keeps the existing executive dashboard's visual language and computed “Signals worth a closer look.”

## Trial design and data provenance

The experiment ledger contains **80,000 independently generated synthetic randomized units** across three separate trials. These are additional simulated trial populations, not revised outcomes for the 500,000 historical acquisition customers. Pre-test source customers supply covariate distributions; their identities are not reused as experimental identities. Trial policy counts must not be added to, or reconciled against, the historical book.

| Trial | Randomization unit and eligibility | Control / treatment | Primary metric | Guardrails |
|---|---|---|---|---|
| Shortened Quote Flow | 28,000 quote starters, assigned before opening the workflow | 8 steps / 5 steps | Completed quote within 30 days, per assigned starter | Policy conversion, support contact |
| Referral Incentive | 40,000 eligible members, assigned before an invitation | $20 / $35 per bound referral policy | Member generates a bound referral policy within 30 days | Early cancellations per eligible member, support contact |
| Carrier Ranking Algorithm | 12,000 completed-quote shoppers, assigned before carrier matching | Existing ordering / conversion and economics ranking | Bound policy within 30 days, per assigned shopper | Carrier matching, support contact |

Assignment is 50:50 Bernoulli randomization. Every mature randomized unit remains in the primary denominator, including zero-outcome units. The referral pilot permits one invite opportunity and at most one rewarded conversion per member. It therefore does not mistake invitees for independent randomized members or ignore within-member clustering; a future multi-referral design would require member-clustered inference.

Enrollment runs May 4–31, June 1–28 and July 6–26, 2026 respectively. At the August 31 snapshot, all registered outcome windows are mature. Enrollment status and follow-up are checked independently of sample adequacy. Carrier ranking is a completed pilot that did not reach its planned sample; “CONTINUE TESTING” means a registered follow-up, not silently extending the old experiment until significance appears.

The generator deliberately includes unequal realized arm sizes, weekday traffic, day-level shocks, a temporary quote-flow degradation affecting both arms, a stronger mobile quote-flow effect, smaller carrier effects, skewed financial values, and referral incentive costs that can offset acquisition lift. These are simulation inputs, never hardcoded analysis outputs. Changing the observations or operating assumptions recomputes the recommendation. No generator branch names a decision.

## Statistical contract

**Primary conversion:** pooled two-proportion z-test with a two-sided p-value. The effect interval uses Newcombe's combination of Wilson score intervals. Sparse cells use Fisher's exact p-value; zero-baseline relative lift remains undefined. Three pre-specified primary hypotheses form one family, with Bonferroni-adjusted p-values and 5% family alpha. Displayed 95% effect intervals are pointwise, not simultaneous. [statsmodels proportion tests](https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.proportions_ztest.html), [difference intervals](https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.confint_proportions_2indep.html).

**Continuous outcomes:** Welch's unequal-variance t-test for differences in randomized-unit means. Financial contribution is zero-inflated and skewed, so its displayed 95% interval is the percentile interval from 3,000 independent within-arm bootstrap resamples of whole randomized units. The p-value is Welch's, not an incorrectly inverted percentile-bootstrap probability. Gross and net value bootstraps use identical sampled indices, retaining their covariance when valuation assumptions change. [SciPy Welch test](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_ind.html).

**Sample sufficiency:** a pre-specified normal-approximation two-proportion power calculation, 80% power and alpha 0.05/3. Planning baselines are 68%, 10% and 40%; detectable effects are 3.0, 1.2 and 1.5 percentage points. Practical decision floors are distinct: 1.5, 0.6 and 0.8 points. Both arms must meet the planned sample for SHIP. Observed post-hoc power is not used.

**Guardrails:** one-sided noninferiority bounds, Bonferroni-adjusted across the two guardrails within each experiment. Harm is a decrease for desirable outcomes and an increase for undesirable outcomes. PASS requires the upper harm bound below tolerance; FAIL requires the lower harm bound above tolerance; otherwise the result is unclear. Non-significance is not evidence of safety. Tolerances are stored with the design before analysis: quote policy decline 0.5 pp and support increase 1.2 pp; referral early-cancellation increase 0.6 pp and support increase 1.0 pp; ranking match decline 1.5 pp and support increase 1.2 pp.

**Heterogeneity:** within-segment randomized comparisons by channel, device, state and risk, followed by an interaction test comparing each segment's treatment effect with its complement. Benjamini–Hochberg correction spans all four dimensions together. At least 200 units per arm and ten successes/failures are required for a flag. These correlated, overlapping comparisons remain exploratory. A significant mobile effect and a non-significant desktop effect alone are not evidence of a difference. No subgroup decision overrides the portfolio policy.

**Timing:** fixed enrollment and a fixed 30-day outcome window. The cumulative chart retrospectively groups final outcomes by assignment date; it is not the information available on those dates. No interim stopping or repeated p-value checks authorize rollout.

## Economics that reconcile

Pre-test channel/risk economics estimate each new policy's **12-month contribution before incentives**, using only policy exposure and monthly ledger data preceding the trial's start month. This uses constant survival, an 8% annual discount rate and the historical service/onboarding assumptions. The trial adds skewed policy-value variation and explicitly models early cancellation. The referral simulation applies a conservative 70% valuation multiplier because invitee economics need not equal member economics. This is a documented model assumption, not a measured retention outcome.

For control C and treatment T, let `p` be policies per randomized unit and `v` be modeled gross contribution per bound policy:

```text
Incremental policies = eligible monthly units × (pT − pC)
Volume contribution  = incremental policies × vC
Value-mix change     = eligible monthly units × pT × (vT − vC)
Gross difference     = volume contribution + value-mix change
Incentive difference = eligible monthly units × (mean rewardT − mean rewardC)
Monthly cohort net  = gross difference − incentive difference
                    − variable delivery cost − recurring rollout cost
Annualized model    = 12 × monthly cohort net − one-time setup cost
```

The financial decomposition reconciles exactly to the difference in mean net modeled value per randomized unit. Conditional per-policy averages appear only in this accounting bridge; they are not used as causal treatment-effect estimators. The causal comparison retains all randomized units.

The higher reward is paid on **all qualifying treatment referrals**, including referrals that would have happened under control. The model therefore deducts both the reward increase on baseline converters and the cost of incremental referrals. It assumes no clawback after early cancellation.

Default eligible monthly volume equals observed enrollment / enrollment days × 30.4375; it is an extrapolation of the pilot's eligibility rate, not a claim about all marketplace traffic. Setup/monthly implementation assumptions are $35,000/$1,500 for quote flow, $12,000/$1,000 for referral, and $65,000/$4,500 for ranking. The UI allows sensitivity changes without altering the registered portfolio case.

**Annualization counts twelve new acquisition cohorts, each valued over twelve policy months.** It is not first-year recognized revenue or realized contribution. The sampling interval excludes uncertainty in traffic, retention assumptions, value calibration and implementation costs. The sensitivity panel explores those assumptions; it is not a marketing optimizer.

## Explicit decision policy

1. Invalid assignment, immature outcomes or failed data checks block SHIP and require review.
2. Demonstrated guardrail harm beyond tolerance, a negative primary-effect interval, or an entirely negative financial interval produces DO NOT SHIP.
3. With sufficient sample and positive, useful primary evidence, a non-positive best estimate of net rollout value produces DO NOT SHIP. This is an operating choice under the stated assumptions, not proof that the true effect is negative.
4. SHIP requires all data and sample gates, adjusted primary p < 0.05, positive primary effect interval, practical lift, a positive lower modeled financial bound, and every guardrail passing.
5. All remaining cases produce CONTINUE TESTING, with the unresolved gates listed explicitly.

SHIP recommends a staged rollout with a persistent randomized holdout. DO NOT SHIP recommends retaining control and revising the failing economics or experience before a new trial. CONTINUE TESTING recommends a pre-specified follow-up or valid sequential design, without opportunistic extension.

## Auditability and limitations

DuckDB preserves the assignment ledger, registry, pre-test value assumptions, arm aggregates and cumulative results. `sql/11_experiment_analysis.sql` exposes intention-to-treat denominators and the financial reconciliation. A download includes the registered design, metrics, methods, segment estimates, guardrails, costs, checks, recommendation and data SHA-256 fingerprint. Source-Parquet fingerprints prevent rebuilding against stale experiment inputs after the historical data changes.

All outcomes are synthetic. The model omits interference, repeat referrals, multi-carrier quote exposure, long-term experimentally observed retention, assignment loss and production telemetry failures. Sample-ratio mismatch, unique units, follow-up, missing results and financial identity are checked, but these checks cannot establish that a real instrumentation pipeline is unbiased. Secondary metrics are diagnostic with unadjusted p-values. The historical executive overview remains a separate operating snapshot; experimental effects are not retroactively inserted into its revenue chart.
