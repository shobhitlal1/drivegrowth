from datetime import date
import pandas as pd
import pytest

from src.analytics import Filters, dashboard_data, overview
from src.database import build_database, connect
from src.generate_data import generate_data
from src.metrics import modeled_ltv
from src.validate_data import validate


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    folder = tmp_path_factory.mktemp("drivegrowth")
    raw = folder / "raw"
    generate_data(6000, 42, raw)
    db = folder / "test.duckdb"
    build_database(raw, db)
    return raw, db


def test_generator_is_reproducible(sample, tmp_path):
    raw, _ = sample
    generate_data(6000, 42, tmp_path)
    for source in raw.glob("*.parquet"):
        pd.testing.assert_frame_equal(pd.read_parquet(source), pd.read_parquet(tmp_path / source.name))


def test_pipeline_invariants(sample):
    _, db = sample
    report = validate(db)
    assert report["all_passed"], report


def test_sql_ltv_matches_independent_python_formula(sample):
    _, db = sample
    with connect(db) as con:
        rows = con.execute("SELECT monthly_margin, monthly_survival, modeled_ltv_24m FROM ltv_assumptions").fetchall()
    for margin, survival, value in rows:
        assert value == pytest.approx(modeled_ltv(margin, survival), abs=1e-7)


def test_filtered_kpis_reconcile_to_channel_rows(sample):
    _, db = sample
    data = dashboard_data(Filters(date(2026, 2, 1), date(2026, 7, 31), state="CA"), db)
    assert data["current"]["policies"] == data["channels"].policies.sum()
    assert data["current"]["spend"] == pytest.approx(data["channels"].spend.sum())
    assert data["current"]["customers"] < 6000


def test_financials_include_earlier_acquisitions(sample):
    _, db = sample
    f = Filters(date(2026, 5, 1), date(2026, 7, 31))
    result = overview(f, db)
    with connect(db) as con:
        revenue = con.execute("SELECT sum(commission_revenue) FROM monthly_customer_value WHERE month BETWEEN ? AND ?", [f.start, f.end]).fetchone()[0]
    assert result["revenue"] == pytest.approx(revenue)


def test_all_filters_apply_together(sample):
    _, db = sample
    f = Filters(date(2025, 1, 1), date(2026, 7, 31), "TX", "Google Search", "Northstar Mutual", "High-intent search")
    result = overview(f, db)
    with connect(db) as con:
        expected = con.execute("SELECT count(*) FROM customer_facts WHERE signup_date BETWEEN ? AND ? AND state='TX' AND acquisition_channel='Google Search' AND carrier_name='Northstar Mutual' AND customer_segment='High-intent search'", [f.start, f.end]).fetchone()[0]
    assert result["customers"] == expected


def test_empty_intersection_returns_undefined_cac(sample):
    _, db = sample
    result = overview(Filters(date(2026, 5, 1), date(2026, 7, 31), channel="Referral", segment="High-intent search"), db)
    assert result["customers"] == 0
    assert result["cac"] is None


def test_previous_period_respects_calendar_months():
    result = Filters(date(2026, 5, 1), date(2026, 7, 31)).previous()
    assert (result.start, result.end) == (date(2026, 2, 1), date(2026, 4, 30))
