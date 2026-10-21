"""
utils/session.py
----------------
Small helpers shared by the pages for the "current soil assessment" (the same thing the web app calls the current check).

Where it comes from, in this order:
  1. ?check=N in the address (the web app's "For teachers" links here with it); the record is read from the database
     through core.checks, so the lab and the web app always see the same readings;
  2. the one chosen earlier in this browser session (the Soil Analysis page, or an address that was opened before);
  3. the newest saved check, as in the web app;
  4. none: the pages show a friendly message.

It is kept in st.session_state like this:
    st.session_state["assessment"] = {
        "id": 7,                                  # row id in the database
        "values": {"N": 37.0, "P": 51.0, ...},    # the seven numbers
        "categories": {"N": "medium", ...},       # low / medium / high labels
    }
Every other page reads it through the functions below, so the storage format
is defined in exactly one place.
"""
import streamlit as st

from core import checks
from core.preprocessing import DEFAULT_K, FEATURES  # FEATURES re-exported for the pages

ASSESSMENT_KEY = "assessment"
SELECTED_K_KEY = "selected_k"   # number of clusters chosen on the Cluster Explorer page
SOIL_PAGE = "pages/2_Soil_Analysis.py"


def _from_check(check: dict) -> dict:
    """A core.checks record in the shape the pages expect."""
    return {"id": check["id"], "values": check["values"], "categories": check["categories"],
            "predicted_crop": check["predicted_crop"], "cluster_id": check["cluster_id"]}


def _check_in_address() -> int | None:
    raw = st.query_params.get("check")
    return int(raw) if isinstance(raw, str) and raw.isdigit() else None


def get_assessment_record() -> dict | None:
    """The full record ({id, values, categories, ...}) or None if there is none yet. See the order in the header."""
    wanted = _check_in_address()
    current = st.session_state.get(ASSESSMENT_KEY)
    current = current if isinstance(current, dict) and current.get("values") else None
    if wanted is not None and not (current and current.get("id") == wanted):
        found = checks.get_check(wanted)
        if found:                                   # an address for a check that does not exist falls through to the next rule
            current = _from_check(found)
            st.session_state[ASSESSMENT_KEY] = current       # remembered, because the lab's own links drop the address
    if current is None:
        newest = checks.list_checks(1)
        current = _from_check(newest[0]) if newest else None
    return current


def get_current_assessment() -> dict | None:
    """The seven soil/weather numbers as {feature: float}, or None if there is no assessment yet."""
    record = get_assessment_record()
    if record is None:
        return None
    try:
        return {f: float(record["values"][f]) for f in FEATURES}
    except (KeyError, TypeError, ValueError):
        return None


def require_assessment() -> dict:
    """
    Return the current assessment. If there is none, show a friendly message with a
    button to the Soil Analysis page and stop the page (instead of crashing).
    """
    values = get_current_assessment()
    if values is None:
        st.info("No soil assessment yet. Enter your soil and weather values on the "
                "Soil Analysis page first, then come back here.")
        if st.button("Go to Soil Analysis", type="primary"):
            st.switch_page(SOIL_PAGE)
        st.stop()
    return values


def get_selected_k() -> int:
    """Number of clusters chosen on the Cluster Explorer page (default if never chosen)."""
    return int(st.session_state.get(SELECTED_K_KEY, DEFAULT_K))
