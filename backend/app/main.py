import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse, JSONResponse

from app.config import Settings

logging.basicConfig(level=logging.INFO, format='{"lvl":"%(levelname)s","msg":"%(message)s","logger":"%(name)s"}')
# httpx는 INFO에서 요청 URL 전체를 남긴다 — YouTube 키가 쿼리스트링에 있어
# 로그로 새므로 WARNING으로 올린다(시크릿은 어떤 로그에도 남기지 않는다는 규칙)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)


def _build_store(settings):
    """Build real TrendStore for production path."""
    import boto3
    from app.store.table import TrendStore
    table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(settings.table_name)
    return TrendStore(table)


def _build_yt(settings):
    """Build real YouTubeClient for production path."""
    from app.collector.youtube import YouTubeClient
    yt = YouTubeClient(settings.yt_api_key)
    yt.load_category_names()
    return yt


def _build_llm(settings):
    """Build real BedrockClient for production path."""
    from app.llm.bedrock import BedrockClient
    return BedrockClient(settings.bedrock_token)


def create_app(settings: Settings, store=None, yt=None, llm=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Guard each dependency independently — injected values must not be overwritten.
        if app.state.store is None:
            app.state.store = _build_store(settings)

        if app.state.yt is None:
            app.state.yt = _build_yt(settings)

        if app.state.llm is None:
            app.state.llm = _build_llm(settings)

        app.state.scheduler = None
        if settings.collect_enabled:
            from apscheduler.schedulers.background import BackgroundScheduler
            from app.collector.run import collect_all
            from app.tagging import ensure_tags

            def _tag_quietly():
                # 태그는 부가 정보 — 실패해도 수집·서빙에 영향 없이 로그만 남긴다
                try:
                    ensure_tags(app.state.store, app.state.llm,
                                datetime.now(timezone.utc))
                except Exception:
                    log.exception("tagging job failed")

            def _collect_and_tag():
                collect_all(app.state.store, app.state.yt,
                            datetime.now(timezone.utc))
                _tag_quietly()

            sched = BackgroundScheduler(timezone="UTC")
            sched.add_job(
                _collect_and_tag,
                trigger="cron", minute=0, id="hourly-collect",
                misfire_grace_time=300, coalesce=True,
            )
            # 기동 직후 1회: 재배포 시 최신 스냅샷이 미태깅인 최대 59분 공백을 메운다
            sched.add_job(_tag_quietly, id="startup-tags")
            sched.start()
            app.state.scheduler = sched
            log.info("scheduler started: hourly-collect")
        yield
        if app.state.scheduler is not None:
            # SIGTERM → uvicorn graceful shutdown → lifespan 종료.
            # wait=False: 수집 중이어도 drain을 막지 않는다(다음 시각에 재수집됨).
            app.state.scheduler.shutdown(wait=False)
            log.info("scheduler stopped")

    app = FastAPI(title="youtube-trends", lifespan=lifespan)
    app.state.settings = settings
    app.state.store = store
    app.state.yt = yt
    app.state.llm = llm

    @app.get("/healthz", response_class=PlainTextResponse)
    def healthz() -> str:
        # ALB 헬스체크: 프로세스 생존만 확인한다. DynamoDB 장애가 태스크 교체 폭풍을
        # 일으키지 않도록 어떤 외부 의존에도 접근하지 않는다.
        return "ok"

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request, exc):
        # 프론트 계약: 모든 오류는 {"error": 한국어} + 4xx — FastAPI 기본 422 detail 배열을 노출하지 않는다
        return JSONResponse({"error": "잘못된 요청입니다"}, status_code=400)

    from app.api import (trending as trending_api, videos as videos_api,
                         trends as trends_api, brief as brief_api,
                         home as home_api, charts as charts_api)
    app.include_router(trending_api.router)
    app.include_router(videos_api.router)
    app.include_router(trends_api.router)
    app.include_router(brief_api.router)
    app.include_router(home_api.router)
    app.include_router(charts_api.router)

    import os
    static_dir = os.environ.get("STATIC_DIR", "/srv/static")
    if os.path.isdir(static_dir):
        from fastapi.staticfiles import StaticFiles
        from starlette.responses import FileResponse

        app.mount("/assets", StaticFiles(directory=f"{static_dir}/assets"), name="assets")

        @app.get("/{path:path}")
        def spa(path: str):
            # 등록된 /api·/healthz 라우트는 이 catch-all보다 먼저 매칭된다.
            # 미등록 /api/* 경로는 SPA 폴백 대상이 아니다 — 404 + 오류 계약 유지
            # (여기 오는 /api/* 는 전부 미등록 경로다).
            if path.startswith("api/"):
                return JSONResponse({"error": "찾을 수 없습니다"}, status_code=404)
            base = os.path.realpath(static_dir)
            full = os.path.realpath(os.path.join(base, path))
            # base 밖으로 탈출한 경로는 파일이 존재해도 서빙하지 않는다(SPA 폴백으로)
            if path and full.startswith(base + os.sep) and os.path.isfile(full):
                return FileResponse(full)
            # index.html은 캐시 재검증 강제 — CloudFront가 24h TTL로 붙잡으면
            # 재배포 후 낡은 index가 사라진 해시 자산을 참조해 사이트가 깨진다
            return FileResponse(os.path.join(base, "index.html"),
                                headers={"Cache-Control": "no-cache"})

    return app


def dev_app():
    """로컬 개발용: uvicorn app.main:dev_app --factory --port 8000"""
    return create_app(Settings.from_env())
