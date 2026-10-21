"""
api/schemas.py
--------------
Every request and response of the API as a pydantic model. The OpenAPI schema generated from these IS the contract with
the web front end (api/openapi.json is committed; a test fails when it drifts from the code).

Crops and features are always sent as {key, label, label_mr}: the client picks the language, the server never translates.
"""
from typing import Literal

from pydantic import BaseModel, Field, create_model

from core.features import FEATURE_LIST

Status = Literal["good", "moderate", "attention"]       # one reading against a crop's usual range
Level = Literal["good", "moderate", "low"]               # how close a crop is compared with the closest crop
Direction = Literal["low", "high", ""]                   # which way a reading is off ("" = in range)


def _readings_model():
    """Readings with one float field per measurement, bounded by core/features.py (ge / le show up in the OpenAPI schema)."""
    fields = {f.key: (float, Field(ge=f.lo, le=f.hi, description=f"{f.label}" + (f" ({f.unit})" if f.unit else " (no unit stated by the dataset)")))
              for f in FEATURE_LIST}
    return create_model("Readings", __doc__="The seven soil and weather readings. Ranges come from core/features.py.", **fields,
                        __config__={"json_schema_extra": {"example": {"N": 90, "P": 42, "K": 43, "temperature": 20.9, "humidity": 82,
                                                                      "ph": 6.5, "rainfall": 202.9}}})


Readings = _readings_model()


class CropRef(BaseModel):
    key: str
    label: str
    label_mr: str
    family: str


class FeatureInfo(BaseModel):
    key: str
    label: str
    label_mr: str
    name: str
    unit: str
    lo: float
    hi: float
    default: float = Field(description="Median of the dataset: where a reading starts when no check is saved yet")


class FamilyInfo(BaseModel):
    key: str
    label: str
    label_mr: str


class Meta(BaseModel):
    records: int
    crops: list[CropRef]
    families: list[FamilyInfo]
    features: list[FeatureInfo]
    languages: list[str]
    saved_checks: int
    model_version: str


class RankedCrop(BaseModel):
    crop: CropRef
    probability: float = Field(description="Gaussian Naive Bayes class probability (uncalibrated, not a yield forecast)")
    match: float = Field(description="Profile similarity 0-100: closeness to the crop's average, in units of its own spread")
    level: Level


class Recommendation(BaseModel):
    best: CropRef
    probability: float
    id3: CropRef
    id3_purity: float = Field(description="Share of training rows at the ID3 leaf that are the predicted crop")
    agrees: bool
    ranking: list[RankedCrop] = Field(description="Every crop ordered by probability")
    similar: list[RankedCrop] = Field(description="Every crop except the best, ordered by match (used for Plan B)")
    reasons: list[str] = Field(description="Feature keys closest to the best crop's usual conditions")


class CheckOut(BaseModel):
    id: int
    created_at: str
    values: Readings
    categories: dict[str, str] = Field(description="low / medium / high per reading (pH: acidic / neutral / alkaline)")
    status: Literal["predicted", "pending"] = Field(description="pending only for rows saved by the old Soil Analysis page")
    predicted_crop: CropRef | None
    probability: float | None
    id3_crop: CropRef | None
    cluster_id: int | None
    model_version: str | None


class DoctorRequest(BaseModel):
    values: Readings
    crop: str


class DoctorReading(BaseModel):
    feature: str
    value: float
    low: float = Field(description="10th percentile of the crop's records")
    high: float = Field(description="90th percentile of the crop's records")
    status: Status
    direction: Direction
    tip: str | None = Field(description="General guidance in English; not a fertiliser prescription")
    tip_key: str | None = Field(description="Stable key of the tip, e.g. 'P.high': clients translate it themselves")


class DoctorResponse(BaseModel):
    crop: CropRef
    overall: Status
    score: float
    needs_attention: int
    readings: list[DoctorReading]


class PlanBRequest(BaseModel):
    values: Readings
    preferred: str


class Need(BaseModel):
    feature: str
    low: float
    high: float
    status: Status


class Alternative(BaseModel):
    crop: CropRef
    match: float
    level: Level
    needs: list[Need]


class PlanBResponse(BaseModel):
    preferred: CropRef
    preferred_match: float
    best_match: float
    best_crop: CropRef
    level: Level
    alternatives: list[Alternative]


