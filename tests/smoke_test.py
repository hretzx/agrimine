"""
tests/smoke_test.py
-------------------
Opens every page of the REAL app with Streamlit's own test runner (AppTest) and
checks that nothing crashes. Needs streamlit installed.

    python tests/smoke_test.py          (or: pytest tests/smoke_test.py)

It uses a temporary database, so your saved assessments are not touched.
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "teachers-lab"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(LAB))             # the lab's own "utils" package

from streamlit.testing.v1 import AppTest  # noqa: E402

import core.db.warehouse as warehouse  # noqa: E402

warehouse.DB_PATH = Path(tempfile.mkdtemp()) / "smoke.db"   # temporary database for the whole run

PAGES = ["2_Soil_Analysis.py", "3_Crop_Advisor.py", "4_What-if_Lab.py",
         "5_Pattern_Mining.py", "6_Cluster_Explorer.py", "7_Data_Insights.py",
         "8_Model_Council.py", "9_Water_Lab.py", "10_Hierarchical.py", "11_FP-Growth_and_Eclat.py",
         "12_Data_Lake.py", "13_Data_Prep.py", "17_For_Teachers.py"]

# A soil profile typical for rice, in the format the Soil Analysis page stores it
ASSESSMENT = {
    "id": None,
    "values": {"N": 90.0, "P": 42.0, "K": 43.0, "temperature": 20.9,
               "humidity": 82.0, "ph": 6.5, "rainfall": 202.9},
    "categories": {"N": "high", "P": "medium", "K": "medium", "temperature": "low",
                   "humidity": "medium", "ph": "medium", "rainfall": "high"},
}


def load(script: str, with_assessment: bool) -> AppTest:
    at = AppTest.from_file(str(LAB / script), default_timeout=120)
    if with_assessment:
        at.session_state["assessment"] = dict(ASSESSMENT)
    return at.run()


def test_the_lab_opens_on_the_for_teachers_page_and_lists_every_technical_page():
    at = load("app.py", with_assessment=False)
    assert not at.exception, at.exception
    text = " ".join(m.value for m in at.markdown) + " ".join(h.value for h in at.subheader)
    assert "Algorithms and where to find them" in text and "Model evaluation" in text
    for title in ("Crop Advisor", "Model Council", "Cluster Explorer", "Hierarchical", "Pattern Mining", "FP-Growth and Eclat",
                  "Water Lab", "Data Insights", "Data Lake", "Data Prep", "What-if Lab", "Soil Analysis"):
        assert title in text, title


def test_the_farmer_pages_live_in_the_web_app_only():
    """Phase 8: the lab no longer has its own Home, What should I grow?, Crop Doctor or Plan B (the web app has them)."""
    files = {p.name for p in (LAB / "pages").glob("*.py")}
    assert not {"14_What_Should_I_Grow.py", "15_Crop_Doctor.py", "16_Plan_B.py"} & files
    assert "def dashboard" not in (LAB / "app.py").read_text()
    assert files == set(PAGES)                                    # every page file is one of the pages this test opens


def test_language_toggle_switches_the_lab_landing_page_to_marathi_and_back():
    at = load("app.py", with_assessment=True)
    at.session_state["lang_choice"] = "मराठी"
    at.run()
    assert not at.exception, at.exception
    assert "शिक्षकांसाठी" in " ".join(m.value for m in at.markdown)
    at.session_state["lang_choice"] = "EN"
    at.run()
    assert not at.exception and "For teachers" in " ".join(m.value for m in at.markdown)


def test_pages_without_an_assessment_show_a_friendly_message():
    for page in PAGES:
        at = load(f"pages/{page}", with_assessment=False)
        assert not at.exception, f"{page}: {at.exception}"


def test_pages_with_an_assessment():
    for page in PAGES:
        at = load(f"pages/{page}", with_assessment=True)
        assert not at.exception, f"{page}: {at.exception}"
    advisor = load("pages/3_Crop_Advisor.py", with_assessment=True)
    assert any(m.label == "Held-out accuracy" for m in advisor.metric)


# ---------------------------------------------------------------- the lab reads the same saved checks as the web app
RICE = {"N": 90, "P": 42, "K": 43, "temperature": 20.9, "humidity": 82, "ph": 6.5, "rainfall": 202.9}
GRAPES = {"N": 20, "P": 130, "K": 200, "temperature": 23, "humidity": 92, "ph": 6, "rainfall": 110}


def _fresh_db(*checks_values):
    """A new empty database with the given checks saved through core.checks (ids 1, 2, ...)."""
    import core.checks as checks
    warehouse.DB_PATH = Path(tempfile.mkdtemp()) / "lab.db"
    return [checks.create_check(v) for v in checks_values]


def _lookup(query: dict | None = None, session: dict | None = None) -> dict:
    """Run session.get_assessment_record() inside a Streamlit script and return what it found ({} for None)."""
    def script():
        import streamlit as st
        from utils.session import get_assessment_record
        st.session_state["found"] = get_assessment_record() or {}
    at = AppTest.from_function(script, default_timeout=60)
    for k, v in (query or {}).items():
        at.query_params[k] = v
    for k, v in (session or {}).items():
        at.session_state[k] = v
    at.run()
    assert not at.exception, at.exception
    return at.session_state["found"]


def test_lab_current_check_is_the_newest_when_nothing_else_is_chosen():
    _fresh_db()
    assert _lookup() == {}                                    # nothing saved: no current check, no invention
    _fresh_db(RICE, GRAPES)
    found = _lookup()
    assert found["id"] == 2 and found["values"]["N"] == 20 and found["predicted_crop"]


def test_lab_check_in_the_address_beats_the_newest():
    _fresh_db(RICE, GRAPES)
    found = _lookup(query={"check": "1"})
    assert found["id"] == 1 and found["values"]["N"] == 90 and found["predicted_crop"] == "rice"


def test_lab_unknown_or_garbage_check_in_the_address_falls_back_to_the_newest():
    _fresh_db(RICE, GRAPES)
    for bad in ("99", "abc", "-1", ""):
        assert _lookup(query={"check": bad})["id"] == 2, bad


def test_lab_remembers_the_check_after_the_address_is_dropped():
    """The lab's own links between pages drop ?check=, so the first page stores it in the session."""
    _fresh_db(RICE, GRAPES)

    def script():
        import streamlit as st
        from utils.session import get_assessment_record
        st.session_state["found"] = (get_assessment_record() or {}).get("id")
    at = AppTest.from_function(script, default_timeout=60)
    at.query_params["check"] = "1"
    at.run()
    assert at.session_state["found"] == 1
    at.query_params.clear()
    at.run()
    assert at.session_state["found"] == 1                     # not the newest (2)


