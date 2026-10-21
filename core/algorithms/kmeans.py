"""
algorithms/kmeans.py
--------------------
K-Means clustering written from scratch (no scikit-learn).

Steps:
 1. Standardize every feature (z-score) so rainfall (hundreds) does not drown
    out pH (single digits).
 2. Pick k starting centroids (k-means++ spreads them out smartly).
 3. Repeat: assign each row to its nearest centroid, then move each centroid to
    the mean of its rows, until nothing changes.
 4. Run several random starts and keep the one with the lowest inertia
    (sum of squared distances to the centroids).

Also in this file: silhouette_score(), a quality measure used with the elbow plot.
"""
import numpy as np


class KMeans:
    def __init__(self, k: int = 4, init: str = "kmeans++", max_iter: int = 100,
                 n_init: int = 5, seed: int = 42):
        self.k, self.init, self.max_iter = k, init, max_iter
        self.n_init, self.seed = n_init, seed

    # ---------------------------------------------------------- standardizing
    def transform(self, X) -> np.ndarray:
        """Z-score: (value - feature mean) / feature standard deviation."""
        return (np.atleast_2d(np.asarray(X, dtype=float)) - self.mean_) / self.std_

    # ---------------------------------------------------------- initialising
    def _init_centroids(self, Z, rng):
        if self.init == "random":
            return Z[rng.choice(len(Z), self.k, replace=False)]
        # k-means++: first centroid random, the others chosen with probability
        # proportional to squared distance from the nearest centroid so far
        centroids = [Z[rng.integers(len(Z))]]
        for _ in range(self.k - 1):
            d2 = np.min([((Z - c) ** 2).sum(axis=1) for c in centroids], axis=0)
            total = d2.sum()
            if total == 0:                      # all rows identical: any row will do
                centroids.append(Z[rng.integers(len(Z))])
            else:
                centroids.append(Z[rng.choice(len(Z), p=d2 / total)])
        return np.array(centroids)

    # ---------------------------------------------------------- one full run
    def _run_once(self, Z, rng):
        centroids = self._init_centroids(Z, rng)
        for _ in range(self.max_iter):
            d = ((Z[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
            labels = d.argmin(axis=1)           # step 1: nearest centroid for every row
            new = np.array([Z[labels == j].mean(axis=0) if (labels == j).any() else centroids[j]
                            for j in range(self.k)])   # step 2: move centroids to cluster means
            if np.allclose(new, centroids):
                break
            centroids = new
        d = ((Z[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        labels = d.argmin(axis=1)
        return centroids, labels, float(d[np.arange(len(Z)), labels].sum())

    def fit(self, X) -> "KMeans":
        X = np.asarray(X, dtype=float)
        self.mean_, self.std_ = X.mean(axis=0), X.std(axis=0)
        self.std_[self.std_ == 0] = 1.0
        Z = self.transform(X)
        rng = np.random.default_rng(self.seed)
        best = None
        for _ in range(self.n_init):
            result = self._run_once(Z, rng)
            if best is None or result[2] < best[2]:
                best = result
        self.centroids_, self.labels_, self.inertia_ = best
        return self

    # ---------------------------------------------------------- using the model
    def predict(self, X) -> np.ndarray:
        """Assign new rows to the nearest centroid (in standardized space)."""
        return self.distances(X).argmin(axis=1)

    def distances(self, X) -> np.ndarray:
        """Distance (standardized space) from each row to every centroid."""
        Z = self.transform(X)
        return np.sqrt(((Z[:, None, :] - self.centroids_[None, :, :]) ** 2).sum(axis=2))

    def centroids_original(self) -> np.ndarray:
        """Centroids converted back to the original units (for profile tables)."""
        return self.centroids_ * self.std_ + self.mean_


def silhouette_score(Z: np.ndarray, labels: np.ndarray) -> float:
    """
    Average silhouette over all rows (range -1 to 1, higher = better separated).
    For one row:  a = average distance to the other rows of its OWN cluster
                  b = average distance to the rows of the NEAREST OTHER cluster
                  silhouette = (b - a) / max(a, b)
    """
    Z = np.asarray(Z, dtype=float)
    labels = np.asarray(labels)
    n = len(Z)
    clusters = np.unique(labels)
    if len(clusters) < 2:
        return 0.0
    # full distance matrix between all pairs of rows
    sq = (Z ** 2).sum(axis=1)
    D = np.sqrt(np.maximum(sq[:, None] + sq[None, :] - 2 * Z @ Z.T, 0.0))
    member = (labels[:, None] == clusters[None, :]).astype(float)   # row x cluster 0/1 table
    sums = D @ member                      # total distance from each row to every cluster
    sizes = member.sum(axis=0)
    own = np.searchsorted(clusters, labels)
    idx = np.arange(n)
    a = sums[idx, own] / np.maximum(sizes[own] - 1, 1)
    others = sums / sizes[None, :]
    others[idx, own] = np.inf              # ignore the row's own cluster
    b = others.min(axis=1)
    s = (b - a) / np.maximum(np.maximum(a, b), 1e-12)
    s[sizes[own] == 1] = 0.0               # a cluster with one row has silhouette 0
    return float(s.mean())
