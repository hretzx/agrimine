"""
pages/12_Data_Lake.py
---------------------
Data Lake: raw files -> cleaned (curated) file -> star-schema warehouse.
The warehouse that the Data Insights page queries is loaded FROM the curated file, so
you can follow one dataset through all three layers. The file work lives in utils/lake.py.
"""
import pandas as pd
import streamlit as st

from core.db.warehouse import table_row_counts, warehouse_ready
from core.lake import CURATED_NAME, LAKE_DIR, ingest_raw, curate, load_warehouse_from_curated, read_catalog
from utils.style import (ALGO, apply_style, page_header, render_html, section_note, show_table,
                         zone_flow)

apply_style()
page_header(
    "Data Lake",
    "Follow the dataset through three layers: raw files exactly as received, a cleaned "
    "curated file, and the star-schema warehouse.",
    eyebrow="Raw · Curated · Warehouse",
    accent=ALGO["lake"], crumbs=["Home", "Data", "Data Lake"],
)
with st.expander("How it works"):
    st.markdown(
        "- **Raw zone:** a byte-for-byte copy of the source CSV and a JSON export of your saved assessments. "
        "Nothing here is ever edited, so you can always start again.\n"
        "- **Curated zone:** the cleaned CSV. Missing values and duplicate rows are dropped, outliers are *flagged* "
        "with the IQR rule (not removed), and each feature gets a low / medium / high category column.\n"
        "- **Warehouse:** the ETL step reads the curated file and loads the star schema in SQLite, ready for the "
        "slice, dice and drill-down queries on the Data Insights page.\n"
        "- **catalog.json** lists every file with its rows, columns, size, SHA-256 hash and time, so you can "
        "tell when a file changed."
    )

catalog = read_catalog()
raw_n = int((catalog["zone"] == "raw").sum()) if len(catalog) else 0
cur_n = int((catalog["zone"] == "curated").sum()) if len(catalog) else 0
fact_rows = (int(table_row_counts().set_index("Table").loc["fact_crop_observation", "Rows"])
             if warehouse_ready() else 0)
render_html(zone_flow([
    ("Raw zone", f"{raw_n} files, kept as received", "#3D86C6"),
    ("Curated zone", f"{cur_n} cleaned file, outliers flagged", "#2E9E6A"),
    ("Warehouse", f"{fact_rows:,} fact rows" if fact_rows else "not loaded yet", "#8467D0"),
]))

# --- Pipeline controls
st.subheader("Pipeline")
if st.button("Run full pipeline", type="primary", icon=":material/play_arrow:"):
    try:
        with st.status("Running the pipeline...", expanded=True) as status:
            st.write("1. Ingest: copying the source CSV and exporting the assessments into the raw zone")
            ingest_raw()
            st.write("2. Curate: cleaning the CSV, flagging outliers, adding category columns")
            _, report = curate()
            st.write("3. Load: building the warehouse from the curated file")
            etl_log = load_warehouse_from_curated()
            status.update(label="Pipeline finished", state="complete")
        st.session_state["lake_report"] = report
        st.session_state["lake_etl_log"] = etl_log
        st.rerun()
    except Exception as exc:   # show the problem instead of a stack trace
        st.error(f"The pipeline stopped: {exc}")

report = st.session_state.get("lake_report")
if report:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Rows in", f"{report['rows_in']:,}")
    m2.metric("Missing dropped", f"{report['missing_dropped']:,}")
    m3.metric("Duplicates dropped", f"{report['duplicates_dropped']:,}")
    m4.metric("Rows with an outlier", f"{report['rows_with_outlier']:,}", help="Flagged, not removed.")
    log = st.session_state.get("lake_etl_log", [])
    with st.expander("Warehouse load log"):
        st.code("\n".join(f"{e['time']}  {e['stage']:<9} {e['message']}" for e in log), language="text", wrap_lines=True)
elif catalog.empty:
    st.info("The lake is empty. Press **Run full pipeline** to fill it.")

# --- Catalogue
st.subheader("File catalogue")
if catalog.empty:
    st.caption("No files yet.")
else:
    section_note(f"Read from {LAKE_DIR.name}/catalog.json.")
    shown = catalog.copy()
    shown["sha256"] = shown["sha256"].str[:12] + "…"
    shown["size_kb"] = (shown.pop("size_bytes") / 1024).round(1)
    show_table(shown.rename(columns={"file": "File", "zone": "Zone", "rows": "Rows", "columns": "Columns",
                                     "sha256": "Hash (SHA-256)", "created": "Created", "size_kb": "Size (KB)"}))
    curated_path = LAKE_DIR / "curated" / CURATED_NAME
    if curated_path.exists():
        with st.expander("Preview of the curated file"):
            show_table(pd.read_csv(curated_path, nrows=8))

# --- Lake vs warehouse
st.subheader("Lake vs warehouse")
comparison = pd.DataFrame([
    ("Holds", "Files in any shape: CSV, JSON, ...", "Tables with a fixed star schema"),
    ("Structure decided", "When you read the data", "Before the data is loaded"),
    ("Data quality", "Raw zone as received; curated zone cleaned", "Checked and categorised by the ETL"),
    ("Best for", "Keeping everything, reprocessing later", "Fast, repeatable SQL: slice, dice, drill-down"),
    ("In AgriMine", "data/lake/raw and data/lake/curated", "SQLite tables in data/agrimine.db"),
], columns=["", "Data lake", "Data warehouse"])
show_table(comparison)
