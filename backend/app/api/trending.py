from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_store
from app.categories import CATEGORIES, CATEGORY_NAMES
from app.derive import with_derived
from app.store import keys

router = APIRouter(prefix="/api")
VALID_SCOPES = {"all"} | {cid for cid, _ in CATEGORIES}


@router.get("/trending")
def trending(scope: str = "all", store=Depends(get_store)):
    if scope not in VALID_SCOPES:
        raise HTTPException(400, detail={"error": "지원하지 않는 분야입니다"})
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
