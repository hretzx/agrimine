"""
tests/test_api.py
-----------------
Tests of the HTTP API (api/), run against a temporary database. Needs fastapi + httpx.   Run: python tests/test_api.py  (or pytest)

What is checked: every endpoint answers with the documented shape, bad input gets the ONE error shape, a check can never
exist without its prediction, an old database is migrated and backfilled, and the committed OpenAPI file matches the code
(that file is the contract with the web front end).
"""
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("AGRIMINE_LAB", "0")          # these tests are about the API: they must not start the Streamlit lab (tests/test_lab_process.py does)

from fastapi.testclient import TestClient  # noqa: E402

import core.db.warehouse as warehouse  # noqa: E402

RICE = {"N": 90, "P": 42, "K": 43, "temperature": 20.9, "humidity": 82, "ph": 6.5, "rainfall": 202.9}
CONTRACT = ROOT / "api" / "openapi.json"


def _client(db: Path | None = None) -> TestClient:
    warehouse.DB_PATH = db or (Path(tempfile.mkdtemp()) / "api.db")        # never touch the real database
    from api.main import app
    return TestClient(app)


def test_health_and_meta():
    with _client() as c:
        assert c.get("/api/health").json()["status"] == "ok"
        meta = c.get("/api/meta").json()
        assert meta["records"] == 2200 and len(meta["crops"]) == 22 and len(meta["features"]) == 7
        assert {"key", "label", "label_mr", "family"} <= set(meta["crops"][0]) and meta["languages"] == ["en", "mr"]
        assert {f["key"] for f in meta["families"]} == {c["family"] for c in meta["crops"]} and all(f["label_mr"] for f in meta["families"])
        n = next(f for f in meta["features"] if f["key"] == "N")
        assert n["unit"] == "" and (n["lo"], n["hi"]) == (0, 140)         # no kg/ha claimed
        assert all(f["lo"] <= f["default"] <= f["hi"] for f in meta["features"])      # a start value that would pass validation
        assert next(f for f in meta["features"] if f["key"] == "rainfall")["default"] == 94.9


def test_recommend_shape_and_agreement_with_core():
    from core import advice
    with _client() as c:
        r = c.post("/api/recommend", json=RICE)
        assert r.status_code == 200
        body = r.json()
        core = advice.recommend({k: float(v) for k, v in RICE.items()})
        assert body["best"]["key"] == core["best"] == "rice" and abs(body["probability"] - core["probability"]) < 1e-12
        assert len(body["ranking"]) == 22 and len(body["similar"]) == 21
        probs = [x["probability"] for x in body["ranking"]]
        assert probs == sorted(probs, reverse=True) and abs(sum(probs) - 1) < 1e-9
        assert "rice" not in [x["crop"]["key"] for x in body["similar"]] and body["agrees"] is True
        assert body["best"]["label_mr"] == "भात" and len(body["reasons"]) == 3


def test_a_check_is_always_saved_with_its_prediction():
    with _client() as c:
        made = c.post("/api/checks", json=RICE)
        assert made.status_code == 201
        check = made.json()
        assert check["status"] == "predicted" and check["predicted_crop"]["key"] == "rice" and check["probability"] > 0.9
        assert check["id3_crop"]["key"] == "rice" and check["cluster_id"] in range(4) and check["model_version"]
        assert check["categories"]["rainfall"] == "high" and check["categories"]["ph"] == "neutral"
        assert c.get(f"/api/checks/{check['id']}").json() == check
        recent = c.get("/api/checks?limit=5").json()
        assert recent[0]["id"] == check["id"] and all(r["status"] == "predicted" for r in recent)
        assert c.get("/api/meta").json()["saved_checks"] == 1


def test_a_rejected_check_leaves_nothing_behind():
    with _client() as c:
        bad = c.post("/api/checks", json={**RICE, "N": 999})
        assert bad.status_code == 422
        assert c.get("/api/meta").json()["saved_checks"] == 0


