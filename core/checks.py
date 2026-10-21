"""
core/checks.py
--------------
A "soil check" is one record: the seven readings, the prediction made from them, and when. It is created, predicted and
saved in ONE transaction, so a check that exists always has its prediction ("saved but not predicted" cannot happen).

Only rows written by the old Soil Analysis page (before this module) can lack a prediction or its probability;
backfill_predictions() fills them in with the current model (and stamps model_version), and until then a row without a
crop reads as status "pending".

    check = create_check({"N": 90, ...})      # validates, predicts, stores -> dict
    get_check(18), list_checks(10)
No Streamlit here. The database file is core.db.warehouse.DB_PATH (tests point it at a temporary file).
"""
from datetime import datetime

from core import advice
from core.db.warehouse import PARAM, connection, init_db
from core.preprocessing import FEATURES, categorize, category_cutoffs, ph_class, validate_inputs

MODEL_VERSION = "naive-bayes+id3 · rules 2026-10"   # change when the models or the ranking rules change
DEFAULT_K = 4                                         # K-Means groups used for the "farms like yours" cluster of a check

COLUMNS = ["id", "created_at", *FEATURES, "predicted_crop", "cluster_id", "probability", "id3_crop", "model_version"]


class InvalidReadings(ValueError):
    """The readings are missing or outside the allowed ranges. .errors is a list of (field, message)."""

    def __init__(self, errors: list[tuple[str, str]]):
        super().__init__("; ".join(f"{field}: {message}" for field, message in errors))
        self.errors = errors


def _check_values(values: dict) -> dict:
    errors = []
    for message in validate_inputs(values):
        field = message.split(":", 1)[0]
        errors.append((field, message.split(":", 1)[1].strip()))
    if errors:
        raise InvalidReadings(errors)
    return {f: float(values[f]) for f in FEATURES}


def _categories(values: dict) -> dict:
    from core.models import get_data
    df, _ = get_data()
    cutoffs = category_cutoffs(df)
    return {f: (ph_class(values[f]) if f == "ph" else categorize(values[f], cutoffs[f])) for f in FEATURES}


def _record(row: tuple) -> dict:
    data = dict(zip(COLUMNS, row))
    values = {f: data[f] for f in FEATURES}
    return {
        "id": data["id"], "created_at": data["created_at"], "values": values, "categories": _categories(values),
        "predicted_crop": data["predicted_crop"], "probability": data["probability"], "id3_crop": data["id3_crop"],
        "cluster_id": data["cluster_id"], "model_version": data["model_version"],
        "status": "predicted" if data["predicted_crop"] else "pending",
    }


def create_check(values: dict, k: int = DEFAULT_K) -> dict:
    """Validate the readings, predict, and save the check with its prediction in one transaction."""
    values = _check_values(values)
    rec = advice.recommend(values)                      # predicts BEFORE anything is written: a failure leaves no half-record
    cluster = advice.nearest_cluster(values, k)
    init_db()
    with connection() as conn:                          # commits on success, rolls back on any error
        cur = conn.execute(
            f"INSERT INTO assessments (created_at, {', '.join(FEATURES)}, predicted_crop, cluster_id, probability, id3_crop, "
            f"model_version) VALUES ({', '.join([PARAM] * (len(FEATURES) + 6))})",
            (datetime.now().strftime("%Y-%m-%d %H:%M"), *[values[f] for f in FEATURES], rec["best"], cluster,
             rec["probability"], rec["id3"], MODEL_VERSION))
        new_id = cur.lastrowid
    return get_check(new_id)


def get_check(check_id: int) -> dict | None:
    init_db()
    with connection() as conn:
        row = conn.execute(f"SELECT {', '.join(COLUMNS)} FROM assessments WHERE id = {PARAM}", (check_id,)).fetchone()
    return _record(row) if row else None


def list_checks(limit: int = 10) -> list[dict]:
    """Newest first."""
    init_db()
    with connection() as conn:
        rows = conn.execute(f"SELECT {', '.join(COLUMNS)} FROM assessments ORDER BY id DESC LIMIT {PARAM}", (limit,)).fetchall()
    return [_record(r) for r in rows]


def count_checks() -> int:
    init_db()
    with connection() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM assessments").fetchone()[0])


def backfill_predictions(k: int = DEFAULT_K) -> int:
    """Predict every check that has no prediction or no probability (rows from the old Soil Analysis page, which stored a crop
    but no probability: its answer came from an older model and would disagree with the live one). Returns how many were filled in."""
    init_db()
    with connection() as conn:
        rows = conn.execute(f"SELECT id, {', '.join(FEATURES)} FROM assessments WHERE predicted_crop IS NULL OR probability IS NULL").fetchall()
    filled = 0
    for row in rows:
        values = dict(zip(FEATURES, row[1:]))
        if any(v is None for v in values.values()):
            continue                                    # an incomplete legacy row cannot be predicted
        rec = advice.recommend(values)
        with connection() as conn:
            conn.execute(
                f"UPDATE assessments SET predicted_crop = {PARAM}, cluster_id = {PARAM}, probability = {PARAM}, "
                f"id3_crop = {PARAM}, model_version = {PARAM} WHERE id = {PARAM}",
                (rec["best"], advice.nearest_cluster(values, k), rec["probability"], rec["id3"], MODEL_VERSION, row[0]))
        filled += 1
    return filled
