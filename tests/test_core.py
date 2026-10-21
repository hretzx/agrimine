"""
tests/test_core.py
------------------
Checks the from-scratch algorithms and the data warehouse. The algorithm tests need only numpy
and pandas; the "farmer pages" tests at the end (utils/advice.py, utils/i18n.py) import Streamlit's
cache decorators, so Streamlit must be installed.   Run:   python tests/test_core.py     (or: pytest tests)

Each check compares our code with something simple and independent: a brute-force
count, a pandas group-by, np.polyfit, or a value worked out by hand. The hierarchical
clustering is also compared with scipy, the ONLY place scipy is used; that check is
skipped when scipy is not installed (pip install scipy, it is optional).
"""
import itertools
import sys
import tempfile
from pathlib import Path
from unittest import SkipTest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "teachers-lab"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(LAB))             # the lab's own "utils" package (i18n, session)

import core.db.warehouse as warehouse                                   # noqa: E402
from core.algorithms.apriori import apriori, association_rules, make_item_masks  # noqa: E402
from core.algorithms.fpgrowth import (closed_itemsets, eclat, fp_growth,  # noqa: E402
                                 make_transactions, maximal_itemsets)
from core.algorithms.hierarchical import (LINKAGES, cophenetic_correlation, cut_tree,  # noqa: E402
                                     dendrogram_layout, diana, diana_labels, linkage, standardize)
from core.algorithms.id3 import ID3Tree, entropy                         # noqa: E402
from core.algorithms.kmeans import KMeans, silhouette_score              # noqa: E402
from core.algorithms.naive_bayes import GaussianNaiveBayes               # noqa: E402
from core.algorithms.pca import pca_fit, pca_transform                   # noqa: E402
from core.algorithms.regression import (MultipleLinearRegression,        # noqa: E402
                                   SimpleLinearRegression, adjusted_r_squared, r_squared)
from core.preprocessing import (FEATURES, TARGET, discretize_dataframe,  # noqa: E402
                                 load_dataset)

DF, _ = load_dataset()


def test_entropy_by_hand():
    assert entropy(np.array([0, 0, 1, 1])) == 1.0          # 50/50 split = 1 bit
    assert entropy(np.array([2, 2, 2])) == 0.0              # pure node = 0 bits


def test_id3_accuracy_on_unseen_rows():
    rng = np.random.default_rng(1)
    idx = rng.permutation(len(DF))
    cut = int(0.8 * len(DF))
    train, test = DF.iloc[idx[:cut]], DF.iloc[idx[cut:]]
    model = ID3Tree().fit(train, FEATURES, TARGET)
    accuracy = np.mean(np.array(model.predict(test)) == test[TARGET].to_numpy())
    assert accuracy > 0.85, accuracy


def test_apriori_matches_brute_force():
    rng = np.random.default_rng(0)
    small = pd.DataFrame({"a": rng.choice(["x", "y"], 300), "b": rng.choice(["p", "q", "r"], 300),
                          "crop": rng.choice(["c1", "c2", "c3"], 300)})
    names, masks = make_item_masks(small)
    found = apriori(masks, len(small), 0.05, max_len=3)
    table = np.column_stack([(small[c].to_numpy() == v) for c in small.columns
                             for v in sorted(small[c].unique())])
    expected = {}
    for size in (1, 2, 3):
        for combo in itertools.combinations(range(table.shape[1]), size):
            count = int(table[:, combo].all(axis=1).sum())
            if count >= int(np.ceil(0.05 * 300 - 1e-9)):
                expected[combo] = count
    assert found == expected


