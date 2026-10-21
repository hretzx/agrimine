"""
algorithms/regression.py
------------------------
Linear regression written from scratch with NumPy (no scikit-learn, no scipy).

  SIMPLE regression   y = a + b x          (one predictor)
      closed form:    slope b = cov(x, y) / var(x),   intercept a = mean(y) - b mean(x)
  MULTIPLE regression y = b0 + b1 x1 + ... + bk xk
      least squares:  choose the b's that make the sum of squared errors smallest;
                      np.linalg.lstsq solves this (stable even when columns are related).

Quality measures
  R-squared           1 - SSE / SST: share of the variation in y the line explains
                      (SSE = sum of squared errors, SST = sum of squares around the mean)
  adjusted R-squared  R-squared with a penalty for every extra predictor:
                      1 - (1 - R2) (n - 1) / (n - k - 1)
  RMSE                square root of the average squared error, in y's own units

Honest testing: train_test_split() keeps 20% of the rows aside, and held_out_report()
measures R-squared and RMSE on those unseen rows.
"""
import numpy as np


def r_squared(y_true, y_pred) -> float:
    """1 - SSE / SST. 1 = perfect fit, 0 = no better than always guessing the mean."""
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    sse = float(((y_true - y_pred) ** 2).sum())
    sst = float(((y_true - y_true.mean()) ** 2).sum())
    return 1.0 - sse / sst if sst > 0 else 0.0


def adjusted_r_squared(r2: float, n: int, k: int) -> float:
    """R-squared corrected for the number of predictors k (n = number of rows)."""
    if n - k - 1 <= 0:
        return float("nan")
    return 1.0 - (1.0 - r2) * (n - 1) / (n - k - 1)


def rmse(y_true, y_pred) -> float:
    """Root mean squared error, in the units of y."""
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    return float(np.sqrt(((y_true - y_pred) ** 2).mean()))


class SimpleLinearRegression:
    """y = intercept + slope * x, fitted with the closed-form formula."""

    def fit(self, x, y) -> "SimpleLinearRegression":
        x, y = np.asarray(x, float).ravel(), np.asarray(y, float).ravel()
        var_x = ((x - x.mean()) ** 2).mean()
        cov_xy = ((x - x.mean()) * (y - y.mean())).mean()
        self.slope_ = cov_xy / var_x if var_x > 0 else 0.0
        self.intercept_ = y.mean() - self.slope_ * x.mean()
        self.r2_ = r_squared(y, self.predict(x))
        self.n_ = len(x)
        return self

    def predict(self, x) -> np.ndarray:
        return self.intercept_ + self.slope_ * np.asarray(x, float).ravel()


class MultipleLinearRegression:
    """y = b0 + b1 x1 + ... + bk xk, fitted by least squares (np.linalg.lstsq)."""

    def fit(self, X, y) -> "MultipleLinearRegression":
        X, y = np.atleast_2d(np.asarray(X, float)), np.asarray(y, float).ravel()
        if X.shape[0] != len(y):
            X = X.T
        design = np.column_stack([np.ones(len(X)), X])      # a column of 1s gives the intercept
        coef, *_ = np.linalg.lstsq(design, y, rcond=None)
        self.intercept_, self.coef_ = float(coef[0]), coef[1:]
        fitted = self.predict(X)
        self.n_, self.k_ = X.shape
        self.r2_ = r_squared(y, fitted)
        self.adj_r2_ = adjusted_r_squared(self.r2_, self.n_, self.k_)
        self.rmse_ = rmse(y, fitted)
        return self

    def predict(self, X) -> np.ndarray:
        X = np.atleast_2d(np.asarray(X, float))
        return self.intercept_ + X @ self.coef_


def train_test_split(n_rows: int, test_share: float = 0.2, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """Random 80/20 split of row numbers -> (train rows, test rows). Same seed = same split."""
    order = np.random.default_rng(seed).permutation(n_rows)
    cut = int(round(n_rows * (1 - test_share)))
    return order[:cut], order[cut:]


def held_out_report(model, X_train, y_train, X_test, y_test) -> dict:
    """Fit on the training rows, then score on the unseen test rows."""
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    k = 1 if np.ndim(X_test) == 1 else np.shape(X_test)[1]
    r2 = r_squared(y_test, pred)
    return {"model": model, "test_r2": r2, "test_adj_r2": adjusted_r_squared(r2, len(y_test), k),
            "test_rmse": rmse(y_test, pred), "train_r2": model.r2_, "pred": pred}