class ErrorBody(BaseModel):
    """The ONE error shape of the API."""
    code: str
    message: str
    field: str | None = None
    errors: list[dict] | None = None


class FarmCluster(BaseModel):
    cluster: int
    records: int
    top_crop: CropRef
    share: float


class FarmsResponse(BaseModel):
    k: int
    silhouette: float
    points: list[tuple[float, float, int]] = Field(description="One [rainfall mm, temperature °C, cluster] triple per record, rounded to 0.1; a compact form on purpose (2,200 records)")
    clusters: list[FarmCluster]
    your_cluster: int | None


class CropNeeds(BaseModel):
    crop: CropRef
    temperature: float
    rainfall: float
    humidity: float


class GainRow(BaseModel):
    feature: str
    gain: float


class Pattern(BaseModel):
    antecedent: list[str]
    consequent: str
    support: float
    confidence: float
    lift: float


class PatternsResponse(BaseModel):
    total: int = Field(description="How many rules ending in a crop exist at the default thresholds")
    items: list[Pattern] = Field(description="The strongest rules by lift")


class ModelAccuracy(BaseModel):
    model: str
    accuracy: float


class AccuracyResponse(BaseModel):
    models: list[ModelAccuracy]
    train_rows: int
    test_rows: int
    seed: int = Field(description="Seed of the stratified train / test split (the same for both models)")
    metric: str = Field(description="What the accuracy number means (English text, for teachers)")


class LabStatus(BaseModel):
    available: bool = Field(description="True when something answers on the lab's port (we started it, or `make lab` did)")
    url: str = Field(description="Where the browser should open the lab")
    note: str = Field(description="Why it is or is not running, for the person starting the app")


class ID3Step(BaseModel):
    feature: str = Field(description="Feature key the tree asked about")
    value: float = Field(description="The reading's value")
    level: str = Field(description="The bin the value fell into (very low ... very high)")
    range: str = Field(description="Numeric range of that bin, as English text")
    lo: float | None = Field(description="The bin starts here (value >= lo); null = no lower limit")
    hi: float | None = Field(description="The bin ends here (value < hi); null = no upper limit")
    gain: float = Field(description="Information gain of this split, in bits")
    rows_here: int = Field(description="Training rows that reached this node")


class ID3Alternative(BaseModel):
    crop: CropRef
    match: float = Field(description="Profile match 0-100 (similarity to the crop's average, NOT the ID3 tree)")


class ID3Model(BaseModel):
    n_bins: int
    max_depth: int
    depth: int = Field(description="Depth the trained tree actually reached")
    leaves: int
    edges: dict[str, list[float]] = Field(description="Equal-frequency bin edges per feature key")


class ID3Hardest(BaseModel):
    crop: CropRef
    accuracy: float


class ID3Report(BaseModel):
    crop: CropRef
    purity: float = Field(description="Share of training rows at the final tree node that are this crop")
    cluster: int = Field(description="K-Means group (0-based) the readings fall in")
    path: list[ID3Step]
    accuracy: float = Field(description="Held-out accuracy (stratified 80/20 split, same seed as everywhere else)")
    n_train: int
    n_test: int
    alternatives: list[ID3Alternative]
    model: ID3Model
    hardest: list[ID3Hardest] = Field(description="Crops the tree finds hardest, by held-out accuracy (lowest first)")


class NBVerdictID3(BaseModel):
    crop: CropRef
    purity: float = Field(description="Share of training rows at the ID3 leaf that are the predicted crop")
    accuracy: float = Field(description="Held-out accuracy")
    nb_probability: float = Field(description="The probability Naive Bayes gives ID3's crop")


class NBVerdictNB(BaseModel):
    crop: CropRef
    probability: float = Field(description="Posterior probability of the winning crop")
    accuracy: float = Field(description="Held-out accuracy (same split as ID3)")
    n_train: int
    n_test: int


class NBTop(BaseModel):
    crop: CropRef
    probability: float


class NBWhy(BaseModel):
    feature: str = Field(description="A feature key, or 'prior' (how common the crop is)")
    difference: float = Field(description="log P(x | winner) - log P(x | runner-up); positive favours the winner")


