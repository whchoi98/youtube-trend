from datetime import datetime, timedelta, timezone
from app.collector.run import collect_all
from app.collector.youtube import UpstreamError
from app.store.table import TrendStore

NOW = datetime(2026, 8, 4, 9, 0, tzinfo=timezone.utc)


def card(video_id, rank, cat="10", views=10):
    return {"rank": rank, "videoId": video_id, "title": "t", "channel": f"ch-{video_id}",
            "views": views, "likes": 1, "category": "음악", "categoryId": cat,
            "thumbnail": "", "publishedAt": "", "channelId": f"chan-{video_id}"}


class FakeYT:
    def __init__(self, fail_categories=(), fail_regions=(), fail_spotlight=False):
        self.fail = set(fail_categories)
        self.fail_regions = set(fail_regions)
        self.fail_spotlight = fail_spotlight

    def most_popular(self, category_id, max_results, region_code="KR"):
        if region_code != "KR":
            if region_code in self.fail_regions:
                raise UpstreamError(404)
            return [card(f"{region_code}-1", 1, "10")]
        if category_id in self.fail:
            raise UpstreamError(404)
        if category_id is None:
            return [card("a", 1, "10", views=50), card("b", 2, "20", views=10)]
        return [card(f"{category_id}-1", 1, category_id)]

    def channel_top(self, handle, max_results):
        if self.fail_spotlight:
            raise UpstreamError(403)
        return [card(f"top-{handle}", 1, "28")]

    def playlist_top(self, playlist_id, max_results):
        return [card(f"pl-{playlist_id[:8]}", 1, "10")]

    def channels_stats(self, channel_ids):
        return [{"channelId": cid, "name": f"이름-{cid}", "thumbnail": "",
                 "subscribers": 1000, "totalViews": 99999}
                for cid in channel_ids]


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


def test_collect_writes_regions_and_spotlight(table):
    store = TrendStore(table)
    result = collect_all(store, FakeYT(), NOW)
    assert result["written"] >= 14  # 전체 1 + 카테고리 8 + 국가 4 + 스포트라이트 1
    assert store.latest_snapshot("rgn-US")["items"][0]["videoId"] == "US-1"
    assert store.latest_snapshot("spot-aws")["items"][0]["videoId"] == "top-AWSKorea"
    assert store.latest_snapshot("spot-anthropic")["items"][0]["videoId"] == "top-anthropic-ai"
    assert store.latest_snapshot("spot-openai")["items"][0]["videoId"] == "top-OpenAI"


def test_failed_region_and_spotlight_do_not_block_others(table):
    store = TrendStore(table)
    result = collect_all(store, FakeYT(fail_regions={"JP"}, fail_spotlight=True), NOW)
    assert store.latest_snapshot("rgn-US") is not None
    assert store.latest_snapshot("rgn-JP") is None
    assert store.latest_snapshot("spot-aws") is None
    assert "rgn-JP" in result["skipped"] and "spot-aws" in result["skipped"]


def test_collect_writes_all_music_charts(table):
    store = TrendStore(table)
    collect_all(store, FakeYT(), NOW)
    # 5종 차트가 각자 scope로 저장된다
    for suffix in ("songs", "mv-daily", "mv-weekly", "shorts", "live"):
        assert store.latest_snapshot(f"chart-{suffix}") is not None


def test_collect_writes_channel_ranking(table):
    store = TrendStore(table)
    collect_all(store, FakeYT(), NOW)
    chans = store.latest_snapshot("chan-top")["items"]
    # 합산 조회수 기준 정렬: a(50) > b(10)
    assert chans[0]["channelId"] == "chan-a" and chans[0]["rank"] == 1
    assert chans[0]["subscribers"] == 1000
    assert chans[0]["topVideoId"] == "a"


def test_collect_writes_chart_points_for_month_series(table):
    store = TrendStore(table)
    collect_all(store, FakeYT(), NOW)
    pts = store.chart_video_history("songs", "pl-PL4fGSI1",
                                    NOW - timedelta(hours=2), NOW)
    assert len(pts) == 1 and pts[0]["rank"] == 1
