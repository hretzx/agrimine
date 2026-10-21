from fastapi import APIRouter, Query

from api.errors import ApiError
from api.routers.common import crop_ref
from api.schemas import (AccuracyResponse, CropNeeds, FarmCluster, FarmsResponse, GainRow, ModelAccuracy, Pattern, PatternsResponse)
from core import advice, checks
from core.models import (SPLIT_SEED, crop_rules, get_data, id3_root_gains, kmeans_silhouette, train_id3, train_kmeans, train_naive_bayes)
from core.preprocessing import TARGET

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/farms", response_model=FarmsResponse, summary="K-Means groups of similar conditions (rainfall x temperature)")
def farms(k: int = Query(4, ge=3, le=5), check: int | None = Query(None, description="Include this check's group")):
    df, _ = get_data()
    labels = train_kmeans(k).labels_
    summary = advice.cluster_summary(k)
    your = None
    if check is not None:
        record = checks.get_check(check)
        if record is None:
            raise ApiError(404, "unknown_check", f"There is no soil check #{check}.", "check")
        your = advice.nearest_cluster(record["values"], k)
    return FarmsResponse(
        k=k, silhouette=kmeans_silhouette(k), your_cluster=your,
        points=[(round(float(r), 1), round(float(t), 1), int(c)) for r, t, c in zip(df["rainfall"], df["temperature"], labels)],
        clusters=[FarmCluster(cluster=int(r.Cluster), records=int(r.Records), top_crop=crop_ref(r._3), share=float(r.Share))
                  for r in summary.itertuples()])


@router.get("/needs", response_model=list[CropNeeds], summary="Average temperature, rainfall and humidity of every crop")
def needs():
    df, _ = get_data()
    mean = df.groupby(TARGET)[["temperature", "rainfall", "humidity"]].mean()
    return [CropNeeds(crop=crop_ref(c), temperature=float(r.temperature), rainfall=float(r.rainfall), humidity=float(r.humidity))
            for c, r in mean.iterrows()]


@router.get("/gain", response_model=list[GainRow], summary="ID3 information gain of every reading at the tree's root, largest first")
def gain():
    g = id3_root_gains().sort_values("Gain", ascending=False)
    return [GainRow(feature=r.Feature, gain=float(r.Gain)) for r in g.itertuples()]


@router.get("/patterns", response_model=PatternsResponse, summary="Apriori rules that end in a crop, strongest lift first")
def patterns(limit: int = Query(5, ge=1, le=50)):
    rules = crop_rules()
    return PatternsResponse(total=len(rules), items=[
        Pattern(antecedent=r.Antecedent.split(" AND "), consequent=r.Consequent, support=float(r.Support),
                confidence=float(r.Confidence), lift=float(r.Lift)) for r in rules.head(limit).itertuples()])


@router.get("/accuracy", response_model=AccuracyResponse, summary="Held-out accuracy of the two classifiers")
def accuracy():
    nb, id3 = train_naive_bayes(), train_id3()
    return AccuracyResponse(models=[ModelAccuracy(model="Naive Bayes", accuracy=nb["accuracy"]), ModelAccuracy(model="ID3 decision tree", accuracy=id3["accuracy"])],
                            train_rows=nb["n_train"], test_rows=nb["n_test"], seed=SPLIT_SEED,
                            metric="accuracy: share of held-out rows classified correctly")
