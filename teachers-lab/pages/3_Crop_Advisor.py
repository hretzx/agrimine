"""
pages/3_Crop_Advisor.py
-----------------------
Crop Advisor: predicts a crop with our own ID3 decision tree, shows the exact
decision path used, and lists 3 alternative crops by profile fit.
"""
import pandas as pd
import streamlit as st

from core.db.warehouse import update_assessment_results
from core import advice
from core.models import train_id3, train_kmeans
from core.features import LABEL_UNIT
from utils.session import FEATURES, get_assessment_record, get_selected_k, require_assessment
from utils.style import (ALGO, apply_style, crop_card, crop_emoji, crop_title, page_header, refresh_sidebar, render_html,
                         result_card, score_bar, section_note, show_table, timeline)

apply_style()
page_header(
    "Crop Advisor",
    "A decision tree built from scratch (entropy + information gain) predicts the crop that "
    "best matches your soil and weather values.",
    eyebrow="ID3 · Decision tree",
    accent=ALGO["id3"], crumbs=["Home", "Assess", "Crop Advisor"],
)
with st.popover("How ID3 decides", icon=":material/info:"):
    st.markdown(
        "ID3 first sorts each value into bins (for example 'rainfall: high'). It then asks the "
        "question that reduces uncertainty the most (information gain), step by step, until it "
        "reaches a crop."
    )

PRETTY = LABEL_UNIT


def profile_fit_ranking(x: dict, exclude: str) -> pd.DataFrame:
    """
    The 3 crops whose average profile is closest to the input, as a 0-100 "profile fit" (same score as the farmer pages:
    utils/advice.match_scores). This is NOT the ID3 tree: it is a separate, simple comparison with crop averages.
    """
    scores = advice.match_scores(x).rename(columns={"Match": "Profile fit"})
    return scores[scores["Crop"] != exclude].head(3).reset_index(drop=True)


# ------------------------------------------------------------------- the page
x = require_assessment()
trained = train_id3()
model, df = trained["model"], trained["df"]
crop, path, purity = model.predict_with_path(x)

# K-Means cluster of this assessment (using the k chosen on the Cluster Explorer page)
k = get_selected_k()
cluster = int(train_kmeans(k).predict([[x[f] for f in FEATURES]])[0])

# Remember the results for other pages and in the database (only when they change)
st.session_state["id3_prediction"] = crop
record = get_assessment_record()
if record is not None and (record.get("predicted_crop"), record.get("cluster")) != (crop, cluster):
    if record.get("id") is not None:
        try:
            update_assessment_results(record["id"], crop, cluster)
        except Exception:
            pass   # the page still works if the database is unavailable
    record["predicted_crop"], record["cluster"] = crop, cluster
    refresh_sidebar()

# --- Prediction card + accuracy
left, right = st.columns([3, 2])
with left:
    render_html(result_card(
        "ID3 recommends", crop_title(crop), emoji=crop_emoji(crop),
        body_html=score_bar(f"Rows at the final tree node that are {crop_title(crop)}", purity * 100),
        sublabel=f"Your profile also sits closest to K-Means cluster {cluster}.",
    ))
with right:
    st.metric("Held-out accuracy", f"{trained['accuracy']:.1%}",
              help="Accuracy on rows the tree never saw during training.")
    st.caption(f"Trained on {trained['n_train']:,} rows, tested on {trained['n_test']:,} unseen rows "
               "(80% / 20% split, same share of every crop).")

# --- Decision path
st.subheader("Decision path for your input")
section_note("Each step is one question the tree asked about your values, from the root downward.")
if not path:
    st.write("The tree predicted directly from the root without asking any question.")
else:
    render_html(timeline(
        [{"feature": PRETTY[s["feature"]], "value": f"{s['value']:.2f}".rstrip("0").rstrip("."),
          "level": s["level"], "range": s["range"], "gain": s["gain"], "rows": f"{s['rows_here']:,}"}
         for s in path],
        final=f"The tree ends at a node where {crop_title(crop)} is the most common crop.",
    ))
    steps = pd.DataFrame([{
        "Step": i + 1,
        "Feature tested": PRETTY[s["feature"]],
        "Your value": round(s["value"], 2),
        "Falls in": s["level"],
        "Range of that bin": s["range"],
        "Info gain": round(s["gain"], 3),
        "Training rows here": s["rows_here"],
    } for i, s in enumerate(path)])
    with st.expander("Decision path as a table"):
        show_table(steps)

# --- Alternatives
st.subheader("Alternative crops")
section_note("Profile-fit ranking, separate from the ID3 tree: how close your values sit to each "
             "crop's average profile in the dataset (0 to 100).")
alts = profile_fit_ranking(x, exclude=crop)
for col, (rank, r) in zip(st.columns(3), alts.iterrows()):
    with col:
        render_html(crop_card(f"Alternative {rank + 1}", r["Crop"],
                              score_bar("Profile fit", r["Profile fit"], accent=True, suffix=" / 100")))

st.write("")
with st.expander("Model details"):
    st.write(
        f"Continuous features were cut into {model.n_bins} equal-frequency bins; the tree stops at "
        f"depth {model.max_depth} (it reached depth {model.depth()} with {model.n_leaves()} leaves)."
    )
    edges = pd.DataFrame({"Bin edges": [", ".join(f"{e:.4g}" for e in model.edges[f]) for f in FEATURES]},
                         index=[PRETTY[f] for f in FEATURES])
    st.dataframe(edges)
    weakest = trained["per_crop"].head(5).copy()
    weakest["Crop"] = weakest["Crop"].map(crop_title)
    st.write("Crops the tree finds hardest (held-out accuracy):")
    show_table(weakest, column_config={
        "Accuracy": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
    })
