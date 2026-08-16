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
    res = client.get("/api/charts/songs/videos/v1/history?hours=96")
    assert res.status_code == 400
    assert res.json() == {"error": "잘못된 요청입니다"}


def test_chart_history_tracks_rank_and_absence_as_null(table):
    client, store = make_client(table)
    store.put_snapshot("chart-songs", NOW - timedelta(hours=2),
                       [card("song-a", 3, views=100)])
    store.put_snapshot("chart-songs", NOW - timedelta(hours=1),
                       [card("song-b", 1, views=999)])  # song-a 차트 아웃
    store.put_snapshot("chart-songs", NOW, [card("song-a", 1, views=200)])

    body = client.get("/api/charts/songs/videos/song-a/history?hours=4").json()
    assert body["chartId"] == "songs"
    ranks = [p["rank"] for p in body["points"]]
    views = [p["views"] for p in body["points"]]
    assert ranks == [3, None, 1]     # 부재 시각은 null — 실측값과 혼용 금지
    assert views == [100, None, 200]


def test_chart_history_empty_without_snapshots(table):
    client, _ = make_client(table)
    body = client.get("/api/charts/songs/videos/v1/history").json()
    assert body["points"] == []
