from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.store import keys
from app.store.table import TrendStore

NOW = datetime.now(timezone.utc)


def card(video_id, rank, category_id="10", category="음악"):
    return {"rank": rank, "videoId": video_id, "title": f"제목-{video_id}",
            "channel": "채널", "views": 100, "likes": 1, "category": category,
            "categoryId": category_id, "thumbnail": "", "publishedAt": ""}


def make_client(table):
    settings = Settings(table_name="t", yt_api_key="x", collect_enabled=False)
    app = create_app(settings, store=TrendStore(table), yt=object())
    return TestClient(app), TrendStore(table)


def test_quiz_rejects_unknown_answer(table):
    client, store = make_client(table)
    store.put_snapshot("all", NOW, [card("video-a", 1)])
    res = client.post("/api/quiz",
                      json={"mood": "설렘", "time": "낮", "style": "몰입"})
    assert res.status_code == 400
    assert res.json() == {"error": "잘못된 요청입니다"}


def test_quiz_rejects_missing_field(table):
    client, _ = make_client(table)
    res = client.post("/api/quiz", json={"mood": "힐링"})
    assert res.status_code == 400
    assert res.json() == {"error": "잘못된 요청입니다"}


def test_quiz_409_without_snapshot(table):
    client, _ = make_client(table)
    res = client.post("/api/quiz",
                      json={"mood": "힐링", "time": "낮", "style": "몰입"})
    assert res.status_code == 409
    assert res.json() == {"error": "표시할 목록이 아직 없습니다"}


def test_quiz_returns_deterministic_type_and_items(table):
    client, store = make_client(table)
    # 입력 순서를 섞어 넣어도(안정 정렬 우연 배제) 동점이면 rank 오름차순
    cards = [card(f"video-{i:02d}", i) for i in (7, 3, 11, 1, 9, 5, 12, 2, 10, 6, 8, 4)]
    store.put_snapshot("all", NOW, cards)
    body = client.post("/api/quiz", json={
        "mood": "도파민", "time": "심야", "style": "몰입"}).json()
    assert body["type"] == "심야 몰아보기 장인"
    assert [c["rank"] for c in body["items"]] == list(range(1, 11))


def test_quiz_category_weight_prefers_mood_match(table):
    client, store = make_client(table)
    store.put_snapshot("all", NOW, [
        card("video-music", 1, category_id="10", category="음악"),
        card("video-game", 2, category_id="20", category="게임"),
    ])
    body = client.post("/api/quiz", json={
        "mood": "도파민", "time": "낮", "style": "몰입"}).json()
    # 도파민은 게임(+3) > 음악(0) — 순위 타이브레이크(1위 우세)를 이긴다
    assert body["items"][0]["videoId"] == "video-game"


def test_quiz_tag_vibe_match_beats_rank(table):
    client, store = make_client(table)
    cards = [card("video-notag", 1, category_id="24", category="엔터테인먼트"),
             card("video-vibe", 10, category_id="24", category="엔터테인먼트")]
    store.put_snapshot("all", NOW, cards)
    store.put_tags(keys.hour_bucket(NOW),
                   {"video-vibe": {"topics": [], "age": "20대", "vibe": "심야"}},
                   NOW)
    body = client.post("/api/quiz", json={
        "mood": "도파민", "time": "심야", "style": "가볍게"}).json()
    assert body["items"][0]["videoId"] == "video-vibe"
