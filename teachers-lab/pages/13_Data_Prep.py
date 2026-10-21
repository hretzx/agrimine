"""
pages/13_Data_Prep.py
---------------------
Data Prep: look at the data before modelling it. Descriptive statistics, box plots and
histograms, correlations, IQR outliers, two ways of rescaling, two ways of binning, and
data reduction with PCA.
"""
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.algorithms.pca import pca_fit
from core.models import get_data
from core.preprocessing import (FEATURES, equal_frequency_bins, equal_width_bins, iqr_outlier_table,
                                 min_max_scale, z_score_scale)
from core.features import AXIS
from utils.style import (ALGO, DIVERGING_SCALE, INK, PALETTE, apply_style, page_header, section_note, show_chart,
                         show_table, style_fig)

apply_style()
page_header(
    "Data Prep",
    "Check the data before modelling it: spread, outliers, correlations, scaling, binning "
    "and how many dimensions are really needed.",
    eyebrow="Exploration · Preprocessing",
    accent=ALGO["prep"], crumbs=["Home", "Data", "Data Prep"],
)
with st.expander("How it works"):
    st.markdown(
        "- **Descriptive statistics** summarise each feature: count, mean, spread and the five-number summary.\n"
        "- **IQR rule:** the middle half of the values lies between Q1 and Q3. A value more than 1.5 × (Q3 − Q1) "
        "beyond either end is flagged as an outlier.\n"
        "- **Min-max** scaling squeezes values into 0 to 1; **z-score** scaling centres them on 0 with a spread of 1.\n"
        "- **Binning:** *equal-width* bins have the same size on the number line; *equal-frequency* bins hold the "
        "same number of rows.\n"
        "- **PCA** finds new axes that capture the most variation. If a few axes hold most of it, the other "
        "dimensions can be dropped (data reduction)."
    )

PRETTY = AXIS
df, _ = get_data()
X = df[FEATURES]

# --- Descriptive statistics
st.subheader("Descriptive statistics")
stats = X.describe().T
stats["skew"] = X.skew()
stats.index = [PRETTY[f] for f in stats.index]
show_table(stats.reset_index().rename(columns={"index": "Feature"}), column_config={
    c: st.column_config.NumberColumn(format="%.2f") for c in stats.columns if c != "count"})

# --- Distribution of one feature
st.subheader("Distribution")
feature = st.selectbox("Feature", FEATURES, format_func=PRETTY.get)
left, right = st.columns(2)
fig = px.histogram(df, x=feature, nbins=30, color_discrete_sequence=[ALGO["prep"]])
fig.update_layout(xaxis_title=PRETTY[feature], yaxis_title="Rows", bargap=0.05)
left.markdown("**Histogram**")
with left:
    show_chart(style_fig(fig, height=300), key="prep_hist")
fig = go.Figure(go.Box(x=df[feature], name="", marker_color=ALGO["prep"], boxpoints="outliers", line=dict(width=2)))
fig.update_layout(xaxis_title=PRETTY[feature], showlegend=False)
right.markdown("**Box plot**")
with right:
    show_chart(style_fig(fig, height=300), key="prep_box")

# --- Scaling
st.subheader("Scaling")
scale = st.radio("Method", ["Min-max (0 to 1)", "Z-score (mean 0, std 1)"], horizontal=True)
scaled = min_max_scale(X) if scale.startswith("Min") else z_score_scale(X)
section_note("All seven features on the same scale: before scaling, rainfall (hundreds) would dwarf pH (single digits).")
fig = go.Figure()
for i, f in enumerate(FEATURES):
    fig.add_trace(go.Box(y=scaled[f], name=PRETTY[f].split(" (")[0], marker_color=PALETTE[i], boxpoints=False))
fig.update_layout(showlegend=False, yaxis_title=scale.split(" (")[0])
show_chart(style_fig(fig, height=340), key="prep_scaled")

