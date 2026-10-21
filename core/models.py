"""
utils/models.py
---------------
Cached model trainers shared by every front end. @cached (core/cache.py) means each model is trained only once per
process, so pages load instantly after the first visit. No Streamlit in this module.

Also here: stratified_split(), the ONE 80/20 split used by every classifier, so ID3
and Naive Bayes are tested on exactly the same unseen rows.
"""
import time

import numpy as np
import pandas as pd

from core.cache import cached

from core.algorithms.apriori import apriori, association_rules, make_item_masks
from core.algorithms.fpgrowth import closed_itemsets, eclat, fp_growth, make_transactions, maximal_itemsets
from core.algorithms.hierarchical import cophenetic_correlation, diana, linkage, standardize
from core.algorithms.id3 import ID3Tree, entropy
from core.algorithms.kmeans import KMeans, silhouette_score
from core.algorithms.naive_bayes import GaussianNaiveBayes
from core.algorithms.pca import pca_fit, pca_transform
from core.algorithms.regression import (MultipleLinearRegression, SimpleLinearRegression, held_out_report,
                                   train_test_split)
from core.preprocessing import FEATURES, TARGET, discretize_dataframe, load_dataset

SPLIT_SEED = 42             # the one seed of the train / test split used by every classifier
K_RANGE = range(2, 11)   # cluster counts tried for the elbow plot


@cached
def get_data() -> tuple[pd.DataFrame, bool]:
    """The dataset (loaded once). Returns (dataframe, is_synthetic)."""
    return load_dataset()


def stratified_split(df: pd.DataFrame, test_share: float = 0.2, seed: int = SPLIT_SEED) -> tuple[list, list]:
    """
    Split every crop 80% / 20% (a "stratified" split) so each crop appears in both parts.
    Returns (train row positions, test row positions). Same seed = same split, so every
    classifier is tested on the same unseen rows.
    """
    rng = np.random.default_rng(seed)
    train_idx, test_idx = [], []
    for _, rows in df.groupby(TARGET).indices.items():
        rows = rng.permutation(rows)
        cut = int(round(len(rows) * (1 - test_share)))
        train_idx.extend(rows[:cut])
        test_idx.extend(rows[cut:])
    return train_idx, test_idx


def _per_crop(actual, predicted) -> pd.DataFrame:
    """Held-out accuracy of every crop, weakest first."""
    return (pd.DataFrame({"Crop": actual, "Correct": predicted == actual})
            .groupby("Crop")["Correct"].agg(["mean", "size"]).reset_index()
            .rename(columns={"mean": "Accuracy", "size": "Test rows"})
            .sort_values("Accuracy").reset_index(drop=True))


@cached
def train_id3() -> dict:
    """
    Train ID3 and measure its accuracy honestly.
      1. stratified_split(): 80% of every crop to train, 20% to test.
      2. Train on the 80% and test on the 20% the tree has never seen -> held-out accuracy.
      3. The tree used for predictions is trained on ALL rows.
    Returns a dict with the model, the accuracy numbers and the dataframe.
    """
    df, _ = get_data()
    train_idx, test_idx = stratified_split(df)
    train, test = df.iloc[train_idx], df.iloc[test_idx]

    check = ID3Tree().fit(train, FEATURES, TARGET)
    predicted = np.array(check.predict(test))
    actual = test[TARGET].to_numpy()

    return {
        "model": ID3Tree().fit(df, FEATURES, TARGET),
        "accuracy": float(np.mean(predicted == actual)),
        "n_train": len(train), "n_test": len(test),
        "per_crop": _per_crop(actual, predicted),
        "test_predictions": predicted,
        "df": df,
    }


@cached
def id3_root_gains() -> pd.DataFrame:
    """
    Information gain of every feature at the ROOT of the tree (all rows, the tree's own
    bins): how much one question about that feature alone would reduce entropy.
    The feature with the highest gain is the tree's first question.
    """
    trained = train_id3()
    model, df = trained["model"], trained["df"]
    y = df[TARGET].map({c: i for i, c in enumerate(model.classes_)}).to_numpy()
    base = entropy(y)
    rows = []
    for f in FEATURES:
        bins = model._bin_col(f, df[f])
        remainder = sum((bins == b).mean() * entropy(y[bins == b]) for b in np.unique(bins))
        rows.append({"Feature": f, "Gain": base - remainder})
    return pd.DataFrame(rows).sort_values("Gain").reset_index(drop=True)


