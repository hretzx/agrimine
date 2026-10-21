"""
db/warehouse.py
---------------
ALL database code lives in this one module.

Part 1  Saved soil assessments (used by Soil Analysis, Crop Advisor, Dashboard).
Part 2  The data warehouse: a star schema, an ETL function and the OLAP queries
        (slice, dice, roll-up, drill-down) used by the Data Insights page.

Moving from SQLite to MySQL later only needs these changes in THIS file:
  1. connection()   - open a MySQL connection instead of sqlite3.connect(...)
                      (and drop the SQLite-only PRAGMA line)
  2. PARAM          - MySQL drivers use "%s" instead of "?" for query values
  3. _table_names() - list tables with SHOW TABLES instead of sqlite_master
  4. the CREATE TABLE statements - INTEGER PRIMARY KEY -> INT PRIMARY KEY (and
     AUTOINCREMENT -> AUTO_INCREMENT), REAL -> DOUBLE, TEXT -> VARCHAR(50)
Nothing else in the project talks to the database.
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pandas as pd

from core.preprocessing import (FEATURES, PH_ACIDIC_BELOW, PH_ALKALINE_ABOVE, TARGET, category_cutoffs,
                                 discretize_dataframe, load_dataset)

DB_PATH = Path(os.environ.get("AGRIMINE_DB") or Path(__file__).resolve().parent.parent.parent / "data" / "agrimine.db")   # default <repo>/data/agrimine.db; AGRIMINE_DB overrides it
PARAM = "?"   # query-value placeholder (SQLite). MySQL would use "%s".


@contextmanager
def connection():
    """
    The single place that opens the database. Commits when the block succeeds,
    rolls back if it fails, and always closes the connection.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")      # make SQLite enforce foreign keys
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# =============================================================================
# PART 1 - saved soil assessments
# =============================================================================
NEW_ASSESSMENT_COLUMNS = {"probability": "REAL", "id3_crop": "TEXT", "model_version": "TEXT"}   # added after the first release


def init_db() -> None:
    """Create the assessments table if it does not exist yet, and add the newer columns to an older table (safe on every run)."""
    with connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS assessments (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at     TEXT NOT NULL,
                N              REAL, P REAL, K REAL,
                ph             REAL, temperature REAL,
                humidity       REAL, rainfall REAL,
                predicted_crop TEXT,    -- the model's answer; NULL only on rows saved by the old Soil Analysis page
                cluster_id     INTEGER, -- the K-Means group of the check
                probability    REAL,    -- Naive Bayes probability of predicted_crop
                id3_crop       TEXT,    -- the ID3 tree's second opinion
                model_version  TEXT     -- which models and rules produced the prediction
            )
            """
        )
        have = {row[1] for row in conn.execute("PRAGMA table_info(assessments)")}
        for column, kind in NEW_ASSESSMENT_COLUMNS.items():       # migrate a database created by an earlier version
            if column not in have:
                conn.execute(f"ALTER TABLE assessments ADD COLUMN {column} {kind}")


def save_assessment(values: dict, predicted_crop: str | None = None,
                    cluster_id: int | None = None) -> int:
    """Insert one soil assessment and return its id."""
    init_db()
    with connection() as conn:
        cur = conn.execute(
            f"""
            INSERT INTO assessments
                (created_at, N, P, K, ph, temperature, humidity, rainfall,
                 predicted_crop, cluster_id)
            VALUES ({", ".join([PARAM] * 10)})
            """,
            (datetime.now().strftime("%Y-%m-%d %H:%M"),
             values["N"], values["P"], values["K"], values["ph"],
             values["temperature"], values["humidity"], values["rainfall"],
             predicted_crop, cluster_id),
        )
        return cur.lastrowid


def update_assessment_results(assessment_id: int, predicted_crop: str,
                              cluster_id: int | None) -> None:
    """Store the ID3 prediction and K-Means cluster on an existing assessment row."""
    init_db()
    with connection() as conn:
        conn.execute(
            f"UPDATE assessments SET predicted_crop = {PARAM}, cluster_id = {PARAM} "
            f"WHERE id = {PARAM}",
            (predicted_crop, cluster_id, assessment_id),
        )


def get_recent_assessments(limit: int = 10) -> pd.DataFrame:
    """Return the most recent saved assessments (newest first)."""
    init_db()
    with connection() as conn:
        return pd.read_sql_query(
            f"SELECT * FROM assessments ORDER BY id DESC LIMIT {PARAM}", conn, params=(limit,)
        )


def count_assessments() -> int:
    """How many assessments have been saved so far."""
    init_db()
    with connection() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM assessments").fetchone()[0])


def assessments_per_day() -> pd.DataFrame:
    """Number of assessments saved on each day (oldest first): columns day, saved."""
    init_db()
    with connection() as conn:
        return pd.read_sql_query(
            "SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS saved "
            "FROM assessments GROUP BY day ORDER BY day", conn)


def get_all_assessments() -> pd.DataFrame:
    """Every saved assessment (oldest first), used for the Data Lake's JSON export."""
    init_db()
    with connection() as conn:
        return pd.read_sql_query("SELECT * FROM assessments ORDER BY id", conn)


