"""
pages/4_What-if_Lab.py
----------------------
What-if Lab: pick a preferred crop, tweak the soil values with sliders and compare
BEFORE (saved assessment) vs AFTER (slider values) using the same ID3 tree and
K-Means model as the other pages.
"""
import math

import pandas as pd
import streamlit as st

from core.models import train_id3, train_kmeans
from core.preprocessing import TARGET
from core.features import LABEL_UNIT
from utils.session import FEATURES, get_selected_k, require_assessment
from utils.style import (ALGO, apply_style, badge, crop_title, outcome_card, page_header, render_html,
                         section_note, show_table, status_cell)

apply_style()
page_header(
    "What-if Lab",
    "Adjust the soil and weather values and see which inputs push the ID3 and K-Means "
    "results toward or away from a preferred crop.",
    eyebrow="ID3 + K-Means · Scenarios",
    accent=ALGO["whatif"], crumbs=["Home", "Assess", "What-if Lab"],
)

PRETTY = LABEL_UNIT
INT_FEATURES = {"N", "P", "K"}
STEP = {"ph": 0.1, "temperature": 0.5, "humidity": 1.0, "rainfall": 1.0}


def status(value: float, low: float, high: float) -> str:
    """Compare a value with a crop's typical range."""
    if value < low:
        return "Below range"
    if value > high:
        return "Above range"
    return "Within range"


def outcome(title: str, crop: str, cluster: int, mismatches: int, preferred: str) -> str:
    """HTML for one side (before / after) of the comparison; highlighted when it matches the preferred crop."""
    return outcome_card(title, crop, [
        ("K-Means cluster", f"Cluster {cluster}"),
        ("Outside typical range", f"{mismatches} / {len(FEATURES)}"),
    ], highlight=crop == preferred)


# ------------------------------------------------------------------- the page
baseline = require_assessment()
trained = train_id3()
id3, df = trained["model"], trained["df"]
kmeans = train_kmeans(get_selected_k())

# Slider limits: the range seen in the data, widened so the saved value always fits.
bounds = {f: (min(float(df[f].min()), baseline[f]), max(float(df[f].max()), baseline[f])) for f in FEATURES}


def reset_sliders() -> None:
    """Put every slider back to the saved assessment value (also used by the Reset button)."""
    for f in FEATURES:
        st.session_state[f"wi_{f}"] = int(round(baseline[f])) if f in INT_FEATURES else float(baseline[f])


# (Re)start from the saved assessment when it is new OR when the slider values were
# discarded. Streamlit drops widget values while you are on another page, so we must
# check for missing keys too, otherwise the sliders would come back at their minimum.
signature = tuple(baseline[f] for f in FEATURES)
slider_keys = [f"wi_{f}" for f in FEATURES]
if (st.session_state.get("wi_signature") != signature
        or any(key not in st.session_state for key in slider_keys)):
    reset_sliders()
    st.session_state["wi_signature"] = signature
    st.session_state["wi_preferred"] = id3.predict_with_path(baseline)[0]   # default: what ID3 predicts now

# --- Controls (left) and the before / after comparison (right)
crops = sorted(df[TARGET].unique())
if st.session_state.get("wi_preferred") not in crops:
    st.session_state["wi_preferred"] = crops[0]

controls, results = st.columns([4, 6], gap="large")
with controls, st.container(key="am_card_controls"):
    preferred = st.selectbox("Preferred crop", crops, key="wi_preferred", format_func=crop_title)
    st.markdown('<div class="am-label" style="margin:0.4rem 0 0.2rem 0">Adjust values</div>',
                unsafe_allow_html=True)
    adjusted = {}
    for f in FEATURES:
        lo, hi = bounds[f]
        if f in INT_FEATURES:
            adjusted[f] = float(st.slider(PRETTY[f], math.floor(lo), math.ceil(hi), key=f"wi_{f}"))
        else:
            adjusted[f] = float(st.slider(PRETTY[f], float(lo), float(hi), step=STEP[f], key=f"wi_{f}"))
    st.button("Reset to current assessment", on_click=reset_sliders, icon=":material/restart_alt:")

