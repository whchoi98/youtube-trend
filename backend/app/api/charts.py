"""YouTube Music 차트 시계열 API.

차트 스냅샷(시간별 저장)에서 특정 곡의 순위/조회수 추이를 계산한다 —
별도 시계열 쓰기 없이 스냅샷 범위 조회로 파생한다. 곡이 그 시각 차트에
없으면 rank/views 모두 null(부재)이다 — 실측 0과 혼용하지 않는다.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.api.deps import get_store
from app.charts import MUSIC_CHARTS

router = APIRouter(prefix="/api")

VALID_CHART_IDS = {suffix for suffix, _pid, _title in MUSIC_CHARTS}
# 차트 스냅샷은 Top20 카드 전체(JSON)라 버킷당 ~14KB — DynamoDB Query 1MB
# 한도를 넘지 않도록 72시간으로 캡한다(기존 96 캡과 같은 근거, 항목이 커서 더 낮음)
MAX_HOURS = 72


@router.get("/charts/{chart_id}/videos/{video_id}/history")
def chart_video_history(chart_id: str, video_id: str,
                        hours: int = Query(default=48, ge=2, le=MAX_HOURS),
                        store=Depends(get_store)):
    if chart_id not in VALID_CHART_IDS:
        return JSONResponse({"error": "지원하지 않는 차트입니다"}, status_code=400)
    now = datetime.now(timezone.utc)
    snaps = store.snapshots_range(f"chart-{chart_id}",
                                  now - timedelta(hours=hours), now)
    points = []
    for s in snaps:
        hit = next((c for c in s["items"] if c.get("videoId") == video_id), None)
        points.append({
            "ts": s["bucket"],
            "rank": hit.get("rank") if hit else None,
            "views": hit.get("views") if hit else None,
        })
    return {"chartId": chart_id, "videoId": video_id, "points": points}
