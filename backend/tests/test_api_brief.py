from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from app.config import Settings
from app.llm.bedrock import LlmDisabled, LlmUpstreamError
from app.main import create_app
from app.store.table import TrendStore

NOW = datetime.now(timezone.utc)


def card(video_id="a", rank=1):
    return {"rank": rank, "videoId": video_id, "title": "t", "channel": "c",
            "views": 10, "likes": 1, "category": "음악", "categoryId": "10",
            "thumbnail": "", "publishedAt": ""}


class FakeLlm:
    def __init__(self, disabled=False, fail=False, stop="end_turn"):
        self.disabled, self.fail, self.stop = disabled, fail, stop
        self.calls = 0

    def converse(self, system, user, max_tokens):
        if self.disabled:
            raise LlmDisabled()
        if self.fail:
            raise LlmUpstreamError(500)
        self.calls += 1
        return "브리핑 텍스트", self.stop


def make_client(table, llm):
    settings = Settings(table_name="t", yt_api_key="x", collect_enabled=False)
    store = TrendStore(table)
    app = create_app(settings, store=store, yt=object(), llm=llm)
    return TestClient(app), store


def test_brief_503_when_llm_disabled(table):
    client, store = make_client(table, FakeLlm(disabled=True))
    store.put_snapshot("all", NOW, [card()])
    res = client.post("/api/brief", json={"scope": "all", "mode": "now"})
    assert res.status_code == 503 and res.json()["enabled"] is False


def test_brief_now_generates_then_caches(table):
    llm = FakeLlm()
    client, store = make_client(table, llm)
    store.put_snapshot("all", NOW, [card()])
    r1 = client.post("/api/brief", json={"scope": "all", "mode": "now"})
    r2 = client.post("/api/brief", json={"scope": "all", "mode": "now"})
    assert r1.json()["cached"] is False and r2.json()["cached"] is True
    assert llm.calls == 1  # 캐시로 토큰 소비 시간당 1회 상한


def test_brief_daily_409_without_baseline(table):
    client, store = make_client(table, FakeLlm())
    store.put_snapshot("all", NOW, [card()])
    res = client.post("/api/brief", json={"scope": "all", "mode": "daily"})
    assert res.status_code == 409 and res.json()["baseline"] is None


def test_brief_daily_uses_24h_snapshot(table):
    client, store = make_client(table, FakeLlm())
    store.put_snapshot("all", NOW - timedelta(hours=24), [card("old")])
    store.put_snapshot("all", NOW, [card("new")])
    res = client.post("/api/brief", json={"scope": "all", "mode": "daily"})
    assert res.status_code == 200 and res.json()["baseline"] is not None


def test_truncated_response_appends_notice_still_200(table):
    client, store = make_client(table, FakeLlm(stop="max_tokens"))
    store.put_snapshot("all", NOW, [card()])
    body = client.post("/api/brief", json={"scope": "all", "mode": "now"}).json()
    assert "잘렸습니다" in body["brief"]


def test_upstream_failure_returns_502_with_code_only(table):
    client, store = make_client(table, FakeLlm(fail=True))
    store.put_snapshot("all", NOW, [card()])
    res = client.post("/api/brief", json={"scope": "all", "mode": "now"})
    assert res.status_code == 502 and res.json()["code"] == 500


def test_trend_report_endpoint(table):
    client, store = make_client(table, FakeLlm())
    store.put_snapshot("all", NOW - timedelta(hours=1), [card("a")])
    store.put_snapshot("all", NOW, [card("b")])
    res = client.post("/api/trends/report", json={"scope": "all"})
    assert res.status_code == 200 and res.json()["report"] == "브리핑 텍스트"
