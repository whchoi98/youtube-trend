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