# =============================================================================
# PART 2 - star schema (data warehouse)
# =============================================================================
# One fact table in the middle (one row per soil/weather observation) surrounded
# by dimension tables that describe each observation. Only attributes that exist
# in the dataset are used: crop, rainfall, pH and temperature.
#
#                      dim_crop
#                         |
#   dim_rainfall_category -- fact_crop_observation -- dim_ph_category
#                         |
#                  dim_temp_category
STAR_SCHEMA_SQL = [
    "DROP TABLE IF EXISTS fact_crop_observation",
    "DROP TABLE IF EXISTS dim_crop",
    "DROP TABLE IF EXISTS dim_rainfall_category",
    "DROP TABLE IF EXISTS dim_ph_category",
    "DROP TABLE IF EXISTS dim_temp_category",
    """CREATE TABLE dim_crop (
           crop_key   INTEGER PRIMARY KEY,
           crop_name  TEXT NOT NULL UNIQUE
       )""",
    """CREATE TABLE dim_rainfall_category (
           rainfall_key  INTEGER PRIMARY KEY,
           category_name TEXT NOT NULL,      -- low / medium / high
           sort_order    INTEGER NOT NULL,
           range_text    TEXT                -- human-readable definition
       )""",
    """CREATE TABLE dim_ph_category (
           ph_key        INTEGER PRIMARY KEY,
           category_name TEXT NOT NULL,      -- acidic / neutral / alkaline
           sort_order    INTEGER NOT NULL,
           range_text    TEXT
       )""",
    """CREATE TABLE dim_temp_category (
           temp_key      INTEGER PRIMARY KEY,
           category_name TEXT NOT NULL,      -- low / medium / high
           sort_order    INTEGER NOT NULL,
           range_text    TEXT
       )""",
    """CREATE TABLE fact_crop_observation (
           observation_id INTEGER PRIMARY KEY,
           crop_key       INTEGER NOT NULL,
           rainfall_key   INTEGER NOT NULL,
           ph_key         INTEGER NOT NULL,
           temp_key       INTEGER NOT NULL,
           nitrogen       REAL,              -- measures (the original numbers)
           phosphorus     REAL,
           potassium      REAL,
           temperature    REAL,
           humidity       REAL,
           ph             REAL,
           rainfall       REAL,
           FOREIGN KEY (crop_key)     REFERENCES dim_crop (crop_key),
           FOREIGN KEY (rainfall_key) REFERENCES dim_rainfall_category (rainfall_key),
           FOREIGN KEY (ph_key)       REFERENCES dim_ph_category (ph_key),
           FOREIGN KEY (temp_key)     REFERENCES dim_temp_category (temp_key)
       )""",
]

WAREHOUSE_TABLES = ["dim_crop", "dim_rainfall_category", "dim_ph_category",
                    "dim_temp_category", "fact_crop_observation"]

# Dimension name (shown in the UI) -> where it lives in the star schema.
#   order = the column used to sort members (low -> high, acidic -> alkaline, A -> Z)
DIMENSIONS = {
    "Crop":        {"alias": "crop",        "table": "dim_crop",              "key": "crop_key",
                    "label": "crop_name",       "order": "crop_name"},
    "Rainfall":    {"alias": "rainfall",    "table": "dim_rainfall_category", "key": "rainfall_key",
                    "label": "category_name",   "order": "sort_order"},
    "pH":          {"alias": "ph",          "table": "dim_ph_category",       "key": "ph_key",
                    "label": "category_name",   "order": "sort_order"},
    "Temperature": {"alias": "temperature", "table": "dim_temp_category",     "key": "temp_key",
                    "label": "category_name",   "order": "sort_order"},
}

