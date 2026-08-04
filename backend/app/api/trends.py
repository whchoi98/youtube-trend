from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from app.aggregate import category_series
from app.api.deps import get_store

router = APIRouter(prefix="/api")


@router.get("/trends/categories")
def trends_categories(hours: int = Query(default=48, ge=2, le=720),
                      store=Depends(get_store)):
    until = datetime.now(timezone.utc)
    snaps = store.snapshots_range("all", until - timedelta(hours=hours), until)
    return {"hours": hours, "series": category_series(snaps)}
