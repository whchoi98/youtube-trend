import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from app.config import Settings

logging.basicConfig(level=logging.INFO, format='{"lvl":"%(levelname)s","msg":"%(message)s","logger":"%(name)s"}')
log = logging.getLogger(__name__)


def _build_real_dependencies(settings):
    """운영 경로에서만 import — 테스트는 주입으로 우회한다."""
    import boto3
    from app.collector.youtube import YouTubeClient
    from app.store.table import TrendStore

    table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(settings.table_name)
    yt = YouTubeClient(settings.yt_api_key)
    yt.load_category_names()
    return TrendStore(table), yt


def create_app(settings: Settings, store=None, yt=None, llm=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app.state.store is None or app.state.yt is None:
            app.state.store, app.state.yt = _build_real_dependencies(settings)
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
        yield
        if app.state.scheduler is not None:
            # SIGTERM → uvicorn graceful shutdown → lifespan 종료.
            # wait=False: 수집 중이어도 drain을 막지 않는다(다음 시각에 재수집됨).
            app.state.scheduler.shutdown(wait=False)

    app = FastAPI(title="youtube-trends", lifespan=lifespan)
    app.state.settings = settings
    app.state.store = store
    app.state.yt = yt
    app.state.llm = llm

    @app.get("/healthz", response_class=PlainTextResponse)
    def healthz() -> str:
        return "ok"

    return app
