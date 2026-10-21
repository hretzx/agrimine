"""
algorithms/hierarchical.py
--------------------------
Hierarchical clustering written from scratch with NumPy (no scipy, no scikit-learn).

AGGLOMERATIVE (bottom-up)
 1. Every object starts as its own cluster.
 2. Merge the two CLOSEST clusters.
 3. Update the distance from the new cluster to every other cluster, then repeat
    until one cluster is left. The list of merges is the dendrogram.

How "distance between two clusters" is measured is the LINKAGE:
    single    closest pair of members         (long, chain-like clusters)
    complete  farthest pair of members        (compact clusters)
    average   average over all member pairs   (in between)
    ward      merge that increases the total within-cluster squared error the least

All four use the same update rule (Lance-Williams). After merging i and j, the
distance from the new cluster to any other cluster k is
    d(k, i+j) = a_i d(k,i) + a_j d(k,j) + b d(i,j) + g |d(k,i) - d(k,j)|
with these coefficients (n_i = size of cluster i):
    single    a_i = a_j = 1/2,  b = 0,  g = -1/2
    complete  a_i = a_j = 1/2,  b = 0,  g = +1/2
    average   a_i = n_i/(n_i+n_j),  a_j = n_j/(n_i+n_j),  b = g = 0
    ward      a_i = (n_i+n_k)/(n_i+n_j+n_k),  a_j = (n_j+n_k)/(n_i+n_j+n_k),
              b = -n_k/(n_i+n_j+n_k),  g = 0      (worked on SQUARED distances;
              the merge height reported is the square root, as scipy does)

The result is stored as a "linkage matrix" in the same layout scipy uses: one row per
merge = [cluster a, cluster b, height, number of objects]. Objects are 0..n-1 and the
cluster made by merge m gets number n + m.

DIVISIVE (top-down): DIANA
 1. Start with everything in one cluster.
 2. Pick the cluster with the largest diameter (largest distance inside it).
 3. Split it with the "splinter group" method: the member with the largest average
    distance to the others leaves first; then keep moving members that are, on
    average, closer to the splinter group than to the rest.
 4. Repeat until every object stands alone (or a chosen number of splits).
"""
import numpy as np

LINKAGES = ["single", "complete", "average", "ward"]


def pairwise_distances(X: np.ndarray) -> np.ndarray:
    """Euclidean distance between every pair of rows (rows x rows matrix)."""
    X = np.asarray(X, dtype=float)
    sq = (X ** 2).sum(axis=1)
    return np.sqrt(np.maximum(sq[:, None] + sq[None, :] - 2 * X @ X.T, 0.0))


def standardize(X: np.ndarray) -> np.ndarray:
    """Z-score every column so no feature dominates just because of its units."""
    X = np.asarray(X, dtype=float)
    std = X.std(axis=0)
    std[std == 0] = 1.0
    return (X - X.mean(axis=0)) / std