# Measure name (shown in the UI) -> column of the fact table (None = just count rows)
MEASURES = {
    "Record count": None,
    "Nitrogen (N)": "nitrogen",
    "Phosphorus (P)": "phosphorus",
    "Potassium (K)": "potassium",
    "Temperature (°C)": "temperature",
    "Humidity (%)": "humidity",
    "pH": "ph",
    "Rainfall (mm)": "rainfall",
}


# ------------------------------------------------------------------------- ETL
def run_etl(df: pd.DataFrame | None = None, source: str | None = None) -> list[dict]:
    """
    Extract - Transform - Load: rebuild the whole warehouse from the CSV.
      EXTRACT   read data/Crop_recommendation.csv, OR use the dataframe passed in
                (the Data Lake page passes its cleaned "curated" file; `source` names it
                in the log)
      TRANSFORM check the data, turn numbers into categories (low/medium/high ...)
      LOAD      create the star schema, fill dimension tables, then the fact table
      VERIFY    row counts match and no fact row points to a missing dimension row
    Returns the ETL log as a list of {time, stage, message} and also stores it in
    the etl_log table so the page can show it later.
    """
    log: list[dict] = []

    def note(stage: str, message: str) -> None:
        log.append({"time": datetime.now().strftime("%H:%M:%S"), "stage": stage, "message": message})

    # ---- EXTRACT
    if df is None:
        df, synthetic = load_dataset()
        source = "generated sample data" if synthetic else "Crop_recommendation.csv"
    else:
        missing = set(FEATURES + [TARGET]) - set(df.columns)
        if missing:
            raise ValueError(f"The data for the warehouse is missing columns: {sorted(missing)}")
        df = df[FEATURES + [TARGET]].reset_index(drop=True)
        source = source or "a dataframe passed to run_etl()"
    note("EXTRACT", f"Read {len(df):,} rows x {df.shape[1]} columns from {source}.")

    # ---- TRANSFORM
    n_missing = int(df.isna().sum().sum())
    n_dupes = int(df.duplicated().sum())
    note("TRANSFORM", f"Data check: {n_missing} missing values, {n_dupes} duplicate rows.")
    cutoffs = category_cutoffs(df)
    labels = discretize_dataframe(df, cutoffs)
    rain_lo, rain_hi = cutoffs["rainfall"]
    temp_lo, temp_hi = cutoffs["temperature"]
    note("TRANSFORM", f"Rainfall categories: low < {rain_lo:.1f} mm <= medium < {rain_hi:.1f} mm <= high "
                      "(bottom / middle / top third of records).")
    note("TRANSFORM", f"Temperature categories: low < {temp_lo:.1f} C <= medium < {temp_hi:.1f} C <= high.")
    note("TRANSFORM", f"pH categories: acidic < {PH_ACIDIC_BELOW}, neutral {PH_ACIDIC_BELOW} to "
                      f"{PH_ALKALINE_ABOVE}, alkaline > {PH_ALKALINE_ABOVE}.")

    # Dimension rows: (key, category_name, sort_order, range_text)
    rainfall_dim = [(1, "low", 1, f"< {rain_lo:.1f} mm"),
                    (2, "medium", 2, f"{rain_lo:.1f} to {rain_hi:.1f} mm"),
                    (3, "high", 3, f">= {rain_hi:.1f} mm")]
    temp_dim = [(1, "low", 1, f"< {temp_lo:.1f} C"),
                (2, "medium", 2, f"{temp_lo:.1f} to {temp_hi:.1f} C"),
                (3, "high", 3, f">= {temp_hi:.1f} C")]
    ph_dim = [(1, "acidic", 1, f"< {PH_ACIDIC_BELOW}"),
              (2, "neutral", 2, f"{PH_ACIDIC_BELOW} to {PH_ALKALINE_ABOVE}"),
              (3, "alkaline", 3, f"> {PH_ALKALINE_ABOVE}")]
    crops = sorted(df[TARGET].unique())
    crop_dim = [(i + 1, name) for i, name in enumerate(crops)]
    crop_key = {name: key for key, name in crop_dim}
    cat_key = {"low": 1, "medium": 2, "high": 3, "acidic": 1, "neutral": 2, "alkaline": 3}

    fact_rows = [
        (i + 1, crop_key[crop], cat_key[rain], cat_key[ph_cat], cat_key[temp],
         float(n), float(p), float(k), float(t), float(h), float(ph), float(r))
        for i, (crop, rain, ph_cat, temp, n, p, k, t, h, ph, r) in enumerate(zip(
            df[TARGET], labels["rainfall"], labels["ph"], labels["temperature"],
            df["N"], df["P"], df["K"], df["temperature"], df["humidity"], df["ph"], df["rainfall"]))
    ]
    note("TRANSFORM", f"Mapped every row to a crop, rainfall, pH and temperature category "
                      f"({len(fact_rows):,} fact rows prepared).")

    # ---- LOAD
    with connection() as conn:
        for statement in STAR_SCHEMA_SQL:
            conn.execute(statement)
        note("LOAD", "Created star schema: 4 dimension tables + fact_crop_observation.")
        conn.executemany(f"INSERT INTO dim_crop VALUES ({PARAM}, {PARAM})", crop_dim)
        conn.executemany(f"INSERT INTO dim_rainfall_category VALUES ({', '.join([PARAM] * 4)})", rainfall_dim)
        conn.executemany(f"INSERT INTO dim_ph_category VALUES ({', '.join([PARAM] * 4)})", ph_dim)
        conn.executemany(f"INSERT INTO dim_temp_category VALUES ({', '.join([PARAM] * 4)})", temp_dim)
        note("LOAD", f"Loaded dimensions: {len(crop_dim)} crops, {len(rainfall_dim)} rainfall, "
                     f"{len(ph_dim)} pH and {len(temp_dim)} temperature categories.")
        conn.executemany(f"INSERT INTO fact_crop_observation VALUES ({', '.join([PARAM] * 12)})", fact_rows)
        note("LOAD", f"Loaded {len(fact_rows):,} rows into fact_crop_observation.")

        # ---- VERIFY
        loaded = conn.execute("SELECT COUNT(*) FROM fact_crop_observation").fetchone()[0]
        ok = "OK" if loaded == len(df) else "MISMATCH"
        note("VERIFY", f"Row count check: CSV {len(df):,} vs warehouse {loaded:,} -> {ok}.")
        orphans = 0
        for dim in DIMENSIONS.values():
            orphans += conn.execute(
                f"SELECT COUNT(*) FROM fact_crop_observation f "
                f"LEFT JOIN {dim['table']} d ON f.{dim['key']} = d.{dim['key']} "
                f"WHERE d.{dim['key']} IS NULL"
            ).fetchone()[0]
        note("VERIFY", f"Foreign key check: {orphans} fact rows point to a missing dimension row -> "
                       f"{'OK' if orphans == 0 else 'PROBLEM'}.")
        note("DONE", "ETL finished.")

        # Keep the log so it can be shown again after a page reload
        conn.execute("DROP TABLE IF EXISTS etl_log")
        conn.execute("CREATE TABLE etl_log (step INTEGER, logged_at TEXT, stage TEXT, message TEXT)")
        conn.executemany(f"INSERT INTO etl_log VALUES ({', '.join([PARAM] * 4)})",
                         [(i + 1, e["time"], e["stage"], e["message"]) for i, e in enumerate(log)])
    return log


