"""
pages/7_Data_Insights.py
------------------------
Data Insights: OLAP on a star schema stored in SQLite (see db/warehouse.py).
  Slice      - fix ONE dimension to one value (e.g. only rainfall = high)
  Dice       - pick several values on several dimensions (a sub-cube)
  Roll-up    - summarise: fewer grouping columns, less detail
  Drill-down - add detail: more grouping columns
Every view runs one SQL GROUP BY query, and the SQL text is shown under the result.
"""
import plotly.express as px
import streamlit as st

from core.db.warehouse import (DIMENSIONS, MEASURES, dimension_definitions, dimension_members,
                          ensure_warehouse, olap_query, run_etl, table_row_counts)
from utils.style import (ALGO, PALETTE, apply_style, crop_title, page_header, render_html,
                         show_chart, show_table, star_schema, style_fig)

apply_style()
page_header(
    "Data Insights",
    "A SQLite star schema explored with slice, dice, roll-up and drill-down. Every view is one "
    "SQL GROUP BY query, shown under the result.",
    eyebrow="OLAP · Star schema",
    accent=ALGO["olap"], crumbs=["Home", "Data", "Data Insights"],
)

# ------------------------------------------------------------------ warehouse
# Build the warehouse the first time this page is opened.
with st.spinner("Preparing the data warehouse..."):
    etl_log = ensure_warehouse()

st.subheader("Data warehouse")
left, right = st.columns(2, gap="large")
with left:
    row_counts = table_row_counts()
    counts = dict(zip(row_counts["Table"], row_counts["Rows"]))
    dims = [t for t in counts if t.startswith("dim_")]
    fact = next((t for t in counts if t.startswith("fact_")), "fact_crop_observation")
    with st.container(key="am_card_schema"):
        render_html('<div class="am-label" style="margin-bottom:0.6rem">Star schema · one fact table, '
                    'four dimensions</div>')
        render_html(star_schema((fact, counts.get(fact, 0)), [(t, counts[t]) for t in dims]))
    st.caption("fact_crop_observation holds one row per record and points to the four "
               "dimension tables by key.")
with right:
    head, action = st.columns([3, 2], vertical_alignment="center")
    head.markdown('<div class="am-label">ETL log · last run</div>', unsafe_allow_html=True)
    if action.button("Re-run ETL", icon=":material/refresh:", width="stretch"):
        with st.spinner("Running ETL..."):
            etl_log = run_etl()
    st.code("\n".join(f"{e['time']}  {e['stage']:<9} {e['message']}" for e in etl_log),
            language="text", height=300, wrap_lines=True)

with st.expander("How are the categories defined?"):
    show_table(dimension_definitions())

# -------------------------------------------------------------------- helpers
st.subheader("Explore the cube")
measure = st.selectbox("Measure", list(MEASURES), index=0,
                       help="'Record count' counts rows. Any other measure shows its average.")
VALUE = "Records" if MEASURES[measure] is None else "Average"
VALUE_LABEL = "Number of records" if MEASURES[measure] is None else f"Average {measure}"


def member_label(dimension: str):
    """Display names for dimension members (crop names title-cased)."""
    return crop_title if dimension == "Crop" else str


def chart_and_table(result, group_by, sql, tab):
    """Draw the result as a bar chart (when it has groups), the table and the SQL used."""
    if result.empty:
        st.info("No records match this combination of filters. Widen the selection and try again.")
        return
    if "Crop" in result.columns:
        result = result.assign(Crop=result["Crop"].map(crop_title))
    if group_by:
        if len(group_by) == 1:
            fig = px.bar(result, x=group_by[0], y=VALUE, color_discrete_sequence=[ALGO["olap"]],
                         labels={VALUE: VALUE_LABEL})
        elif len(group_by) == 2:
            fig = px.bar(result, x=group_by[0], y=VALUE, color=group_by[1], barmode="group",
                         color_discrete_sequence=PALETTE, labels={VALUE: VALUE_LABEL})
        else:
            # Three or more grouping columns: join them into one label, show the 15 largest groups
            top = result.sort_values(VALUE, ascending=False).head(15).copy()
            top["Group"] = top[group_by].astype(str).agg(" | ".join, axis=1)
            fig = px.bar(top.iloc[::-1], x=VALUE, y="Group", orientation="h",
                         color_discrete_sequence=[ALGO["olap"]], labels={VALUE: VALUE_LABEL})
            fig.update_layout(yaxis_title=None)
            st.caption("Chart shows the 15 largest groups; the table lists all of them.")
        show_chart(style_fig(fig), key=f"olap_chart_{tab}")
    else:
        st.metric(VALUE_LABEL, f"{result[VALUE].iloc[0]:,.2f}" if VALUE == "Average"
                  else f"{int(result[VALUE].iloc[0]):,}")
    show_table(result)
    render_html('<div class="am-label" style="margin:0.8rem 0 0.35rem 0">SQL used</div>')
    st.code(sql, language="sql")


