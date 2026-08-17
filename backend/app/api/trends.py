import math
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from app.aggregate import category_series
from app.api.deps import get_store

router = APIRouter(prefix="/api")

# 96h까지는 전 버킷 Query(스냅샷 ~11KB×버킷, 1MB 한도 내 안전 마진).
# 그 초과(~720h)는 step 간격 GetItem 다운샘플 — 포인트 수를 96 이하로 유지해
# 읽기량이 기간과 무관하게 상수다. entered/exited는 인접 샘플 버킷 간 차이가
# 된다(1시간 간격이 아니라 step 간격 변화량).
FULL_RANGE_MAX_HOURS = 96
MAX_POINTS = 96


@router.get("/trends/categories")
def trends_categories(
    hours: int = Query(default=48, ge=2, le=720),
    store=Depends(get_store)):
    until = datetime.now(timezone.utc)
    since = until - timedelta(hours=hours)
    if hours <= FULL_RANGE_MAX_HOURS:
        step = 1
        snaps = store.snapshots_range("all", since, until)
    else:
        step = math.ceil(hours / MAX_POINTS)
        snaps = store.snapshots_sampled("all", since, until, step)
    return {"hours": hours, "stepHours": step, "series": category_series(snaps)}