def test_rule_metrics_by_hand():
    rows = pd.DataFrame({"rain": ["high"] * 6 + ["low"] * 4,
                         "crop": ["rice"] * 5 + ["jute"] + ["jute"] * 4})
    names, masks = make_item_masks(rows)
    rules = association_rules(apriori(masks, 10, 0.1, 2), names, 10, 0.0)
    rule = rules[(rules.Antecedent == "rain=high") & (rules.Consequent == "crop=rice")].iloc[0]
    assert abs(rule.Support - 0.5) < 1e-12                  # 5 of 10 rows have both
    assert abs(rule.Confidence - 5 / 6) < 1e-12             # 5 of the 6 'high' rows are rice
    assert abs(rule.Lift - (5 / 6) / 0.5) < 1e-12           # rice is 50% of all rows


def test_kmeans_is_repeatable_and_silhouette_by_hand():
    X = DF[FEATURES].to_numpy(float)
    a, b = KMeans(k=4).fit(X), KMeans(k=4).fit(X)
    assert (a.labels_ == b.labels_).all() and a.inertia_ == b.inertia_
    # three points on a line: [0, 1] together, [10] alone -> singleton counts as 0
    s = silhouette_score(np.array([[0.0], [1.0], [10.0]]), np.array([0, 0, 1]))
    point0 = (10.0 - 1.0) / 10.0     # a = 1 (its partner), b = 10 (the other cluster)
    point1 = (9.0 - 1.0) / 9.0       # a = 1,                b = 9
    assert abs(s - (point0 + point1 + 0.0) / 3) < 1e-12


def test_pca_variance_and_shape():
    Z = KMeans(k=3).fit(DF[FEATURES].to_numpy(float)).transform(DF[FEATURES].to_numpy(float))
    mean, components, ratio = pca_fit(Z)
    assert components.shape == (2, 7) and 0 < ratio.sum() <= 1 and ratio[0] >= ratio[1]
    assert np.allclose(components @ components.T, np.eye(2))      # directions are perpendicular, length 1
    assert pca_transform(Z, mean, components).shape == (len(Z), 2)


def test_warehouse_etl_and_olap_match_pandas():
    warehouse.DB_PATH = Path(tempfile.mkdtemp()) / "test.db"       # never touch the real database
    log = warehouse.ensure_warehouse()
    assert any("ETL finished" in e["message"] for e in log)
    assert warehouse.table_row_counts().Rows.tolist() == [22, 3, 3, 3, len(DF)]

    labels = discretize_dataframe(DF)
    data = pd.DataFrame({"Crop": DF[TARGET], "Rainfall": labels["rainfall"], "pH": labels["ph"],
                         "Temperature": labels["temperature"], "value": DF["rainfall"]})
    for size in range(1, 4):
        for group in itertools.combinations(["Crop", "Rainfall", "pH", "Temperature"], size):
            result, _ = warehouse.olap_query("Rainfall (mm)", list(group))
            expected = data.groupby(list(group)).agg(Records=("value", "size"), Average=("value", "mean")).reset_index()
            got = result.sort_values(list(group)).reset_index(drop=True)
            expected = expected.sort_values(list(group)).reset_index(drop=True)
            assert (got.Records.to_numpy() == expected.Records.to_numpy()).all()
            assert np.allclose(got.Average, expected.Average.round(2))

    # slice: only high rainfall, broken down by crop
    result, sql = warehouse.olap_query("Record count", ["Crop"], {"Rainfall": ["high"]})
    assert result.Records.sum() == (labels["rainfall"] == "high").sum() and "WHERE" in sql
    # grand total (roll-up to the top)
    total, _ = warehouse.olap_query("Record count", [])
    assert int(total.Records.iloc[0]) == len(DF)


def test_olap_rejects_unknown_names():
    for bad in (lambda: warehouse.olap_query("x; DROP TABLE dim_crop", []),
                lambda: warehouse.olap_query("Record count", ["Crop; --"])):
        try:
            bad()
        except ValueError:
            continue
        raise AssertionError("an unknown name reached the SQL")


