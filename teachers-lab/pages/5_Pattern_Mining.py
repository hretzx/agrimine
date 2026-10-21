"""
pages/5_Pattern_Mining.py
-------------------------
Pattern Mining: Apriori association rules written from scratch.
Every row of the dataset becomes a "basket" of items such as rainfall=high,
ph=acidic and crop=rice. Apriori finds items that often appear together and turns
them into rules like  "humidity=high AND rainfall=high -> crop=rice".
"""
import time

import plotly.express as px
import streamlit as st

from core.algorithms.apriori import apriori, association_rules, make_item_masks
from core.models import get_data
from core.preprocessing import TARGET, discretize_dataframe
from utils.style import (ALGO, CLAY, apply_style, card_grid, crop_title, page_header, render_html, rule_card,
                         section_note, show_chart, show_table, style_fig)

apply_style()
page_header(
    "Pattern Mining",
    "Association rules built from scratch on categorised soil, weather and crop values. "
    "These are associations in historical data, not causal recommendations.",
    eyebrow="Apriori · Association rules",
    accent=ALGO["apriori"], crumbs=["Home", "Mine", "Pattern Mining"],
)


@st.cache_data(show_spinner=False)
def get_items():
    """
    Turn every row into items. N, P, K, temperature, humidity and rainfall become
    low / medium / high; pH becomes acidic / neutral / alkaline; the crop is an item too.
    Returns (item names, one bitset per item, number of rows, list of crops).
    """
    df, _ = get_data()
    labels = discretize_dataframe(df)
    labels["crop"] = df[TARGET].to_numpy()
    names, masks = make_item_masks(labels)
    return names, masks, len(df), sorted(df[TARGET].unique())


@st.cache_data(show_spinner="Mining frequent itemsets...")
def mine(min_support: float, max_len: int):
    """Run Apriori (cached, so moving only the confidence slider is instant)."""
    names, masks, n_rows, _ = get_items()
    started = time.perf_counter()
    frequent = apriori(masks, n_rows, min_support, max_len)
    return frequent, time.perf_counter() - started


names, masks, n_rows, crops = get_items()

# --- Controls
with st.container(key="am_card_controls"):
    c1, c2, c3 = st.columns(3, gap="large")
    min_support = c1.slider("Minimum support", 0.005, 0.10, 0.01, 0.005, format="%.3f",
                            help="Share of all rows that must contain the whole pattern. "
                                 "Each crop makes up only about 4.5% of the rows.")
    min_conf = c2.slider("Minimum confidence", 0.50, 1.00, 0.60, 0.05,
                         help="Of the rows matching the 'if' part, the share that also match the 'then' part.")
    max_len = c3.select_slider("Largest pattern size (items)", options=[2, 3, 4, 5], value=5,
                               help="Bigger patterns find more detailed rules but take longer.")
    f1, f2 = st.columns([1, 2], gap="large", vertical_alignment="bottom")
    crop_choice = f1.selectbox("Filter by crop", ["All crops"] + crops,
                               format_func=lambda c: c if c == "All crops" else crop_title(c))
    only_crop = f2.toggle("Only rules that end in a crop (X -> crop)", value=True,
                          help="Turn this off to also see rules between soil and weather values.")

# --- Mine and build rules
frequent, seconds = mine(min_support, max_len)
rules = association_rules(frequent, names, n_rows, min_conf, "crop=" if only_crop else None)
if crop_choice != "All crops":
    item = f"crop={crop_choice}"
    in_antecedent = rules["Antecedent"].apply(lambda text: item in text.split(" AND "))
    rules = rules[(rules["Consequent"] == item) | in_antecedent].reset_index(drop=True)

st.write("")
m1, m2, m3 = st.columns(3)
m1.metric("Frequent itemsets", f"{len(frequent):,}")
m2.metric("Rules shown", f"{len(rules):,}")
m3.metric("Mining time", f"{seconds:.2f} s")

if rules.empty:
    st.subheader("Rules")
    st.info("No rules meet these settings. Try lowering the minimum support or confidence, "
            "or choose 'All crops'.")
else:
    # --- Strongest rules as cards
    st.subheader("Strongest rules")
    section_note("Ranked by lift, then confidence, then support.")
    render_html(card_grid([
        rule_card(rank, r["Antecedent"], r["Consequent"], r["Confidence"], r["Lift"], r["Support"])
        for rank, (_, r) in enumerate(rules.head(3).iterrows(), start=1)
    ]))

    # --- Rules table (click a column header to sort)
    st.subheader("All rules")
    section_note("Read a row as: when the 'If' part holds, the 'Then' part also holds in the share of "
                 "cases given by confidence. Click a column header to sort.")
    table = rules.rename(columns={"Antecedent": "If (antecedent)", "Consequent": "Then (consequent)"})
    show_table(table, column_config={
        "Support": st.column_config.NumberColumn(format="%.4f"),
        "Confidence": st.column_config.ProgressColumn(format="percent", min_value=0.0, max_value=1.0),
        "Lift": st.column_config.NumberColumn(format="%.2f"),
    })

    # --- Top rules by lift
    st.subheader("Top rules by lift")
    section_note("Lift above 1 means the pattern appears together more often than chance. "
                 "The strongest rule is highlighted.")
    top = rules.head(10).iloc[::-1].copy()          # reversed so the best rule is drawn on top
    top["Rule"] = top["Antecedent"].str.replace(" AND ", " + ") + "  →  " + top["Consequent"]
    fig = px.bar(top, x="Lift", y="Rule", orientation="h", hover_data=["Support", "Confidence"])
    fig.update_traces(marker_color=[ALGO["apriori"]] * (len(top) - 1) + [CLAY])
    fig.update_layout(yaxis_title=None, xaxis_title="Lift")
    show_chart(style_fig(fig, height=max(280, 40 * len(top) + 80)), key="top_rules_chart")

with st.expander("What do support, confidence and lift mean?"):
    st.markdown(
        "- **Support**: the share of all rows that contain the whole pattern (the 'if' and the 'then' together).\n"
        "- **Confidence**: among rows where the 'if' part holds, the share where the 'then' part also holds.\n"
        "- **Lift**: confidence divided by how common the 'then' item is overall. "
        "1 means no link; the higher above 1, the stronger the association."
    )
