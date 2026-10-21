"""
pages/6_Cluster_Explorer.py
---------------------------
Cluster Explorer: K-Means clustering written from scratch.
Groups the records into k clusters of similar soil and weather, draws them on a 2D
map (PCA done by hand with NumPy SVD) and shows which cluster your assessment is
closest to.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.models import (get_data, get_projection, kmeans_diagnostics, project_point,
                          train_kmeans)
from core.preprocessing import FEATURES, TARGET
from core.features import AXIS
from utils.session import SELECTED_K_KEY, get_current_assessment, get_selected_k
from utils.style import (ALGO, CLAY, PALETTE, SEQ_SCALE, SURFACE, apply_style, crop_title, page_header,
                         section_note, show_chart, show_table, style_fig)

apply_style()
page_header(
    "Cluster Explorer",
    "Groups the records into k clusters of similar soil and weather (z-score standardisation, "
    "k-means++ start), shown on a 2D PCA map.",
    eyebrow="K-Means + PCA · Clustering",
    accent=ALGO["kmeans"], crumbs=["Home", "Mine", "Cluster Explorer"],
)

PRETTY = AXIS

df, _ = get_data()
diagnostics = kmeans_diagnostics()

# --- Choose k. The choice is kept in a plain session key so the What-if Lab and the
# Crop Advisor use the same k (widget values are lost when you change pages).
with st.container(key="am_card_k"):
    k = st.slider("Number of clusters (k)", int(diagnostics["k"].min()), int(diagnostics["k"].max()),
                  value=get_selected_k(),
                  help="Use the elbow and silhouette charts at the bottom to choose a sensible k.")
st.session_state[SELECTED_K_KEY] = k

km = train_kmeans(k)
labels = km.labels_
projection = get_projection()
coords = projection["coords"]
row = diagnostics[diagnostics["k"] == k].iloc[0]

st.write("")
m1, m2, m3 = st.columns(3)
m1.metric("Inertia", f"{row['Inertia']:,.0f}", help="Sum of squared distances to the centroids. Lower = tighter clusters.")
m2.metric("Silhouette score", f"{row['Silhouette']:.3f}", help="From -1 to 1. Higher = better separated clusters.")
m3.metric("Variance shown on map", f"{projection['ratio'].sum():.0%}",
          help="Share of the information in the 7 features that the 2D map keeps.")

# --- Where does the current assessment fall?
x = get_current_assessment()
nearest = None
if x is not None:
    values = [[x[f] for f in FEATURES]]
    nearest = int(km.predict(values)[0])
    st.success(f"Your current assessment is closest to **Cluster {nearest}**.")
else:
    st.info("Enter a soil assessment on the Soil Analysis page to see where it falls on this map. "
            "You can still explore the clusters below.")

# --- 2D scatter
st.subheader("Cluster map")
plot = pd.DataFrame({"PC1": coords[:, 0], "PC2": coords[:, 1],
                     "Cluster": [f"Cluster {c}" for c in labels], "Crop": df[TARGET].map(crop_title)})
order = [f"Cluster {c}" for c in range(k)]
fig = px.scatter(plot, x="PC1", y="PC2", color="Cluster", hover_data=["Crop"],
                 category_orders={"Cluster": order}, color_discrete_sequence=PALETTE, opacity=0.85)
fig.update_traces(marker=dict(size=6, line=dict(width=0.5, color=SURFACE)))
if nearest is not None:
    # Fade the other clusters so the nearest one stands out
    for trace in fig.data:
        if trace.name != f"Cluster {nearest}":
            trace.update(opacity=0.22)
    px_, py_ = project_point(projection, x)
    # Same WebGL trace type as the dots, otherwise the star would be drawn underneath them
    fig.add_trace(go.Scattergl(x=[px_], y=[py_], mode="markers", name="Your assessment",
                               marker=dict(size=22, symbol="star", color=CLAY, line=dict(color=SURFACE, width=2))))
fig.update_layout(xaxis_title=f"PC1 ({projection['ratio'][0]:.0%} of variance)",
                  yaxis_title=f"PC2 ({projection['ratio'][1]:.0%} of variance)",
                  legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0))
show_chart(style_fig(fig, height=460), key="cluster_map")
st.caption("Each dot is one record. The 7 standardised features are squeezed into 2 directions (PCA, "
           "NumPy SVD), so distances on the map are only approximate.")

# --- Cluster profiles (average of each feature, original units)
st.subheader("Cluster profiles")
profile = df[FEATURES].groupby(labels).mean()
profile.columns = [PRETTY[f] for f in FEATURES]
profile = profile.round(1)
sizes = pd.Series(labels).value_counts().sort_index()
crop_counts = pd.crosstab(labels, df[TARGET])                 # clusters x crops
top_crop = crop_counts.idxmax(axis=1).map(crop_title)
purity = (crop_counts.max(axis=1) / crop_counts.sum(axis=1) * 100).round(0).astype(int)
profile.insert(0, "Records", sizes)
profile.insert(1, "Most common crop", top_crop)
profile.insert(2, "Share of that crop", purity.astype(str) + "%")
profile.index = [f"Cluster {c}" for c in profile.index]
profile.index.name = "Cluster"
profile = profile.reset_index()
if nearest is not None:
    profile["Cluster"] = profile["Cluster"].where(profile["Cluster"] != f"Cluster {nearest}",
                                                  f"Cluster {nearest}  (nearest to you)")
show_table(profile)
st.caption("Feature columns are the cluster averages in the original units (the centroids).")

# --- Crop distribution per cluster
st.subheader("Crop distribution per cluster")
section_note("Number of records of each crop in each cluster. Dark cells mean a crop is concentrated in one cluster.")
heat = crop_counts.copy()
heat.index = [f"Cluster {c}" for c in heat.index]
heat.columns = [crop_title(c) for c in heat.columns]
fig_heat = px.imshow(heat, text_auto=True, aspect="auto", color_continuous_scale=SEQ_SCALE)
fig_heat.update_traces(xgap=2, ygap=2, textfont=dict(size=11))
fig_heat.update_layout(coloraxis_showscale=False, xaxis_title=None, yaxis_title=None)
fig_heat.update_xaxes(showgrid=False)
fig_heat.update_yaxes(showgrid=False)
fig_heat.update_xaxes(tickangle=-45, side="bottom")
show_chart(style_fig(fig_heat, height=max(260, 48 * k + 140)), key="cluster_crop_heatmap")

# --- Elbow and silhouette
st.subheader("Choosing k: elbow and silhouette")
e1, e2 = st.columns(2)
with e1:
    fig_e = px.line(diagnostics, x="k", y="Inertia", markers=True, color_discrete_sequence=[ALGO["kmeans"]])
    fig_e.add_vline(x=k, line_dash="dot", line_color=CLAY, line_width=2)
    fig_e.update_layout(title="Elbow plot (inertia)")
    show_chart(style_fig(fig_e, height=300), key="elbow_chart")
with e2:
    fig_s = px.line(diagnostics, x="k", y="Silhouette", markers=True, color_discrete_sequence=[ALGO["kmeans"]])
    fig_s.add_vline(x=k, line_dash="dot", line_color=CLAY, line_width=2)
    fig_s.update_layout(title="Silhouette score")
    show_chart(style_fig(fig_s, height=300), key="silhouette_chart")
best_k = int(diagnostics.loc[diagnostics["Silhouette"].idxmax(), "k"])
st.caption(f"Elbow: inertia always falls as k grows; pick the k where the drop starts to flatten. "
           f"Silhouette: higher is better; it is highest at k = {best_k} here. "
           f"Weigh both charts and your own judgement: a very small k often scores well but merges "
           f"different crops. The dotted line marks your current k = {k}.")
