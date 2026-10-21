from fastapi import APIRouter

from api.routers.common import crop_ref
from api.schemas import FamilyInfo, FeatureInfo, Meta
from core.checks import MODEL_VERSION, count_checks
from core.crops import CROP_LIST, FAMILIES, FAMILY_LABELS
from core.features import FEATURE_LIST
from core.models import get_data

router = APIRouter(tags=["meta"])


@router.get("/meta", response_model=Meta, summary="Counts, crops, the feature registry and languages")
def meta():
    df, _ = get_data()
    return Meta(records=len(df), crops=[crop_ref(c.key) for c in CROP_LIST],
                families=[FamilyInfo(key=f, label=FAMILY_LABELS[f][0], label_mr=FAMILY_LABELS[f][1]) for f in FAMILIES],
                features=[FeatureInfo(key=f.key, label=f.label, label_mr=f.label_mr, name=f.name, unit=f.unit, lo=f.lo, hi=f.hi,
                                      default=round(float(df[f.key].median()), 1))
                          for f in FEATURE_LIST],
                languages=["en", "mr"], saved_checks=count_checks(), model_version=MODEL_VERSION)
