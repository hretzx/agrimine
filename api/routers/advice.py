from fastapi import APIRouter

from api.routers.common import crop_ref, known_crop
from api.schemas import (Alternative, DoctorReading, DoctorRequest, DoctorResponse, Need, PlanBRequest, PlanBResponse, RankedCrop,
                         Readings, Recommendation)
from core import advice

router = APIRouter(tags=["advice"])


def _ranked(frame) -> list[RankedCrop]:
    has_probability = "Probability" in frame.columns
    return [RankedCrop(crop=crop_ref(r.Crop), probability=float(r.Probability) if has_probability else 0.0,
                       match=float(r.Match), level=r.Level) for r in frame.itertuples()]


@router.post("/recommend", response_model=Recommendation,
             summary="Stateless recommendation for a set of readings (nothing is saved)")
def recommend(values: Readings):
    v = values.model_dump()
    rec = advice.recommend(v)
    similar = rec["similar"].copy()
    similar["Probability"] = similar["Crop"].map(rec["posterior"]).astype(float)
    return Recommendation(best=crop_ref(rec["best"]), probability=rec["probability"], id3=crop_ref(rec["id3"]),
                          id3_purity=rec["id3_purity"], agrees=rec["agrees"], ranking=_ranked(rec["ranking"]),
                          similar=_ranked(similar), reasons=advice.closest_features(v, rec["best"], 3))


@router.post("/doctor", response_model=DoctorResponse, summary="Crop Doctor: every reading against the crop's usual range")
def doctor(body: DoctorRequest):
    crop = known_crop(body.crop)
    report = advice.doctor_report(body.values.model_dump(), crop)
    return DoctorResponse(crop=crop_ref(crop), overall=report["overall"], score=report["score"], needs_attention=report["needs_attention"],
                          readings=[DoctorReading(**r) for r in report["readings"]])


@router.post("/plan-b", response_model=PlanBResponse, summary="Plan B: how well the preferred crop fits and which crops fit better")
def plan_b(body: PlanBRequest):
    preferred = known_crop(body.preferred)
    report = advice.plan_b(body.values.model_dump(), preferred)
    return PlanBResponse(preferred=crop_ref(preferred), preferred_match=report["preferred_match"], best_match=report["best_match"],
                         best_crop=crop_ref(report["best_crop"]), level=report["level"],
                         alternatives=[Alternative(crop=crop_ref(a["crop"]), match=a["match"], level=a["level"],
                                                   needs=[Need(**n) for n in a["needs"]]) for a in report["alternatives"]])
