from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import get_store
from app.categories import CATEGORIES, CATEGORY_NAMES
from app.derive import with_derived
from app.store import keys

router = APIRouter(prefix="/api")
VALID_SCOPES = {"all"} | {cid for cid, _ in CATEGORIES}


@router.get("/trending")
def trending(scope: str = "all", store=Depends(get_store)):
    if scope not in VALID_SCOPES:
        return JSONResponse({"error": "지원하지 않는 분야입니다"}, status_code=400)
    snap = store.latest_snapshot(scope)
    if snap is None:
        return []
    now = datetime.now(timezone.utc)
    baseline = store.baseline_snapshot(scope, now, keys.RECENT_OFFSETS,
                                       min_age_hours=keys.MIN_AGE_HOURS)
    return with_derived(snap["items"], baseline, now)


@router.get("/categories")
def categories():
    return [{"id": cid, "name": CATEGORY_NAMES[cid]} for cid, _ in CATEGORIES]