# =============================================================================
# Agglomerative clustering
# =============================================================================
def linkage(X: np.ndarray, method: str = "ward") -> np.ndarray:
    """
    Agglomerative clustering of the rows of X.
    Returns the (n-1) x 4 linkage matrix [cluster a, cluster b, height, size].
    """
    if method not in LINKAGES:
        raise ValueError(f"Unknown linkage: {method}")
    D = pairwise_distances(X)
    n = len(D)
    if method == "ward":
        D = D ** 2                       # Ward's update works on squared distances
    D = D.copy()
    np.fill_diagonal(D, np.inf)

    active = np.ones(n, dtype=bool)      # slots still holding a cluster
    cluster_id = np.arange(n)            # which cluster number each slot holds
    size = np.ones(n)
    Z = np.zeros((n - 1, 4))

    for m in range(n - 1):
        # 1. closest pair of active clusters
        masked = np.where(active[:, None] & active[None, :], D, np.inf)
        i, j = np.unravel_index(np.argmin(masked), masked.shape)
        if i > j:
            i, j = j, i
        d_ij = D[i, j]
        ni, nj = size[i], size[j]

        # 2. Lance-Williams update of the distances from the merged cluster (kept in slot i)
        others = np.where(active)[0]
        others = others[(others != i) & (others != j)]
        dki, dkj = D[others, i], D[others, j]
        if method == "single":
            new = 0.5 * dki + 0.5 * dkj - 0.5 * np.abs(dki - dkj)
        elif method == "complete":
            new = 0.5 * dki + 0.5 * dkj + 0.5 * np.abs(dki - dkj)
        elif method == "average":
            new = (ni * dki + nj * dkj) / (ni + nj)
        else:   # ward
            nk = size[others]
            total = ni + nj + nk
            new = ((ni + nk) * dki + (nj + nk) * dkj - nk * d_ij) / total
        D[others, i] = D[i, others] = new

        # 3. record the merge (smaller cluster number first, like scipy)
        a, b = sorted((cluster_id[i], cluster_id[j]))
        height = np.sqrt(max(d_ij, 0.0)) if method == "ward" else d_ij
        Z[m] = [a, b, height, ni + nj]

        size[i] = ni + nj
        cluster_id[i] = n + m
        active[j] = False
        D[j, :] = D[:, j] = np.inf
    return Z


def _members(Z: np.ndarray, n: int | None = None) -> list[list[int]]:
    """members[c] = the original objects inside cluster number c (objects and merges)."""
    n = len(Z) + 1 if n is None else n
    members = [[i] for i in range(n)]
    for a, b, _, _ in Z:
        members.append(members[int(a)] + members[int(b)])
    return members


def cut_tree(Z: np.ndarray, k: int) -> np.ndarray:
    """
    Cut the dendrogram into k clusters: undo the last k-1 merges.
    Returns one label per object, numbered 0..k-1 in order of first appearance
    (object 0 is always in cluster 0).
    """
    n = len(Z) + 1
    k = max(1, min(int(k), n))
    kept = Z[: n - k]                            # apply only the first n-k merges
    members = _members(kept, n)
    # a cluster that is not merged again within the kept merges is one of the k final clusters
    used = {int(c) for c in kept[:, :2].ravel()}
    roots = [c for c in range(n + len(kept)) if c not in used]
    label = np.empty(n, dtype=int)
    for r, c in enumerate(roots):
        label[members[c]] = r
    # renumber in order of first appearance
    order = {}
    return np.array([order.setdefault(x, len(order)) for x in label])


def cophenetic_matrix(Z: np.ndarray) -> np.ndarray:
    """Cophenetic distance of two objects = height of the merge where they first meet."""
    n = len(Z) + 1
    members = _members(Z)
    C = np.zeros((n, n))
    for m, (a, b, h, _) in enumerate(Z):
        left, right = members[int(a)], members[int(b)]
        C[np.ix_(left, right)] = h
        C[np.ix_(right, left)] = h
    return C


def cophenetic_correlation(Z: np.ndarray, X: np.ndarray) -> float:
    """
    How faithfully the dendrogram keeps the original distances: the correlation between
    the original pairwise distances and the cophenetic distances (1 = perfectly).
    """
    D = pairwise_distances(X)
    C = cophenetic_matrix(Z)
    iu = np.triu_indices(len(D), k=1)
    return float(np.corrcoef(D[iu], C[iu])[0, 1])


def leaf_order(Z: np.ndarray) -> list[int]:
    """Objects in the left-to-right order the dendrogram draws them."""
    n = len(Z) + 1

    def walk(c):
        if c < n:
            return [c]
        a, b = int(Z[c - n, 0]), int(Z[c - n, 1])
        return walk(a) + walk(b)
    return walk(2 * n - 2)


