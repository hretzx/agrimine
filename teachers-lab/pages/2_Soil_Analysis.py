"""
pages/2_Soil_Analysis.py
------------------------
Collects one soil/weather profile, validates it, labels each value as
low / medium / high, saves it to the database and stores it in
st.session_state["assessment"] so the other pages can use it.
"""
import streamlit as st

from core.db.warehouse import save_assessment
from core.models import get_data
from core.preprocessing import (FEATURES, VALID_RANGES, categorize, category_cutoffs,
                                 ph_class, validate_inputs)
from core.features import LABEL
from utils.session import ASSESSMENT_KEY, get_assessment_record
from utils.style import ALGO, apply_style, badge, feature_tile, page_header, refresh_sidebar, render_html

apply_style()
page_header(
    "Soil Analysis",
    "Enter one field's soil and weather values. Each is compared with the whole dataset "
    "and labelled low, medium or high.",
    eyebrow="Step 1 · Percentile profiling",
    accent=ALGO["soil"], crumbs=["Home", "Assess", "Soil Analysis"],
)
with st.popover("What do low / medium / high mean?", icon=":material/info:"):
    st.markdown(
        "Low / medium / high means the bottom third, middle third and top third of the records. "
        "These labels describe where a value sits in the data; they are not a judgement of the soil."
    )

LABELS = LABEL


@st.cache_data(show_spinner=False)
def get_cutoffs_and_medians():
    """Cut-offs for the categories and median values used as form defaults."""
    df, _ = get_data()
    return category_cutoffs(df), df[FEATURES].median().to_dict()


cutoffs, medians = get_cutoffs_and_medians()

# Pre-fill with the current assessment if there is one, otherwise with dataset medians.
current = (get_assessment_record() or {}).get("values", {})
start = {f: current.get(f, medians[f]) for f in FEATURES}


def field(name: str):
    """One number input; range, unit and step come from VALID_RANGES."""
    lo, hi, unit = VALID_RANGES[name]
    is_int = name in ("N", "P", "K")
    label = f"{LABELS[name]} ({unit})" if unit else LABELS[name]
    return st.number_input(
        label,
        min_value=float(lo), max_value=float(hi),
        value=float(min(max(round(start[name], 1), lo), hi)),
        step=1.0 if is_int else 0.1,
        format="%.0f" if is_int else "%.1f",
        key=f"in_{name}",
    )


with st.form("soil_form"):
    st.markdown("##### :material/landscape: Soil")
    a, b, c, d = st.columns(4)
    with a:
        n = field("N")
    with b:
        p = field("P")
    with c:
        k = field("K")
    with d:
        ph = field("ph")

    st.write("")
    st.markdown("##### :material/partly_cloudy_day: Climate")
    e, f_, g = st.columns(3)
    with e:
        temperature = field("temperature")
    with f_:
        humidity = field("humidity")
    with g:
        rainfall = field("rainfall")

    st.write("")
    submitted = st.form_submit_button("Save assessment", type="primary", icon=":material/save:")

if submitted:
    values = {"N": n, "P": p, "K": k, "ph": ph,
              "temperature": temperature, "humidity": humidity, "rainfall": rainfall}

    errors = validate_inputs(values)   # range check (the inputs are also range-limited)
    if errors:
        for msg in errors:
            st.error(msg)
    else:
        categories = {f: categorize(values[f], cutoffs[f]) for f in FEATURES}
        try:
            assessment_id = save_assessment(values)      # database write
        except Exception as exc:                          # keep the app usable if the DB is locked
            assessment_id = None
            st.warning(f"The assessment could not be saved to the database ({exc}). "
                       "It is still available to the other pages in this session.")
        # Share with the other pages. They reset themselves when these values change.
        st.session_state[ASSESSMENT_KEY] = {
            "id": assessment_id, "values": values, "categories": categories,
        }
        if assessment_id is not None:
            st.query_params["check"] = str(assessment_id)       # the address always names the check being looked at
            st.success(f"Assessment #{assessment_id} saved.")
        else:
            st.query_params.pop("check", None)

# ---- Show the current assessment (also after navigating back to this page)
assessment = get_assessment_record()
if submitted:
    refresh_sidebar()   # the sidebar card was drawn before this run saved the assessment
if assessment and assessment.get("values"):
    title = f"Current assessment (#{assessment['id']})" if assessment.get("id") else "Current assessment"
    st.subheader(title)
    st.caption("Hover a tile to see the low / medium / high cut-offs used. "
               "Shared with the Crop Advisor, What-if Lab and Cluster Explorer.")
    for row in (FEATURES[:4], FEATURES[4:]):
        cols = st.columns(4)
        for col, f in zip(cols, row):
            unit = VALID_RANGES[f][2]
            lo_cut, hi_cut = cutoffs[f]
            extra = badge(ph_class(assessment["values"][f]), "info") if f == "ph" else ""
            with col:
                render_html(feature_tile(
                    LABELS[f], f"{assessment['values'][f]:g}", unit, assessment["categories"][f],
                    tooltip=f"low < {lo_cut:.1f} <= medium < {hi_cut:.1f} <= high", extra_html=extra,
                ))
        st.write("")
    if st.button("Continue to Crop Advisor", type="primary", icon=":material/arrow_forward:"):
        st.switch_page("pages/3_Crop_Advisor.py")
else:
    st.caption("No assessment yet. Fill in the form and save to continue.")
