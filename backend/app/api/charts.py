"""YouTube Music 차트 시계열 API.

수집기가 차트 곡별로 적재한 소형 시계열 포인트(CVID#)를 조회한다 — 스냅샷
범위 파생(버킷당 ~14KB)과 달리 아이템이 작아 한 달(720h) 조회도 가볍다.
곡이 그 시각 차트에 없으면 해당 버킷 포인트 자체가 없다(선이 끊김).
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.api.deps import get_store
from app.charts import MUSIC_CHARTS

router = APIRouter(prefix="/api")

VALID_CHART_IDS = {suffix for suffix, _pid, _title in MUSIC_CHARTS}
# 곡별 포인트는 소형 아이템이라 스냅샷 TTL(30일)과 같은 한 달까지 허용
MAX_HOURS = 720


@router.get("/charts/{chart_id}/videos/{video_id}/history")
def chart_video_history(chart_id: str, video_id: str,
                        hours: int = Query(default=168, ge=2, le=MAX_HOURS),
                        store=Depends(get_store)):
    if chart_id not in VALID_CHART_IDS:
        return JSONResponse({"error": "지원하지 않는 차트입니다"}, status_code=400)
    now = datetime.now(timezone.utc)
    points = store.chart_video_history(chart_id, video_id,
                                       now - timedelta(hours=hours), now)
    return {"chartId": chart_id, "videoId": video_id, "points": points}
