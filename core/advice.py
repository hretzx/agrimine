"""
utils/advice.py
---------------
The farmer-facing logic behind Home, What should I grow?, Crop Doctor and Plan B. Nothing here is typed in:
every number comes from the dataset or from the models already trained in utils/models.py.

  * match_scores()   how close a field is to each crop's AVERAGE profile (0 to 100). This is the same
                     "profile fit" the Crop Advisor has always used: for every feature, the distance from
                     the crop's mean in units of the crop's own spread, averaged, then 100 / (1 + distance).
                     It is a similarity score, NOT a probability and NOT a yield forecast.
  * recommend()      the best crop (Naive Bayes class probability, checked against the ID3 tree), plus every
                     crop ranked by match score.
  * soil_health()    each measurement against the range that crop actually grows in in the data
                     (10th to 90th percentile of its records = "good"; inside its observed min to max =
                     "moderate"; outside everything seen for that crop = "needs attention").
  * improvement tips short, general agronomy advice for a low / high reading (not a fertiliser prescription).
  * cluster_summary() what each K-Means group of farms mostly grows.
"""
import pandas as pd

from core.cache import cached
from core.models import get_data, train_id3, train_kmeans, train_naive_bayes
from core.preprocessing import FEATURES, TARGET, VALID_RANGES

NUTRIENTS = ["N", "P", "K", "ph"]
CLIMATE = ["temperature", "humidity", "rainfall"]
GOOD_RATIO, MODERATE_RATIO = 0.85, 0.60     # match score as a share of the best match: good / moderate / low


# ------------------------------------------------------------------ crop profiles
@cached
def crop_profiles() -> dict:
    """Per-crop mean, spread and ranges of every feature (rows = crops, columns = features)."""
    df, _ = get_data()
    g = df.groupby(TARGET)[FEATURES]
    return {"mean": g.mean(), "std": g.std(), "p10": g.quantile(0.10), "p90": g.quantile(0.90),
            "min": g.min(), "max": g.max(), "overall_std": df[FEATURES].std()}


def match_scores(values: dict) -> pd.DataFrame:
    """Every crop with its match score (0 to 100), best first. Columns: Crop, Match."""
    prof = crop_profiles()
    stds = prof["std"].clip(lower=0.1 * prof["overall_std"], axis=1)       # avoid dividing by a tiny spread
    z = ((prof["mean"] - pd.Series(values)[FEATURES]).abs() / stds).mean(axis=1)
    out = pd.DataFrame({"Crop": z.index, "Match": (100 / (1 + z)).round(1).to_numpy()})
    return out.sort_values("Match", ascending=False).reset_index(drop=True)


def match_level(score: float, best: float) -> str:
    """'good' / 'moderate' / 'low': the score as a share of the best score of any crop for this field."""
    ratio = score / best if best else 0.0
    return "good" if ratio >= GOOD_RATIO else "moderate" if ratio >= MODERATE_RATIO else "low"


def recommend(values: dict) -> dict:
    """
    The recommendation for one field.
      best        crop with the highest Naive Bayes probability (the model's answer)
      probability that probability (a class probability from Gaussian Naive Bayes, not calibrated)
      id3         the crop the ID3 tree predicts, and agrees (True when both models say the same crop)
      ranking     every crop ordered by Naive Bayes probability. Columns: Crop, Probability, Match, Level
                  (Match = profile similarity 0-100, a SEPARATE measure; Level = Match against the best Match of any crop)
      similar     every crop except `best`, ordered by Match: the crops whose conditions are closest (used for Plan B)
    """
    posterior = train_naive_bayes()["model"].posterior(values)
    best = str(posterior.index[0])
    id3_crop, _, purity = train_id3()["model"].predict_with_path(values)
    scores = match_scores(values)
    top = float(scores["Match"].max())
    match = scores.set_index("Crop")["Match"]
    ranking = pd.DataFrame({"Crop": posterior.index.astype(str), "Probability": posterior.to_numpy(float)})
    ranking["Match"] = ranking["Crop"].map(match)
    ranking["Level"] = [match_level(m, top) for m in ranking["Match"]]
    similar = scores[scores["Crop"] != best].reset_index(drop=True)
    similar["Level"] = [match_level(m, top) for m in similar["Match"]]
    return {"best": best, "probability": float(posterior.iloc[0]), "posterior": posterior,
            "id3": str(id3_crop), "id3_purity": float(purity), "agrees": str(id3_crop) == best,
            "ranking": ranking, "similar": similar}


