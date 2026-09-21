"""Small analytical primitives with explicit denominator handling."""
from __future__ import annotations
import math


def safe_ratio(numerator: float, denominator: float) -> float | None:
    """Undefined metrics remain missing instead of becoming misleading zeros."""
    return numerator / denominator if denominator > 0 else None


def cac(spend: float, policies: int) -> float | None:
    if spend < 0 or policies < 0:
        raise ValueError("Spend and policy counts must be nonnegative.")
    return safe_ratio(spend, policies)


def conversion_rate(converted: int, eligible: int) -> float | None:
    if min(converted, eligible) < 0 or converted > eligible:
        raise ValueError("Conversions must be between zero and the eligible population.")
    return safe_ratio(converted, eligible)


def contribution_margin(commission: float, service: float, onboarding: float = 0) -> float:
    """Marketplace contribution before acquisition cost, excluding carrier claims."""
    return commission - service - onboarding


def modeled_ltv(monthly_margin: float, monthly_survival: float,
                months: int = 24, annual_discount: float = .08,
                onboarding: float = 7.5) -> float:
    """Expected discounted contribution, conditional on acquiring a policy."""
    if not 0 <= monthly_survival <= 1 or months < 1 or annual_discount < 0:
        raise ValueError("Invalid lifetime value assumptions.")
    ratio = monthly_survival / (1 + annual_discount) ** (1 / 12)
    return sum(monthly_margin * ratio ** m for m in range(months)) - onboarding


def relative_change(current: float, previous: float) -> float | None:
    if previous <= 0 or not all(map(math.isfinite, [current, previous])):
        return None
    return current / previous - 1