# ------------------------------------------------------------------ Naive Bayes
def _stratified(df, seed=42):
    """Same stratified 80/20 split as utils/models.stratified_split (kept here so no Streamlit is needed)."""
    rng = np.random.default_rng(seed)
    train, test = [], []
    for _, rows in df.groupby(TARGET).indices.items():
        rows = rng.permutation(rows)
        cut = int(round(len(rows) * 0.8))
        train.extend(rows[:cut])
        test.extend(rows[cut:])
    return df.iloc[train], df.iloc[test]


def test_naive_bayes_accuracy_on_unseen_rows():
    train, test = _stratified(DF)
    model = GaussianNaiveBayes().fit(train, FEATURES, TARGET)
    accuracy = np.mean(model.predict(test) == test[TARGET].to_numpy())
    assert accuracy > 0.95, accuracy
    proba = model.predict_proba(test)
    assert np.allclose(proba.sum(axis=1), 1.0) and (proba >= 0).all()


def test_naive_bayes_by_hand_and_explain():
    # one feature, two classes: a: 0, 2 (mean 1, var 1)   b: 10, 12 (mean 11, var 1)
    tiny = pd.DataFrame({"x": [0.0, 2.0, 10.0, 12.0], "y": ["a", "a", "b", "b"]})
    model = GaussianNaiveBayes(var_smoothing=0.0).fit(tiny, ["x"], "y")
    assert np.allclose(model.mean_.ravel(), [1, 11]) and np.allclose(model.var_.ravel(), [1, 1])
    # x = 5: log N(5|1,1) - log N(5|11,1) = (-(16) + 36) / 2 = 10 -> P(a) = 1 / (1 + e^-10)
    p_a = model.predict_proba(np.array([[5.0]]))[0, 0]
    assert abs(p_a - 1 / (1 + np.exp(-10))) < 1e-12
    # explain(): the differences add up to the log posterior odds of winner vs runner-up
    row = dict(zip(FEATURES, DF[FEATURES].iloc[0]))
    full = GaussianNaiveBayes().fit(DF, FEATURES, TARGET)
    post = full.posterior(row)
    table = full.explain(row)
    assert abs(table["Log-likelihood difference"].sum() - np.log(post.iloc[0] / post.iloc[1])) < 1e-6


# ------------------------------------------------------------------- Regression
def test_simple_regression_matches_polyfit():
    x, y = DF["P"].to_numpy(float), DF["K"].to_numpy(float)
    model = SimpleLinearRegression().fit(x, y)
    slope, intercept = np.polyfit(x, y, 1)
    assert abs(model.slope_ - slope) < 1e-9 and abs(model.intercept_ - intercept) < 1e-9
    assert abs(model.r2_ - np.corrcoef(x, y)[0, 1] ** 2) < 1e-9     # simple regression: R2 = r^2


def test_multiple_regression_matches_normal_equations():
    X = DF[["N", "P", "K", "temperature"]].to_numpy(float)
    y = DF["humidity"].to_numpy(float)
    model = MultipleLinearRegression().fit(X, y)
    A = np.column_stack([np.ones(len(X)), X])
    beta = np.linalg.solve(A.T @ A, A.T @ y)          # (A'A) b = A'y, solved independently
    assert np.allclose([model.intercept_, *model.coef_], beta)
    assert abs(model.r2_ - r_squared(y, A @ beta)) < 1e-12
    assert abs(adjusted_r_squared(0.5, 101, 4) - (1 - 0.5 * 100 / 96)) < 1e-12


# ----------------------------------------------------------------- Hierarchical
def _crop_profiles():
    return standardize(DF.groupby(TARGET)[FEATURES].mean().to_numpy(float))