@cached
def train_naive_bayes() -> dict:
    """
    Train Gaussian Naive Bayes on the SAME stratified 80/20 split as ID3 and report its
    held-out accuracy. The model used for predictions is trained on all rows.
    """
    df, _ = get_data()
    train_idx, test_idx = stratified_split(df)
    train, test = df.iloc[train_idx], df.iloc[test_idx]

    check = GaussianNaiveBayes().fit(train, FEATURES, TARGET)
    predicted = check.predict(test)
    actual = test[TARGET].to_numpy()

    return {
        "model": GaussianNaiveBayes().fit(df, FEATURES, TARGET),
        "accuracy": float(np.mean(predicted == actual)),
        "n_train": len(train), "n_test": len(test),
        "per_crop": _per_crop(actual, predicted),
        "test_predictions": predicted,
        "df": df,
    }


def model_scores() -> pd.DataFrame:
    """Held-out accuracy of both classifiers, best first (columns: Model, Accuracy)."""
    rows = [{"Model": "Naive Bayes", "Accuracy": train_naive_bayes()["accuracy"]},
            {"Model": "ID3", "Accuracy": train_id3()["accuracy"]}]
    return pd.DataFrame(rows).sort_values("Accuracy", ascending=False).reset_index(drop=True)


@cached
def train_kmeans(k: int) -> KMeans:
    """Train K-Means for a given k (cached per k)."""
    df, _ = get_data()
    return KMeans(k=k).fit(df[FEATURES].to_numpy(float))


@cached
def get_projection() -> dict:
    """
    2D view of the data for the cluster scatter plot: standardize, then PCA by SVD.
    Returns the 2D coordinates of every row plus what is needed to place a new point.
    """
    df, _ = get_data()
    X = df[FEATURES].to_numpy(float)
    mean, std = X.mean(axis=0), X.std(axis=0)
    std[std == 0] = 1.0
    Z = (X - mean) / std
    pca_mean, components, ratio = pca_fit(Z)
    return {
        "coords": pca_transform(Z, pca_mean, components),
        "ratio": ratio, "feature_mean": mean, "feature_std": std,
        "pca_mean": pca_mean, "components": components,
    }


def project_point(projection: dict, values: dict) -> np.ndarray:
    """Place one assessment on the same 2D plot (same standardization + PCA)."""
    x = np.array([[values[f] for f in FEATURES]], dtype=float)
    z = (x - projection["feature_mean"]) / projection["feature_std"]
    return pca_transform(z, projection["pca_mean"], projection["components"])[0]


@cached
def kmeans_silhouette(k: int) -> float:
    """Silhouette score of the cached K-Means model for one k (the same number kmeans_diagnostics() reports for that k)."""
    df, _ = get_data()
    km = train_kmeans(k)
    return float(silhouette_score(km.transform(df[FEATURES].to_numpy(float)), km.labels_))


@cached
def kmeans_diagnostics() -> pd.DataFrame:
    """Inertia (elbow) and silhouette score for k = 2 ... 10."""
    rows = []
    df, _ = get_data()
    X = df[FEATURES].to_numpy(float)
    for k in K_RANGE:
        km = KMeans(k=k).fit(X)
        rows.append({"k": k, "Inertia": km.inertia_,
                     "Silhouette": silhouette_score(km.transform(X), km.labels_)})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ regression
@cached
def best_regression_pair() -> tuple[str, str, float]:
    """The two features with the strongest linear relationship -> (x, y, correlation r)."""
    df, _ = get_data()
    strength = df[FEATURES].corr().abs().to_numpy(copy=True)
    np.fill_diagonal(strength, 0)                     # a feature with itself does not count
    i, j = np.unravel_index(np.argmax(strength), strength.shape)
    x, y = FEATURES[i], FEATURES[j]
    # put the feature listed first in FEATURES on the x-axis, so the choice is repeatable
    if FEATURES.index(x) > FEATURES.index(y):
        x, y = y, x
    return x, y, float(df[x].corr(df[y]))


@cached
def fit_regression(target: str, predictors: tuple[str, ...]) -> dict:
    """
    Fit simple (first predictor only) and multiple (all predictors) linear regression on
    a random 80% of the rows and score both on the other 20%. Cached per choice.
    """
    df, _ = get_data()
    train, test = train_test_split(len(df), 0.2, seed=42)
    y = df[target].to_numpy(float)
    X = df[list(predictors)].to_numpy(float)
    x1 = X[:, 0]
    simple = held_out_report(SimpleLinearRegression(), x1[train], y[train], x1[test], y[test])
    multiple = held_out_report(MultipleLinearRegression(), X[train], y[train], X[test], y[test])
    return {"simple": simple, "multiple": multiple, "train": train, "test": test,
            "target": target, "predictors": list(predictors)}


