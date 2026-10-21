"""
core/teachers.py
----------------
What the teacher pages show, as plain data (no Streamlit, no HTML): one function per algorithm page. The Streamlit lab and the
web app both read these, so the numbers on the two can never differ. Every number is computed from the dataset and the models.

    id3_report(values)  -> the ID3 decision tree's answer, the path it took, held-out accuracy, alternatives, model details
    apriori_report(...) -> association rules mined with Apriori at the chosen support, confidence and size (the lab's Pattern Mining)
    hierarchical_report(method, k) -> a family tree of the 22 crops, bottom-up (four linkages) and top-down (DIANA) (the lab's Hierarchical page)
    kmeans_report(values, k) -> K-Means groups on a 2D PCA map, profiles, crops per group, elbow and silhouette (the lab's Cluster Explorer)
    nb_report(values)   -> Naive Bayes against ID3 on the same readings (the lab's Model Council page)
"""
import numpy as np

import time

from core import advice
from core.algorithms.apriori import apriori, association_rules
from core.algorithms.hierarchical import cut_tree, dendrogram_layout, diana_labels
from core.cache import cached
import pandas as pd

from core.preprocessing import DEFAULT_K, FEATURES, TARGET
from core.models import crop_diana, crop_linkage, crop_profiles_standardized, get_data, get_projection, mining_items, kmeans_diagnostics, project_point, train_id3, train_kmeans, train_naive_bayes


def id3_report(values: dict) -> dict:
    """The Crop Advisor page: ID3's prediction for one set of readings and how it got there."""
    trained = train_id3()
    model = trained["model"]
    crop, path, purity = model.predict_with_path(values)
    for step in path:                                               # the bin as numbers too, so a front end can word it in any language
        edges, b = model.edges[step["feature"]], int(model._bin_col(step["feature"], [step["value"]])[0])
        step["lo"] = float(edges[b - 1]) if b > 0 else None         # the value is >= lo ...
        step["hi"] = float(edges[b]) if b < len(edges) else None    # ... and < hi (None = no limit on that side)
    alternatives = advice.match_scores(values)
    alternatives = alternatives[alternatives["Crop"] != crop].head(3)
    return {
        "crop": crop,
        "purity": purity,                                           # share of training rows at the final node that are `crop`
        "cluster": advice.nearest_cluster(values, DEFAULT_K),       # K-Means group (0-based), the k the Home page uses
        "path": path,                                               # [{feature, value, level, range, lo, hi, gain, rows_here}, ...]
        "accuracy": trained["accuracy"], "n_train": trained["n_train"], "n_test": trained["n_test"],
        "alternatives": [{"crop": r.Crop, "match": float(r.Match)} for r in alternatives.itertuples()],
        "model": {
            "n_bins": model.n_bins, "max_depth": model.max_depth, "depth": model.depth(), "leaves": model.n_leaves(),
            "edges": {f: [float(e) for e in np.asarray(model.edges[f])] for f in FEATURES},
        },
        "hardest": [{"crop": r.Crop, "accuracy": float(r.Accuracy)} for r in trained["per_crop"].head(5).itertuples()],
    }


def nb_report(values: dict) -> dict:
    """The Model Council page: ID3 and Gaussian Naive Bayes on the same readings, where they agree, why Naive Bayes chose, and the formula worked out."""
    id3, nb = train_id3(), train_naive_bayes()
    id3_crop, _, purity = id3["model"].predict_with_path(values)
    model = nb["model"]
    posterior = model.posterior(values)
    nb_crop, nb_prob = posterior.index[0], float(posterior.iloc[0])
    runner_up = posterior.index[1]
    why = model.explain(values)                                     # one row per feature + the prior; the column adds up to ln(odds)
    wi = int(np.where(model.classes_ == nb_crop)[0][0])
    ll = model.feature_log_likelihood(values)[0, wi]
    jll = model.joint_log_likelihood(values)[0]
    sigma = np.sqrt(model.var_[wi])
    per = (id3["per_crop"][["Crop", "Accuracy"]].rename(columns={"Accuracy": "ID3"})
           .merge(nb["per_crop"][["Crop", "Accuracy"]].rename(columns={"Accuracy": "NaiveBayes"}), on="Crop")
           .sort_values(["ID3", "NaiveBayes"]).reset_index(drop=True))
    return {
        "agree": id3_crop == nb_crop,
        "id3": {"crop": id3_crop, "purity": purity, "accuracy": id3["accuracy"], "nb_probability": float(posterior.get(id3_crop, 0.0))},
        "nb": {"crop": nb_crop, "probability": nb_prob, "accuracy": nb["accuracy"], "n_train": nb["n_train"], "n_test": nb["n_test"]},
        "top": [{"crop": c, "probability": float(p)} for c, p in posterior.head(6).items()],
        "runner_up": runner_up,
        "why": [{"feature": f, "difference": float(d)} for f, d in zip(why["Feature"], why["Log-likelihood difference"])],
        "why_total": float(why["Log-likelihood difference"].sum()),
        "worked": {
            "crop": nb_crop,
            "features": [{"feature": f, "value": float(values[f]), "mean": float(model.mean_[wi][i]), "sigma": float(sigma[i]),
                          "distance": float((values[f] - model.mean_[wi][i]) / sigma[i]), "log_likelihood": float(ll[i])}
                         for i, f in enumerate(FEATURES)],
            "prior": float(model.prior_[wi]), "log_prior": float(np.log(model.prior_[wi])), "sum_log_likelihood": float(ll.sum()),
            "joint": float(jll[wi]), "n_crops": len(jll),
        },
        "per_crop": [{"crop": r.Crop, "id3": float(r.ID3), "nb": float(r.NaiveBayes)} for r in per.itertuples()],
    }