def test_errors_use_one_shape():
    with _client() as c:
        invalid = c.post("/api/recommend", json={**RICE, "ph": 99}).json()
        missing = c.post("/api/recommend", json={"N": 1}).json()
        unknown_crop = c.post("/api/doctor", json={"values": RICE, "crop": "wheat"})
        unknown_check = c.get("/api/checks/12345")
        for body in (invalid, missing, unknown_crop.json(), unknown_check.json()):
            assert set(body) == {"code", "message", "field", "errors"}, body
        assert invalid["code"] == "validation_error" and invalid["field"] == "ph"
        assert {e["field"] for e in missing["errors"]} >= {"P", "K", "temperature"}
        assert unknown_crop.status_code == 404 and unknown_crop.json()["code"] == "unknown_crop"
        assert unknown_check.status_code == 404 and unknown_check.json()["code"] == "unknown_check"
        assert c.get("/api/checks?limit=0").status_code == 422


def test_doctor_and_plan_b_follow_the_core_rules():
    from core import advice
    with _client() as c:
        doctor = c.post("/api/doctor", json={"values": RICE, "crop": "coffee"}).json()
        want = advice.doctor_report({k: float(v) for k, v in RICE.items()}, "coffee")
        assert doctor["overall"] == want["overall"] == "attention" and doctor["needs_attention"] == want["needs_attention"] == 5
        assert len(doctor["readings"]) == 7 and all(set(r) >= {"low", "high", "status", "direction", "tip"} for r in doctor["readings"])
        phosphorus = next(r for r in doctor["readings"] if r["feature"] == "P")
        assert phosphorus["status"] == "attention" and phosphorus["direction"] == "high" and phosphorus["tip"]
        assert phosphorus["tip_key"] == "P.high" and next(r for r in doctor["readings"] if r["feature"] == "N")["tip_key"] is None
        plan = c.post("/api/plan-b", json={"values": RICE, "preferred": "cotton"}).json()
        assert plan["level"] == "low" and plan["best_crop"]["key"] == "rice" and len(plan["alternatives"]) == 3
        assert all(a["crop"]["key"] != "cotton" and len(a["needs"]) == 7 for a in plan["alternatives"])
        good = c.post("/api/plan-b", json={"values": RICE, "preferred": "rice"}).json()
        assert good["level"] == "good" and good["preferred_match"] == good["best_match"]


def test_insights():
    with _client() as c:
        farms = c.get("/api/insights/farms?k=4").json()
        assert farms["k"] == 4 and len(farms["points"]) == 2200 and len(farms["clusters"]) == 4 and farms["your_cluster"] is None
        assert sum(x["records"] for x in farms["clusters"]) == 2200 and 0 < farms["silhouette"] < 1
        assert len(farms["points"][0]) == 3 and {p[2] for p in farms["points"]} == {0, 1, 2, 3}
        check = c.post("/api/checks", json=RICE).json()
        assert c.get(f"/api/insights/farms?k=4&check={check['id']}").json()["your_cluster"] in range(4)
        assert c.get("/api/insights/farms?k=9").status_code == 422
        assert len(c.get("/api/insights/needs").json()) == 22
        gain = c.get("/api/insights/gain").json()
        assert gain[0]["gain"] >= gain[-1]["gain"] and gain[0]["feature"] in ("humidity", "rainfall")
        from core.models import crop_rules
        body = c.get("/api/insights/patterns?limit=3").json()
        patterns = body["items"]
        assert body["total"] == len(crop_rules()) > 3                                     # the real number of rules, not a typed-in one
        assert len(patterns) == 3 and patterns[0]["lift"] >= patterns[-1]["lift"] and isinstance(patterns[0]["antecedent"], list)
        acc = c.get("/api/insights/accuracy").json()
        assert {m["model"] for m in acc["models"]} == {"Naive Bayes", "ID3 decision tree"} and acc["test_rows"] == 440 and acc["train_rows"] == 1760 and acc["seed"] == 42


