"""Data for the teacher pages (the algorithms made visible). One route per page; all logic is in core/teachers.py."""
from typing import Literal

from fastapi import APIRouter, Query

from api.routers.common import crop_ref
from api.schemas import (ID3Alternative, ID3Hardest, ID3Model, ID3Report, ID3Step, NBPerCrop, NBReport, NBTop, NBVerdictID3, NBVerdictNB, NBWhy, NBWorked,
                         NBWorkedRow, Readings)
from api.errors import ApiError
from api.routers.common import known_crop
from api.schemas import AprioriReport, DendroSegment, DianaStep, HierarchicalReport, KMeansCluster, KMeansDiagnostic, KMeansReport, Pattern
from core import teachers

router = APIRouter(prefix="/teachers", tags=["teachers"])


@router.post("/id3", response_model=ID3Report, summary="ID3 decision tree: the prediction, the path it took, accuracy, alternatives")
def id3(values: Readings):
    r = teachers.id3_report(values.model_dump())
    return ID3Report(
        crop=crop_ref(r["crop"]), purity=r["purity"], cluster=r["cluster"], path=[ID3Step(**s) for s in r["path"]],
        accuracy=r["accuracy"], n_train=r["n_train"], n_test=r["n_test"],
        alternatives=[ID3Alternative(crop=crop_ref(a["crop"]), match=a["match"]) for a in r["alternatives"]],
        model=ID3Model(**r["model"]), hardest=[ID3Hardest(crop=crop_ref(h["crop"]), accuracy=h["accuracy"]) for h in r["hardest"]])


@router.post("/naive-bayes", response_model=NBReport, summary="Model Council: Naive Bayes against ID3 on the same readings, with the formula worked out")
def naive_bayes(values: Readings):
    r = teachers.nb_report(values.model_dump())
    w = r["worked"]
    return NBReport(
        agree=r["agree"], id3=NBVerdictID3(**{**r["id3"], "crop": crop_ref(r["id3"]["crop"])}), nb=NBVerdictNB(**{**r["nb"], "crop": crop_ref(r["nb"]["crop"])}),
        top=[NBTop(crop=crop_ref(t["crop"]), probability=t["probability"]) for t in r["top"]], runner_up=crop_ref(r["runner_up"]),
        why=[NBWhy(**x) for x in r["why"]], why_total=r["why_total"],
        worked=NBWorked(**{**w, "crop": crop_ref(w["crop"]), "features": [NBWorkedRow(**f) for f in w["features"]]}),
        per_crop=[NBPerCrop(crop=crop_ref(p["crop"]), id3=p["id3"], nb=p["nb"]) for p in r["per_crop"]])


@router.post("/kmeans", response_model=KMeansReport, summary="Cluster Explorer: K-Means groups on a PCA map, profiles, crops per group, choosing k")
def kmeans(values: Readings, k: int = Query(4, ge=2, le=10, description="Number of groups")):
    r = teachers.kmeans_report(values.model_dump(), k)
    return KMeansReport(
        **{**r, "clusters": [KMeansCluster(**{**c, "top_crop": crop_ref(c["top_crop"])}) for c in r["clusters"]],
           "crops": [crop_ref(c) for c in r["crops"]], "diagnostics": [KMeansDiagnostic(**d) for d in r["diagnostics"]]})


@router.get("/apriori", response_model=AprioriReport, summary="Pattern Mining: Apriori association rules at the chosen support, confidence and size")
def apriori_rules(min_support: float = Query(0.01, ge=0.005, le=0.10), min_confidence: float = Query(0.6, ge=0.5, le=1.0),
                  max_len: int = Query(5, ge=2, le=5, description="Largest pattern size, in items"),
                  crop: str | None = Query(None, description="Only rules that mention this crop"),
                  only_crop: bool = Query(True, description="Only rules that end in a crop"), limit: int = Query(100, ge=1, le=500)):
    if crop is not None:
        known_crop(crop)
    r = teachers.apriori_report(min_support, min_confidence, max_len, crop, only_crop, limit)
    return AprioriReport(itemsets=r["itemsets"], rules_total=r["rules_total"], seconds=r["seconds"],
                         rules=[Pattern(**x) for x in r["rules"]])


@router.get("/hierarchical", response_model=HierarchicalReport, summary="Hierarchical clustering of the 22 crops: dendrogram, k clusters, and top-down DIANA")
def hierarchical(method: Literal["ward", "average", "complete", "single"] = Query("ward", description="How the distance between two groups is measured"),
                 k: int = Query(4, ge=2, le=10, description="Cut the tree into this many clusters")):
    r = teachers.hierarchical_report(method, k)
    refs = lambda keys: [crop_ref(c) for c in keys]
    return HierarchicalReport(
        **{**r, "crops": refs(r["crops"]), "segments": [DendroSegment(**g) for g in r["segments"]],
           "clusters": [refs(c) for c in r["clusters"]], "diana_clusters": [refs(c) for c in r["diana_clusters"]],
           "diana_steps": [DianaStep(**{**st, "splinter": refs(st["splinter"]), "rest": refs(st["rest"])}) for st in r["diana_steps"]]})