def kmeans_report(values: dict, k: int) -> dict:
    """The Cluster Explorer page: K-Means with k groups on a 2D PCA map, group profiles in real units, which crops sit in which group, and how to choose k."""
    df, _ = get_data()
    km = train_kmeans(k)
    labels = km.labels_
    projection = get_projection()
    coords = projection["coords"]
    diag = kmeans_diagnostics()
    row = diag[diag["k"] == k].iloc[0]
    yours = project_point(projection, values)
    averages = df[FEATURES].groupby(labels).mean()                      # centroids in the original units
    crops = pd.crosstab(labels, df[TARGET])                              # groups x crops
    sizes = pd.Series(labels).value_counts().sort_index()
    return {
        "k": k, "inertia": float(row["Inertia"]), "silhouette": float(row["Silhouette"]),
        "variance": [float(v) for v in projection["ratio"]],            # share of the information PC1 and PC2 keep
        "your_cluster": advice.nearest_cluster(values, k),
        "your_point": [float(yours[0]), float(yours[1])],
        "points": [[round(float(x), 2), round(float(y), 2), int(c)] for (x, y), c in zip(coords, labels)],
        "clusters": [{"cluster": int(c), "records": int(sizes[c]), "top_crop": crops.loc[c].idxmax(), "share": float(crops.loc[c].max() / crops.loc[c].sum()),
                      "averages": {f: float(averages.loc[c, f]) for f in FEATURES}} for c in averages.index],
        "crops": [str(c) for c in crops.columns],
        "crop_counts": [[int(n) for n in crops.loc[c]] for c in crops.index],   # [group][crop]
        "diagnostics": [{"k": int(r.k), "inertia": float(r.Inertia), "silhouette": float(r.Silhouette)} for r in diag.itertuples()],
        "best_k": int(diag.loc[diag["Silhouette"].idxmax(), "k"]),
    }


@cached
def _mine(min_support: float, max_len: int) -> tuple[dict, float]:
    """Run Apriori once per (support, size) and remember it, with the time it took (measured, never typed in), so moving only the confidence is instant."""
    items = mining_items()
    started = time.perf_counter()
    frequent = apriori(items["masks"], items["n_rows"], min_support, max_len)
    return frequent, time.perf_counter() - started


def apriori_report(min_support: float, min_confidence: float, max_len: int, crop: str | None, only_crop: bool, limit: int = 100) -> dict:
    """The Pattern Mining page: association rules from Apriori on the categorised readings and crops. These are associations in the data, not causes."""
    items = mining_items()
    frequent, seconds = _mine(round(min_support, 4), max_len)
    rules = association_rules(frequent, items["names"], items["n_rows"], min_confidence, "crop=" if only_crop else None)
    if crop:
        item = f"crop={crop}"
        mentions = rules["Antecedent"].apply(lambda text: item in text.split(" AND "))
        rules = rules[(rules["Consequent"] == item) | mentions].reset_index(drop=True)
    return {
        "itemsets": len(frequent), "rules_total": len(rules), "seconds": seconds,
        "rules": [{"antecedent": r.Antecedent.split(" AND "), "consequent": r.Consequent, "support": float(r.Support),
                   "confidence": float(r.Confidence), "lift": float(r.Lift)} for r in rules.head(limit).itertuples()],
    }


LINKAGES = ("ward", "average", "complete", "single")


def hierarchical_report(method: str, k: int) -> dict:
    """The Hierarchical page: the 22 crops as a family tree. Bottom-up (agglomerative, with the chosen linkage) cut into k clusters, and top-down (DIANA)."""
    crops, X = crop_profiles_standardized()
    info = crop_linkage(method)
    Z = info["Z"]
    labels = cut_tree(Z, k)
    layout = dendrogram_layout(Z, k)
    groups = lambda lab: [[crops[i] for i in range(len(crops)) if lab[i] == c] for c in range(k)]      # crop keys per cluster
    dlabels = diana_labels(X, k)
    steps = crop_diana()
    return {
        "method": method, "k": k, "cophenetic": float(info["cophenetic"]), "last_height": float(Z[-1, 2]),
        "crops": crops, "order": [int(i) for i in layout["order"]],
        "segments": [{"x": [float(v) for v in g["x"]], "y": [float(v) for v in g["y"]], "cluster": g["cluster"], "height": float(g["height"])} for g in layout["segments"]],
        "threshold": layout["threshold"], "clusters": groups(labels), "diana_clusters": groups(dlabels),
        "same": {frozenset(c) for c in groups(labels)} == {frozenset(c) for c in groups(dlabels)},
        "diana_steps": [{"step": int(st["step"]), "diameter": float(st["diameter"]), "size": len(st["parent"]),
                         "splinter": [crops[i] for i in st["splinter"]], "rest": [crops[i] for i in st["rest"]]} for st in steps[:min(len(steps), k + 4)]],
    }
