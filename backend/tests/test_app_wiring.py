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


def test_partial_injection_preserves_injected_store():
    """Basic: both injected values are preserved (no independent-guard regression)."""
    settings = Settings(table_name="t", yt_api_key="x", collect_enabled=False)
    sentinel_store, sentinel_yt = object(), object()
    app = create_app(settings, store=sentinel_store, yt=sentinel_yt)
    with TestClient(app):
        assert app.state.store is sentinel_store
        assert app.state.yt is sentinel_yt


def test_partial_injection_builds_only_missing_dependency(monkeypatch):
    """Critical regression: partial injection must build only missing dependencies.

    Proves that each dependency guard is independent by injecting store (yt=None),
    mocking _build_yt to return a sentinel, and mocking _build_store to raise
    AssertionError if called. If guards are independent, only _build_yt runs.
    If buggy or-guard returns, _build_store would raise and test fails.
    """
    from app import main as main_mod

    settings = Settings(table_name="t", yt_api_key="x", collect_enabled=False)
    sentinel_store = object()
    sentinel_yt = object()

    # Mock builders to verify which ones are called
    monkeypatch.setattr(main_mod, "_build_yt", lambda s: sentinel_yt)
    monkeypatch.setattr(main_mod, "_build_store",
                        lambda s: (_ for _ in ()).throw(AssertionError("store must not be rebuilt")))

    # Inject only store; yt=None should trigger _build_yt only
    app = create_app(settings, store=sentinel_store, yt=None)
    with TestClient(app):
        assert app.state.store is sentinel_store  # Injected value preserved
        assert app.state.yt is sentinel_yt        # Missing dependency built
