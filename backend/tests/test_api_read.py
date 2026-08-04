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


def test_trending_empty_when_no_snapshot(table):
    client, _ = make_client(table)
    res = client.get("/api/trending")
    assert res.status_code == 200 and res.json() == []


def test_trending_includes_derived_fields(table):
    client, store = make_client(table)
    store.put_snapshot("all", NOW - timedelta(hours=2), [card("a", 5, views=50)])
    store.put_snapshot("all", NOW, [card("a", 2, views=350)])
    body = client.get("/api/trending?scope=all").json()
    assert body[0]["delta"] == 3
    assert body[0]["viewsPerHour"] == 150


def test_trending_rejects_unknown_scope(table):
    client, _ = make_client(table)
    res = client.get("/api/trending?scope=999")
    assert res.status_code == 400
    assert res.json() == {"error": "지원하지 않는 분야입니다"}


def test_out_of_range_hours_returns_error_contract(table):
    client, _ = make_client(table)
    res = client.get("/api/trends/categories?hours=1")
    assert res.status_code == 400
    assert res.json() == {"error": "잘못된 요청입니다"}


def test_categories_lists_fixed_eight(table):
    client, _ = make_client(table)
    body = client.get("/api/categories").json()
    assert len(body) == 8 and body[0] == {"id": "10", "name": "음악"}


def test_video_history_endpoint(table):
    client, store = make_client(table)
    ts = NOW - timedelta(hours=1)
    store.put_video_points(ts.strftime("%Y-%m-%dT%H"), ts,
                           [{"videoId": "a", "rank": 3, "views": 42,
                             "likes": 0, "categoryId": "10", "title": "t"}])
    body = client.get("/api/videos/a/history?hours=24").json()
    assert body["videoId"] == "a" and body["points"][0]["views"] == 42


def test_trends_categories_endpoint(table):
    client, store = make_client(table)
    store.put_snapshot("all", NOW - timedelta(hours=1), [card("a", 1)])
    store.put_snapshot("all", NOW, [card("b", 1)])
    body = client.get("/api/trends/categories?hours=48").json()
    assert body["hours"] == 48 and len(body["series"]) == 2
    assert body["series"][1]["entered"] == 1
