"""
pages/8_Model_Council.py
------------------------
Model Council: the ID3 decision tree and Gaussian Naive Bayes look at the SAME soil
assessment and each give an answer. The page shows where they agree, how sure each one
is, which features pushed Naive Bayes towards its answer, and the Bayes formula worked
out with your own numbers.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.models import train_id3, train_naive_bayes
from core.preprocessing import FEATURES
from core.features import NAME
from utils.session import require_assessment
from utils.style import (ALGO, apply_style, badge, crop_title, outcome_card, page_header, render_html,
                         rgba, section_note, show_chart, show_table, style_fig)

apply_style()
page_header(
    "Model Council",
    "Two different classifiers, one soil assessment: a decision tree (ID3) and Gaussian "
    "Naive Bayes. Do they agree, and how sure is each one?",
    eyebrow="Naive Bayes vs ID3 · Classification",
    accent=ALGO["naive_bayes"], crumbs=["Home", "Assess", "Model Council"],
)
with st.expander("How it works"):
    st.markdown(
        "- **ID3** asks a chain of questions about binned values (for example 'rainfall: high') and "
        "stops at a leaf. Its confidence is the share of training rows at that leaf that are the winning crop.\n"
        "- **Naive Bayes** keeps, for every crop, the mean and variance of every feature. A new value is "
        "scored with that crop's bell curve; the seven scores are multiplied (the 'naive' independence "
        "assumption), multiplied by how common the crop is, and turned into probabilities that add up to 1.\n"
        "- Both models are tested on the **same** held-out 20% of the rows, so their accuracies can be compared fairly."
    )

PRETTY = {**NAME, "prior": "Crop frequency (prior)"}

x = require_assessment()
id3, nb = train_id3(), train_naive_bayes()
id3_crop, _, purity = id3["model"].predict_with_path(x)
posterior = nb["model"].posterior(x)
nb_crop, nb_prob = posterior.index[0], float(posterior.iloc[0])
agree = id3_crop == nb_crop

# --- Verdict
st.write("")
render_html(badge("The models agree" if agree else "The models disagree", "success" if agree else "warning"))
left, right = st.columns(2, gap="large")
left.markdown(outcome_card("ID3 decision tree", id3_crop, [
    ("Confidence (leaf purity)", f"{purity:.0%}"),
    ("Held-out accuracy", f"{id3['accuracy']:.1%}"),
], highlight=agree), unsafe_allow_html=True)
right.markdown(outcome_card("Gaussian Naive Bayes", nb_crop, [
    ("Posterior probability", f"{nb_prob:.1%}"),
    ("Held-out accuracy", f"{nb['accuracy']:.1%}"),
], highlight=agree), unsafe_allow_html=True)
if not agree:
    st.caption(f"Naive Bayes gives {crop_title(id3_crop)} (ID3's answer) a probability of "
               f"{posterior.get(id3_crop, 0.0):.1%}.")

# --- Probability bars
st.subheader("How sure is each model?")
section_note("Naive Bayes spreads probability over all crops; ID3 gives one crop with the purity of its leaf.")
top = posterior.head(6).iloc[::-1]
colors = [ALGO["naive_bayes"] if c == nb_crop else rgba(ALGO["naive_bayes"], 0.45) for c in top.index]
fig = go.Figure(go.Bar(x=top.values, y=[crop_title(c) for c in top.index], orientation="h", marker_color=colors,
                       hovertemplate="%{y}: %{x:.1%}<extra></extra>"))
fig.update_layout(xaxis=dict(title="Naive Bayes posterior probability", tickformat=".0%", range=[0, 1.05]),
                  yaxis_title=None)
show_chart(style_fig(fig, height=300), key="council_probs")

# --- Which features pushed the decision
st.subheader("Which features pushed Naive Bayes?")
if len(posterior) < 2:
    st.info("Only one crop in the data: there is no runner-up to compare with.")
else:
    runner_up = posterior.index[1]
    why = nb["model"].explain(x)
    section_note(f"For each feature: how much more typical the value is of {crop_title(nb_crop)} (right, winner) "
                 f"than of {crop_title(runner_up)} (left, runner-up). Units are log-likelihood.")
    ordered = why.iloc[::-1]
    fig = go.Figure(go.Bar(
        x=ordered["Log-likelihood difference"], y=[PRETTY[f] for f in ordered["Feature"]], orientation="h",
        marker_color=[ALGO["naive_bayes"] if v >= 0 else "#3D86C6" for v in ordered["Log-likelihood difference"]],
        hovertemplate="%{y}: %{x:+.2f}<extra></extra>"))
    fig.update_layout(xaxis_title=f"← favours {crop_title(runner_up)}      favours {crop_title(nb_crop)} →",
                      yaxis_title=None)
    show_chart(style_fig(fig, height=330), key="council_why")
    total = float(why["Log-likelihood difference"].sum())
    st.caption(f"The bars add up to {total:+.2f} = ln(odds of {crop_title(nb_crop)} over {crop_title(runner_up)}), "
               f"so {crop_title(nb_crop)} is about {np.exp(min(total, 50)):,.3g} times more likely.")

    # --- Bayes' formula with the user's numbers
    st.subheader("Bayes' formula with your numbers")
    st.latex(r"P(\text{crop}\mid x)\;\propto\;P(\text{crop})\prod_{f=1}^{7}"
             r"\frac{1}{\sqrt{2\pi\sigma_f^2}}\,e^{-(x_f-\mu_f)^2/(2\sigma_f^2)}")
    model = nb["model"]
    wi = int(np.where(model.classes_ == nb_crop)[0][0])
    ll = model.feature_log_likelihood(x)[0, wi]
    worked = pd.DataFrame({
        "Feature": [PRETTY[f] for f in FEATURES],
        "Your value": [x[f] for f in FEATURES],
        f"Mean for {crop_title(nb_crop)}": model.mean_[wi],
        "Spread (σ)": np.sqrt(model.var_[wi]),
        "Distance (σ units)": [(x[f] - model.mean_[wi][i]) / np.sqrt(model.var_[wi][i]) for i, f in enumerate(FEATURES)],
        "Log-likelihood": ll,
    })
    show_table(worked, column_config={c: st.column_config.NumberColumn(format="%.2f") for c in worked.columns[1:]})
    log_prior = float(np.log(model.prior_[wi]))
    jll = model.joint_log_likelihood(x)[0]
    st.markdown(
        f"- ln P({crop_title(nb_crop)}) = **{log_prior:.2f}** (the crop makes up {model.prior_[wi]:.1%} of the rows)\n"
        f"- sum of the seven log-likelihoods = **{ll.sum():.2f}**\n"
        f"- joint score = {log_prior:.2f} + {ll.sum():.2f} = **{jll[wi]:.2f}**\n"
        f"- softmax over all {len(jll)} crops (subtract the largest score, exponentiate, divide by the sum) "
        f"→ P({crop_title(nb_crop)} | your values) = **{nb_prob:.1%}**"
    )

# --- Per-crop accuracy comparison
st.subheader("Accuracy for each crop")
section_note("Held-out accuracy of each model on the crop's unseen rows (same 20% test split for both).")
per = (id3["per_crop"][["Crop", "Accuracy"]].rename(columns={"Accuracy": "ID3"})
       .merge(nb["per_crop"][["Crop", "Accuracy"]].rename(columns={"Accuracy": "Naive Bayes"}), on="Crop")
       .sort_values(["ID3", "Naive Bayes"]).reset_index(drop=True))
fig = go.Figure()
for name, color in (("ID3", ALGO["id3"]), ("Naive Bayes", ALGO["naive_bayes"])):
    fig.add_trace(go.Bar(x=[crop_title(c) for c in per["Crop"]], y=per[name], name=name, marker_color=color,
                         hovertemplate="%{x}: %{y:.0%}<extra>" + name + "</extra>"))
fig.update_layout(barmode="group", yaxis=dict(tickformat=".0%", range=[0, 1.05], title="Held-out accuracy"),
                  xaxis=dict(tickangle=-45), legend=dict(orientation="h", y=1.1, x=0))
show_chart(style_fig(fig, height=380), key="council_per_crop")
both = (per["ID3"] == 1).sum(), (per["Naive Bayes"] == 1).sum()
st.caption(f"Crops classified perfectly on the test rows: ID3 {both[0]} of {len(per)}, Naive Bayes {both[1]} of {len(per)}.")
