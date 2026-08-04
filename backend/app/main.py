import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse, JSONResponse

from app.config import Settings

logging.basicConfig(level=logging.INFO, format='{"lvl":"%(levelname)s","msg":"%(message)s","logger":"%(name)s"}')
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

            sched = BackgroundScheduler(timezone="UTC")
            sched.add_job(
                lambda: collect_all(app.state.store, app.state.yt,
                                    datetime.now(timezone.utc)),
                trigger="cron", minute=0, id="hourly-collect",
                misfire_grace_time=300, coalesce=True,
            )
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

    from app.api import trending as trending_api, videos as videos_api, trends as trends_api, brief as brief_api
    app.include_router(trending_api.router)
    app.include_router(videos_api.router)
    app.include_router(trends_api.router)
    app.include_router(brief_api.router)

    import os
    static_dir = os.environ.get("STATIC_DIR", "/srv/static")
    if os.path.isdir(static_dir):
        from fastapi.staticfiles import StaticFiles
        from starlette.responses import FileResponse

        app.mount("/assets", StaticFiles(directory=f"{static_dir}/assets"), name="assets")

        @app.get("/{path:path}")
        def spa(path: str):
            # /api·/healthz는 위에서 먼저 매칭된다. 나머지는 SPA 폴백.
            full = os.path.join(static_dir, path)
            if path and os.path.isfile(full):
                return FileResponse(full)
            return FileResponse(os.path.join(static_dir, "index.html"))

    return app


def dev_app():
    """로컬 개발용: uvicorn app.main:dev_app --factory --port 8000"""
    return create_app(Settings.from_env())
