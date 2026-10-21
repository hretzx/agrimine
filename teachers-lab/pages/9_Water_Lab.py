"""
pages/9_Water_Lab.py
--------------------
Water Lab: linear regression written from scratch. Pick one feature to predict (the
target) and the features to predict it from. The page fits a simple regression (one
predictor, closed form) and a multiple regression (all predictors, least squares) on 80%
of the rows and scores both on the 20% they never saw.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.models import fit_regression, get_data
from core.preprocessing import FEATURES
from core.features import LABEL_UNIT
from utils.session import get_current_assessment
from utils.style import ALGO, apply_style, page_header, section_note, show_chart, show_table, style_fig

apply_style()
page_header(
    "Water Lab",
    "Predict one soil or weather value from others with linear regression, and see how well "
    "the line holds up on rows it never saw.",
    eyebrow="Regression · Prediction",
    accent=ALGO["regression"], crumbs=["Home", "Assess", "Water Lab"],
)
with st.expander("How it works"):
    st.markdown(
        "- **Simple regression** draws the best straight line y = a + b·x through one predictor. "
        "The slope is b = cov(x, y) / var(x) and the intercept is a = mean(y) − b·mean(x).\n"
        "- **Multiple regression** does the same with several predictors at once: it picks the "
        "coefficients that make the sum of squared errors smallest (`np.linalg.lstsq`).\n"
        "- **R²** is the share of the variation in y the model explains (1 = perfect, 0 = no better than "
        "guessing the average). **Adjusted R²** penalises extra predictors. **RMSE** is the typical error in y's own units.\n"
        "- 80% of the rows fit the model; the numbers shown are measured on the other 20% (held out)."
    )

PRETTY = LABEL_UNIT

df, _ = get_data()

with st.container(key="am_card_controls"):
    c1, c2 = st.columns([1, 2], gap="large")
    target = c1.selectbox("What to predict (target)", FEATURES, index=FEATURES.index("humidity"),
                          format_func=PRETTY.get)
    others = [f for f in FEATURES if f != target]
    strongest = sorted(others, key=lambda f: -abs(df[f].corr(df[target])))   # strongest relationship first
    predictors = c2.multiselect("Predict it from (predictors)", others, default=strongest[:3],
                                format_func=PRETTY.get,
                                help="Simple regression uses the predictor with the strongest correlation.")
if not predictors:
    st.info("Choose at least one predictor.")
    st.stop()
predictors = sorted(predictors, key=lambda f: -abs(df[f].corr(df[target])))
fit = fit_regression(target, tuple(predictors))
simple, multiple = fit["simple"], fit["multiple"]
first = predictors[0]
test = df.iloc[fit["test"]]
st.caption(f"Simple regression uses {PRETTY[first]}, the predictor most correlated with the target "
           f"(r = {df[first].corr(df[target]):+.2f}). Fitted on {len(fit['train']):,} rows, tested on {len(fit['test']):,}.")

# --- Scores on the unseen rows
m1, m2, m3, m4 = st.columns(4)
m1.metric("Simple R²", f"{simple['test_r2']:.3f}", help="Held-out R² of the one-predictor line.")
m2.metric("Multiple R²", f"{multiple['test_r2']:.3f}", help="Held-out R² using all the chosen predictors.")
m3.metric("Multiple adjusted R²", f"{multiple['test_adj_r2']:.3f}")
m4.metric("Multiple RMSE", f"{multiple['test_rmse']:.2f}", help=f"Typical error, in the units of {PRETTY[target]}.")
if multiple["test_r2"] < 0.1:
    st.warning("These predictors explain very little of the target (R² below 0.1): predictions will be close to the average.")

# --- Fitted line
st.subheader("Simple regression: the fitted line")
section_note("Each dot is an unseen test row; the white line is fitted on the training rows.")
model = simple["model"]
xs = np.array([df[first].min(), df[first].max()])
fig = go.Figure()
fig.add_trace(go.Scatter(x=test[first], y=test[target], mode="markers", name="Test rows",
                         marker=dict(size=6, color=ALGO["regression"], opacity=0.6)))
fig.add_trace(go.Scatter(x=xs, y=model.predict(xs), mode="lines", name="Fitted line", line=dict(color="#1E3A2B", width=2.5)))
fig.update_layout(xaxis_title=PRETTY[first], yaxis_title=PRETTY[target], legend=dict(orientation="h", y=1.08, x=0))
show_chart(style_fig(fig, height=380), key="water_line")
st.caption(f"{PRETTY[target]} = {model.intercept_:.3f} + {model.slope_:.4f} × {PRETTY[first]}   "
           f"(held-out R² = {simple['test_r2']:.3f}, training R² = {simple['train_r2']:.3f}).")

# --- Residuals of the multiple model
st.subheader("Multiple regression: residuals")
section_note("Residual = actual − predicted. A good model scatters evenly around the zero line with no pattern.")
pred = multiple["pred"]
resid = test[target].to_numpy(float) - pred
fig = go.Figure(go.Scatter(x=pred, y=resid, mode="markers", marker=dict(size=6, color=ALGO["regression"], opacity=0.6),
                           hovertemplate="predicted %{x:.1f}<br>residual %{y:+.1f}<extra></extra>"))
fig.add_hline(y=0, line=dict(color="#1E3A2B", width=1.5, dash="dot"))
fig.update_layout(xaxis_title=f"Predicted {PRETTY[target]}", yaxis_title="Residual", showlegend=False)
show_chart(style_fig(fig, height=320), key="water_resid")

coefs = pd.DataFrame({"Term": ["Intercept"] + [PRETTY[f] for f in predictors],
                      "Coefficient": [multiple["model"].intercept_] + list(multiple["model"].coef_)})
with st.expander("Coefficients of the multiple regression"):
    show_table(coefs, column_config={"Coefficient": st.column_config.NumberColumn(format="%.4f")})

# --- Predict for the current assessment
st.subheader("Predict for my assessment")
x = get_current_assessment()
if x is None:
    st.info("Enter a soil assessment on the Soil Analysis page to predict its "
            f"{PRETTY[target]} from the predictors you chose.")
else:
    inputs = [[x[f] for f in predictors]]
    guess = float(multiple["model"].predict(inputs)[0])
    one = float(model.predict([x[first]])[0])
    p1, p2, p3 = st.columns(3)
    p1.metric(f"Multiple regression: {PRETTY[target]}", f"{guess:.2f}")
    p2.metric("Simple regression", f"{one:.2f}")
    p3.metric("Value you entered", f"{x[target]:.2f}", delta=f"{x[target] - guess:+.2f} vs multiple", delta_color="off")
    st.caption(f"Typical error of the multiple model on unseen rows: about ±{multiple['test_rmse']:.2f}.")