def test_hierarchical_matches_scipy():
    try:
        from scipy.cluster.hierarchy import cophenet
        from scipy.cluster.hierarchy import cut_tree as scipy_cut
        from scipy.cluster.hierarchy import linkage as scipy_linkage
        from scipy.spatial.distance import pdist
    except ImportError:
        raise SkipTest("scipy is not installed (optional, only needed for this check)")
    rng = np.random.default_rng(3)
    for X in (_crop_profiles(), rng.normal(size=(120, 4))):
        for method in LINKAGES:
            ours, ref = linkage(X, method), scipy_linkage(X, method)
            assert np.allclose(np.sort(ours[:, 2]), np.sort(ref[:, 2])), method       # merge heights
            assert (ours[:, 3] == ref[:, 3]).all() or np.allclose(np.sort(ours[:, 3]), np.sort(ref[:, 3]))
            for k in (2, 3, 4, 6):
                assert (cut_tree(ours, k) == scipy_cut(ref, k).ravel()).all(), (method, k)
            assert abs(cophenetic_correlation(ours, X) - cophenet(ref, pdist(X))[0]) < 1e-9


def test_cut_tree_and_dendrogram_by_hand():
    # points on a line: {0, 1} and {10, 11} are clear pairs, 30 is far away
    X = np.array([[0.0], [1.0], [10.0], [11.0], [30.0]])
    Z = linkage(X, "single")
    assert np.allclose(Z[:, 2], [1, 1, 9, 19])
    assert cut_tree(Z, 3).tolist() == [0, 0, 1, 1, 2]
    assert cut_tree(Z, 1).tolist() == [0] * 5 and cut_tree(Z, 5).tolist() == [0, 1, 2, 3, 4]
    layout = dendrogram_layout(Z, k=3)
    assert len(layout["segments"]) == 4 and 1 < layout["threshold"] < 9
    assert [s["cluster"] is None for s in layout["segments"]] == [False, False, True, True]


def test_diana_splits_the_far_group_first():
    X = np.array([[0.0], [1.0], [2.0], [10.0], [11.0]])
    first = diana(X)[0]
    assert sorted(first["splinter"]) == [3, 4] or sorted(first["rest"]) == [3, 4]
    assert diana_labels(X, 2).tolist() == [0, 0, 0, 1, 1]
    assert len(diana(_crop_profiles())) == 21                   # 22 crops -> 21 splits down to singletons


# --------------------------------------------------- Apriori, FP-Growth, Eclat
def _real_items():
    labels = discretize_dataframe(DF)
    labels["crop"] = DF[TARGET].to_numpy()
    names, masks = make_item_masks(labels)
    names_fp, transactions = make_transactions(labels)
    assert names == names_fp                                   # same item numbering
    return masks, transactions


def test_apriori_fpgrowth_eclat_agree_on_real_data():
    masks, transactions = _real_items()
    for support in (0.005, 0.01, 0.03, 0.1):
        for max_len in (2, 5):
            a = apriori(masks, len(DF), support, max_len)
            assert a == fp_growth(transactions, support, max_len) == eclat(masks, len(DF), support, max_len), \
                (support, max_len)


def test_closed_and_maximal_against_brute_force():
    masks, _ = _real_items()
    frequent = apriori(masks, len(DF), 0.02, 4)
    sets = {s: frozenset(s) for s in frequent}
    brute_closed, brute_maximal = {}, {}
    for s, count in frequent.items():
        supersets = [t for t in frequent if len(t) > len(s) and sets[s] < sets[t]]
        if not any(frequent[t] == count for t in supersets):
            brute_closed[s] = count
        if not supersets:
            brute_maximal[s] = count
    assert closed_itemsets(frequent) == brute_closed
    assert maximal_itemsets(frequent) == brute_maximal
    assert set(brute_maximal) <= set(brute_closed) <= set(frequent)


def test_run_etl_accepts_a_dataframe():
    warehouse.DB_PATH = Path(tempfile.mkdtemp()) / "lake.db"
    curated = DF.head(300).copy()
    curated["extra column"] = 1                                 # extra columns are ignored
    log = warehouse.run_etl(curated, source="curated.csv")
    assert any("curated.csv" in e["message"] for e in log)
    assert warehouse.table_row_counts().Rows.tolist()[-1] == 300


