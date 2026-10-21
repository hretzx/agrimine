from fastapi import APIRouter, Query

from api.errors import ApiError
from api.routers.common import crop_ref
from api.schemas import CheckOut, Readings
from core import checks

router = APIRouter(prefix="/checks", tags=["checks"])


def to_out(record: dict) -> CheckOut:
    pick = lambda key: crop_ref(key) if key else None
    return CheckOut(id=record["id"], created_at=record["created_at"], values=record["values"], categories=record["categories"],
                    status=record["status"], predicted_crop=pick(record["predicted_crop"]), probability=record["probability"],
                    id3_crop=pick(record["id3_crop"]), cluster_id=record["cluster_id"], model_version=record["model_version"])


@router.post("", response_model=CheckOut, status_code=201,
             summary="Create a soil check: validate, predict and save in one transaction")
def create(values: Readings):
    return to_out(checks.create_check(values.model_dump()))


@router.get("", response_model=list[CheckOut], summary="Recent checks, newest first")
def recent(limit: int = Query(10, ge=1, le=100)):
    return [to_out(r) for r in checks.list_checks(limit)]


@router.get("/{check_id}", response_model=CheckOut, summary="One check")
def one(check_id: int):
    record = checks.get_check(check_id)
    if record is None:
        raise ApiError(404, "unknown_check", f"There is no soil check #{check_id}.", "check_id")
    return to_out(record)
