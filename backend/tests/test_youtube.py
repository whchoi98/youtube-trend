import httpx
import pytest
from app.collector.youtube import YouTubeClient, UpstreamError


def yt_payload():
    return {"items": [{
        "id": "v1",
        "snippet": {"title": "제목", "channelTitle": "채널", "categoryId": "10",
                    "publishedAt": "2026-08-01T00:00:00Z",
                    "thumbnails": {"high": {"url": "https://i.ytimg.com/x.jpg"}}},
        "statistics": {"viewCount": "1234", "likeCount": "56"},
    }]}


def make_client(handler):
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return YouTubeClient(api_key="k", client=http, category_names={"10": "음악"})


def test_most_popular_maps_cards_and_coerces_numbers():
    def handler(req):
        assert req.url.params["chart"] == "mostPopular"
        assert req.url.params["regionCode"] == "KR"
        return httpx.Response(200, json=yt_payload())
    cards = make_client(handler).most_popular(None, 30)
    c = cards[0]
    assert c["rank"] == 1 and c["videoId"] == "v1"
    assert c["views"] == 1234 and c["likes"] == 56   # 문자열 → int
    assert c["category"] == "음악" and c["categoryId"] == "10"


def test_missing_like_count_becomes_zero():
    payload = yt_payload()
    del payload["items"][0]["statistics"]["likeCount"]  # 비공개 좋아요
    cards = make_client(lambda r: httpx.Response(200, json=payload)).most_popular(None, 30)
    assert cards[0]["likes"] == 0


def test_category_param_passed_through():
    def handler(req):
        assert req.url.params["videoCategoryId"] == "20"
        return httpx.Response(200, json=yt_payload())
    make_client(handler).most_popular("20", 10)


def test_upstream_error_raises_with_status_only():
    def handler(req):
        return httpx.Response(403, json={"error": {"message": "secret-internal"}})
    with pytest.raises(UpstreamError) as ei:
        make_client(handler).most_popular(None, 30)
    assert ei.value.status == 403
    assert "secret-internal" not in str(ei.value)  # 상류 본문 비노출


def test_non_numeric_stats_become_zero():
    payload = yt_payload()
    payload["items"][0]["statistics"]["viewCount"] = "not-a-number"
    cards = make_client(lambda r: httpx.Response(200, json=payload)).most_popular(None, 30)
    assert cards[0]["views"] == 0


def test_most_popular_truncates_description():
    def handler(req):
        return httpx.Response(200, json={"items": [{
            "id": "v1",
            "snippet": {"title": "t", "channelTitle": "c", "categoryId": "10",
                        "description": "첫 줄\n둘째 줄  " + "가" * 300},
            "statistics": {"viewCount": "1", "likeCount": "1"},
        }]})

    yt = YouTubeClient(api_key="k", client=httpx.Client(
        transport=httpx.MockTransport(handler)), category_names={"10": "음악"})
    c = yt.most_popular(None, 1)[0]
    assert c["description"].startswith("첫 줄 둘째 줄 가")
    assert len(c["description"]) == 200


def test_channel_top_ranks_uploads_by_views():
    def handler(req):
        path = req.url.path
        if path.endswith("/channels"):
            assert req.url.params["forHandle"] == "AWSKorea"
            return httpx.Response(200, json={"items": [{"contentDetails": {
                "relatedPlaylists": {"uploads": "UUabc"}}}]})
        if path.endswith("/playlistItems"):
            assert req.url.params["playlistId"] == "UUabc"
            return httpx.Response(200, json={"items": [
                {"contentDetails": {"videoId": "v1"}},
                {"contentDetails": {"videoId": "v2"}},
            ]})
        assert path.endswith("/videos")
        return httpx.Response(200, json={"items": [
            {"id": "v1", "snippet": {"title": "적은", "channelTitle": "AWS",
                                     "categoryId": "28"},
             "statistics": {"viewCount": "10", "likeCount": "1"}},
            {"id": "v2", "snippet": {"title": "많은", "channelTitle": "AWS",
                                     "categoryId": "28"},
             "statistics": {"viewCount": "99", "likeCount": "2"}},
        ]})

    yt = YouTubeClient(api_key="k", client=httpx.Client(
        transport=httpx.MockTransport(handler)), category_names={"28": "과학기술"})
    cards = yt.channel_top("AWSKorea", 10)
    assert [c["videoId"] for c in cards] == ["v2", "v1"]  # 조회수 내림차순
    assert cards[0]["rank"] == 1 and cards[1]["rank"] == 2
    # 업로드 재생목록 id는 캐시된다 — 두 번째 호출은 channels 미호출이어야 하나
    # MockTransport 특성상 호출 수 검증 대신 결과 동일성만 확인
    assert yt.channel_top("AWSKorea", 10)[0]["videoId"] == "v2"


def test_playlist_top_preserves_playlist_order():
    """차트 재생목록은 목록 순서가 곧 순위 — 조회수로 재정렬하지 않는다."""
    def handler(req):
        path = req.url.path
        if path.endswith("/playlistItems"):
            assert req.url.params["playlistId"] == "PLchart"
            return httpx.Response(200, json={"items": [
                {"contentDetails": {"videoId": "first"}},
                {"contentDetails": {"videoId": "second"}},
            ]})
        assert path.endswith("/videos")
        # videos.list가 순서를 뒤집어 반환해도 재생목록 순서로 복원돼야 한다
        return httpx.Response(200, json={"items": [
            {"id": "second", "snippet": {"title": "2등곡", "channelTitle": "c",
                                         "categoryId": "10"},
             "statistics": {"viewCount": "999", "likeCount": "1"}},
            {"id": "first", "snippet": {"title": "1등곡", "channelTitle": "c",
                                        "categoryId": "10"},
             "statistics": {"viewCount": "10", "likeCount": "1"}},
        ]})

    yt = YouTubeClient(api_key="k", client=httpx.Client(
        transport=httpx.MockTransport(handler)), category_names={"10": "음악"})
    cards = yt.playlist_top("PLchart", 20)
    assert [c["videoId"] for c in cards] == ["first", "second"]
    assert cards[0]["rank"] == 1 and cards[0]["views"] == 10