def dendrogram_layout(Z: np.ndarray, k: int | None = None) -> dict:
    """
    Everything needed to draw the dendrogram with Plotly line traces.
    Leaves sit at x = 5, 15, 25, ... (the scipy convention); every merge is one
    upside-down U: up from the left child, across, down to the right child.
    With k given, merges below the cut are coloured by the cluster they belong to
    (cluster = cut_tree(Z, k) label) and merges above the cut get cluster None.
    Returns {"segments": [{"x": [4 values], "y": [4 values], "cluster": int | None}],
             "order": leaf order, "leaf_x": x of each leaf in that order,
             "threshold": a height between the last merge kept and the first one undone}.
    """
    n = len(Z) + 1
    order = leaf_order(Z)
    x_of = {leaf: 10 * pos + 5 for pos, leaf in enumerate(order)}
    y_of = {leaf: 0.0 for leaf in range(n)}
    labels = cut_tree(Z, k) if k else None
    members = _members(Z)
    keep = n - k if k else n - 1                     # merges with index < keep are below the cut

    segments = []
    for m, (a, b, h, _) in enumerate(Z):
        a, b = int(a), int(b)
        xa, xb = x_of[a], x_of[b]
        cluster = int(labels[members[n + m][0]]) if (k and m < keep) else None
        segments.append({"x": [xa, xa, xb, xb], "y": [y_of[a], h, h, y_of[b]], "cluster": cluster, "height": h})
        x_of[n + m], y_of[n + m] = (xa + xb) / 2, h

    threshold = None
    if k and 1 < k <= n:
        lower = Z[n - k - 1, 2] if n - k - 1 >= 0 else 0.0
        upper = Z[n - k, 2]
        threshold = float((lower + upper) / 2)
    return {"segments": segments, "order": order, "leaf_x": [10 * p + 5 for p in range(n)],
            "threshold": threshold}


# =============================================================================
# Divisive clustering (DIANA)
# =============================================================================
def _splinter_split(D: np.ndarray, group: list[int]) -> tuple[list[int], list[int]]:
    """Split one group with the splinter-group method -> (splinter group, rest)."""
    rest = list(group)
    sub = D[np.ix_(rest, rest)]
    start = rest[int(np.argmax(sub.sum(axis=1) / (len(rest) - 1)))]   # most "isolated" member
    splinter = [start]
    rest.remove(start)
    while len(rest) > 1:
        to_rest = D[np.ix_(rest, rest)].sum(axis=1) / (len(rest) - 1)
        to_splinter = D[np.ix_(rest, splinter)].mean(axis=1)
        gain = to_rest - to_splinter            # > 0: closer to the splinter group on average
        best = int(np.argmax(gain))
        if gain[best] <= 0:
            break
        splinter.append(rest.pop(best))
    return splinter, rest


def diana(X: np.ndarray, max_splits: int | None = None) -> list[dict]:
    """
    DIANA from the top: returns the splits in the order they happen. Each split is
    {"step", "diameter", "parent", "splinter", "rest"} with lists of object numbers.
    """
    D = pairwise_distances(X)
    n = len(D)
    clusters = [list(range(n))]
    splits = []
    limit = n - 1 if max_splits is None else min(max_splits, n - 1)
    while len(splits) < limit:
        diam = [D[np.ix_(c, c)].max() if len(c) > 1 else -1.0 for c in clusters]
        idx = int(np.argmax(diam))
        if diam[idx] <= 0:
            break
        parent = clusters.pop(idx)
        splinter, rest = _splinter_split(D, parent)
        clusters.extend([splinter, rest])
        splits.append({"step": len(splits) + 1, "diameter": float(diam[idx]),
                       "parent": parent, "splinter": splinter, "rest": rest})
    return splits


def diana_labels(X: np.ndarray, k: int) -> np.ndarray:
    """Cluster labels after DIANA has made k-1 splits (numbered by first appearance)."""
    n = len(X)
    k = max(1, min(int(k), n))
    clusters = [list(range(n))]
    for s in diana(X, max_splits=k - 1):
        clusters.remove(s["parent"])
        clusters.extend([s["splinter"], s["rest"]])
    label = np.empty(n, dtype=int)
    for c, members in enumerate(clusters):
        label[members] = c
    order = {}
    return np.array([order.setdefault(x, len(order)) for x in label])