# ------------------------------------------------------- hierarchical clustering
@cached
def crop_profiles_standardized() -> tuple[list[str], np.ndarray]:
    """Mean profile of every crop (22 rows x 7 features), z-scored column by column."""
    df, _ = get_data()
    profile = df.groupby(TARGET)[FEATURES].mean()
    return list(profile.index), standardize(profile.to_numpy(float))


@cached
def crop_linkage(method: str = "ward") -> dict:
    """Agglomerative clustering of the 22 crops: linkage matrix + cophenetic correlation."""
    crops, X = crop_profiles_standardized()
    Z = linkage(X, method)
    return {"Z": Z, "crops": crops, "X": X, "cophenetic": cophenetic_correlation(Z, X)}


@cached
def crop_diana() -> list[dict]:
    """DIANA split order of the 22 crops (object numbers refer to crop_profiles_standardized)."""
    _, X = crop_profiles_standardized()
    return diana(X)


# ------------------------------------------------------------ frequent itemsets
@cached
def mining_items() -> dict:
    """
    The same items for all three miners: N, P, K, temperature, humidity and rainfall as
    low / medium / high, pH as acidic / neutral / alkaline, and the crop.
    Returns item names, one bitset per item (Apriori, Eclat) and transactions (FP-Growth).
    """
    df, _ = get_data()
    labels = discretize_dataframe(df)
    labels["crop"] = df[TARGET].to_numpy()
    names, masks = make_item_masks(labels)
    names_fp, transactions = make_transactions(labels)
    assert names == names_fp, "item numbering differs between miners"
    return {"names": names, "masks": masks, "transactions": transactions, "n_rows": len(df)}


@cached
def crop_rules(min_support: float = 0.01, min_confidence: float = 0.6, max_len: int = 5) -> pd.DataFrame:
    """Apriori rules that end in a crop (the Pattern Mining defaults)."""
    items = mining_items()
    frequent = apriori(items["masks"], items["n_rows"], min_support, max_len)
    return association_rules(frequent, items["names"], items["n_rows"], min_confidence, "crop=")


def _best_time(fn, repeats: int) -> tuple[float, dict]:
    """Run fn several times; keep the fastest time (least disturbed by other work)."""
    best, result = None, None
    for _ in range(repeats):
        started = time.perf_counter()
        result = fn()
        took = time.perf_counter() - started
        best = took if best is None else min(best, took)
    return best, result


@cached
def benchmark_miners(supports: tuple[float, ...] = (0.01,), max_len: int = 5, repeats: int = 3) -> pd.DataFrame:
    """
    Time the three miners on the same items for every minimum support. One row per
    (support, algorithm) with the run time, the number of itemsets found and whether
    the result is identical to Apriori's. Times are measured, never typed in, and are
    cached for the server run (so they are the times from the first visit).
    """
    items = mining_items()
    masks, transactions, n = items["masks"], items["transactions"], items["n_rows"]
    rows = []
    for sup in supports:
        t_a, ref = _best_time(lambda: apriori(masks, n, sup, max_len), repeats)
        t_f, fp = _best_time(lambda: fp_growth(transactions, sup, max_len), repeats)
        t_e, ec = _best_time(lambda: eclat(masks, n, sup, max_len), repeats)
        for name, took, found in (("Apriori", t_a, ref), ("FP-Growth", t_f, fp), ("Eclat", t_e, ec)):
            rows.append({"Min support": sup, "Algorithm": name, "Seconds": took,
                         "Itemsets": len(found), "Same as Apriori": found == ref})
    return pd.DataFrame(rows)


@cached
def itemset_summary(min_support: float, max_len: int = 5) -> pd.DataFrame:
    """All / closed / maximal frequent itemsets counted by size (number of items)."""
    items = mining_items()
    frequent = apriori(items["masks"], items["n_rows"], min_support, max_len)
    kinds = {"All frequent": frequent, "Closed": closed_itemsets(frequent), "Maximal": maximal_itemsets(frequent)}
    rows = [{"Kind": kind, "Size": len(s)} for kind, found in kinds.items() for s in found]
    return pd.DataFrame(rows).groupby(["Kind", "Size"]).size().rename("Itemsets").reset_index()
