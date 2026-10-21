"""
pages/10_Hierarchical.py
------------------------
Hierarchical clustering of the 22 crops, written from scratch.
  Agglomerative (bottom-up): start with 22 single crops and keep merging the two closest
                             groups; four ways to measure "closest" (linkage).
  Divisive / DIANA (top-down): start with one group of all crops and keep splitting off
                             the member that is furthest from the rest.
Every crop is described by its average profile over the seven features, standardised.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.algorithms.hierarchical import cut_tree, dendrogram_layout, diana_labels
from core.models import crop_diana, crop_linkage, crop_profiles_standardized
from utils.style import (ALGO, INK_3, PALETTE, apply_style, badge, chip, crop_emoji, crop_title, page_header,
                         render_html, section_note, show_chart, show_table, style_fig)

apply_style()
page_header(
    "Hierarchical",
    "A family tree of the 22 crops: which ones have the most similar soil and weather needs, "
    "built bottom-up (agglomerative) and top-down (DIANA).",
    eyebrow="Agglomerative + DIANA · Clustering",
    accent=ALGO["hierarchical"], crumbs=["Home", "Mine", "Hierarchical"],
)
with st.expander("How it works"):
    st.markdown(
        "- Every crop becomes a point: its average N, P, K, temperature, humidity, pH and rainfall, each "
        "standardised so no feature dominates.\n"
        "- **Agglomerative:** begin with 22 groups of one crop. Repeatedly merge the two closest groups. "
        "*Single* link measures the closest pair of members, *complete* the furthest pair, *average* the mean "
        "of all pairs, and *Ward* the merge that adds the least spread inside the group.\n"
        "- The **height** of a merge is the distance at which it happened. Cutting the tree at a height gives "
        "k clusters.\n"
        "- **Cophenetic correlation** checks how faithfully the tree keeps the original distances (1 = perfectly).\n"
        "- **DIANA** works the other way: the group with the widest diameter is split by moving members that "
        "are closer to a growing 'splinter' group than to the rest."
    )

LINKAGES = {"Ward": "ward", "Average": "average", "Complete": "complete", "Single": "single"}
crops, X = crop_profiles_standardized()

with st.container(key="am_card_controls"):
    c1, c2 = st.columns([3, 2], gap="large")
    method_name = c1.radio("Linkage", list(LINKAGES), horizontal=True,
                           help="How the distance between two groups of crops is measured.")
    k = c2.slider("Cut the tree into k clusters", 2, 10, 4)
method = LINKAGES[method_name]
info = crop_linkage(method)
Z = info["Z"]
labels = cut_tree(Z, k)

m1, m2, m3 = st.columns(3)
m1.metric("Crops", len(crops))
m2.metric("Cophenetic correlation", f"{info['cophenetic']:.3f}",
          help="Correlation between the original distances and the distances the tree implies.")
m3.metric("Last merge height", f"{Z[-1, 2]:.2f}")

# --- Dendrogram
st.subheader("Dendrogram")
section_note("Read from the bottom: crops that join low are alike. Colours show the clusters from the cut; "
             "the dashed line is the cut height.")
layout = dendrogram_layout(Z, k)
fig = go.Figure()
for seg in layout["segments"]:
    color = PALETTE[seg["cluster"] % len(PALETTE)] if seg["cluster"] is not None else INK_3
    fig.add_trace(go.Scatter(x=seg["x"], y=seg["y"], mode="lines", line=dict(color=color, width=2),
                             hovertemplate=f"merge height {seg['height']:.2f}<extra></extra>", showlegend=False))
if layout["threshold"] is not None:
    fig.add_hline(y=layout["threshold"], line=dict(color="#1E3A2B", width=1, dash="dash"))
fig.update_layout(
    xaxis=dict(tickmode="array", tickvals=layout["leaf_x"], tickangle=-60, showgrid=False,
               ticktext=[crop_title(crops[i]) for i in layout["order"]]),
    yaxis=dict(title=f"Merge height ({method_name})"))
show_chart(style_fig(fig, height=480), key="hier_dendro")

# --- Clusters
st.subheader(f"The {k} clusters")
cols = st.columns(min(k, 4))
for c in range(k):
    members = [crops[i] for i in range(len(crops)) if labels[i] == c]
    with cols[c % len(cols)], st.container(key=f"am_card_cluster_{c}"):
        render_html(f'<div class="am-label" style="color:{PALETTE[c % len(PALETTE)]}">Cluster {c + 1} · '
                    f'{len(members)} crops</div>' + "".join(chip(f"{crop_emoji(m)} {crop_title(m)}", crop=True) for m in members))

# --- DIANA
st.subheader("Divisive clustering (DIANA)")
section_note("The same crops split from the top. Each step takes the widest group and breaks off a splinter group.")
splits = crop_diana()
rows = [{"Step": s["step"], "Group diameter": s["diameter"],
         "Splits": f"{len(s['parent'])} crops",
         "Splinter group": ", ".join(crop_title(crops[i]) for i in s["splinter"]),
         "Rest": ", ".join(crop_title(crops[i]) for i in s["rest"])} for s in splits[:min(len(splits), k + 4)]]
show_table(pd.DataFrame(rows), column_config={"Group diameter": st.column_config.NumberColumn(format="%.2f")})

dlabels = diana_labels(X, k)
same = {frozenset(i for i in range(len(crops)) if labels[i] == c) for c in range(k)} == \
       {frozenset(i for i in range(len(crops)) if dlabels[i] == c) for c in range(k)}
render_html(badge(f"At k = {k}, DIANA and {method_name} linkage give "
                  f"{'the same clusters' if same else 'different clusters'}", "success" if same else "info"))
if not same:
    st.caption("They start from opposite ends, so they need not agree.")
    cols = st.columns(min(k, 4))
    for c in range(k):
        members = [crops[i] for i in range(len(crops)) if dlabels[i] == c]
        with cols[c % len(cols)]:
            st.markdown(f"**DIANA cluster {c + 1}**: " + ", ".join(crop_title(m) for m in members))
