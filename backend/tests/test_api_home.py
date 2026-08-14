from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.store import keys
from app.store.table import TrendStore


def _now():
    """테스트별 기준 시각 — 모듈 로드 시각과 요청 시각의 간격이 벌어지면
    viewsPerHour 정확 일치 단언이 흔들리므로 테스트 안에서 새로 잡는다."""
    return datetime.now(timezone.utc)


def card(video_id, rank, views=100, category_id="10", category="음악"):
    return {"rank": rank, "videoId": video_id, "title": f"제목-{video_id}",
            "channel": "채널", "views": views, "likes": 1, "category": category,
            "categoryId": category_id, "thumbnail": "http://t/img.jpg",
            "publishedAt": ""}


def make_client(table, bedrock_token=""):
    settings = Settings(table_name="t", yt_api_key="x",
                        bedrock_token=bedrock_token, collect_enabled=False)
    app = create_app(settings, store=TrendStore(table), yt=object())
    return TestClient(app), TrendStore(table)


def test_home_409_without_snapshot(table):
    client, _ = make_client(table)
    res = client.get("/api/home")
    assert res.status_code == 409
    assert res.json() == {"error": "표시할 목록이 아직 없습니다"}


def test_home_hero_rows_and_insights(table):
    NOW = _now()
    client, store = make_client(table)
    store.put_snapshot("all", NOW - timedelta(hours=2),
                       [card("video-a", 1, views=100), card("video-b", 5)])
    store.put_snapshot("all", NOW,
                       [card("video-a", 1, views=700), card("video-b", 2),
                        card("video-c", 3, category_id="20", category="게임")])
    store.put_snapshot("10", NOW, [card("video-a", 1, views=700)])

    body = client.get("/api/home").json()

    assert body["tagged"] is False
    assert body["llmEnabled"] is False
    assert body["capturedAt"]

    hero = body["hero"]
    assert hero["videoId"] == "video-a"
    assert hero["heroThumbnail"] == "https://i.ytimg.com/vi/video-a/maxresdefault.jpg"
    assert hero["tenureHours"] >= 1

    rows = {r["kind"]: r for r in body["rows"]}
    assert rows["top10"]["items"][0]["videoId"] == "video-a"
    # 가속: video-a만 viewsPerHour 양수(600/2h=300)
    assert rows["accel"]["items"][0]["videoId"] == "video-a"
    assert rows["accel"]["items"][0]["viewsPerHour"] == 300
    assert rows["category"]["categoryId"] == "10"
    assert "음악" in rows["category"]["title"]

    joined = " ".join(body["insights"])
    assert "3계단 상승" in joined          # video-b: 5위 -> 2위
    assert "새 진입 1편" in joined          # video-c
    assert "음악" in joined                 # 최다 카테고리 점유


def test_home_first_snapshot_has_no_accel_row(table):
    NOW = _now()
    client, store = make_client(table)
    store.put_snapshot("all", NOW, [card("video-a", 1)])
    body = client.get("/api/home").json()
    kinds = [r["kind"] for r in body["rows"]]
    assert "top10" in kinds and "accel" not in kinds
    # 파생 전원 null — 상승/가속/신규 칩은 없어야 한다
    assert all("상승" not in s and "새 진입" not in s for s in body["insights"])


def test_home_hero_tenure_counts_consecutive_buckets(table):
    NOW = _now()
    client, store = make_client(table)
    store.put_snapshot("all", NOW, [card("video-a", 1)])
    for off in (2, 1, 0):
        ts = NOW - timedelta(hours=off)
        store.put_video_points(ts.strftime("%Y-%m-%dT%H"), ts,
                               [{"videoId": "video-a", "rank": 1, "views": 10}])
    body = client.get("/api/home").json()
    assert body["hero"]["tenureHours"] == 3


def test_home_merges_tags_topic_and_age_rows(table):
    NOW = _now()
    client, store = make_client(table)
    cards = [card(f"video-{i:02d}", i) for i in range(1, 7)]
    store.put_snapshot("all", NOW, cards)
    bucket = keys.hour_bucket(NOW)
    tags = {f"video-{i:02d}": {"topics": ["먹방"], "age": "20대", "vibe": "도파민"}
            for i in range(1, 4)}
    store.put_tags(bucket, tags, NOW)

    body = client.get("/api/home").json()

    assert body["tagged"] is True
    rows = {r["kind"]: r for r in body["rows"]}
    assert rows["topic"]["title"] == "#먹방"
    assert len(rows["topic"]["items"]) == 3
    assert rows["age"]["title"] == "👀 20대가 보는 중 (추정)"
    assert rows["top10"]["items"][0]["tags"] == {
        "topics": ["먹방"], "age": "20대", "vibe": "도파민"}
    # 태그 없는 카드에는 tags 필드가 없다
    assert "tags" not in rows["top10"]["items"][5]


def test_home_llm_enabled_flag_follows_token(table):
    NOW = _now()
    client, store = make_client(table, bedrock_token="tok")
    store.put_snapshot("all", NOW, [card("video-a", 1)])
    assert client.get("/api/home").json()["llmEnabled"] is True


def test_home_never_uses_self_as_baseline(table):
    """수집이 한 사이클 빠져 최신 스냅샷이 1~4시간 전 버킷이면, 자기 자신과
    비교해 delta=0/viewsPerHour=0(가짜 실측)이 되면 안 된다 — 전부 null."""
    NOW = _now()
    client, store = make_client(table)
    store.put_snapshot("all", NOW - timedelta(hours=2), [card("video-a", 1)])
    body = client.get("/api/home").json()
    hero = body["hero"]
    assert hero["baseline"] is None
    assert hero["prevRank"] is None and hero["delta"] is None
    assert hero["viewsPerHour"] is None
    assert all(r["kind"] != "accel" for r in body["rows"])
    assert all("새 진입" not in s for s in body["insights"])


def test_home_hero_tenure_breaks_on_gap(table):
    """간격 2시간 초과는 연속으로 보지 않는다 — (5h, 1h, 0h)면 최근 런은 2."""
    NOW = _now()
    client, store = make_client(table)
    store.put_snapshot("all", NOW, [card("video-a", 1)])
    for off in (5, 1, 0):
        ts = NOW - timedelta(hours=off)
        store.put_video_points(ts.strftime("%Y-%m-%dT%H"), ts,
                               [{"videoId": "video-a", "rank": 1, "views": 10}])
    body = client.get("/api/home").json()
    assert body["hero"]["tenureHours"] == 2


def test_home_hero_thumbnail_rejects_malformed_video_id(table):
    """후행 개행 등 형태 위반 videoId로는 maxres URL을 조립하지 않는다."""
    NOW = _now()
    client, store = make_client(table)
    store.put_snapshot("all", NOW, [card("video-a\n", 1)])
    body = client.get("/api/home").json()
    assert body["hero"]["heroThumbnail"] == "http://t/img.jpg"


def test_home_response_is_cached_within_ttl(table):
    """홈 응답은 프로세스 내 30초 캐시된다 — 사이 데이터 변화가 즉시 반영되지
    않아도 된다(수집은 시간 단위, 프론트 폴링은 60초)."""
    NOW = _now()
    client, store = make_client(table)
    store.put_snapshot("all", NOW, [card("video-a", 1)])
    first = client.get("/api/home").json()
    assert first["tagged"] is False
    store.put_tags(keys.hour_bucket(NOW), {"video-a": {
        "topics": ["먹방"], "age": "20대", "vibe": "몰입"}}, NOW)
    second = client.get("/api/home").json()
    assert second["tagged"] is False  # 캐시 히트 — 재조합하지 않았다
