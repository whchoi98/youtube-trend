from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_store

router = APIRouter(prefix="/api")


@router.get("/videos/{video_id}/history")
def video_history(video_id: str, hours: int = Query(default=168, ge=1, le=720),
                  store=Depends(get_store)):
    until = datetime.now(timezone.utc)
    since = until - timedelta(hours=hours)
    return {"videoId": video_id, "points": store.video_history(video_id, since, until)}