class NBWorkedRow(BaseModel):
    feature: str
    value: float
    mean: float = Field(description="The winning crop's mean for this feature")
    sigma: float = Field(description="The winning crop's standard deviation")
    distance: float = Field(description="(value - mean) / sigma")
    log_likelihood: float


class NBWorked(BaseModel):
    crop: CropRef
    features: list[NBWorkedRow]
    prior: float
    log_prior: float
    sum_log_likelihood: float
    joint: float = Field(description="log_prior + sum_log_likelihood")
    n_crops: int


class NBPerCrop(BaseModel):
    crop: CropRef
    id3: float
    nb: float


class NBReport(BaseModel):
    agree: bool
    id3: NBVerdictID3
    nb: NBVerdictNB
    top: list[NBTop] = Field(description="The six most likely crops by Naive Bayes")
    runner_up: CropRef
    why: list[NBWhy] = Field(description="Why Naive Bayes preferred its crop over the runner-up, one row per feature plus the prior")
    why_total: float = Field(description="Sum of 'why' = ln(odds of the winner over the runner-up)")
    worked: NBWorked
    per_crop: list[NBPerCrop] = Field(description="Held-out accuracy of both models for every crop, ID3's weakest first")


class KMeansCluster(BaseModel):
    cluster: int = Field(description="0-based group number")
    records: int
    top_crop: CropRef
    share: float = Field(description="Share of the group's records that are the top crop")
    averages: dict[str, float] = Field(description="The group's centroid in real units, per feature key")


class KMeansDiagnostic(BaseModel):
    k: int
    inertia: float
    silhouette: float


class KMeansReport(BaseModel):
    k: int
    inertia: float = Field(description="Sum of squared distances to the centroids (lower = tighter groups)")
    silhouette: float = Field(description="-1 to 1, higher = better separated groups")
    variance: list[float] = Field(description="Share of the information that PC1 and PC2 keep")
    your_cluster: int
    your_point: tuple[float, float] = Field(description="The readings on the PCA map (PC1, PC2)")
    points: list[tuple[float, float, int]] = Field(description="Every record: PC1, PC2, group")
    clusters: list[KMeansCluster]
    crops: list[CropRef] = Field(description="Column order of crop_counts")
    crop_counts: list[list[int]] = Field(description="Records per group (rows) and crop (columns)")
    diagnostics: list[KMeansDiagnostic] = Field(description="Inertia and silhouette for k = 2 to 10")
    best_k: int = Field(description="The k with the highest silhouette")


class AprioriReport(BaseModel):
    itemsets: int = Field(description="Frequent itemsets found at this minimum support and size")
    rules_total: int = Field(description="Rules that meet the settings (after the crop filter)")
    seconds: float = Field(description="Measured mining time of the first run for this support and size")
    rules: list[Pattern] = Field(description="The strongest rules by lift, then confidence, then support (at most `limit`)")


class DendroSegment(BaseModel):
    x: list[float] = Field(description="Four x values of one upside-down U (left leaf column, left, right, right)")
    y: list[float] = Field(description="The matching four heights")
    cluster: int | None = Field(description="Cluster number (0-based) of a merge below the cut; null above the cut")
    height: float = Field(description="Height of this merge")


class DianaStep(BaseModel):
    step: int
    diameter: float = Field(description="Widest distance inside the group that is split")
    size: int = Field(description="Crops in the group that is split")
    splinter: list[CropRef]
    rest: list[CropRef]


class HierarchicalReport(BaseModel):
    method: Literal["ward", "average", "complete", "single"]
    k: int
    cophenetic: float = Field(description="How faithfully the tree keeps the original distances (1 = perfectly)")
    last_height: float = Field(description="Height of the final merge")
    crops: list[CropRef] = Field(description="The 22 crops; `order` indexes into this list")
    order: list[int] = Field(description="Left-to-right order of the crops along the bottom of the dendrogram")
    segments: list[DendroSegment]
    threshold: float | None = Field(description="Height of the cut that gives k clusters")
    clusters: list[list[CropRef]] = Field(description="The k clusters from the agglomerative tree")
    diana_clusters: list[list[CropRef]] = Field(description="The k clusters from top-down DIANA")
    same: bool = Field(description="Whether both methods give the same clusters at this k")
    diana_steps: list[DianaStep] = Field(description="The first splits of DIANA")
