import pytest
from streamlit.testing.v1 import AppTest
from src.config import DB_PATH, ROOT

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="Generate the full local dataset first")


def test_overview_runs_and_state_filter_changes_totals():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception
    default_content = " ".join(x.value for x in app.markdown)
    app.selectbox[2].set_value("CA").run()
    assert not app.exception
    assert " ".join(x.value for x in app.markdown) != default_content


def test_empty_filter_state_and_invalid_dates_are_handled():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    app.selectbox[3].set_value("Referral")
    app.selectbox[5].set_value("High-intent search").run()
    assert not app.exception
    assert any("No acquired customers" in x.value for x in app.info)
    app.selectbox[0].set_value(app.selectbox[0].value.replace(month=7))
    app.selectbox[1].set_value(app.selectbox[1].value.replace(month=5)).run()
    assert not app.exception
    assert any("start month" in x.value for x in app.warning)