def _table_names(conn) -> set[str]:
    """Names of all tables in the database (SQLite keeps them in sqlite_master)."""
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def get_etl_log() -> list[dict]:
    """Return the log of the most recent ETL run (empty list if it never ran)."""
    with connection() as conn:
        if "etl_log" not in _table_names(conn):
            return []
        rows = conn.execute("SELECT logged_at, stage, message FROM etl_log ORDER BY step").fetchall()
    return [{"time": t, "stage": s, "message": m} for t, s, m in rows]


def warehouse_ready() -> bool:
    """True when every star-schema table exists and the fact table has rows."""
    with connection() as conn:
        if not set(WAREHOUSE_TABLES) <= _table_names(conn):
            return False
        return conn.execute("SELECT COUNT(*) FROM fact_crop_observation").fetchone()[0] > 0


def ensure_warehouse() -> list[dict]:
    """Build the warehouse on first use. Returns the (stored or fresh) ETL log."""
    if not warehouse_ready():
        return run_etl()
    return get_etl_log()


def table_row_counts() -> pd.DataFrame:
    """Row count of every warehouse table (shown as the schema overview)."""
    with connection() as conn:
        rows = [(t, conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]) for t in WAREHOUSE_TABLES]
    return pd.DataFrame(rows, columns=["Table", "Rows"])


