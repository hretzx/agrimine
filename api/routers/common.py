"""Small helpers shared by the routers."""
from api.errors import ApiError
from api.schemas import CropRef
from core.crops import CROPS_BY_KEY


def crop_ref(key: str) -> CropRef:
    c = CROPS_BY_KEY[key]
    return CropRef(key=c.key, label=c.label, label_mr=c.label_mr, family=c.family)


def known_crop(key: str) -> str:
    """The crop key, or a 404 in the API's error shape."""
    if key not in CROPS_BY_KEY:
        raise ApiError(404, "unknown_crop", f"There is no crop called '{key}'.", "crop")
    return key
