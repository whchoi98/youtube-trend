from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.aggregate import category_series
from app.api.deps import get_llm, get_store
from app.api.trending import VALID_SCOPES
from app.llm import prompts
from app.llm.bedrock import MODEL_ID, LlmDisabled, LlmUpstreamError
from app.store import keys

router = APIRouter(prefix="/api")

MAX_TOKENS = {"brief-now": 1200, "brief-daily": 600, "trend": 1500}
ERR = {"upstream": "분석 생성에 실패했습니다", "disabled": "브리핑 기능이 설정되지 않았습니다",
       "no_baseline": "비교할 어제 데이터가 아직 없습니다", "no_snapshot": "표시할 목록이 아직 없습니다"}


class BriefReq(BaseModel):
    scope: str = "all"
    mode: str = "now"


class ReportReq(BaseModel):
    scope: str = "all"


def _cached_or_generate(store, llm, kind, scope, now, build):
    """캐시 우선 생성. build() -> (system, user) 또는 오류 응답(JSONResponse)."""
    bucket = keys.hour_bucket(now)
    hit = store.get_report(kind, scope, bucket)
    if hit:
        return {"text": hit["text"], "cached": True}
    built = build()
    if isinstance(built, JSONResponse):
        return built
    system, user = built
    try:
        text, stop = llm.converse(system, user, MAX_TOKENS[kind])
    except LlmDisabled:
        return JSONResponse({"error": ERR["disabled"], "enabled": False}, status_code=503)
    except LlmUpstreamError as e:
        return JSONResponse({"error": ERR["upstream"], "code": e.status}, status_code=502)
    if stop == "max_tokens":
        text += prompts.TRUNCATION_NOTICE
    store.put_report(kind, scope, bucket, text, MODEL_ID, now)
    return {"text": text, "cached": False}


@router.post("/brief")
def brief(req: BriefReq, store=Depends(get_store), llm=Depends(get_llm)):
    if req.scope not in VALID_SCOPES or req.mode not in ("now", "daily"):
        return JSONResponse({"error": "잘못된 요청입니다"}, status_code=400)
    now = datetime.now(timezone.utc)
    snap = store.latest_snapshot(req.scope)
    if snap is None:
        return JSONResponse({"error": ERR["no_snapshot"]}, status_code=409)

    baseline = None
    if req.mode == "daily":
        baseline = store.baseline_snapshot(req.scope, now, keys.DAILY_OFFSETS)
        if baseline is None:
            return JSONResponse({"error": ERR["no_baseline"], "baseline": None},
                                status_code=409)

    kind = f"brief-{req.mode}"
    build = (lambda: prompts.build_daily(snap["items"], baseline)) if req.mode == "daily" \
        else (lambda: prompts.build_brief(snap["items"]))
    out = _cached_or_generate(store, llm, kind, req.scope, now, build)
    if isinstance(out, JSONResponse):
        return out
    body = {"brief": out["text"], "cached": out["cached"]}
    if baseline:
        body["baseline"] = baseline["capturedAt"]
    return body


@router.post("/trends/report")
def trend_report(req: ReportReq, store=Depends(get_store), llm=Depends(get_llm)):
    if req.scope not in VALID_SCOPES:
        return JSONResponse({"error": "잘못된 요청입니다"}, status_code=400)
    now = datetime.now(timezone.utc)

    def build():
        snaps = store.snapshots_range(req.scope, now - timedelta(hours=48), now)
        if not snaps:
            return JSONResponse({"error": ERR["no_snapshot"]}, status_code=409)
        series = category_series(snaps)
        movers = sorted(snaps[-1]["items"], key=lambda c: c.get("views", 0),
                        reverse=True)
        return prompts.build_trend_report(series, movers)

    out = _cached_or_generate(store, llm, "trend", req.scope, now, build)
    if isinstance(out, JSONResponse):
        return out
    return {"report": out["text"], "cached": out["cached"]}