def test_a_lab_page_opened_with_a_check_uses_its_readings():
    _fresh_db(RICE, GRAPES)
    at = AppTest.from_file(str(LAB / "pages/3_Crop_Advisor.py"), default_timeout=120)
    at.query_params["check"] = "1"
    at.run()
    assert not at.exception, at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "#1" in text and "N 90" in text and "N 20" not in text      # the sidebar card shows check 1's readings


def test_hierarchical_every_linkage_and_k():
    at = load("pages/10_Hierarchical.py", with_assessment=False)
    for method in ("Ward", "Average", "Complete", "Single"):
        at.radio[0].set_value(method).run()
        assert not at.exception, f"{method}: {at.exception}"
    for k in (2, 7, 10):
        at.slider[0].set_value(k).run()
        assert not at.exception, f"k={k}: {at.exception}"


def test_water_lab_every_target():
    from core.preprocessing import FEATURES
    at = load("pages/9_Water_Lab.py", with_assessment=True)
    for target in FEATURES:
        at.selectbox[0].set_value(target).run()
        assert not at.exception, f"{target}: {at.exception}"
    at.multiselect[0].set_value([]).run()      # no predictor: a message, not a crash
    assert not at.exception and at.info


def test_data_prep_every_option():
    at = load("pages/13_Data_Prep.py", with_assessment=False)
    for choice in ("Z-score (mean 0, std 1)", "Min-max (0 to 1)"):
        at.radio[0].set_value(choice).run()
        assert not at.exception, at.exception
    for choice in ("Equal-frequency", "Equal-width"):
        at.radio[1].set_value(choice).run()
        assert not at.exception, at.exception


def test_data_lake_pipeline_button():
    at = load("pages/12_Data_Lake.py", with_assessment=False)
    at.button[0].click().run()
    assert not at.exception and not at.error, (at.exception, [e.value for e in at.error])


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS  {name}")
    print("\nAll pages opened without errors.")
