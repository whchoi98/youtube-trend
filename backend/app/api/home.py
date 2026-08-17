"""홈 조합 API. 기존 저장 데이터의 재조합 계층 — 새 수집·저장 없음.

GET /api/home  — 히어로·인사이트 칩·행(스트립) 구성을 한 번에 반환
POST /api/quiz — 취향 퀴즈 답변 → 유형명 + 맞춤 추천 카드(결정적, LLM 미호출)
"""
import re
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import home as home_logic
from app.api.deps import get_settings, get_store
from app.categories import CATEGORIES
from app.charts import MUSIC_CHARTS
from app.derive import with_derived
from app.regions import REGIONS
from app.spotlights import SPOTLIGHTS
from app.store import keys

router = APIRouter(prefix="/api")

ERR_NO_SNAPSHOT = "표시할 목록이 아직 없습니다"
HISTORY_WINDOW_HOURS = 72
# 홈은 요청당 DynamoDB 호출이 많다(ALL/카테고리 8종 스냅샷+기준선, 태그, 히어로
# 시계열). 스냅샷은 시간 버킷 단위 불변이므로 조합 결과를 프로세스 내 단기
# 캐시로 재사용한다 — 프론트 60초 폴링과 정합하고 무인증 비용 증폭을 막는다.
CACHE_TTL_SECONDS = 30
# YouTube videoId 형태 검증 — 히어로 maxres URL은 저장값이 아니라 조립값이므로
# 예상 밖 문자열로 URL을 만들지 않는다(불일치 시 저장된 thumbnail만 사용).
# \Z 사용: $는 후행 개행을 통과시켜 URL에 개행이 삽입될 수 있다.
_VIDEO_ID_RE = re.compile(r"[A-Za-z0-9_-]{5,20}\Z")


class QuizReq(BaseModel):
    mood: str
    time: str
    style: str


def _derived_items(store, scope, now):
    """스냅샷 + 파생 병합. 스냅샷이 없으면 None.

    exclude_bucket=자기 버킷: 수집 공백 시 자기 자신과 비교해 파생 필드가
    가짜 0이 되는 것을 막는다(null vs 0 계약)."""
    snap = store.latest_snapshot(scope)
    if snap is None:
        return None
    baseline = store.baseline_snapshot(scope, now, keys.RECENT_OFFSETS,
                                       min_age_hours=keys.MIN_AGE_HOURS,
                                       exclude_bucket=snap["bucket"])
    return snap, with_derived(snap["items"], baseline, now)


@router.get("/home")
def home(request: Request, store=Depends(get_store),
         settings=Depends(get_settings)):
    cached = getattr(request.app.state, "home_cache", None)
    if cached is not None and cached[0] > time.monotonic():
        return cached[1]
    now = datetime.now(timezone.utc)
    got = _derived_items(store, "all", now)
    if got is None:
        return JSONResponse({"error": ERR_NO_SNAPSHOT}, status_code=409)
    snap, items = got

    tags = store.get_tags(snap["bucket"])
    items = home_logic.merge_tags(items, tags)

    cat_items = {}
    for cid, _name in CATEGORIES:
        cgot = _derived_items(store, cid, now)
        if cgot is None:
            continue
        _csnap, cards = cgot
        cat_items[cid] = home_logic.merge_tags(cards, tags)

    region_items = {}
    for code, _name in REGIONS:
        rgot = _derived_items(store, f"rgn-{code}", now)
        if rgot is not None:
            region_items[code] = home_logic.merge_tags(rgot[1], tags)

    spotlight_items = {}
    for suffix, _handle, _title in SPOTLIGHTS:
        sgot = _derived_items(store, f"spot-{suffix}", now)
        if sgot is not None:
            spotlight_items[suffix] = home_logic.merge_tags(sgot[1], tags)

    chart_items = {}
    for suffix, _pid, _title in MUSIC_CHARTS:
        cgot = _derived_items(store, f"chart-{suffix}", now)
        if cgot is not None:
            chart_items[suffix] = home_logic.merge_tags(cgot[1], tags)

    hero = None
    if items:
        hero = dict(min(items, key=lambda c: c.get("rank") or 999))
        history = store.video_history(
            hero.get("videoId", ""),
            now - timedelta(hours=HISTORY_WINDOW_HOURS), now)
        hero["tenureHours"] = home_logic.tenure_hours(history)
        vid = hero.get("videoId", "")
        hero["heroThumbnail"] = (
            f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg"
            if _VIDEO_ID_RE.match(vid) else hero.get("thumbnail", ""))

    chan_snap = store.latest_snapshot("chan-top")

    payload = {
        "capturedAt": snap["capturedAt"],
        "channels": chan_snap["items"] if chan_snap else None,
        "tagged": tags is not None,
        "llmEnabled": bool(settings.bedrock_token),
        "insights": home_logic.build_insights(items),
        "hero": hero,
        "rows": home_logic.build_rows(items, cat_items, region_items,
                                      spotlight_items, chart_items),
    }
    request.app.state.home_cache = (time.monotonic() + CACHE_TTL_SECONDS, payload)
    return payload


@router.post("/quiz")
def quiz(req: QuizReq, store=Depends(get_store)):
    if (req.mood not in home_logic.QUIZ_MOODS
            or req.time not in home_logic.QUIZ_TIMES
            or req.style not in home_logic.QUIZ_STYLES):
        return JSONResponse({"error": "잘못된 요청입니다"}, status_code=400)
    now = datetime.now(timezone.utc)
    got = _derived_items(store, "all", now)
    if got is None:
        return JSONResponse({"error": ERR_NO_SNAPSHOT}, status_code=409)
    snap, items = got
    items = home_logic.merge_tags(items, store.get_tags(snap["bucket"]))
    return {
        "type": home_logic.quiz_type(req.mood, req.time, req.style),
        "items": home_logic.quiz_pick(items, req.mood, req.time, req.style),
    }
