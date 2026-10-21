"""
utils/farm.py
-------------
Shared pieces for the farmer pages (Home, What should I grow?, Crop Doctor, Plan B):
  * saving the prediction on the current assessment (so a saved check is told apart from a finished prediction)
  * the soil-health panel HTML, built from utils/advice.soil_health()
  * short reasons in the chosen language
  * soil_inputs(): the validated number inputs used by the detail pages
"""
import streamlit as st

from core.db.warehouse import update_assessment_results
from core import advice
from utils.i18n import crop_name, t
from core.models import get_data
from core.preprocessing import FEATURES, VALID_RANGES, validate_inputs
from utils.session import get_assessment_record, get_selected_k
from utils.style import refresh_sidebar
from utils.farm_ui import status_row


def feature_label(feature: str) -> str:
    """'Nitrogen (N)' or its Marathi name."""
    return t(f"f_{feature}")


def ensure_prediction(values: dict, rec: dict) -> None:
    """
    Run the prediction for the current assessment and store it with the saved row (predicted crop and K-Means
    group). Until this has run, the assessment is only "saved". Same behaviour as the Crop Advisor page.
    """
    record = get_assessment_record()
    if record is None:
        return
    cluster = advice.nearest_cluster(values, get_selected_k())
    crop = rec["id3"]
    if (record.get("predicted_crop"), record.get("cluster")) != (crop, cluster):
        if record.get("id") is not None:
            try:
                update_assessment_results(record["id"], crop, cluster)
            except Exception:
                pass   # the page still works if the database is unavailable
        record["predicted_crop"], record["cluster"] = crop, cluster
        refresh_sidebar()


def short_reason(values: dict, crop: str) -> str:
    """The one feature closest to the crop's usual conditions, as a short phrase."""
    f = advice.closest_features(values, crop, 1)[0]
    return f"{feature_label(f)} {advice.pretty_value(f, values[f])} · usual {advice.crop_range_text(crop, f)}"


@st.cache_data(show_spinner=False)
def _span() -> dict:
    """Smallest and largest value of every feature in the whole dataset (the length of a status bar)."""
    df, _ = get_data()
    return {f: (float(df[f].min()), float(df[f].max())) for f in FEATURES}


def soil_rows_html(values: dict, crop: str, features: list[str]) -> str:
    """Status bars for the chosen measurements against the range `crop` grows in."""
    health = advice.soil_health(values, crop).set_index("Feature")
    span = _span()
    rows = []
    for f in features:
        r = health.loc[f]
        lo, hi = span[f]
        scale = (hi - lo) or 1.0
        rows.append(status_row(
            feature_label(f), advice.pretty_value(f, r["Value"]), advice.crop_range_text(crop, f), r["Status"],
            t(r["Status"]),
            pos=(r["Value"] - lo) / scale, band=((r["Low"] - lo) / scale, (r["High"] - lo) / scale)))
    return f'<div class="srows">{"".join(rows)}</div>'


def soil_inputs(prefix: str, caption: bool = True) -> dict | None:
    """
    The seven validated number inputs, pre-filled from the current assessment (or the dataset medians).
    Returns the values, or None when something is outside its allowed range (an error is shown).
    Nothing is saved: these pages only try values out; saving happens on the Soil Analysis page.
    """
    df, _ = get_data()
    record = get_assessment_record()
    start = (record or {}).get("values") or df[FEATURES].median().to_dict()
    names = {"N": 1.0, "P": 1.0, "K": 1.0, "ph": 0.1, "temperature": 0.1, "humidity": 0.1, "rainfall": 0.1}
    values = {}
    cols = st.columns(7)
    for col, (f, step) in zip(cols, names.items()):
        lo, hi, unit = VALID_RANGES[f]
        integer = f in ("N", "P", "K")
        label = f"{feature_label(f)} ({unit})" if unit else feature_label(f)
        values[f] = col.number_input(label, min_value=float(lo), max_value=float(hi), step=step,
                                     value=float(min(max(round(start[f], 1), lo), hi)),
                                     format="%.0f" if integer else "%.1f", key=f"{prefix}_{f}")
    errors = validate_inputs(values)
    if errors:
        for msg in errors:
            st.error(msg)
        return None
    if caption and record is None:
        st.caption("Starting from the dataset's typical values. Save a soil check to use your own field.")
    return values


def crop_options() -> list[str]:
    df, _ = get_data()
    return sorted(df["label"].unique())


crop_label = crop_name   # for selectboxes: format_func=crop_label


def range_short(crop: str, feature: str) -> str:
    """'21–26 °C' style range (10th to 90th percentile of the crop's records) for the small rings."""
    prof = advice.crop_profiles()
    lo, hi = prof["p10"].loc[crop, feature], prof["p90"].loc[crop, feature]
    unit = VALID_RANGES[feature][2]
    fmt = "{:.0f}" if feature in ("N", "P", "K", "rainfall", "humidity", "temperature") else "{:.1f}"
    unit = {"mm": " mm", "°C": "°C", "%": "%"}.get(unit, "")
    return f"{fmt.format(lo)}–{fmt.format(hi)}{unit}"
