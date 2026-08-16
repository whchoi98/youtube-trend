"""SSE 스트리밍 브리핑(GET /api/brief/stream) 계약 테스트."""
import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.config import Settings
from app.llm.bedrock import LlmDisabled, LlmUpstreamError
from app.main import create_app
from app.store.table import TrendStore

NOW = datetime.now(timezone.utc)


def card(video_id="a", rank=1):
    return {"rank": rank, "videoId": video_id, "title": "t", "channel": "c",
            "views": 10, "likes": 1, "category": "음악", "categoryId": "10",
            "thumbnail": "", "publishedAt": ""}


class FakeStreamLlm:
    def __init__(self, deltas=("브리핑 ", "텍스트"), stop="end_turn",
                 disabled=False, fail_before=False, fail_mid=False):
        self.deltas, self.stop = deltas, stop
        self.disabled, self.fail_before, self.fail_mid = disabled, fail_before, fail_mid
        self.calls = 0

    def converse_stream(self, system, user, max_tokens):
        self.calls += 1
        if self.disabled:
            raise LlmDisabled()
        if self.fail_before:
            raise LlmUpstreamError(429)
        for i, d in enumerate(self.deltas):
            yield ("delta", d)
            if self.fail_mid and i == 0:
                raise LlmUpstreamError(500)
        yield ("stop", self.stop)


def make_client(table, llm):
    settings = Settings(table_name="t", yt_api_key="x", collect_enabled=False)
    store = TrendStore(table)
    app = create_app(settings, store=store, yt=object(), llm=llm)
    return TestClient(app), store


def sse_events(res_text):
    """SSE 본문을 (event, data) 리스트로 파싱한다."""
    out = []
    for block in res_text.strip().split("\n\n"):
        event, data = None, None
        for line in block.splitlines():
            if line.startswith("event: "):
                event = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        if event:
            out.append((event, data))
    return out


def test_stream_emits_steps_deltas_done_and_caches(table):
    llm = FakeStreamLlm()
    client, store = make_client(table, llm)
    store.put_snapshot("all", NOW, [card()])

    res = client.get("/api/brief/stream?scope=all&mode=now")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    events = sse_events(res.text)

    step_labels = [d["label"] for e, d in events if e == "step"]
    assert "DynamoDB 최신 스냅샷 조회" in step_labels
    assert any("프롬프트 구성" in s for s in step_labels)
    assert any("ConverseStream" in s for s in step_labels)
    assert any("캐시 저장" in s for s in step_labels)

    deltas = [d["text"] for e, d in events if e == "delta"]
    assert "".join(deltas) == "브리핑 텍스트"
    assert events[-1] == ("done", {"cached": False})

    # 같은 시간 버킷 재요청 → 캐시 히트, LLM 재호출 없음
    res2 = client.get("/api/brief/stream?scope=all&mode=now")
    events2 = sse_events(res2.text)
    assert any("캐시 히트" in d["label"] for e, d in events2 if e == "step")
    assert [d["text"] for e, d in events2 if e == "delta"] == ["브리핑 텍스트"]
    assert events2[-1] == ("done", {"cached": True})
    assert llm.calls == 1


def test_stream_rejects_bad_mode(table):
    client, _ = make_client(table, FakeStreamLlm())
    res = client.get("/api/brief/stream?scope=all&mode=hourly")
    assert res.status_code == 400
    assert res.json() == {"error": "잘못된 요청입니다"}


def test_stream_409_without_snapshot(table):
    client, _ = make_client(table, FakeStreamLlm())
    res = client.get("/api/brief/stream?scope=all&mode=now")
    assert res.status_code == 409
    assert res.json() == {"error": "표시할 목록이 아직 없습니다"}


def test_stream_503_when_disabled(table):
    client, store = make_client(table, FakeStreamLlm(disabled=True))
    store.put_snapshot("all", NOW, [card()])
    res = client.get("/api/brief/stream?scope=all&mode=now")
    assert res.status_code == 503 and res.json()["enabled"] is False


