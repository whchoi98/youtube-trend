from datetime import datetime, timezone

from app.llm.bedrock import LlmDisabled, LlmUpstreamError
from app.store import keys
from app.store.table import TrendStore
from app.tagging import ensure_tags, parse_tags

NOW = datetime.now(timezone.utc)


def card(video_id, rank):
    return {"rank": rank, "videoId": video_id, "title": f"제목-{video_id}",
            "channel": "채널", "views": 100, "likes": 1, "category": "음악",
            "categoryId": "10", "thumbnail": "", "publishedAt": ""}


class FakeLlm:
    def __init__(self, text="", disabled=False, fail=False):
        self.text, self.disabled, self.fail = text, disabled, fail
        self.calls = 0

    def converse(self, system, user, max_tokens):
        self.calls += 1
        if self.disabled:
            raise LlmDisabled()
        if self.fail:
            raise LlmUpstreamError(500)
        return self.text, "end_turn"


def test_ensure_tags_stores_and_is_idempotent(table):
    store = TrendStore(table)
    store.put_snapshot("all", NOW, [card("video-a", 1)])
    llm = FakeLlm(text='```json\n{"video-a": {"topics": ["먹방"], '
                       '"age": "20대", "vibe": "몰입"}}\n```')
    got = ensure_tags(store, llm, NOW)
    assert got == {"video-a": {"topics": ["먹방"], "age": "20대",
                               "vibe": "몰입", "comment": None}}
    assert store.get_tags(keys.hour_bucket(NOW)) == got
    # 같은 버킷 재호출은 LLM을 다시 태우지 않는다
    again = ensure_tags(store, llm, NOW)
    assert again == got and llm.calls == 1


def test_ensure_tags_none_without_snapshot(table):
    store = TrendStore(table)
    assert ensure_tags(store, FakeLlm(), NOW) is None


def test_ensure_tags_none_when_llm_disabled(table):
    store = TrendStore(table)
    store.put_snapshot("all", NOW, [card("video-a", 1)])
    assert ensure_tags(store, FakeLlm(disabled=True), NOW) is None
    assert store.get_tags(keys.hour_bucket(NOW)) is None


def test_ensure_tags_none_on_upstream_failure(table):
    store = TrendStore(table)
    store.put_snapshot("all", NOW, [card("video-a", 1)])
    assert ensure_tags(store, FakeLlm(fail=True), NOW) is None
    assert store.get_tags(keys.hour_bucket(NOW)) is None


def test_ensure_tags_bad_output_not_stored(table):
    store = TrendStore(table)
    store.put_snapshot("all", NOW, [card("video-a", 1)])
    assert ensure_tags(store, FakeLlm(text="분류할 수 없습니다"), NOW) is None
    assert store.get_tags(keys.hour_bucket(NOW)) is None


def test_parse_tags_filters_vocab_and_unknown_ids():
    text = ('{"video-a": {"topics": ["먹방", "우주여행"], "age": "90대", '
            '"vibe": "심야"}, "video-x": {"topics": ["먹방"], "age": "20대", '
            '"vibe": "몰입"}, "video-b": {"topics": "먹방"}}')
    got = parse_tags(text, {"video-a", "video-b"})
    # video-x는 스냅샷에 없는 id, 우주여행/90대는 어휘 밖, topics 비배열은 빈 배열
    assert got == {"video-a": {"topics": ["먹방"], "age": None,
                               "vibe": "심야", "comment": None}}


def test_parse_tags_tolerates_non_string():
    assert parse_tags(None, {"video-a"}) == {}
    assert parse_tags("[1, 2]", {"video-a"}) == {}


def test_parse_tags_sanitizes_comment():
    text = ('{"video-a": {"topics": [], "age": "20대", "vibe": "몰입", '
            '"comment": "줄바꿈\\n포함  분석 ' + "가" * 100 + '"}, '
            '"video-b": {"topics": [], "age": "20대", "vibe": "몰입", '
            '"comment": 123}}')
    got = parse_tags(text, {"video-a", "video-b"})
    c = got["video-a"]["comment"]
    assert "\n" not in c and c.startswith("줄바꿈 포함 분석")
    assert len(c) == 80  # COMMENT_MAX 절단
    assert got["video-b"]["comment"] is None  # 비문자열은 버린다


def test_parse_tags_dedupes_topics_preserving_order():
    text = '{"video-a": {"topics": ["먹방", "먹방", "브이로그"], "age": "20대", "vibe": "몰입"}}'
    got = parse_tags(text, {"video-a"})
    assert got["video-a"]["topics"] == ["먹방", "브이로그"]


def test_put_tags_first_writer_wins(table):
    store = TrendStore(table)
    bucket = keys.hour_bucket(NOW)
    first = {"video-a": {"topics": ["먹방"], "age": "20대", "vibe": "몰입"}}
    later = {"video-a": {"topics": ["이슈"], "age": "3040", "vibe": "심야"}}
    assert store.put_tags(bucket, first, NOW) is True
    assert store.put_tags(bucket, later, NOW) is False
    assert store.get_tags(bucket) == first


def test_ensure_tags_returns_winner_on_lost_race(table):
    """LLM 호출 중 다른 태스크가 먼저 태그를 쓰면(check-then-act 창) 선착
    결과를 반환한다 — 모든 소비자가 같은 태그를 본다."""
    store = TrendStore(table)
    store.put_snapshot("all", NOW, [card("video-a", 1)])
    winner = {"video-a": {"topics": ["먹방"], "age": "20대", "vibe": "몰입"}}
    bucket = keys.hour_bucket(NOW)

    class RacingLlm(FakeLlm):
        def converse(self, system, user, max_tokens):
            store.put_tags(bucket, winner, NOW)  # 경쟁 태스크가 먼저 저장
            return ('{"video-a": {"topics": ["이슈"], "age": "3040", '
                    '"vibe": "심야"}}', "end_turn")

    got = ensure_tags(store, RacingLlm(), NOW)
    assert got == winner
    assert store.get_tags(bucket) == winner
