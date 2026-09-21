import pytest
from src.metrics import cac, conversion_rate, contribution_margin, modeled_ltv, relative_change


def test_cac_uses_purchased_policies():
    assert cac(1000, 20) == 50


@pytest.mark.parametrize("function,args", [(cac, (10, 0)), (conversion_rate, (0, 0))])
def test_zero_denominators_are_missing(function, args):
    assert function(*args) is None


def test_conversion():
    assert conversion_rate(25, 100) == .25


@pytest.mark.parametrize("args", [(101, 100), (-1, 100), (0, -1)])
def test_invalid_conversions_raise(args):
    with pytest.raises(ValueError):
        conversion_rate(*args)


def test_marketplace_margin_does_not_subtract_carrier_claims():
    assert contribution_margin(30, 5, 7.5) == 17.5


def test_ltv_no_churn_no_discount():
    assert modeled_ltv(10, 1, 24, 0, 0) == 240


def test_ltv_hand_calculated_survival():
    assert modeled_ltv(10, .5, 3, 0, 2) == 15.5


def test_ltv_discount_reduces_value():
    assert modeled_ltv(10, .95, annual_discount=.08) < modeled_ltv(10, .95, annual_discount=0)


def test_relative_change_and_missing_baseline():
    assert relative_change(120, 100) == pytest.approx(.2)
    assert relative_change(100, 0) is None