def test_an_old_database_is_migrated_and_backfilled():
    """A database made by the first release (no prediction columns, a row without a prediction) must keep working."""
    db = Path(tempfile.mkdtemp()) / "old.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE assessments (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, N REAL, P REAL, K REAL, "
                 "ph REAL, temperature REAL, humidity REAL, rainfall REAL, predicted_crop TEXT, cluster_id INTEGER)")
    conn.execute("INSERT INTO assessments (created_at, N, P, K, ph, temperature, humidity, rainfall) VALUES ('2026-10-01 09:00', 90, 42, 43, 6.5, 20.9, 82, 202.9)")
    conn.commit()
    conn.close()
    with _client(db) as c:                                   # startup runs the migration and the backfill
        assert c.get("/api/health").json()["backfilled_checks"] == 1
        row = c.get("/api/checks/1").json()
        assert row["status"] == "predicted" and row["predicted_crop"]["key"] == "rice" and row["model_version"]
    columns = {r[1] for r in sqlite3.connect(db).execute("PRAGMA table_info(assessments)")}
    assert {"probability", "id3_crop", "model_version"} <= columns


def test_an_old_prediction_without_a_probability_is_redone_with_the_current_model():
    """The first release stored a crop but no probability or model version; such a row must not keep a stale answer next to a live one."""
    db = Path(tempfile.mkdtemp()) / "stale.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE assessments (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, N REAL, P REAL, K REAL, "
                 "ph REAL, temperature REAL, humidity REAL, rainfall REAL, predicted_crop TEXT, cluster_id INTEGER)")
    conn.execute("INSERT INTO assessments (created_at, N, P, K, ph, temperature, humidity, rainfall, predicted_crop, cluster_id) "
                 "VALUES ('2026-10-01 09:00', 90, 42, 43, 6.5, 20.9, 82, 202.9, 'cotton', 2)")
    conn.commit()
    conn.close()
    with _client(db) as c:
        assert c.get("/api/health").json()["backfilled_checks"] == 1
        row = c.get("/api/checks/1").json()
        assert row["predicted_crop"]["key"] == "rice" and row["probability"] > 0.9 and row["model_version"]
        assert c.get("/api/health").json()["backfilled_checks"] == 1       # first start only; a second start finds nothing left
    with _client(db) as c:
        assert c.get("/api/health").json()["backfilled_checks"] == 0


def test_teachers_id3_gives_the_prediction_the_path_and_honest_numbers():
    with _client() as c:
        r = c.post("/api/teachers/id3", json=RICE)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["crop"]["key"] == "rice" and 0.5 < d["purity"] <= 1 and 0 <= d["cluster"] < 4
        assert d["path"], "the tree asks at least one question for these readings"
        for step in d["path"]:                                    # every step is one real question about one real reading
            assert step["feature"] in RICE and step["value"] == RICE[step["feature"]] and step["gain"] > 0 and step["rows_here"] > 0
            assert step["level"] and step["range"]
            assert (step["lo"] is None or step["lo"] <= step["value"]) and (step["hi"] is None or step["value"] < step["hi"])   # the reading is inside its bin
            assert step["lo"] is not None or step["hi"] is not None
        rows = [s["rows_here"] for s in d["path"]]
        assert rows == sorted(rows, reverse=True) and rows[0] == 2200      # the root sees every training row, then fewer and fewer
        assert [s["gain"] for s in d["path"]][0] == max(g["gain"] for g in c.get("/api/insights/gain").json())   # the root question is the highest-gain feature
        accuracy = next(m for m in c.get("/api/insights/accuracy").json()["models"] if "ID3" in m["model"])["accuracy"]
        assert d["accuracy"] == accuracy                                   # the same held-out number as the Home page shows
        assert d["n_train"] + d["n_test"] == 2200
        alts = d["alternatives"]
        assert len(alts) == 3 and d["crop"]["key"] not in {a["crop"]["key"] for a in alts}
        assert [a["match"] for a in alts] == sorted((a["match"] for a in alts), reverse=True)
        assert d["model"]["n_bins"] == 5 and d["model"]["depth"] <= d["model"]["max_depth"] and d["model"]["leaves"] > 1
        assert set(d["model"]["edges"]) == set(RICE) and all(e == sorted(e) for e in d["model"]["edges"].values())
        assert len(d["hardest"]) == 5 and [h["accuracy"] for h in d["hardest"]] == sorted(h["accuracy"] for h in d["hardest"])