# --- Correlation
st.subheader("Correlation")
corr = X.corr()
fig = px.imshow(corr.round(2), zmin=-1, zmax=1, color_continuous_scale=DIVERGING_SCALE, text_auto=True, aspect="auto")
fig.update_layout(coloraxis_showscale=False, xaxis_title=None, yaxis_title=None)
fig.update_xaxes(showgrid=False)
fig.update_yaxes(showgrid=False)
fig.update_xaxes(ticktext=[PRETTY[f].split(" (")[0] for f in FEATURES], tickvals=list(range(len(FEATURES))))
fig.update_yaxes(ticktext=[PRETTY[f].split(" (")[0] for f in FEATURES], tickvals=list(range(len(FEATURES))))
show_chart(style_fig(fig, height=400), key="prep_corr")
pairs = corr.where(np.triu(np.ones(corr.shape, dtype=bool), k=1)).stack()
top = pairs.abs().idxmax()
st.caption(f"Strongest relationship: {PRETTY[top[0]]} and {PRETTY[top[1]]} (r = {pairs[top]:+.2f}).")

# --- Outliers
st.subheader("Outliers (IQR rule)")
out = iqr_outlier_table(df)
out["Feature"] = out["Feature"].map(PRETTY)
out["Share of rows"] = out["Outliers"] / len(df)
show_table(out, column_config={
    "Lower fence": st.column_config.NumberColumn(format="%.2f"),
    "Upper fence": st.column_config.NumberColumn(format="%.2f"),
    "Share of rows": st.column_config.ProgressColumn(format="percent", min_value=0.0, max_value=1.0)})
st.caption("Outliers are unusual, not necessarily wrong: a crop that likes a lot of rain has a legitimate high "
           "rainfall. They are flagged in the Data Lake's curated file, not deleted.")

# --- Binning
st.subheader("Binning")
b1, b2 = st.columns([2, 1])
method = b1.radio("Binning method", ["Equal-width", "Equal-frequency"], horizontal=True)
n_bins = b2.slider("Number of bins", 2, 10, 5)
values = df[feature].to_numpy(float)
bins, edges = (equal_width_bins if method == "Equal-width" else equal_frequency_bins)(values, n_bins)
counts = np.bincount(bins, minlength=n_bins)
names = [f"{edges[i]:.1f} to {edges[i + 1]:.1f}" for i in range(n_bins)]
fig = go.Figure(go.Bar(x=names, y=counts, marker_color=ALGO["prep"], text=counts, textposition="outside",
                       textfont=dict(color=INK), cliponaxis=False))
fig.update_layout(xaxis_title=f"{PRETTY[feature]}: bin range", yaxis_title="Rows")
show_chart(style_fig(fig, height=320), key="prep_bins")
st.caption(f"{method} bins hold between {counts.min():,} and {counts.max():,} rows"
           + (": the same width, very different counts when the data is skewed." if method == "Equal-width"
              else ": about the same count, with different widths."))

# --- Data reduction with PCA
st.subheader("Data reduction (PCA)")
_, _, ratio = pca_fit(z_score_scale(X).to_numpy(), n_components=len(FEATURES))
cumulative = np.cumsum(ratio)
goal = st.slider("Keep at least this much of the variation", 0.50, 0.99, 0.90, 0.01, format="%.2f")
needed = int(np.searchsorted(cumulative, goal) + 1)
fig = go.Figure()
fig.add_trace(go.Bar(x=[f"PC{i + 1}" for i in range(len(ratio))], y=ratio, name="Each component",
                     marker_color=[ALGO["prep"] if i < needed else "#B9CDBE" for i in range(len(ratio))]))
fig.add_trace(go.Scatter(x=[f"PC{i + 1}" for i in range(len(ratio))], y=cumulative, name="Cumulative", mode="lines+markers",
                         line=dict(color="#1E3A2B", width=2)))
fig.update_layout(yaxis=dict(tickformat=".0%", title="Explained variance", range=[0, 1.05]),
                  legend=dict(orientation="h", y=1.1, x=0))
show_chart(style_fig(fig, height=320), key="prep_pca")
st.caption(f"{needed} of {len(FEATURES)} components keep {cumulative[needed - 1]:.1%} of the variation "
           f"(goal {goal:.0%}).")
