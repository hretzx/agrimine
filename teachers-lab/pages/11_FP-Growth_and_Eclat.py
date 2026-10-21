"""
pages/11_FP-Growth_and_Eclat.py
-------------------------------
FP-Growth and Eclat: two more ways to find frequent itemsets, compared with Apriori on
the same items. All three must return exactly the same itemsets; only the run time differs,
and the times shown here are measured on this machine, never typed in.
"""
import plotly.graph_objects as go
import streamlit as st

from core.models import benchmark_miners, itemset_summary, mining_items
from utils.style import (ALGO, apply_style, badge, card_grid, info_card, page_header, render_html, section_note,
                         show_chart, show_table, style_fig)

apply_style()
page_header(
    "FP-Growth and Eclat",
    "Three miners, one answer: Apriori, FP-Growth and Eclat find the same frequent itemsets. "
    "Which one is quickest on this dataset?",
    eyebrow="FP-Growth · Eclat · Frequent itemsets",
    accent=ALGO["fpgrowth"], crumbs=["Home", "Mine", "FP-Growth and Eclat"],
)
with st.expander("How it works"):
    st.markdown(
        "A *frequent itemset* is a set of items (like `rainfall=high` + `crop=rice`) that appears in at least "
        "the **minimum support** share of the rows.\n\n"
        "- **Apriori** builds itemsets level by level (size 1, then 2, ...) and checks each candidate against the data.\n"
        "- **FP-Growth** squeezes all rows into a compact tree (the FP-tree) that shares common prefixes, then "
        "mines it recursively using each item's *conditional pattern base*, without generating candidates.\n"
        "- **Eclat** stores, for every item, the set of rows that contain it (a bitset). The support of a bigger "
        "itemset is the intersection of those sets.\n"
        "- **Closed** itemsets have no bigger itemset with the same support; **maximal** itemsets have no frequent "
        "bigger itemset at all. Both are shorter summaries of the full list."
    )

items = mining_items()
render_html(card_grid([
    info_card("Apriori", "Level by level, with bitsets. Simple and predictable."),
    info_card("FP-Growth", "One compact tree, then recursion. No candidate lists, but building the tree costs time."),
    info_card("Eclat", "Intersect the row sets of items depth first."),
]))

# --- Benchmark
st.subheader("Run time at different minimum supports")
SUPPORTS = (0.005, 0.01, 0.02, 0.05)
bench = benchmark_miners(SUPPORTS)
section_note(f"{items['n_rows']:,} rows, itemsets up to 5 items. Each time is the best of 3 runs, "
             "measured when this page was first opened.")
colors = {"Apriori": ALGO["apriori"], "FP-Growth": ALGO["fpgrowth"], "Eclat": "#D45BC6"}
fig = go.Figure()
for name in ("Apriori", "FP-Growth", "Eclat"):
    part = bench[bench["Algorithm"] == name]
    fig.add_trace(go.Bar(x=[f"{s:.1%}" for s in part["Min support"]], y=part["Seconds"] * 1000, name=name,
                         marker_color=colors[name], hovertemplate="%{y:.1f} ms<extra>" + name + "</extra>"))
fig.update_layout(barmode="group", xaxis=dict(title="Minimum support", type="category"), yaxis_title="Run time (ms)",
                  legend=dict(orientation="h", y=1.1, x=0))
show_chart(style_fig(fig, height=360), key="miners_bench")

winners = bench.loc[bench.groupby("Min support")["Seconds"].idxmin(), "Algorithm"].value_counts()
slowest = bench.groupby("Algorithm")["Seconds"].sum().idxmax()
st.caption(f"Fastest most often here: {winners.index[0]} ({winners.iloc[0]} of {len(SUPPORTS)} supports); "
           f"slowest overall: {slowest}.")
if slowest == "FP-Growth":
    st.caption("FP-Growth is not the quickest on this small dataset in pure Python: building and walking the tree "
               "costs more than it saves. Its advantage is meant for much larger data with long patterns.")

# --- Same result check
st.subheader("Same result check")
check = bench.pivot(index="Min support", columns="Algorithm", values="Itemsets").reset_index()
check["Same itemsets and counts"] = [bool(bench[bench["Min support"] == s]["Same as Apriori"].all())
                                     for s in check["Min support"]]
show_table(check, column_config={"Min support": st.column_config.NumberColumn(format="%.3f")})
if bench["Same as Apriori"].all():
    render_html(badge("All three miners return identical itemsets and counts", "success"))
else:
    render_html(badge("The miners disagree: this is a bug", "danger"))

# --- Closed / maximal
st.subheader("All, closed and maximal itemsets")
support = st.select_slider("Minimum support", options=list(SUPPORTS), value=0.01, format_func=lambda s: f"{s:.1%}")
summary = itemset_summary(support)
section_note("Number of frequent itemsets of each size. Closed and maximal lists are shorter but keep the same information.")
fig = go.Figure()
for kind, color in (("All frequent", "#8FA39A"), ("Closed", ALGO["fpgrowth"]), ("Maximal", "#E3A92B")):
    part = summary[summary["Kind"] == kind]
    fig.add_trace(go.Bar(x=part["Size"], y=part["Itemsets"], name=kind, marker_color=color))
fig.update_layout(barmode="group", xaxis=dict(title="Items in the set", dtick=1), yaxis_title="Itemsets",
                  legend=dict(orientation="h", y=1.1, x=0))
show_chart(style_fig(fig, height=340), key="miners_closed")
totals = summary.groupby("Kind")["Itemsets"].sum()
a, c, m = (int(totals.get(k, 0)) for k in ("All frequent", "Closed", "Maximal"))
st.caption(f"At {support:.1%} support: {a:,} frequent itemsets, of which {c:,} are closed and {m:,} are maximal.")
