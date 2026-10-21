"""
algorithms/pca.py
-----------------
Principal Component Analysis done by hand with NumPy's SVD (no scikit-learn).
Used only to draw the 7-feature rows on a 2D scatter plot in the Cluster Explorer.

Idea: find the two directions along which the standardized data varies the most
and describe every row by its position along those two directions.
"""
import numpy as np


def pca_fit(Z: np.ndarray, n_components: int = 2):
    """
    Fit PCA on already-standardized data Z (rows x features).
    Returns (mean, components, explained_ratio):
      components      - n_components x features matrix; each row is one direction
      explained_ratio - share of the total variance captured by each direction
    """
    Z = np.asarray(Z, dtype=float)
    mean = Z.mean(axis=0)
    # SVD of the centered data: the rows of Vt are the principal directions,
    # sorted from most to least variance.
    _, S, Vt = np.linalg.svd(Z - mean, full_matrices=False)
    components = Vt[:n_components].copy()
    # An SVD direction can point either way; fix the sign so results are repeatable
    for i in range(len(components)):
        if components[i][np.argmax(np.abs(components[i]))] < 0:
            components[i] *= -1
    variance = S ** 2 / (len(Z) - 1)
    return mean, components, (variance / variance.sum())[:n_components]


def pca_transform(Z: np.ndarray, mean: np.ndarray, components: np.ndarray) -> np.ndarray:
    """Project standardized rows onto the principal directions."""
    return (np.atleast_2d(Z) - mean) @ components.T