def test_data_prep_helpers_by_hand():
    from core.preprocessing import (equal_frequency_bins, equal_width_bins, iqr_bounds, min_max_scale,
                                     z_score_scale)
    values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100]
    lo, hi = iqr_bounds(values)                           # Q1 = 3.25, Q3 = 7.75 -> fences -3.5 and 14.5
    assert abs(lo + 3.5) < 1e-9 and abs(hi - 14.5) < 1e-9
    assert [v for v in values if v < lo or v > hi] == [100]
    scaled = min_max_scale(DF[FEATURES])
    assert np.allclose(scaled.min(), 0) and np.allclose(scaled.max(), 1)
    z = z_score_scale(DF[FEATURES])
    assert np.allclose(z.mean(), 0, atol=1e-9) and np.allclose(z.std(ddof=0), 1)
    bins, edges = equal_width_bins(values, 3)
    assert np.allclose(np.diff(edges), np.diff(edges)[0]) and bins.tolist() == [0] * 9 + [2]
    bins, _ = equal_frequency_bins(DF["rainfall"], 4)
    counts = np.bincount(bins)
    assert counts.max() - counts.min() <= 0.02 * len(DF)   # about the same number in every bin


def test_data_lake_pipeline(tmp=None):
    from core import lake
    warehouse.DB_PATH = Path(tempfile.mkdtemp()) / "lake_pipeline.db"
    folder = Path(tempfile.mkdtemp())
    result = lake.run_pipeline(folder)
    assert result["report"]["rows_out"] == len(DF.drop_duplicates())
    catalog = lake.read_catalog(folder)
    assert set(catalog["zone"]) == {"raw", "curated"} and len(catalog) == 3
    raw_copy = next((folder / "raw").glob("*.csv"))
    assert catalog.set_index("file").loc[f"raw/{raw_copy.name}", "sha256"] == lake._sha256(raw_copy)
    curated = pd.read_csv(folder / "curated" / lake.CURATED_NAME)
    assert curated["any_outlier"].sum() == result["report"]["rows_with_outlier"]
    # the warehouse was loaded FROM the curated file
    assert any("curated" in e["message"] for e in result["etl_log"] if e["stage"] == "EXTRACT")
    assert warehouse.table_row_counts().Rows.tolist()[-1] == len(curated)


# ---------------------------------------------------------------- farmer pages (need streamlit installed)
RICE_FIELD = {"N": 90.0, "P": 42.0, "K": 43.0, "temperature": 20.9, "humidity": 82.0, "ph": 6.5, "rainfall": 202.9}


def test_match_scores_are_bounded_sorted_and_find_the_crop_profile():
    from core import advice
    scores = advice.match_scores(RICE_FIELD)
    assert len(scores) == DF[TARGET].nunique() and scores["Match"].between(0, 100).all()
    assert scores["Match"].is_monotonic_decreasing
    mean_profile = DF.groupby(TARGET)[FEATURES].mean()
    for crop in ("rice", "cotton", "apple"):                       # a crop's own average profile matches that crop best
        assert advice.match_scores(mean_profile.loc[crop].to_dict()).iloc[0]["Crop"] == crop


def test_ranking_is_by_naive_bayes_probability_with_similarity_separate():
    from core import advice
    rec = advice.recommend(RICE_FIELD)
    ranking, similar = rec["ranking"], rec["similar"]
    assert ranking["Probability"].is_monotonic_decreasing and abs(ranking["Probability"].sum() - 1) < 1e-9
    assert ranking.iloc[0]["Crop"] == rec["best"] == "rice"
    assert {"Crop", "Probability", "Match", "Level"} <= set(ranking.columns)
    assert "rice" not in set(similar["Crop"]) and similar["Match"].is_monotonic_decreasing   # Plan B: closest by conditions
    scores = advice.match_scores(RICE_FIELD).set_index("Crop")["Match"]
    assert all(abs(ranking.set_index("Crop").loc[c, "Match"] - scores[c]) < 1e-9 for c in ranking["Crop"])   # same similarity numbers


