"""
utils/lake.py
-------------
The Data Lake: plain files in two zones, then the warehouse loaded from the cleaned file.

  RAW zone      data exactly as it arrived: a copy of the source CSV and a JSON export of
                the saved assessments. Nothing is changed or deleted here.
  CURATED zone  the cleaned CSV: duplicates dropped, missing values dropped, an outlier
                flag for every feature (IQR rule) and a low/medium/high category column.
  WAREHOUSE     the star schema in SQLite, loaded FROM the curated file (db.warehouse.run_etl).
  catalog.json  one entry per file: zone, rows, columns, size, SHA-256 hash and time.

This module does not import streamlit, so it can be tested on its own. Every function
takes the lake folder as an argument (default: data/lake) so tests use a temporary one.
"""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

from core.db.warehouse import get_all_assessments, run_etl
from core.preprocessing import (DATA_DIR, DATA_PATH, FEATURES, SYNTHETIC_PATH, TARGET, discretize_dataframe,
                                 iqr_bounds)

LAKE_DIR = DATA_DIR / "lake"
CURATED_NAME = "crop_curated.csv"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _catalog_entry(path: Path, zone: str, rows: int, columns: int) -> dict:
    return {"file": f"{zone}/{path.name}", "zone": zone, "rows": rows, "columns": columns,
            "size_bytes": path.stat().st_size, "sha256": _sha256(path), "created": _now()}


def read_catalog(lake: Path = LAKE_DIR) -> pd.DataFrame:
    """The catalogue as a table (empty when the pipeline has never run)."""
    path = Path(lake) / "catalog.json"
    if not path.exists():
        return pd.DataFrame(columns=["file", "zone", "rows", "columns", "size_bytes", "sha256", "created"])
    return pd.DataFrame(json.loads(path.read_text())["files"])


def _write_catalog(entries: list[dict], lake: Path) -> None:
    (Path(lake) / "catalog.json").write_text(json.dumps({"updated": _now(), "files": entries}, indent=2))


def source_csv() -> tuple[Path, bool]:
    """The CSV the lake ingests -> (path, is_synthetic). The real file wins when it exists."""
    if DATA_PATH.exists():
        return DATA_PATH, False
    from core.preprocessing import load_dataset
    load_dataset()   # writes the generated stand-in file the first time
    return SYNTHETIC_PATH, True


def ingest_raw(lake: Path = LAKE_DIR, source: Path | None = None) -> list[dict]:
    """Copy the source CSV and export the saved assessments as JSON, untouched, into raw/."""
    lake = Path(lake)
    raw = lake / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    source = Path(source) if source else source_csv()[0]
    copy = raw / source.name
    shutil.copyfile(source, copy)
    entries = [_catalog_entry(copy, "raw", len(pd.read_csv(copy)), len(pd.read_csv(copy, nrows=1).columns))]

    assessments = get_all_assessments()
    export = raw / "assessments_export.json"
    export.write_text(assessments.to_json(orient="records", indent=2))
    entries.append(_catalog_entry(export, "raw", len(assessments), len(assessments.columns)))
    _write_catalog(entries, lake)
    return entries


def curate(lake: Path = LAKE_DIR) -> tuple[pd.DataFrame, dict]:
    """
    Clean the raw CSV into the curated zone. Returns (curated dataframe, what was done).
    Outliers are FLAGGED, not removed: that is a decision for the analyst, not the pipeline.
    """
    lake = Path(lake)
    raw_files = sorted((lake / "raw").glob("*.csv"))
    if not raw_files:
        raise FileNotFoundError("The raw zone has no CSV yet: run the ingest step first.")
    df = pd.read_csv(raw_files[0])
    missing = set(FEATURES + [TARGET]) - set(df.columns)
    if missing:
        raise ValueError(f"The raw CSV is missing columns: {sorted(missing)}")
    df = df[FEATURES + [TARGET]]
    report = {"rows_in": len(df)}

    df = df.dropna()
    report["missing_dropped"] = report["rows_in"] - len(df)
    before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    report["duplicates_dropped"] = before - len(df)

    for f in FEATURES:
        lo, hi = iqr_bounds(df[f])
        df[f"{f}_outlier"] = (df[f] < lo) | (df[f] > hi)
    df["any_outlier"] = df[[f"{f}_outlier" for f in FEATURES]].any(axis=1)
    labels = discretize_dataframe(df[FEATURES + [TARGET]])
    for f in FEATURES:
        df[f"{f}_category"] = labels[f]

    report["rows_out"] = len(df)
    report["rows_with_outlier"] = int(df["any_outlier"].sum())
    curated = lake / "curated"
    curated.mkdir(parents=True, exist_ok=True)
    path = curated / CURATED_NAME
    df.to_csv(path, index=False)

    entries = [e for e in read_catalog(lake).to_dict("records") if e["zone"] == "raw"]
    entries.append(_catalog_entry(path, "curated", len(df), len(df.columns)))
    _write_catalog(entries, lake)
    return df, report


def load_warehouse_from_curated(lake: Path = LAKE_DIR) -> list[dict]:
    """Run the warehouse ETL on the curated file (not on the original CSV). Returns the ETL log."""
    path = Path(lake) / "curated" / CURATED_NAME
    if not path.exists():
        raise FileNotFoundError("The curated zone is empty: run the curate step first.")
    return run_etl(pd.read_csv(path), source=f"lake/curated/{CURATED_NAME}")


def run_pipeline(lake: Path = LAKE_DIR) -> dict:
    """Raw -> curated -> warehouse in one go. Returns {"report": ..., "etl_log": ...}."""
    ingest_raw(lake)
    _, report = curate(lake)
    return {"report": report, "etl_log": load_warehouse_from_curated(lake)}