# --- Typical range of the preferred crop: 10th to 90th percentile of its rows
crop_rows = df[df[TARGET] == preferred]
typical = {f: (float(crop_rows[f].quantile(0.10)), float(crop_rows[f].quantile(0.90))) for f in FEATURES}


def evaluate(values: dict) -> tuple[str, int, int]:
    """Run both models on one set of values -> (ID3 crop, K-Means cluster, parameters out of range)."""
    crop, _, _ = id3.predict_with_path(values)
    cluster = int(kmeans.predict([[values[f] for f in FEATURES]])[0])
    miss = sum(status(values[f], *typical[f]) != "Within range" for f in FEATURES)
    return crop, cluster, miss


b_crop, b_cluster, b_miss = evaluate(baseline)
a_crop, a_cluster, a_miss = evaluate(adjusted)

# --- Before vs after
changed = [f for f in FEATURES if abs(adjusted[f] - baseline[f]) > 1e-9]
with results:
    st.subheader("Before vs after", anchor=False)
    c1, arrow, c2 = st.columns([10, 1, 10], vertical_alignment="center")
    c1.markdown(outcome("Before · saved", b_crop, b_cluster, b_miss, preferred), unsafe_allow_html=True)
    arrow.markdown('<div class="outcome-arrow" aria-hidden="true">&rarr;</div>', unsafe_allow_html=True)
    c2.markdown(outcome("After · sliders", a_crop, a_cluster, a_miss, preferred), unsafe_allow_html=True)
    st.write("")
    if not changed:
        st.caption("No values changed yet. Move a slider to see what happens.")
    else:
        deltas = []
        for f in changed:
            d = adjusted[f] - baseline[f]
            deltas.append(badge(f"{PRETTY[f].split(' (')[0]} {round(d, 1):+g}", "accent"))
        render_html('<div class="am-label" style="margin-bottom:0.35rem">Changed</div>'
                    f'<div class="rule-line" style="margin:0 0 0.9rem 0">{"".join(deltas)}</div>')
        if a_crop == preferred:
            st.success(f"With these changes, ID3 predicts {crop_title(preferred)}.")
        else:
            st.info(f"With these changes, ID3 predicts {crop_title(a_crop)}, not {crop_title(preferred)}.")

# --- Mismatch table
st.subheader(f"Parameters vs {crop_title(preferred)}'s typical range")
section_note("Typical range = the middle 80% (10th to 90th percentile) of that crop's records in the dataset.")
MARK = {"Within range": "● Within range", "Below range": "▼ Below range", "Above range": "▲ Above range"}
table = pd.DataFrame([{
    "Parameter": PRETTY[f],
    "Typical range": f"{typical[f][0]:.1f} to {typical[f][1]:.1f}",
    "Before": round(baseline[f], 2),
    "Before status": status(baseline[f], *typical[f]),
    "After": round(adjusted[f], 2),
    "After status": status(adjusted[f], *typical[f]),
} for f in FEATURES])

show_table(table.style.map(lambda v: status_cell(v == "Within range"), subset=["Before status", "After status"])
           .format(MARK.get, subset=["Before status", "After status"])
           .format("{:g}", subset=["Before", "After"]))

still = [PRETTY[f] for f in FEATURES if status(adjusted[f], *typical[f]) != "Within range"]
if still:
    render_html('<div class="rule-line"><span class="rule-kw">STILL OUTSIDE</span>'
                + "".join(badge(p, "warning") for p in still) + "</div>")
else:
    render_html(badge("All parameters are now within the typical range for this crop", "success"))

st.write("")
st.caption("This simulates model behaviour and does not guarantee real soil outcomes.")
