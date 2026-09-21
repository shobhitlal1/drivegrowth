import numpy as np
import pandas as pd
import pytest

from src.experimentation import (Estimate, binary_estimate, welch_estimate,
    bootstrap_differences, financial_estimate, financial_impact, incremental_policies,
    planned_sample_per_arm, guardrail_result, decide, segment_effects)


def binary(successes, size):
    return np.r_[np.ones(successes), np.zeros(size-successes)]


def test_conversion_lift_and_reference_p_value():
    e = binary_estimate(binary(100, 1000), binary(120, 1000))
    assert e.control == .10 and e.treatment == .12
    assert e.difference == pytest.approx(.02)
    assert e.relative_lift == pytest.approx(.20)
    assert e.p_value == pytest.approx(.152923, abs=.0001)
    assert e.ci_low < 0 < e.ci_high


def test_conversion_interval_changes_sign_when_arms_swap():
    c, t = binary(100, 1000), binary(160, 1000)
    e, reverse = binary_estimate(c, t), binary_estimate(t, c)
    assert e.ci_low > 0 and e.p_value < .001
    assert reverse.ci_low == pytest.approx(-e.ci_high)
    assert reverse.ci_high == pytest.approx(-e.ci_low)
    assert reverse.p_value == pytest.approx(e.p_value)


@pytest.mark.parametrize("value", [0, 1])
def test_boundary_conversions_have_finite_intervals(value):
    e = binary_estimate(np.full(100, value), np.full(100, value))
    assert e.p_value == 1 and e.difference == 0
    assert e.ci_low < 0 < e.ci_high
    if value == 0:
        assert e.relative_lift is None


def test_sparse_conversion_uses_exact_test():
    e = binary_estimate(binary(0, 12), binary(8, 12))
    assert "Fisher" in e.method
    assert 0 < e.p_value < .01


@pytest.mark.parametrize("bad", [[0, 2, 1], [0, np.nan, 1], [0]])
def test_invalid_or_missing_observations_do_not_silently_disappear(bad):
    with pytest.raises(ValueError):
        binary_estimate(bad, [0, 1, 1])


def test_welch_unequal_variance_reference_and_direction():
    e = welch_estimate([1, 2, 3, 4, 5], [3, 7, 8, 12, 18, 26])
    assert e.difference == pytest.approx(12.333333333 - 3)
    assert e.ci_low < e.difference < e.ci_high
    assert e.p_value < .05
    reverse = welch_estimate([3, 7, 8, 12, 18, 26], [1, 2, 3, 4, 5])
    assert reverse.ci_low == pytest.approx(-e.ci_high)


def test_bootstrap_is_reproducible_and_keeps_zero_nonconverters():
    c = np.r_[np.zeros(90), np.full(10, 100)]
    t = np.r_[np.zeros(80), np.full(20, 100)]
    e, draws = financial_estimate(c, t, 500, seed=12)
    assert e.control == 10 and e.treatment == 20
    np.testing.assert_array_equal(draws, bootstrap_differences(c, t, 500, seed=12))
    assert e.ci_low < 10 < e.ci_high
    assert 0 <= e.p_value <= 1


@pytest.fixture
def financial_arms():
    c = pd.DataFrame({"policy_purchased": [1,0,0,0], "modeled_policy_value_12m": [100,0,0,0],
                      "incentive_cost": [20,0,0,0], "variable_cost": [0,0,0,0]})
    t = pd.DataFrame({"policy_purchased": [1,1,0,0], "modeled_policy_value_12m": [100,120,0,0],
                      "incentive_cost": [35,35,0,0], "variable_cost": [1,1,1,1]})
    return c, t


def test_incremental_policies_uses_absolute_not_relative_lift():
    assert incremental_policies(.10, .12, 10000) == pytest.approx(200)


def test_financial_bridge_counts_incentive_increase_on_baseline_converters(financial_arms):
    c, t = financial_arms
    impact = financial_impact(c, t, 1000, 500, 10000, np.full(200, 16.5))
    assert impact["incremental_policies"] == 250
    assert impact["volume_contribution"] == 25000
    assert impact["value_mix_contribution"] == 5000
    assert impact["incremental_gross_contribution"] == 30000
    assert impact["incremental_incentives"] == 12500
    assert impact["incremental_variable_cost"] == 1000
    assert impact["monthly_net"] == 16000
    assert impact["annualized_net"] == impact["annual_ci_low"] == impact["annual_ci_high"] == 182000