def test_teachers_id3_rejects_bad_readings_in_the_one_error_shape():
    with _client() as c:
        r = c.post("/api/teachers/id3", json={**RICE, "ph": 99})
        assert r.status_code == 422 and r.json()["code"] == "validation_error"
        assert any(e["field"] == "ph" for e in r.json()["errors"])
        assert c.post("/api/teachers/id3", json={"N": 1}).status_code == 422


def test_teachers_id3_is_exactly_what_the_model_says():
    """The report must be the model's own answer, not a re-implementation: compare with a direct call."""
    from core import teachers
    from core.models import train_id3
    crop, path, purity = train_id3()["model"].predict_with_path(RICE)
    report = teachers.id3_report(RICE)
    assert report["crop"] == crop and report["purity"] == purity
    assert [{k: v for k, v in s.items() if k not in ("lo", "hi")} for s in report["path"]] == path      # the model's steps, plus the bin as numbers


def test_teachers_naive_bayes_is_the_models_own_answer_and_its_arithmetic_adds_up():
    import math
    with _client() as c:
        r = c.post("/api/teachers/naive-bayes", json=RICE)
        assert r.status_code == 200, r.text
        d = r.json()
        rec = c.post("/api/recommend", json=RICE).json()
        assert d["nb"]["crop"]["key"] == rec["best"]["key"] and d["nb"]["probability"] == rec["probability"]      # the same answer as What should I grow?
        assert d["id3"]["crop"]["key"] == rec["id3"]["key"] and d["agree"] == rec["agrees"]
        accuracy = {m["model"]: m["accuracy"] for m in c.get("/api/insights/accuracy").json()["models"]}
        assert d["nb"]["accuracy"] == next(v for k, v in accuracy.items() if "Bayes" in k) and d["id3"]["accuracy"] == next(v for k, v in accuracy.items() if "ID3" in k)
        top = d["top"]
        assert len(top) == 6 and [t["probability"] for t in top] == sorted((t["probability"] for t in top), reverse=True)
        assert top[0]["crop"]["key"] == d["nb"]["crop"]["key"] and top[1]["crop"]["key"] == d["runner_up"]["key"]
        assert sum(t["probability"] for t in top) <= 1 + 1e-9
        assert math.isclose(sum(w["difference"] for w in d["why"]), d["why_total"])          # the bars add up to ln(odds) ...
        odds = math.log(top[0]["probability"] / top[1]["probability"])
        assert math.isclose(d["why_total"], odds, rel_tol=1e-6, abs_tol=1e-6)                 # ... which is exactly the two posteriors' ratio
        assert {w["feature"] for w in d["why"]} == set(RICE) | {"prior"}
        w = d["worked"]
        assert w["crop"]["key"] == d["nb"]["crop"]["key"] and len(w["features"]) == 7
        for f in w["features"]:
            assert math.isclose(f["distance"], (f["value"] - f["mean"]) / f["sigma"], rel_tol=1e-9) and f["value"] == RICE[f["feature"]]
        assert math.isclose(w["sum_log_likelihood"], sum(f["log_likelihood"] for f in w["features"]))
        assert math.isclose(w["joint"], w["log_prior"] + w["sum_log_likelihood"]) and math.isclose(w["log_prior"], math.log(w["prior"]))
        assert len(d["per_crop"]) == 22 and [p["id3"] for p in d["per_crop"]] == sorted(p["id3"] for p in d["per_crop"])
        assert c.post("/api/teachers/naive-bayes", json={**RICE, "N": -5}).status_code == 422


