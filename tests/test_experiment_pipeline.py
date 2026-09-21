import json
import numpy as np
import pandas as pd
import pytest

from src.config import DB_PATH, ROOT
from src.database import connect
from src.experiment_analysis import experiment_data, quality_checks, portfolio, decision_record, json_default
from src.executive_insights import observations

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="Build the full database first")


@pytest.fixture(scope="module")
def trials():
    return experiment_data()


def test_full_trial_quality_and_reconciliation(trials):
    designs, frame, snapshot = trials
    assert len(frame) == 80000
    assert not frame.unit_id.duplicated().any()
    for d in designs:
        subset = frame[frame.experiment_id == d.experiment_id]
        assert all(c["passed"] for c in quality_checks(subset, d, snapshot))
        assert subset.groupby("variant").outcome_observed.all().all()
        if d.experiment_id == "referral":
            expected = subset.policy_purchased * np.where(subset.variant == "Treatment", 35, 20)
            np.testing.assert_array_equal(subset.incentive_cost, expected)


def test_bad_randomization_and_missing_outcomes_block_rollout(trials):
    designs, frame, snapshot = trials
    d = designs[0]
    bad = frame[frame.experiment_id == d.experiment_id].copy()
    bad.loc[bad.index[:10000], "variant"] = "Treatment"
    assert not next(x for x in quality_checks(bad, d, snapshot) if x["name"] == "Sample-ratio mismatch")["passed"]
    bad.loc[bad.index[0], d.primary] = np.nan
    assert not next(x for x in quality_checks(bad, d, snapshot) if x["name"] == "No missing mature outcomes")["passed"]


def test_immature_outcomes_are_not_ready_for_shipping(trials):
    designs, frame, snapshot = trials
    d = designs[0]
    subset = frame[frame.experiment_id == d.experiment_id]
    early = pd.Timestamp(d.end)
    assert not next(x for x in quality_checks(subset, d, early) if x["name"] == "Complete follow-up")["passed"]


def test_pretest_valuation_has_no_future_cutoff(trials):
    with connect() as con:
        assert con.execute("SELECT count(*) FROM experiment_value_assumptions a JOIN experiment_registry r USING(experiment_id) WHERE a.fit_before > CAST(r.start AS DATE)").fetchone()[0] == 0


def test_sql_matches_raw_itt_denominators(trials):
    designs, frame, snapshot = trials
    with connect() as con:
        sql = con.execute((ROOT / "sql" / "11_experiment_analysis.sql").read_text()).fetchdf().set_index("experiment_id")
    for d in designs:
        part = frame[frame.experiment_id == d.experiment_id]
        c, t = part[part.variant == "Control"], part[part.variant == "Treatment"]
        assert sql.loc[d.experiment_id, "control_n"] == len(c)
        assert sql.loc[d.experiment_id, "treatment_n"] == len(t)
        assert sql.loc[d.experiment_id, "absolute_lift"] == pytest.approx(t[d.primary].mean()-c[d.primary].mean())
        assert sql.loc[d.experiment_id, "net_value_delta"] == pytest.approx(t.net_value_12m.mean()-c.net_value_12m.mean())


def test_insight_leader_is_selected_from_data_not_a_named_channel():
    channels = pd.DataFrame({"channel": ["Referral", "Another channel"], "policies": [500, 500],
                             "spend": [5000, 10000], "cac": [10,20], "ltv": [100,400], "ltv_cac": [10,20]})
    result = observations(channels, pd.DataFrame({"device_type": []}))
    assert result[0]["title"].startswith("Another channel")


def test_decision_record_is_portable_and_serializable():
    results = portfolio(draws=300)
    for r in results:
        record = decision_record(r)
        encoded = json.dumps(record, default=json_default)
        assert "/Users/" not in encoded
        assert len(record["data_fingerprint_sha256"]) == 64
        assert all(check["passed"] for check in record["quality_checks"])
        assert record["decision"]["recommendation"] in {"SHIP", "DO NOT SHIP", "CONTINUE TESTING"}


def test_trial_generation_is_reproducible_from_pretest_profiles(tmp_path):
    from src.generate_experiments import generate_experiments, SOURCE_TABLES
    from src.config import RAW_DIR
    for name in SOURCE_TABLES:
        (tmp_path / f"{name}.parquet").symlink_to(RAW_DIR / f"{name}.parquet")
    first_manifest = generate_experiments(tmp_path, seed=12345, scale=.02)
    first = pd.read_parquet(tmp_path / "experiments.parquet")
    second_manifest = generate_experiments(tmp_path, seed=12345, scale=.02)
    pd.testing.assert_frame_equal(first, pd.read_parquet(tmp_path / "experiments.parquet"))
    assert first_manifest == second_manifest
