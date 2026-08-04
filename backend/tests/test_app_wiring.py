from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app


def test_scheduler_not_started_when_collect_disabled():
    settings = Settings(table_name="t", yt_api_key="x", collect_enabled=False)
    app = create_app(settings, store=object(), yt=object())
    with TestClient(app):  # lifespan 실행
        assert app.state.scheduler is None


def test_scheduler_started_when_enabled():
    settings = Settings(table_name="t", yt_api_key="x", collect_enabled=True)
    app = create_app(settings, store=object(), yt=object())
    with TestClient(app):
        assert app.state.scheduler is not None
        jobs = app.state.scheduler.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == "hourly-collect"
    assert app.state.scheduler.running is False  # 종료 시 정리