def test_teachers_kmeans_groups_are_consistent_with_the_data_and_the_other_routes():
    with _client() as c:
        d = c.post("/api/teachers/kmeans?k=4", json=RICE).json()
        assert d["k"] == 4 and len(d["points"]) == 2200 and len(d["clusters"]) == 4
        assert sum(g["records"] for g in d["clusters"]) == 2200                                   # every record is in exactly one group
        assert [sum(1 for p in d["points"] if p[2] == g["cluster"]) for g in d["clusters"]] == [g["records"] for g in d["clusters"]]
        assert [sum(row) for row in d["crop_counts"]] == [g["records"] for g in d["clusters"]]    # the crop table adds up to the group sizes
        assert len(d["crops"]) == 22 and all(len(row) == 22 for row in d["crop_counts"])
        for g, row in zip(d["clusters"], d["crop_counts"]):                                       # the top crop and its share come from that table
            assert g["top_crop"]["key"] == d["crops"][row.index(max(row))]["key"] and abs(g["share"] - max(row) / sum(row)) < 1e-9
            assert set(g["averages"]) == set(RICE)
        made = c.post("/api/checks", json=RICE).json()["id"]
        farms = c.get(f"/api/insights/farms?k=4&check={made}")
        assert farms.status_code == 200
        assert d["silhouette"] == farms.json()["silhouette"]                                      # the same silhouette the Home page quotes
        assert d["your_cluster"] == farms.json()["your_cluster"]                                  # and the same group for these readings
        assert [g["records"] for g in d["clusters"]] == [g["records"] for g in farms.json()["clusters"]]
        v = d["variance"]
        assert 0 < v[1] <= v[0] < 1 and v[0] + v[1] <= 1
        diag = {x["k"]: x for x in d["diagnostics"]}
        assert sorted(diag) == list(range(2, 11)) and diag[4]["inertia"] == d["inertia"] and diag[4]["silhouette"] == d["silhouette"]
        assert diag[d["best_k"]]["silhouette"] == max(x["silhouette"] for x in diag.values())
        inertia = [diag[k]["inertia"] for k in range(2, 11)]
        assert inertia == sorted(inertia, reverse=True)                                           # more groups never make the groups looser
        assert 0 <= d["your_cluster"] < 4
        assert c.post("/api/teachers/kmeans?k=10", json=RICE).json()["k"] == 10
        for bad in (1, 11):
            assert c.post(f"/api/teachers/kmeans?k={bad}", json=RICE).status_code == 422


def test_teachers_apriori_rules_obey_their_settings_and_agree_with_the_home_page():
    with _client() as c:
        d = c.get("/api/teachers/apriori").json()
        home = c.get("/api/insights/patterns?limit=3").json()
        assert d["rules_total"] == home["total"]                                                    # the defaults are the Home page's rules
        assert d["rules"][0]["antecedent"] == home["items"][0]["antecedent"] and d["rules"][0]["lift"] == home["items"][0]["lift"]
        assert len(d["rules"]) == 100 and d["itemsets"] > d["rules_total"] and d["seconds"] > 0
        for r in d["rules"]:                                                                         # every rule meets every setting and is well formed
            assert r["confidence"] >= 0.6 - 1e-9 and r["support"] >= 0.01 - 1e-9 and r["consequent"].startswith("crop=") and len(r["antecedent"]) <= 4
            assert 0 < r["support"] <= r["confidence"] <= 1 and r["lift"] > 0
        key = [(r["lift"], r["confidence"], r["support"]) for r in d["rules"]]
        assert key == sorted(key, reverse=True)                                                      # strongest first
        strict = c.get("/api/teachers/apriori?min_confidence=0.95&min_support=0.03&max_len=3&limit=500").json()
        assert 0 < strict["rules_total"] < d["rules_total"]                                          # stricter settings keep fewer rules
        assert all(r["confidence"] >= 0.95 - 1e-9 and r["support"] >= 0.03 - 1e-9 and len(r["antecedent"]) <= 2 for r in strict["rules"])
        rice = c.get("/api/teachers/apriori?crop=rice&limit=500").json()
        assert rice["rules_total"] > 0 and all(r["consequent"] == "crop=rice" or "crop=rice" in r["antecedent"] for r in rice["rules"])
        loose = c.get("/api/teachers/apriori?only_crop=false&limit=500").json()
        assert loose["rules_total"] > 10 * d["rules_total"]                                          # switching the crop-only filter off adds the soil-and-weather rules
        assert c.get("/api/teachers/apriori?crop=nope").status_code == 404
        for bad in ("min_support=0.5", "min_confidence=0.2", "max_len=9"):
            assert c.get(f"/api/teachers/apriori?{bad}").status_code == 422


