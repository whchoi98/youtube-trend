from datetime import datetime, timezone
from app.collector.run import collect_all
from app.collector.youtube import UpstreamError
from app.store.table import TrendStore

NOW = datetime(2026, 8, 4, 9, 0, tzinfo=timezone.utc)


def card(video_id, rank, cat="10"):
    return {"rank": rank, "videoId": video_id, "title": "t", "channel": "c",
            "views": 10, "likes": 1, "category": "음악", "categoryId": cat,
            "thumbnail": "", "publishedAt": ""}


class FakeYT:
    def __init__(self, fail_categories=()):
        self.fail = set(fail_categories)

    def most_popular(self, category_id, max_results):
        if category_id in self.fail:
            raise UpstreamError(404)
        if category_id is None:
            return [card("a", 1, "10"), card("b", 2, "20")]
        return [card(f"{category_id}-1", 1, category_id)]


def test_collect_writes_all_and_categories(table):
    store = TrendStore(table)
    result = collect_all(store, FakeYT(), NOW)
    assert result["written"] >= 9  # 전체 1 + 카테고리 8
    assert store.latest_snapshot("all") is not None
    assert store.latest_snapshot("10") is not None


def test_failed_category_falls_back_to_derived_from_all(table):
    store = TrendStore(table)
    result = collect_all(store, FakeYT(fail_categories={"20"}), NOW)
    snap = store.latest_snapshot("20")
    assert snap["degraded"] is True           # 전체 목록 파생 폴백
    assert snap["items"][0]["videoId"] == "b"
    assert "20" in result["degraded"]


def test_video_points_written_for_all_scope(table):
    store = TrendStore(table)
    collect_all(store, FakeYT(), NOW)
    pts = store.video_history("a", NOW.replace(hour=0), NOW)
    assert len(pts) == 1 and pts[0]["rank"] == 1
