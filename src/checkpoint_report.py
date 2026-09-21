"""Write an executive checkpoint memo exclusively from the current database."""
from datetime import date
from src.analytics import Filters, dashboard_data
from src.config import ROOT, DISCLAIMER
from src.executive_insights import observations


def write_report() -> None:
    data = dashboard_data(Filters(date(2026, 5, 1), date(2026, 7, 31)))
    k = data["current"]
    channel = data["channels"].set_index("channel")
    mobile = data["devices"].set_index("device_type")
    findings = observations(data["channels"], data["devices"])
    body = f"""# Executive checkpoint memo

**Reporting period:** May–July 2026. **Snapshot:** August 31, 2026. **Scope:** operating overview and experiment checkpoint.

{DISCLAIMER}

## Executive summary

The simulated marketplace acquired {k['customers']:,.0f} registered visitors and {k['policies']:,.0f} policies in the reporting cohorts. Acquired-policy CAC was ${k['cac']:,.2f}, based on ${k['spend']:,.0f} of allocated acquisition spend. The separate active book earned ${k['revenue']:,.0f} in commission revenue and ${k['contribution_margin']:,.0f} in contribution before acquisition cost.

## Key findings

1. **Channel value differs materially.** Referral modeled LTV is ${channel.loc['Referral', 'ltv']:,.0f} against ${channel.loc['Referral', 'cac']:,.0f} CAC ({channel.loc['Referral', 'ltv_cac']:.1f}×). Google Search is ${channel.loc['Google Search', 'ltv']:,.0f} against ${channel.loc['Google Search', 'cac']:,.0f} ({channel.loc['Google Search', 'ltv_cac']:.1f}×). These reflect specified simulation economics, not externally validated acquisition opportunities.
2. **Downstream value changes the channel story.** Comparison Websites converts {channel.loc['Comparison Websites', 'conversion']:.1%} of started quotes, but its modeled LTV is ${channel.loc['Comparison Websites', 'ltv']:,.0f}, versus ${channel.loc['Google Search', 'ltv']:,.0f} for Google Search. Purchase conversion alone misses retention and servicing differences.
3. **Mobile completion is weaker.** Mobile completes {mobile.loc['Mobile', 'completion']:.1%} of started quotes; desktop completes {mobile.loc['Desktop', 'completion']:.1%}. The {(mobile.loc['Desktop', 'completion'] - mobile.loc['Mobile', 'completion']) * 100:.1f}-point gap is observational and partly induced by the generator's device and channel mix.
4. **The funnel loses volume before purchase.** {k['quote_starts']:,.0f} starts lead to {k['quote_completions']:,.0f} completed quotes, {k['carrier_matches']:,.0f} matches and {k['policies']:,.0f} purchased policies. Visit-to-policy conversion is {k['policies'] / k['customers']:.1%}; quote-to-policy is {k['conversion']:.1%}.
5. **Renewal is conditional.** {k['renewal_rate']:.1%} of {k['renewal_eligible']:,.0f} policies reaching a first renewal anniversary during the reporting window renew. This excludes earlier cancellations; mature-cohort 365-day retention must be used for total book persistence.

## Growth opportunities and recommended actions

"""
    for finding in findings:
        body += f"- **{finding['title']}.** {finding['evidence']} {finding['action']}\n"
    body += """
## Experiment results

Three separate synthetic trials now have intention-to-treat analysis, confidence intervals, multiplicity-adjusted primary evidence, guardrails, sample plans, modeled impact and explicit decisions. See [the generated experiment review](experiment_review.md) for the current calculated outcomes. These populations are separate from the historical operating book summarized above.

## Risks and limitations

The 24-month contribution scenario uses constant survival fitted to the full snapshot and an 8% annual discount. It is not a validated predictive model or a historical backtest. Filtered CAC allocates daily channel costs proportionally to visitors. Channel averages do not measure capacity or diminishing returns. Commission revenue and contribution use the entire active book, while customer and policy acquisition use signup cohorts. Causal claims and budget changes require further work.

## Next actions

Review the Experiments workspace's evidence, financial tradeoffs and decision rules. The optimizer has not been started. After experiment review, prioritize constrained growth optimization, carrier strategy and executive decisions. Preserve explicit metric definitions and synthetic-data labeling throughout.
"""
    (ROOT / "docs" / "executive_memo.md").write_text(body)
    print("Wrote docs/executive_memo.md from current database metrics.")


if __name__ == "__main__":
    write_report()