def test_recommend_agrees_with_the_naive_bayes_model():
    from core import advice
    from core.models import train_naive_bayes
    rec = advice.recommend(RICE_FIELD)
    assert rec["best"] == train_naive_bayes()["model"].predict(RICE_FIELD)[0] == "rice"
    assert rec["ranking"].iloc[0]["Crop"] == "rice" and 0 < rec["probability"] <= 1
    assert abs(float(rec["posterior"].sum()) - 1) < 1e-9


def test_soil_health_thresholds_come_from_the_crop_data():
    from core import advice
    rice = DF[DF[TARGET] == "rice"]
    prof = advice.crop_profiles()
    lo, hi = prof["p10"].loc["rice", "ph"], prof["p90"].loc["rice", "ph"]
    assert abs(lo - rice["ph"].quantile(0.10)) < 1e-9 and abs(hi - rice["ph"].quantile(0.90)) < 1e-9
    assert advice.feature_status(float(rice["ph"].median()), "rice", "ph") == "good"
    assert advice.feature_status(float(rice["ph"].max()), "rice", "ph") in ("good", "moderate")   # inside what rice has seen
    assert advice.feature_status(float(rice["ph"].max()) + 1.0, "rice", "ph") == "attention"
    assert advice.feature_status(float(rice["ph"].min()) - 1.0, "rice", "ph") == "attention"
    health = advice.soil_health({**RICE_FIELD, "ph": 9.5}, "rice").set_index("Feature")
    assert health.loc["ph", "Status"] == "attention" and health.loc["ph", "Direction"] == "high"
    assert advice.tip_for("ph", "high") and advice.tip_for("ph", "") is None
    report = advice.doctor_report({**RICE_FIELD, "ph": 9.5}, "rice")
    assert next(r for r in report["readings"] if r["feature"] == "ph")["tip_key"] == "ph.high"
    assert {f"{f}.{d}" for f, d in advice.TIPS} >= {r["tip_key"] for r in report["readings"] if r["tip_key"]}   # every key the report can send has a tip


def test_overall_health_levels():
    from core import advice
    import pandas as pd
    def level(statuses):
        return advice.overall_health(pd.DataFrame({"Feature": FEATURES[:len(statuses)], "Status": statuses}))[0]
    assert level(["good"] * 7) == "good" and level(["attention"] * 7) == "attention"
    assert level(["good"] * 6 + ["attention"]) == "good" and level(["good"] * 5 + ["attention"] * 2) == "moderate" and level(["good"] * 3 + ["attention"] * 4) == "moderate"


def test_clusters_are_summarised_from_the_data():
    from core import advice
    summary = advice.cluster_summary(3)
    assert summary["Records"].sum() == len(DF) and summary["Share"].between(0, 1).all()
    assert 0 <= advice.nearest_cluster(RICE_FIELD, 3) < 3


def test_marathi_crop_names_cover_every_crop_and_n_p_k_have_no_unit():
    from utils.i18n import CROP_MR
    from core.preprocessing import VALID_RANGES
    assert set(CROP_MR) == set(DF[TARGET].unique()) and all(CROP_MR.values())
    assert len(set(CROP_MR.values())) == len(CROP_MR)                      # no two crops share a name
    assert all(VALID_RANGES[f][2] == "" for f in ("N", "P", "K"))          # no kg/ha claimed until the source unit is confirmed


def test_translations_are_complete_and_consistent():
    import re
    from utils.i18n import TEXT, t
    for key, (en, mr) in TEXT.items():
        assert en and mr, f"{key}: missing text"
        assert re.findall(r"\{(\w+)\}", en) == re.findall(r"\{(\w+)\}", mr), f"{key}: placeholders differ"
    assert t("nav_home") == "Home" and t("kpi_records_note", n=7) == "7 measurements each"