def test_financial_sensitivity_scales_value_but_not_incentives(financial_arms):
    c, t = financial_arms
    impact = financial_impact(c, t, 1000, 500, 10000, np.full(200, 16.5), .5, np.full(200, 30))
    assert impact["incremental_incentives"] == 12500
    assert impact["annualized_net"] == impact["annual_ci_low"] == 2000


def test_zero_traffic_still_includes_rollout_costs(financial_arms):
    c, t = financial_arms
    impact = financial_impact(c, t, 0, 500, 10000, np.full(200, 16.5))
    assert impact["incremental_policies"] == 0
    assert impact["annualized_net"] == -16000


def test_bootstrap_sensitivity_preserves_covariance():
    c = np.arange(20, dtype=float)
    t = np.arange(30, dtype=float)
    gross = bootstrap_differences(c, t, 300, seed=11)
    net = bootstrap_differences(c - 2, t - 5, 300, seed=11)
    np.testing.assert_allclose(gross - net, 3)


def test_smaller_effect_and_stricter_alpha_require_larger_sample():
    assert planned_sample_per_arm(.4, .01) > planned_sample_per_arm(.4, .02)
    assert planned_sample_per_arm(.4, .02, alpha=.01) > planned_sample_per_arm(.4, .02, alpha=.05)


@pytest.fixture
def clear_case():
    primary = Estimate(10000, 10000, .5, .55, .05, .1, .035, .065, .00001, "fixture")
    return dict(primary=primary, adjusted_p=.00003,
                impact={"annualized_net": 100000, "annual_ci_low": 50000, "annual_ci_high": 150000},
                guardrails=[{"label": "Support", "state": "Pass"}], sufficient=True,
                data_valid=True, practical_effect=.01)


def test_ship_requires_all_gates(clear_case):
    assert decide(**clear_case)["recommendation"] == "SHIP"


@pytest.mark.parametrize("field,value", [("sufficient", False), ("data_valid", False), ("adjusted_p", .08), ("practical_effect", .08)])
def test_weak_evidence_never_ships(clear_case, field, value):
    clear_case[field] = value
    assert decide(**clear_case)["recommendation"] == "CONTINUE TESTING"


def test_unclear_guardrail_is_not_treated_as_safe(clear_case):
    clear_case["guardrails"][0]["state"] = "Unclear"
    assert decide(**clear_case)["recommendation"] == "CONTINUE TESTING"


def test_demonstrated_guardrail_harm_blocks_shipping(clear_case):
    clear_case["guardrails"][0]["state"] = "Fail"
    assert decide(**clear_case)["recommendation"] == "DO NOT SHIP"


def test_significant_conversion_can_still_be_an_economic_no(clear_case):
    clear_case["impact"].update(annualized_net=-10000, annual_ci_low=-30000, annual_ci_high=10000)
    decision = decide(**clear_case)
    assert decision["recommendation"] == "DO NOT SHIP"
    assert "not proof" in decision["reasons"][0]


def test_positive_point_value_with_negative_downside_requires_more_evidence(clear_case):
    clear_case["impact"]["annual_ci_low"] = -100
    assert decide(**clear_case)["recommendation"] == "CONTINUE TESTING"


def test_guardrail_noninferiority_is_not_a_null_significance_test():
    # Identical small arms do not prove a tight safety margin.
    uncertain = guardrail_result(binary(10, 100), binary(10, 100), "lower_good", .005, 2)
    assert uncertain["estimate"].p_value == 1 and uncertain["state"] == "Unclear"
    safe = guardrail_result(binary(100, 10000), binary(100, 10000), "lower_good", .012, 2)
    assert safe["state"] == "Pass"
    harmed = guardrail_result(binary(100, 10000), binary(400, 10000), "lower_good", .012, 2)
    assert harmed["state"] == "Fail"


def test_heterogeneity_tests_effect_differences_not_one_significant_subgroup():
    frames = []
    for device, treatment_success in [("Mobile", 1500), ("Desktop", 1050)]:
        for variant, successes in [("Control", 1000), ("Treatment", treatment_success)]:
            frames.append(pd.DataFrame({"device_type": device, "variant": variant,
                                       "metric": binary(successes, 3000), "acquisition_channel": "Search", "state": "CA", "risk_segment": "Low"}))
    result = segment_effects(pd.concat(frames, ignore_index=True), "metric")
    assert result[result.dimension == "device_type"].heterogeneous.all()
