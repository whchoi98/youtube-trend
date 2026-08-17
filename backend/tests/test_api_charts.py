"""YouTube Music 차트 시계열(GET /api/charts/.../history) 계약 테스트."""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.store.table import TrendStore

NOW = datetime.now(timezone.utc)


def card(video_id, rank, views=100):
    return {"rank": rank, "videoId": video_id, "title": "t", "channel": "c",
            "views": views, "likes": 1, "category": "음악", "categoryId": "10",
            "thumbnail": "", "publishedAt": ""}


def make_client(table):
    settings = Settings(table_name="t", yt_api_key="x", collect_enabled=False)
    app = create_app(settings, store=TrendStore(table), yt=object())
    return TestClient(app), TrendStore(table)


def test_chart_history_rejects_unknown_chart(table):
    client, _ = make_client(table)
    res = client.get("/api/charts/nope/videos/v1/history")
    assert res.status_code == 400
    assert res.json() == {"error": "지원하지 않는 차트입니다"}


def test_chart_history_hours_validation_follows_contract(table):
    client, _ = make_client(table)
    res = client.get("/api/charts/songs/videos/v1/history?hours=721")
    assert res.status_code == 400
    assert res.json() == {"error": "잘못된 요청입니다"}


def test_chart_history_reads_chart_points_over_a_month(table):
    client, store = make_client(table)
    for off, rank, views in ((600, 3, 100), (1, 2, 150), (0, 1, 200)):
        ts = NOW - timedelta(hours=off)
        store.put_chart_points("songs", ts.strftime("%Y-%m-%dT%H"), ts,
                               [{"videoId": "song-a", "rank": rank, "views": views}])

    body = client.get("/api/charts/songs/videos/song-a/history?hours=720").json()
    assert body["chartId"] == "songs"
    assert [p["rank"] for p in body["points"]] == [3, 2, 1]
    # 기본 168시간 창은 600시간 전 포인트를 포함하지 않는다
    body = client.get("/api/charts/songs/videos/song-a/history").json()
    assert [p["rank"] for p in body["points"]] == [2, 1]


def test_chart_history_empty_without_snapshots(table):
    client, _ = make_client(table)
    body = client.get("/api/charts/songs/videos/v1/history").json()
    assert body["points"] == []