# --------------------------------------------------------------------- soil health
def feature_status(value: float, crop: str, feature: str) -> str:
    """'good', 'moderate' or 'attention' for one measurement against one crop's data."""
    prof = crop_profiles()
    lo, hi = prof["p10"].loc[crop, feature], prof["p90"].loc[crop, feature]
    if lo <= value <= hi:
        return "good"
    if prof["min"].loc[crop, feature] <= value <= prof["max"].loc[crop, feature]:
        return "moderate"
    return "attention"


def soil_health(values: dict, crop: str) -> pd.DataFrame:
    """
    One row per measurement: the measured value, the range that `crop` grows in (10th to 90th percentile
    of its records), the status and which way it is off ('low', 'high' or '').
    Columns: Feature, Value, Low, High, Status, Direction.
    """
    prof = crop_profiles()
    rows = []
    for f in FEATURES:
        lo, hi = float(prof["p10"].loc[crop, f]), float(prof["p90"].loc[crop, f])
        v = float(values[f])
        rows.append({"Feature": f, "Value": v, "Low": lo, "High": hi, "Status": feature_status(v, crop, f),
                     "Direction": "low" if v < lo else "high" if v > hi else ""})
    return pd.DataFrame(rows)


def overall_health(health: pd.DataFrame, features: list[str] | None = None) -> tuple[str, float]:
    """('good' | 'moderate' | 'attention', 0..1): good = 1, moderate = 0.5, attention = 0, averaged."""
    part = health if features is None else health[health["Feature"].isin(features)]
    score = float(part["Status"].map({"good": 1.0, "moderate": 0.5, "attention": 0.0}).mean())
    return ("good" if score >= 0.75 else "moderate" if score >= 0.4 else "attention"), score


# What a low / high reading usually means and what farmers commonly do. General guidance only.
TIPS = {
    ("N", "low"): "Nitrogen is low: add nitrogen fertiliser or compost, or rotate with a legume crop.",
    ("N", "high"): "Nitrogen is high: skip extra nitrogen this season to avoid leafy growth and run-off.",
    ("P", "low"): "Phosphorus is low: add a phosphate fertiliser or well-rotted manure before sowing.",
    ("P", "high"): "Phosphorus is high: no phosphate needed; extra can lock up other nutrients.",
    ("K", "low"): "Potassium is low: add potash (muriate or sulphate of potash) or wood ash.",
    ("K", "high"): "Potassium is high: no potash needed this season.",
    ("ph", "low"): "The soil is acidic: lime or dolomite raises pH; organic matter helps buffer it.",
    ("ph", "high"): "The soil is alkaline: gypsum, sulphur or lots of organic matter help bring pH down.",
    ("temperature", "low"): "It is cooler than this crop likes: consider a later sowing date or a hardier crop.",
    ("temperature", "high"): "It is hotter than this crop likes: consider mulching, shade, or a heat-tolerant crop.",
    ("humidity", "low"): "The air is drier than this crop likes: mulch and irrigate more often.",
    ("humidity", "high"): "The air is more humid than this crop likes: widen spacing and watch for fungal disease.",
    ("rainfall", "low"): "Rainfall is lower than this crop usually gets: plan irrigation or drip watering.",
    ("rainfall", "high"): "Rainfall is higher than this crop usually gets: make sure the field drains well.",
}


def tip_for(feature: str, direction: str) -> str | None:
    """The tip for a low / high reading, or None when the reading is in range."""
    return TIPS.get((feature, direction))


# ---------------------------------------------------------------- reasons, ranges
def pretty_value(feature: str, value: float) -> str:
    """'202.9 mm', '6.5', '90' (N, P, K have no unit) using the units of the input form."""
    unit = VALID_RANGES[feature][2]
    num = f"{value:.0f}" if feature in ("N", "P", "K", "rainfall") else f"{value:.1f}"
    return f"{num} {unit}".strip()