# ---------------------------------------------------------------- the core/ package (Phase 1 guarantees)
def test_core_runs_without_streamlit():
    """core/ must never import Streamlit: run a recommendation in a fresh interpreter where Streamlit cannot be imported."""
    import subprocess
    code = (
        "import sys\n"
        "class B:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name == 'streamlit' or name.startswith('streamlit.'): raise ImportError('streamlit blocked')\n"
        "sys.meta_path.insert(0, B()); sys.path.insert(0, %r)\n"
        "import core.advice, core.models, core.lake, core.db.warehouse\n"
        "r = core.advice.recommend({'N': 90., 'P': 42., 'K': 43., 'temperature': 20.9, 'humidity': 82., 'ph': 6.5, 'rainfall': 202.9})\n"
        "assert r['best'] == 'rice' and not any(m.startswith('streamlit') for m in sys.modules)\n"
        "print('ok')\n" % str(ROOT))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert out.returncode == 0 and out.stdout.strip() == "ok", out.stderr[-800:]


def test_cached_returns_copies_of_dataframes():
    from core.models import get_data
    first, _ = get_data()
    first["scratch"] = 1                                   # a caller mutating its frame...
    second, _ = get_data()
    assert "scratch" not in second.columns                 # ...must not leak into the next caller's


def test_single_k_silhouette_equals_the_full_diagnostics_table():
    from core.models import kmeans_diagnostics, kmeans_silhouette
    table = kmeans_diagnostics().set_index("k")["Silhouette"]
    for k in (3, 4, 5):
        assert abs(kmeans_silhouette(k) - table[k]) < 1e-12


def test_cached_computes_once_even_with_concurrent_callers():
    import threading
    import time
    from core.cache import cached
    calls = []

    @cached
    def slow(x):
        calls.append(x)
        time.sleep(0.3)
        return x * 2

    results = []
    threads = [threading.Thread(target=lambda: results.append(slow(21))) for _ in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results == [42] * 6 and len(calls) == 1                  # six callers, ONE computation


def test_feature_and_crop_registries_match_the_dataset():
    from core.crops import CROPS_BY_KEY, CROP_LIST
    from core.features import FEATURE_LIST, FEATURES_BY_KEY
    from core.preprocessing import VALID_RANGES
    assert [f.key for f in FEATURE_LIST] == FEATURES == list(VALID_RANGES)          # same keys, same order as the models use
    assert set(CROPS_BY_KEY) == set(DF[TARGET].unique()) and len(CROP_LIST) == 22
    from core.crops import FAMILIES, FAMILY_LABELS
    assert set(FAMILY_LABELS) == set(FAMILIES) and all(en and mr for en, mr in FAMILY_LABELS.values())
    assert all(c.label and c.label_mr and c.family for c in CROP_LIST) and all(f.label_mr for f in FEATURE_LIST)
    assert all(DF[f.key].between(f.lo, f.hi).all() for f in FEATURE_LIST)         # every real record passes validation
    assert FEATURES_BY_KEY["temperature"].label_unit == "Temperature (°C)" and FEATURES_BY_KEY["N"].label_unit == "Nitrogen (N)"


def test_no_page_keeps_its_own_feature_label_table():
    """The audit found 9 copies of the label dictionary; labels now come from core/features.py only."""
    import re
    offenders = []
    for path in list((LAB / "pages").glob("*.py")) + [LAB / "app.py"] + list((LAB / "utils").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if path.name != "i18n.py" and re.search(r'"N":\s*"Nitrogen|"N":\s*"N",\s*"P":\s*"P"', text):
            offenders.append(path.name)
    assert not offenders, offenders


if __name__ == "__main__":
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except SkipTest as why:
                print(f"SKIP  {name}: {why}")
            except Exception as exc:                                  # noqa: BLE001
                failed += 1
                print(f"FAIL  {name}: {type(exc).__name__}: {exc}")
    print("\nAll core checks passed." if not failed else f"\n{failed} check(s) failed.")
    sys.exit(1 if failed else 0)
