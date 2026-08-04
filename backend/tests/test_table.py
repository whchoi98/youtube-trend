from datetime import datetime, timedelta, timezone
from app.store.table import TrendStore

NOW = datetime(2026, 8, 4, 9, 0, tzinfo=timezone.utc)
CARD = {"rank": 1, "videoId": "v1", "title": "t", "channel": "c", "views": 100,
        "likes": 5, "category": "음악", "categoryId": "10",
        "thumbnail": "https://i.ytimg.com/vi/v1/hqdefault.jpg", "publishedAt": "2026-08-01T00:00:00Z"}


def test_put_snapshot_is_conditional(table):
    s = TrendStore(table)
    assert s.put_snapshot("all", NOW, [CARD]) is True
    assert s.put_snapshot("all", NOW, [CARD]) is False  # 같은 시각 키 중복 쓰기 거부


def test_latest_snapshot_returns_most_recent(table):
    s = TrendStore(table)
    s.put_snapshot("all", NOW - timedelta(hours=2), [dict(CARD, views=50)])
    s.put_snapshot("all", NOW, [CARD])
    got = s.latest_snapshot("all")
    assert got["items"][0]["views"] == 100
    assert s.latest_snapshot("10") is None


def test_baseline_snapshot_falls_back_and_respects_min_age(table):
    s = TrendStore(table)
    # 1시간 전 없음, 3시간 전 존재 → 오프셋 [1,2,3,4]가 3에서 발견
    s.put_snapshot("all", NOW - timedelta(hours=3), [CARD])
    got = s.baseline_snapshot("all", NOW, [1, 2, 3, 4])
    assert got is not None
    # min_age: 방금(0.2h 전 capturedAt) 스냅샷은 건너뛴다
    s2 = TrendStore(table)
    s2.put_snapshot("10", NOW - timedelta(minutes=12), [CARD])
    assert s2.baseline_snapshot("10", NOW, [1], min_age_hours=0.75) is None


def test_video_history_orders_ascending(table):
    s = TrendStore(table)
    for h, views in [(3, 10), (2, 20), (1, 30)]:
        ts = NOW - timedelta(hours=h)
        s.put_video_points(ts.strftime("%Y-%m-%dT%H"), ts,
                           [{"videoId": "v1", "rank": 1, "views": views,
                             "likes": 0, "categoryId": "10", "title": "t"}])
    pts = s.video_history("v1", NOW - timedelta(hours=4), NOW)
    assert [p["views"] for p in pts] == [10, 20, 30]


def test_report_roundtrip(table):
    s = TrendStore(table)
    assert s.get_report("brief-now", "all", "2026-08-04T09") is None
    s.put_report("brief-now", "all", "2026-08-04T09", "요약", "sonnet-4.6", NOW)
    got = s.get_report("brief-now", "all", "2026-08-04T09")
    assert got["text"] == "요약"