def test_stream_502_on_prestream_upstream_error(table):
    client, store = make_client(table, FakeStreamLlm(fail_before=True))
    store.put_snapshot("all", NOW, [card()])
    res = client.get("/api/brief/stream?scope=all&mode=now")
    assert res.status_code == 502 and res.json()["code"] == 429


def test_stream_midstream_error_is_in_band_and_not_cached(table):
    llm = FakeStreamLlm(deltas=("일부", "나머지"), fail_mid=True)
    client, store = make_client(table, llm)
    store.put_snapshot("all", NOW, [card()])
    res = client.get("/api/brief/stream?scope=all&mode=now")
    assert res.status_code == 200  # 스트림 시작 후라 상태는 200, in-band error
    events = sse_events(res.text)
    assert events[-1][0] == "error" and events[-1][1]["code"] == 500
    # 실패한 생성은 캐시되지 않는다 → 재요청 시 LLM 재호출
    client.get("/api/brief/stream?scope=all&mode=now")
    assert llm.calls == 2


def test_stream_max_tokens_appends_truncation_notice(table):
    llm = FakeStreamLlm(stop="max_tokens")
    client, store = make_client(table, llm)
    store.put_snapshot("all", NOW, [card()])
    res = client.get("/api/brief/stream?scope=all&mode=now")
    deltas = [d["text"] for e, d in sse_events(res.text) if e == "delta"]
    assert "잘렸습니다" in "".join(deltas)


def test_stream_trend_mode_uses_series_pipeline(table):
    llm = FakeStreamLlm()
    client, store = make_client(table, llm)
    store.put_snapshot("all", NOW, [card()])
    res = client.get("/api/brief/stream?scope=all&mode=trend")
    labels = [d["label"] for e, d in sse_events(res.text) if e == "step"]
    assert any("48시간" in s for s in labels)
    assert any("집계" in s for s in labels)


def test_stream_without_stop_event_is_not_cached(table):
    """stop 미수신(절단 위장) 스트림은 캐시하지 않는다 — 재요청 시 재생성."""
    class NoStopLlm(FakeStreamLlm):
        def converse_stream(self, system, user, max_tokens):
            self.calls += 1
            yield ("delta", "앞부분만")

    llm = NoStopLlm()
    client, store = make_client(table, llm)
    store.put_snapshot("all", NOW, [card()])
    res = client.get("/api/brief/stream?scope=all&mode=now")
    events = sse_events(res.text)
    assert all("캐시 저장" not in (d or {}).get("label", "")
               for e, d in events if e == "step")
    client.get("/api/brief/stream?scope=all&mode=now")
    assert llm.calls == 2  # 캐시되지 않아 재생성


def test_stream_trend_cache_hit_skips_range_query(table):
    """trend 캐시 히트는 48시간 범위 조회·집계를 건너뛴다 (POST 경로와 동일 순서)."""
    class CountingStore(TrendStore):
        range_calls = 0

        def snapshots_range(self, *a, **kw):
            type(self).range_calls += 1
            return super().snapshots_range(*a, **kw)

    llm = FakeStreamLlm()
    settings = Settings(table_name="t", yt_api_key="x", collect_enabled=False)
    store = CountingStore(table)
    app = create_app(settings, store=store, yt=object(), llm=llm)
    client = TestClient(app)
    store.put_snapshot("all", NOW, [card()])

    client.get("/api/brief/stream?scope=all&mode=trend")
    assert CountingStore.range_calls == 1
    res2 = client.get("/api/brief/stream?scope=all&mode=trend")
    assert CountingStore.range_calls == 1  # 히트 — 범위 조회 생략
    assert any("캐시 히트" in d["label"] for e, d in sse_events(res2.text) if e == "step")
    assert llm.calls == 1
