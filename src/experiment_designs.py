"""Pre-specified designs and decision thresholds, never experiment conclusions."""
from __future__ import annotations
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Guardrail:
    metric: str
    label: str
    direction: str  # higher_good or lower_good
    tolerance: float


@dataclass(frozen=True)
class ExperimentDesign:
    experiment_id: str
    name: str
    control: str
    treatment: str
    hypothesis: str
    population: str
    unit: str
    start: str
    end: str
    primary: str
    primary_label: str
    planning_rate: float
    mde: float
    practical_effect: float
    sample: int
    setup_cost: float
    monthly_cost: float
    guardrails: tuple[Guardrail, ...]
    observation_days: int = 30

    def record(self) -> dict:
        return asdict(self)


DESIGNS = (
    ExperimentDesign(
        "quote_flow", "Shortened Quote Flow", "Existing 8-step workflow", "Redesigned 5-step workflow",
        "Removing three quote steps increases completion, especially on mobile, without reducing policy conversion or increasing support demand beyond tolerance.",
        "Eligible new quote starters; one assignment before the workflow opens.", "Quote starter",
        "2026-05-04", "2026-05-31", "quote_completed", "Quote completion", .68, .03, .015,
        28_000, 35_000, 1_500,
        (Guardrail("policy_purchased", "Policy conversion", "higher_good", .005),
         Guardrail("support_contact", "Support contact rate", "lower_good", .012)),
    ),
    ExperimentDesign(
        "referral", "Referral Incentive", "$20 per bound referral", "$35 per bound referral",
        "A larger referral reward increases members generating a bound referral policy, with enough incremental policy value to pay for the higher reward on all qualifying referrals.",
        "Existing eligible members, randomized before invitation; one invite opportunity and at most one rewarded policy per member.", "Eligible member",
        "2026-06-01", "2026-06-28", "policy_purchased", "Member → bound referral", .10, .012, .006,
        40_000, 12_000, 1_000,
        (Guardrail("early_cancel", "Early cancellation / eligible member", "lower_good", .006),
         Guardrail("support_contact", "Support contact rate", "lower_good", .010)),
    ),
    ExperimentDesign(
        "carrier_ranking", "Carrier Ranking Algorithm", "Existing carrier ordering", "Conversion + economics ranking",
        "Ranking carriers by expected conversion and economics improves policy conversion without materially reducing carrier match or increasing support demand.",
        "Completed-quote shoppers eligible for carrier matching; assignment occurs before any carrier results are shown.", "Completed-quote shopper",
        "2026-07-06", "2026-07-26", "policy_purchased", "Quote → bound policy", .40, .015, .008,
        12_000, 65_000, 4_500,
        (Guardrail("carrier_matched", "Carrier match rate", "higher_good", .015),
         Guardrail("support_contact", "Support contact rate", "lower_good", .012)),
    ),
)
BY_ID = {d.experiment_id: d for d in DESIGNS}
ALPHA = .05
FAMILY_SIZE = len(DESIGNS)
POWER = .80
BOOTSTRAP_DRAWS = 3000
EXPERIMENT_SEED = 20261017
