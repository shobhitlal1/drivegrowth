# Executive memo

**Reporting period:** May–July 2026. **Snapshot:** August 31, 2026. **Scope:** acquisition economics and experimentation.

This project uses synthetically generated customer-level data designed to simulate realistic insurance marketplace behavior. It is not affiliated with or based on proprietary data from any insurance company.

## Executive summary

The simulated marketplace acquired 72,092 registered visitors and 15,675 policies in the reporting cohorts. Acquired-policy CAC was $69.52, based on $1,089,727 of allocated acquisition spend. The separate active book earned $5,478,074 in commission revenue and $3,856,097 in contribution before acquisition cost.

## Key findings

1. **Channel value differs materially.** Referral modeled LTV is $348 against $28 CAC (12.6×). Google Search is $319 against $104 (3.1×). These reflect specified simulation economics, not externally validated acquisition opportunities.
2. **Downstream value changes the channel story.** Comparison Websites converts 33.3% of started quotes, but its modeled LTV is $233, versus $319 for Google Search. Purchase conversion alone misses retention and servicing differences.
3. **Mobile completion is weaker.** Mobile completes 64.9% of started quotes; desktop completes 79.2%. The 14.3-point gap is observational and partly induced by the generator's device and channel mix.
4. **The funnel loses volume before purchase.** 51,092 starts lead to 35,486 completed quotes, 32,667 matches and 15,675 purchased policies. Visit-to-policy conversion is 21.7%; quote-to-policy is 30.7%.
5. **Renewal is conditional.** 82.1% of 9,318 policies reaching a first renewal anniversary during the reporting window renew. This excludes earlier cancellations; mature-cohort 365-day retention must be used for total book persistence.

## Growth opportunities and recommended actions

- **Referral leads on customer value.** 12.6× modeled LTV/CAC vs 3.9× across the other channels. Test incremental capacity before increasing the budget. Historical averages do not measure marginal returns.
- **A lower CAC can hide weaker value.** TikTok / Social: $100 CAC / 2.1× value. Google Search: $104 / 3.1×. Compare retention and risk mix before rewarding cheaper acquisition.
- **Mobile quote completion trails desktop.** 14.3 percentage-point gap · 64.9% mobile vs 79.2% desktop. Segment by acquisition source, then test a shorter mobile quote flow. This gap is observational.

## Experiment results

Three separate synthetic trials now have intention-to-treat analysis, confidence intervals, multiplicity-adjusted primary evidence, guardrails, sample plans, modeled impact and explicit decisions. See [the generated experiment review](experiment_review.md) for the current calculated outcomes. These populations are separate from the historical operating book summarized above.

## Risks and limitations

The 24-month contribution scenario uses constant survival fitted to the full snapshot and an 8% annual discount. It is not a validated predictive model or a historical backtest. Filtered CAC allocates daily channel costs proportionally to visitors. Channel averages do not measure capacity or diminishing returns. Commission revenue and contribution use the entire active book, while customer and policy acquisition use signup cohorts. Causal claims and budget changes require further work.

## Potential extensions

Future iterations could incorporate constrained marketing allocation, carrier-partnership optimization, and prospective forecasting. These are intentionally outside the current project's scope, which focuses on acquisition economics and experimentation.