def dimension_definitions() -> pd.DataFrame:
    """The category definitions (what 'high rainfall' means) for the three category dimensions."""
    parts = []
    with connection() as conn:
        for name, d in DIMENSIONS.items():
            if name == "Crop":
                continue
            frame = pd.read_sql_query(
                f"SELECT category_name AS Category, range_text AS Definition "
                f"FROM {d['table']} ORDER BY sort_order", conn)
            frame.insert(0, "Dimension", name)
            parts.append(frame)
    return pd.concat(parts, ignore_index=True)


def dimension_members(dimension: str) -> list[str]:
    """All values of a dimension in a sensible order (low -> high, A -> Z)."""
    d = DIMENSIONS[dimension]
    with connection() as conn:
        rows = conn.execute(f"SELECT {d['label']} FROM {d['table']} ORDER BY {d['order']}").fetchall()
    return [r[0] for r in rows]


# ------------------------------------------------------------------ OLAP query
def olap_query(measure: str, group_by: list[str],
               filters: dict[str, list[str]] | None = None) -> tuple[pd.DataFrame, str]:
    """
    One SQL GROUP BY query over the star schema. This single function powers all
    four OLAP operations:
        SLICE      filters = {one dimension: [one value]}
        DICE       filters = {several dimensions: [several values each]}
        ROLL-UP    fewer group_by dimensions  (less detail, more summarised)
        DRILL-DOWN more group_by dimensions   (more detail)
    measure   - a key of MEASURES ("Record count" or an average of a fact column)
    group_by  - dimension names to group by ([] = one grand-total row)
    filters   - {dimension name: [allowed values]} used in the WHERE clause
    Returns (result table, the SQL text with the values filled in).
    Only dimension/measure names from the lists above can reach the SQL text;
    the filter VALUES are always passed as query parameters.
    """
    filters = {d: list(v) for d, v in (filters or {}).items() if v}
    if measure not in MEASURES:
        raise ValueError(f"Unknown measure: {measure}")
    for d in list(group_by) + list(filters):
        if d not in DIMENSIONS:
            raise ValueError(f"Unknown dimension: {d}")

    # Join each dimension table that is used for grouping or filtering
    used = list(dict.fromkeys(list(group_by) + list(filters)))
    alias = {d: f"d{i}" for i, d in enumerate(used)}
    joins = [
        f"JOIN {DIMENSIONS[d]['table']} {alias[d]} "
        f"ON f.{DIMENSIONS[d]['key']} = {alias[d]}.{DIMENSIONS[d]['key']}"
        for d in used
    ]

    # SELECT: the group-by columns, then the record count, then the average
    select = [f"{alias[d]}.{DIMENSIONS[d]['label']} AS {DIMENSIONS[d]['alias']}" for d in group_by]
    if not group_by:
        select.append("'All records' AS grp")
    select.append("COUNT(*) AS records")
    column = MEASURES[measure]
    if column:
        select.append(f"ROUND(AVG(f.{column}), 2) AS average")

    # WHERE: one IN (...) list per filtered dimension
    where, params = [], []
    for d, values in filters.items():
        where.append(f"{alias[d]}.{DIMENSIONS[d]['label']} IN ({', '.join([PARAM] * len(values))})")
        params.extend(values)

    # GROUP BY / ORDER BY: label plus the sort column so members come out in order
    group_cols, order_cols = [], []
    for d in group_by:
        cfg = DIMENSIONS[d]
        group_cols.append(f"{alias[d]}.{cfg['label']}")
        if cfg["order"] != cfg["label"]:
            group_cols.append(f"{alias[d]}.{cfg['order']}")
        order_cols.append(f"{alias[d]}.{cfg['order']}")

    sql = "SELECT " + ", ".join(select) + "\nFROM fact_crop_observation f"
    for j in joins:
        sql += "\n" + j
    if where:
        sql += "\nWHERE " + "\n  AND ".join(where)
    if group_cols:
        sql += "\nGROUP BY " + ", ".join(group_cols)
        sql += "\nORDER BY " + ", ".join(order_cols)

    with connection() as conn:
        result = pd.read_sql_query(sql, conn, params=params)

    # Friendly column names for the page
    rename = {DIMENSIONS[d]["alias"]: d for d in group_by}
    rename.update({"grp": "Level", "records": "Records", "average": "Average"})
    result = result.rename(columns=rename)

    # The same SQL with the values filled in, for showing to the user
    shown = sql
    for value in params:
        shown = shown.replace(PARAM, "'" + str(value).replace("'", "''") + "'", 1)
    return result, shown