def crop_range_text(crop: str, feature: str) -> str:
    """The usual range of a feature for a crop, e.g. '180 to 298 mm' (10th to 90th percentile)."""
    prof = crop_profiles()
    lo, hi = prof["p10"].loc[crop, feature], prof["p90"].loc[crop, feature]
    fmt = "{:.0f}" if feature in ("N", "P", "K", "rainfall") else "{:.1f}"
    unit = VALID_RANGES[feature][2]
    return f"{fmt.format(lo)} to {fmt.format(hi)} {unit}".strip()


def closest_features(values: dict, crop: str, n: int = 2) -> list[str]:
    """The n features where the field is closest to the crop's average (in units of its spread)."""
    prof = crop_profiles()
    stds = prof["std"].loc[crop].clip(lower=0.1 * prof["overall_std"])
    z = ((prof["mean"].loc[crop] - pd.Series(values)[FEATURES]).abs() / stds).sort_values()
    return list(z.index[:n])


def reason(values: dict, crop: str, labels: dict[str, str] | None = None) -> str:
    """One short sentence on why a crop fits: the features closest to its usual conditions."""
    labels = labels or {f: f for f in FEATURES}
    parts = [f"{labels[f].lower()} {pretty_value(f, values[f])} (usual {crop_range_text(crop, f)})"
             for f in closest_features(values, crop)]
    return "Your " + " and ".join(parts)


# ----------------------------------------------------------------- farm clusters
@cached
def cluster_summary(k: int) -> pd.DataFrame:
    """For each K-Means group: its size, the crop most of its records grow and that crop's share."""
    df, _ = get_data()
    labels = train_kmeans(k).labels_
    rows = []
    for c in range(k):
        crops = df[TARGET][labels == c]
        top = crops.value_counts()
        rows.append({"Cluster": c, "Records": int(len(crops)), "Top crop": str(top.index[0]),
                     "Share": float(top.iloc[0] / len(crops))})
    return pd.DataFrame(rows)


def nearest_cluster(values: dict, k: int) -> int:
    """Which K-Means group the field falls in (the same call the Crop Advisor makes)."""
    return int(train_kmeans(k).predict([[values[f] for f in FEATURES]])[0])


# ------------------------------------------------------------- reports used by the API (and any front end)
def doctor_report(values: dict, crop: str) -> dict:
    """
    Crop Doctor for one field and one crop: every reading against the range that crop grows in.
      overall   'good' | 'moderate' | 'attention' and score (0..1)
      readings  one dict per measurement: feature, value, low, high (the crop's usual range), status, direction, tip (English text),
                tip_key ("P.high": a front end looks the wording up in its own language)
    """
    health = soil_health(values, crop)
    overall, score = overall_health(health)
    readings = [{"feature": r.Feature, "value": float(r.Value), "low": float(r.Low), "high": float(r.High),
                 "status": r.Status, "direction": r.Direction, "tip": tip_for(r.Feature, r.Direction),
                 "tip_key": f"{r.Feature}.{r.Direction}" if r.Direction else None}
                for r in health.itertuples()]
    return {"crop": crop, "overall": overall, "score": float(score), "readings": readings,
            "needs_attention": sum(1 for r in readings if r["status"] == "attention")}


def plan_b(values: dict, preferred: str, how_many: int = 3) -> dict:
    """
    Plan B: how well does the preferred crop fit, and which other crops fit better?
      level          'good' | 'moderate' | 'low': the preferred crop's match against the best match of any crop
      alternatives   the closest other crops by match score, each with the range it needs for every reading
    """
    scores = match_scores(values).set_index("Crop")["Match"]
    top = float(scores.max())
    alternatives = []
    for crop, match in scores.drop(preferred).sort_values(ascending=False).head(how_many).items():
        needs = [{"feature": r["feature"], "low": r["low"], "high": r["high"], "status": r["status"]}
                 for r in doctor_report(values, crop)["readings"]]
        alternatives.append({"crop": crop, "match": float(match), "level": match_level(float(match), top), "needs": needs})
    return {"preferred": preferred, "preferred_match": float(scores[preferred]), "best_match": top,
            "best_crop": str(scores.idxmax()), "level": match_level(float(scores[preferred]), top), "alternatives": alternatives}
