"""
algorithms/naive_bayes.py
-------------------------
Gaussian Naive Bayes written from scratch (no scikit-learn).

How it works, in plain language:
 1. PRIOR: how common each crop is in the training rows, P(crop).
 2. LIKELIHOOD: for every crop and every feature we store the mean and the variance
    of that feature over the crop's rows. A new value is scored with the normal
    (Gaussian) bell curve of that crop: values near the crop's mean score high.
 3. "NAIVE": we pretend the features are independent once the crop is known, so the
    likelihood of the whole row is the PRODUCT of the seven per-feature scores.
 4. BAYES' RULE:  P(crop | row) is proportional to P(crop) x P(row | crop).
    Multiplying many small numbers underflows, so we add LOGARITHMS instead and turn
    the totals back into probabilities with the softmax (subtract the largest, exp,
    divide by the sum).

A tiny "variance floor" is added to every variance so a feature that happens to be
constant for one crop does not cause a division by zero.
"""
import numpy as np
import pandas as pd


class GaussianNaiveBayes:
    def __init__(self, var_smoothing: float = 1e-9):
        # variance floor = var_smoothing x the largest feature variance (same idea as
        # the usual textbook / library default)
        self.var_smoothing = var_smoothing

    # ---------------------------------------------------------------- training
    def fit(self, df: pd.DataFrame, features: list[str], target: str) -> "GaussianNaiveBayes":
        self.features = list(features)
        X = df[self.features].to_numpy(float)
        y = df[target].to_numpy()
        self.classes_ = np.array(sorted(pd.unique(y)))
        self.epsilon_ = self.var_smoothing * X.var(axis=0).max()

        self.prior_ = np.empty(len(self.classes_))
        self.mean_ = np.empty((len(self.classes_), X.shape[1]))
        self.var_ = np.empty((len(self.classes_), X.shape[1]))
        for i, c in enumerate(self.classes_):
            rows = X[y == c]
            self.prior_[i] = len(rows) / len(X)          # P(crop)
            self.mean_[i] = rows.mean(axis=0)            # per-crop mean of every feature
            self.var_[i] = rows.var(axis=0) + self.epsilon_   # per-crop variance + floor
        return self

    # -------------------------------------------------------------- the maths
    def _as_matrix(self, X) -> np.ndarray:
        """Accept a DataFrame, a dict (one row) or an array and return rows x features."""
        if isinstance(X, dict):
            return np.array([[float(X[f]) for f in self.features]])
        if isinstance(X, pd.DataFrame):
            return X[self.features].to_numpy(float)
        return np.atleast_2d(np.asarray(X, dtype=float))

    def feature_log_likelihood(self, X) -> np.ndarray:
        """
        log N(x | mean, var) for every row, crop and feature -> shape (rows, crops, features).
        Normal density: 1 / sqrt(2 pi var) * exp(-(x - mean)^2 / (2 var)); its log is below.
        """
        X = self._as_matrix(X)
        diff = X[:, None, :] - self.mean_[None, :, :]
        return -0.5 * np.log(2 * np.pi * self.var_)[None, :, :] - diff ** 2 / (2 * self.var_[None, :, :])

    def joint_log_likelihood(self, X) -> np.ndarray:
        """log P(crop) + sum over features of log P(x_f | crop) -> shape (rows, crops)."""
        return np.log(self.prior_)[None, :] + self.feature_log_likelihood(X).sum(axis=2)

    def predict_proba(self, X) -> np.ndarray:
        """Softmax of the joint log-likelihoods = posterior probability of every crop."""
        jll = self.joint_log_likelihood(X)
        jll = jll - jll.max(axis=1, keepdims=True)       # largest becomes 0: exp() cannot overflow
        p = np.exp(jll)
        return p / p.sum(axis=1, keepdims=True)

    def predict(self, X) -> np.ndarray:
        """Crop with the highest posterior probability for every row."""
        return self.classes_[self.joint_log_likelihood(X).argmax(axis=1)]

    def posterior(self, row: dict) -> pd.Series:
        """Posterior of every crop for ONE input, sorted from most to least likely."""
        return pd.Series(self.predict_proba(row)[0], index=self.classes_).sort_values(ascending=False)

    # --------------------------------------------------------------- explaining
    def explain(self, row: dict, winner: str | None = None, runner_up: str | None = None) -> pd.DataFrame:
        """
        Which features favoured the winner over the runner-up?
        For every feature: log P(x | winner) - log P(x | runner-up). Positive = this
        value is more typical of the winner. The prior difference is added as its own
        row, and the column total equals the log of the posterior odds
        log( P(winner | x) / P(runner-up | x) ).
        """
        post = self.posterior(row)
        winner = winner or post.index[0]
        runner_up = runner_up or post.index[1]
        wi = int(np.where(self.classes_ == winner)[0][0])
        ri = int(np.where(self.classes_ == runner_up)[0][0])
        ll = self.feature_log_likelihood(row)[0]
        out = pd.DataFrame({
            "Feature": self.features,
            "Value": [float(row[f]) for f in self.features],
            "Winner mean": self.mean_[wi],
            "Runner-up mean": self.mean_[ri],
            "Log-likelihood difference": ll[wi] - ll[ri],
        })
        prior = pd.DataFrame([{"Feature": "prior", "Value": np.nan, "Winner mean": np.nan, "Runner-up mean": np.nan,
                               "Log-likelihood difference": float(np.log(self.prior_[wi]) - np.log(self.prior_[ri]))}])
        out = pd.concat([out, prior], ignore_index=True)
        out["Favours"] = np.where(out["Log-likelihood difference"] >= 0, winner, runner_up)
        return out.sort_values("Log-likelihood difference", key=np.abs, ascending=False).reset_index(drop=True)
