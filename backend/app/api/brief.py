import itertools
import json
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

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

# 스트리밍 모드 → 캐시 kind 매핑 (POST 계약의 mode/kind와 동일 계열)
STREAM_MODES = {"now": "brief-now", "daily": "brief-daily", "trend": "trend"}
_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
_STREAM_END = object()  # 스트림 소진 표지 — StopIteration을 await 경계 밖으로 안 새게


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


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
        # exclude_bucket: 수집이 오래 멈춰 최신 스냅샷이 24시간 이상 묵으면
        # 자기 자신과 비교해 "변화 없음" 브리핑이 조작된다 — 자기 버킷 제외
        baseline = store.baseline_snapshot(req.scope, now, keys.DAILY_OFFSETS,
                                           exclude_bucket=snap["bucket"])
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


@router.get("/brief/stream")
def brief_stream(scope: str = "all", mode: str = "now",
                 store=Depends(get_store), llm=Depends(get_llm)):
    """SSE 스트리밍 브리핑 — Bedrock ConverseStream의 토큰을 그대로 흘려보낸다.

    이벤트: step(파이프라인 단계 표기) → delta(텍스트 조각)* → done.
    스트림 시작 전 오류는 기존 HTTP 상태 계약(400/409/502/503)을 그대로 따르고,
    시작 후 상류 오류만 in-band `error` 이벤트로 전달한다.
    """
    if scope not in VALID_SCOPES or mode not in STREAM_MODES:
        return JSONResponse({"error": "잘못된 요청입니다"}, status_code=400)
    kind = STREAM_MODES[mode]
    now = datetime.now(timezone.utc)
    steps: list[dict] = []

    def timed(label, fn):
        t0 = time.perf_counter()
        out = fn()
        steps.append({"label": label,
                      "ms": round((time.perf_counter() - t0) * 1000)})
        return out

    bucket = keys.hour_bucket(now)
    baseline = None
    build = None
    if mode == "trend":
        # 캐시 확인이 먼저다 — 48시간 범위 조회·집계가 가장 비싼 작업이라
        # 히트 시 건너뛴다 (POST /api/trends/report의 _cached_or_generate와 동일 순서)
        hit = timed("리포트 캐시 확인 (UTC 시간 버킷)",
                    lambda: store.get_report(kind, scope, bucket))
        if hit is None:
            snaps = timed("DynamoDB 스냅샷 범위 조회 (48시간)",
                          lambda: store.snapshots_range(
                              scope, now - timedelta(hours=48), now))
            if not snaps:
                return JSONResponse({"error": ERR["no_snapshot"]}, status_code=409)
            series = timed("카테고리 점유율·진입/이탈 집계",
                           lambda: category_series(snaps))
            movers = sorted(snaps[-1]["items"], key=lambda c: c.get("views", 0),
                            reverse=True)
            build = lambda: prompts.build_trend_report(series, movers)  # noqa: E731
    else:
        snap = timed("DynamoDB 최신 스냅샷 조회",
                     lambda: store.latest_snapshot(scope))
        if snap is None:
            return JSONResponse({"error": ERR["no_snapshot"]}, status_code=409)
        if mode == "daily":
            baseline = timed("기준선 스냅샷 조회 (24~26시간 전)",
                             lambda: store.baseline_snapshot(
                                 scope, now, keys.DAILY_OFFSETS,
                                 exclude_bucket=snap["bucket"]))
            if baseline is None:
                return JSONResponse({"error": ERR["no_baseline"],
                                     "baseline": None}, status_code=409)
            build = lambda: prompts.build_daily(snap["items"], baseline)  # noqa: E731
        else:
            build = lambda: prompts.build_brief(snap["items"])  # noqa: E731
        hit = timed("리포트 캐시 확인 (UTC 시간 버킷)",
                    lambda: store.get_report(kind, scope, bucket))

    done_data: dict = {"cached": hit is not None}
    if baseline:
        done_data["baseline"] = baseline["capturedAt"]

    if hit:
        steps.append({"label": "캐시 히트 — 재생성 생략", "ms": None})

        def cached_gen():
            for s in steps:
                yield _sse("step", s)
            yield _sse("delta", {"text": hit["text"]})
            yield _sse("done", done_data)

        return StreamingResponse(cached_gen(), media_type="text/event-stream",
                                 headers=_SSE_HEADERS)

    builder_name = {"brief-now": "build_brief", "brief-daily": "build_daily",
                    "trend": "build_trend_report"}[kind]
    system, user = timed(f"프롬프트 구성 ({builder_name})", build)

    stream = llm.converse_stream(system, user, MAX_TOKENS[kind])
    try:
        # 첫 이벤트를 눈앞에서 당긴다 — 요청/상태 오류가 스트림 시작 전에
        # 드러나므로 503/502를 정상 HTTP 상태로 돌려줄 수 있다.
        first = next(stream, None)
    except LlmDisabled:
        return JSONResponse({"error": ERR["disabled"], "enabled": False},
                            status_code=503)
    except LlmUpstreamError as e:
        return JSONResponse({"error": ERR["upstream"], "code": e.status},
                            status_code=502)
    steps.append({"label": f"Bedrock ConverseStream 호출 — {MODEL_ID}",
                  "ms": None})

    async def gen():
        chunks: list[str] = []
        stop = ""
        it = itertools.chain([first] if first is not None else [], stream)
        try:
            for s in steps:
                yield _sse("step", s)
            while True:
                # 토큰 당김은 스레드풀에서 — 동기 httpx가 이벤트 루프를 막지 않게.
                # 클라이언트 disconnect 시 이 await/yield 지점에서 취소되고
                # finally가 Bedrock 스트림을 닫아 토큰 낭비를 멈춘다.
                ev = await run_in_threadpool(next, it, _STREAM_END)
                if ev is _STREAM_END:
                    break
                tag, val = ev
                if tag == "delta":
                    chunks.append(val)
                    yield _sse("delta", {"text": val})
                elif tag == "stop":
                    stop = val
        except LlmUpstreamError as e:
            # 스트림 도중 상류 실패 — HTTP 상태는 이미 200이므로 in-band 전달
            yield _sse("error", {"error": ERR["upstream"], "code": e.status})
            return
        finally:
            stream.close()
        text = "".join(chunks)
        if stop == "max_tokens":
            text += prompts.TRUNCATION_NOTICE
            yield _sse("delta", {"text": prompts.TRUNCATION_NOTICE})
        # stop 미수신(절단) 텍스트는 캐시하지 않는다 — 시간 버킷 전체 오염 방지
        if text and stop:
            await run_in_threadpool(
                store.put_report, kind, scope, bucket, text, MODEL_ID, now)
            yield _sse("step", {"label": "응답 캐시 저장 (TTL 2일)", "ms": None})
        yield _sse("done", done_data)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers=_SSE_HEADERS)


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