slice_tab, dice_tab, drill_tab = st.tabs([":material/content_cut: Slice", ":material/grid_view: Dice",
                                         ":material/unfold_more: Roll-up / Drill-down"])

# ---------------------------------------------------------------------- SLICE
with slice_tab:
    st.caption("Slice = cut the cube by fixing one dimension to a single value, "
               "then look at the result broken down by another dimension.")
    s1, s2, s3 = st.columns(3)
    slice_dim = s1.selectbox("Fix this dimension", list(DIMENSIONS), index=1, key="slice_dim")
    # keys include the chosen dimension so a value from one dimension is never reused for another
    slice_value = s2.selectbox("To this value", dimension_members(slice_dim), key=f"slice_value_{slice_dim}",
                               format_func=member_label(slice_dim))
    by_options = [d for d in DIMENSIONS if d != slice_dim]
    slice_by = s3.selectbox("Break down by", by_options, key=f"slice_by_{slice_dim}")
    result, sql = olap_query(measure, [slice_by], {slice_dim: [slice_value]})
    chart_and_table(result, [slice_by], sql, "slice")

# ----------------------------------------------------------------------- DICE
with dice_tab:
    st.caption("Dice = choose several values on several dimensions at once (a smaller cube), "
               "then group the matching records.")
    cols = st.columns(4)
    dice_filters = {}
    for col, dim in zip(cols, DIMENSIONS):
        members = dimension_members(dim)
        dice_filters[dim] = col.multiselect(dim, members, default=members, key=f"dice_{dim}",
                                            format_func=member_label(dim))
    dice_by = st.multiselect("Group by (up to 2)", list(DIMENSIONS), default=["Rainfall", "pH"],
                             max_selections=2, key="dice_by")
    if any(len(v) == 0 for v in dice_filters.values()):
        st.info("Select at least one value in every dimension.")
    elif not dice_by:
        st.info("Choose one or two dimensions to group by.")
    else:
        # A dimension with every value selected does not restrict anything, so skip it
        active = {d: v for d, v in dice_filters.items() if len(v) < len(dimension_members(d))}
        result, sql = olap_query(measure, dice_by, active)
        chart_and_table(result, dice_by, sql, "dice")

# ---------------------------------------------------------- ROLL-UP / DRILL-DOWN
DRILL_PATHS = {
    "Rainfall > pH > Temperature > Crop": ["Rainfall", "pH", "Temperature", "Crop"],
    "Crop > Rainfall > pH > Temperature": ["Crop", "Rainfall", "pH", "Temperature"],
    "Temperature > pH > Rainfall > Crop": ["Temperature", "pH", "Rainfall", "Crop"],
}


def roll_up() -> None:
    st.session_state["olap_level"] = max(0, st.session_state.get("olap_level", 1) - 1)


def drill_down() -> None:
    st.session_state["olap_level"] = min(4, st.session_state.get("olap_level", 1) + 1)


with drill_tab:
    st.caption("Roll-up = remove the most detailed grouping column (summarise). "
               "Drill-down = add the next one (see more detail). Level 0 is the grand total.")
    path_name = st.selectbox("Drill path (order of grouping columns)", list(DRILL_PATHS), key="drill_path")
    path = DRILL_PATHS[path_name]
    level = min(4, max(0, st.session_state.get("olap_level", 1)))

    b1, b2, b3 = st.columns([1, 1, 3])
    b1.button("Roll up", on_click=roll_up, disabled=level == 0, key="btn_roll_up",
              icon=":material/unfold_less:", width="stretch")
    b2.button("Drill down", on_click=drill_down, disabled=level == 4, key="btn_drill_down",
              icon=":material/unfold_more:", width="stretch")
    grouped = path[:level]
    b3.markdown(f"**Level {level} of 4:** " + ("all records (grand total)" if not grouped
                                              else "grouped by " + ", ".join(grouped)))
    result, sql = olap_query(measure, grouped)
    chart_and_table(result, grouped, sql, "drill")
