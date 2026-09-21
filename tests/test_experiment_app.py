import pytest
from streamlit.testing.v1 import AppTest
from src.config import ROOT, DB_PATH

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="Build the full database first")


def test_experiment_navigation_details_segments_and_scenarios():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120).run()
    app.radio(key="workspace").set_value("Experiments").run()
    assert not app.exception
    content = " ".join(x.value for x in app.markdown)
    assert "Which changes deserve a rollout?" in content
    for experiment_id in ["quote_flow", "referral", "carrier_ranking"]:
        app.selectbox(key="experiment_choice").set_value(experiment_id).run()
        assert not app.exception
        assert len(app.tabs) == 3
        assert "The rollout decision" in " ".join(x.value for x in app.markdown)
    app.selectbox(key="effect_dimension").set_value("State").run()
    assert not app.exception
    app.number_input(key="scenario_setup_carrier_ranking").set_value(10000000.0).run()
    assert not app.exception
    assert "DO NOT SHIP" in " ".join(x.value for x in app.markdown)
    app.radio(key="workspace").set_value("Executive overview").run()
    assert not app.exception
    assert "Pre-acquisition contribution" in " ".join(x.value for x in app.markdown)
