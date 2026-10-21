"""
utils/preprocessing.py
----------------------
Shared data helpers used by every page:
  * loading the dataset (real CSV, or a clearly-flagged synthetic fallback)
  * feature names, allowed input ranges and input validation
  * ONE shared definition of the categories (low/medium/high, acidic/neutral/
    alkaline) so Soil Analysis, Pattern Mining and the OLAP warehouse all
    describe the data in the same words.

This module deliberately does NOT import streamlit, so the database code in
db/warehouse.py can use it too.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from core.features import FEATURES_BY_KEY

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Where the REAL Kaggle "Crop Recommendation" CSV must be placed.
DATA_PATH = DATA_DIR / "Crop_recommendation.csv"
# Where the generated stand-in is saved. It is kept under a different name so it
# can never be mistaken for the real file on the next run.
SYNTHETIC_PATH = DATA_DIR / "synthetic_crop_recommendation.csv"

FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]   # model input order (do not reorder: trained models depend on it)
TARGET = "label"
DEFAULT_K = 4  # default number of K-Means clusters

# --------------------------------------------------------------- Synthetic data
# Approximate average profile of each crop: N, P, K, temp, humidity, ph, rainfall.
# Used ONLY to build a synthetic dataset when the real CSV is missing.
_CROP_PROFILES = {
    "rice": (80, 48, 40, 23.7, 82, 6.4, 236),
    "maize": (78, 48, 20, 22.4, 65, 6.25, 85),
    "chickpea": (40, 68, 80, 18.9, 17, 7.3, 80),
    "kidneybeans": (21, 68, 20, 20.0, 22, 5.75, 106),
    "pigeonpeas": (21, 68, 20, 27.7, 48, 5.8, 149),
    "mothbeans": (21, 48, 20, 28.2, 53, 6.8, 51),
    "mungbean": (21, 48, 20, 28.5, 85, 6.7, 48),
    "blackgram": (40, 67, 19, 29.0, 65, 7.1, 68),
    "lentil": (19, 68, 19, 24.5, 65, 6.9, 46),
    "pomegranate": (18, 19, 40, 21.8, 90, 6.4, 108),
    "banana": (100, 82, 50, 27.4, 80, 5.98, 104),
    "mango": (20, 27, 30, 31.2, 50, 5.76, 95),
    "grapes": (23, 132, 200, 23.8, 82, 6.0, 69),
    "watermelon": (99, 17, 50, 25.6, 85, 6.5, 50),
    "muskmelon": (100, 17, 50, 28.7, 92, 6.36, 25),
    "apple": (21, 134, 200, 22.6, 92, 5.93, 113),
    "orange": (20, 10, 10, 22.8, 92, 7.0, 110),
    "papaya": (50, 59, 50, 33.7, 92, 6.74, 143),
    "coconut": (22, 17, 31, 27.4, 95, 5.98, 176),
    "cotton": (118, 46, 20, 24.0, 80, 6.9, 80),
    "jute": (78, 46, 40, 25.0, 80, 6.7, 175),
    "coffee": (101, 29, 30, 25.5, 59, 6.8, 158),
}


def generate_synthetic_dataset(per_crop: int = 100, seed: int = 42) -> pd.DataFrame:
    """Create 22 crops x per_crop rows by adding random noise around each crop profile."""
    rng = np.random.default_rng(seed)
    rows = []
    for crop, (n, p, k, t, h, ph, r) in _CROP_PROFILES.items():
        block = pd.DataFrame({
            "N": rng.normal(n, max(3, 0.08 * n), per_crop).clip(0, 140).round(),
            "P": rng.normal(p, max(3, 0.08 * p), per_crop).clip(5, 145).round(),
            "K": rng.normal(k, max(3, 0.08 * k), per_crop).clip(5, 205).round(),
            "temperature": rng.normal(t, 1.5, per_crop).clip(8, 44),
            "humidity": rng.normal(h, 3, per_crop).clip(14, 100),
            "ph": rng.normal(ph, 0.4, per_crop).clip(3.5, 9.9),
            "rainfall": rng.normal(r, 0.12 * r + 5, per_crop).clip(20, 300),
            "label": crop,
        })
        rows.append(block)
    df = pd.concat(rows, ignore_index=True)
    return df.sample(frac=1, random_state=seed).reset_index(drop=True)


def load_dataset() -> tuple[pd.DataFrame, bool]:
    """
    Return (dataframe, is_synthetic).
    Uses the real CSV (data/Crop_recommendation.csv) when it exists. Otherwise it
    falls back to a generated stand-in and returns is_synthetic=True so pages can
    warn the user every time.
    """
    if DATA_PATH.exists():
        df = pd.read_csv(DATA_PATH)
        synthetic = False
    else:
        if SYNTHETIC_PATH.exists():
            df = pd.read_csv(SYNTHETIC_PATH)
        else:
            df = generate_synthetic_dataset()
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            df.to_csv(SYNTHETIC_PATH, index=False)
        synthetic = True

    missing = set(FEATURES + [TARGET]) - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {sorted(missing)}")
    df = df[FEATURES + [TARGET]].dropna().reset_index(drop=True)
    return df, synthetic


# ---------------------------------------------------------------- Validation
# Allowed input range per feature: (min, max, unit). N, P and K have NO unit here on purpose: the dataset does not state one
# (Kaggle only calls them "ratios"), so we do not claim kg/ha until the source is confirmed. These cover the values
# seen in the Crop Recommendation dataset, with a little headroom.
VALID_RANGES = {k: (f.lo, f.hi, f.unit) for k, f in FEATURES_BY_KEY.items()}   # from core/features.py: edit ranges there


def validate_inputs(values: dict) -> list[str]:
    """Return a list of readable error messages (empty list = all inputs valid)."""
    errors = []
    for name, (lo, hi, unit) in VALID_RANGES.items():
        v = values.get(name)
        try:
            v = float(v)
        except (TypeError, ValueError):
            v = None
        if v is None or not np.isfinite(v):
            errors.append(f"{name}: a number is required.")
        elif not lo <= v <= hi:
            errors.append(f"{name}: {v:g} is outside the allowed range {lo} to {hi}{(' ' + unit) if unit else ''}.")
    return errors


# ---------------------------------------------------------------- Categories
# Low / medium / high = bottom third, middle third, top third of the dataset.
# pH additionally has an agronomic class: acidic / neutral / alkaline.
PH_ACIDIC_BELOW = 6.0
PH_ALKALINE_ABOVE = 7.0


def category_cutoffs(df: pd.DataFrame) -> dict:
    """
    Low/medium/high cut-offs for each feature = 33rd and 67th percentile of the
    dataset. So 'high N' means 'higher than about two thirds of the records'.
    """
    return {
        f: (float(df[f].quantile(1 / 3)), float(df[f].quantile(2 / 3)))
        for f in FEATURES
    }


def categorize(value: float, cutoff: tuple[float, float]) -> str:
    """Return 'low', 'medium' or 'high' for one value given its (low, high) cut-offs."""
    low_cut, high_cut = cutoff
    if value < low_cut:
        return "low"
    if value < high_cut:
        return "medium"
    return "high"


def ph_class(value: float) -> str:
    """Agronomic pH class: acidic (< 6.0), neutral (6.0 to 7.0), alkaline (> 7.0)."""
    if value < PH_ACIDIC_BELOW:
        return "acidic"
    if value > PH_ALKALINE_ABOVE:
        return "alkaline"
    return "neutral"


def discretize_dataframe(df: pd.DataFrame, cutoffs: dict | None = None) -> pd.DataFrame:
    """
    Turn every numeric feature into a category label (one column per feature).
    Used by Pattern Mining (Apriori items) and by the OLAP warehouse.
        N, P, K, temperature, humidity, rainfall -> low / medium / high
        ph                                        -> acidic / neutral / alkaline
    """
    cutoffs = cutoffs or category_cutoffs(df)
    out = pd.DataFrame(index=df.index)
    for f in FEATURES:
        if f == "ph":
            out[f] = np.select([df[f] < PH_ACIDIC_BELOW, df[f] > PH_ALKALINE_ABOVE],
                               ["acidic", "alkaline"], default="neutral")
        else:
            lo, hi = cutoffs[f]
            out[f] = np.select([df[f] < lo, df[f] < hi], ["low", "medium"], default="high")
    return out


# ---------------------------------------------------------------- Data preparation
def iqr_bounds(values, factor: float = 1.5) -> tuple[float, float]:
    """The IQR fences: Q1 - 1.5 x IQR and Q3 + 1.5 x IQR. Values outside them are flagged as outliers."""
    q1, q3 = float(np.quantile(values, 0.25)), float(np.quantile(values, 0.75))
    spread = q3 - q1
    return q1 - factor * spread, q3 + factor * spread


def iqr_outlier_table(df: pd.DataFrame) -> pd.DataFrame:
    """For every feature: the two fences and how many rows fall outside them."""
    rows = []
    for f in FEATURES:
        lo, hi = iqr_bounds(df[f])
        rows.append({"Feature": f, "Lower fence": lo, "Upper fence": hi,
                     "Outliers": int(((df[f] < lo) | (df[f] > hi)).sum())})
    return pd.DataFrame(rows)


def min_max_scale(df: pd.DataFrame) -> pd.DataFrame:
    """Rescale every column to 0..1:  (x - min) / (max - min)."""
    span = (df.max() - df.min()).replace(0, 1.0)
    return (df - df.min()) / span


def z_score_scale(df: pd.DataFrame) -> pd.DataFrame:
    """Rescale every column to mean 0 and standard deviation 1:  (x - mean) / std."""
    std = df.std(ddof=0).replace(0, 1.0)
    return (df - df.mean()) / std


def equal_width_bins(values, n_bins: int) -> tuple[np.ndarray, np.ndarray]:
    """Cut the value range into n_bins slices of the same width -> (bin number of every value, bin edges)."""
    values = np.asarray(values, float)
    edges = np.linspace(values.min(), values.max(), n_bins + 1)
    return np.clip(np.digitize(values, edges[1:-1]), 0, n_bins - 1), edges


def equal_frequency_bins(values, n_bins: int) -> tuple[np.ndarray, np.ndarray]:
    """Cut at quantiles so every bin holds (about) the same number of values -> (bin numbers, bin edges)."""
    values = np.asarray(values, float)
    edges = np.quantile(values, np.linspace(0, 1, n_bins + 1))
    return np.clip(np.searchsorted(edges[1:-1], values, side="right"), 0, n_bins - 1), edges