def test_teachers_hierarchical_tree_is_consistent_for_every_linkage_and_k():
    with _client() as c:
        for method in ("ward", "average", "complete", "single"):
            d = c.get(f"/api/teachers/hierarchical?method={method}&k=4").json()
            keys = [x["key"] for x in d["crops"]]
            assert len(keys) == 22 and len(set(keys)) == 22 and sorted(d["order"]) == list(range(22))
            assert len(d["segments"]) == 21                                                       # 22 crops need 21 merges
            heights = [s["height"] for s in d["segments"]]
            assert heights == sorted(heights) and d["last_height"] == heights[-1]                 # merges happen at rising heights
            assert 0.5 < d["cophenetic"] <= 1
            for s in d["segments"]:
                assert len(s["x"]) == 4 and len(s["y"]) == 4 and s["y"][1] == s["y"][2] == s["height"] and s["y"][0] <= s["height"] and s["y"][3] <= s["height"]
            below = {s["cluster"] for s in d["segments"] if s["cluster"] is not None}
            assert below <= set(range(4)) and d["threshold"] is not None and d["threshold"] < d["last_height"]
            for groups in (d["clusters"], d["diana_clusters"]):
                members = [x["key"] for g in groups for x in g]
                assert len(groups) == 4 and sorted(members) == sorted(keys) and all(groups)       # every crop in exactly one non-empty cluster
            assert d["same"] == ({frozenset(x["key"] for x in g) for g in d["clusters"]} == {frozenset(x["key"] for x in g) for g in d["diana_clusters"]})
            steps = d["diana_steps"]
            assert len(steps) == 8 and [s["step"] for s in steps] == list(range(1, 9))
            assert steps[0]["size"] == 22 and len(steps[0]["splinter"]) + len(steps[0]["rest"]) == 22
            assert all(len(s["splinter"]) + len(s["rest"]) == s["size"] for s in steps)
        two = c.get("/api/teachers/hierarchical?k=2").json()
        ten = c.get("/api/teachers/hierarchical?k=10").json()
        assert len(two["clusters"]) == 2 and len(ten["clusters"]) == 10
        ward = c.get("/api/teachers/hierarchical?method=ward&k=4").json()
        single = c.get("/api/teachers/hierarchical?method=single&k=4").json()
        assert ward["last_height"] != single["last_height"]                                        # the linkage really changes the tree
        for bad in ("method=nope", "k=1", "k=11"):
            assert c.get(f"/api/teachers/hierarchical?{bad}").status_code == 422


def test_openapi_contract_has_not_drifted():
    """api/openapi.json is what the web app's TypeScript types are generated from. Regenerate: python -m api.export"""
    from api.main import app
    assert CONTRACT.exists(), "run: python -m api.export"
    assert json.loads(CONTRACT.read_text(encoding="utf-8")) == app.openapi(), "api/openapi.json is out of date: run python -m api.export"


if __name__ == "__main__":
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except Exception as exc:                                   # noqa: BLE001
                failed += 1
                print(f"FAIL  {name}: {type(exc).__name__}: {exc}")
    print("\nAll API checks passed." if not failed else f"\n{failed} check(s) failed.")
    sys.exit(1 if failed else 0)
