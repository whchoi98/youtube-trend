import httpx
import pytest
from app.llm.bedrock import BedrockClient, LlmDisabled, LlmUpstreamError, ENDPOINT


def ok_payload(text="분석", stop="end_turn"):
    return {"output": {"message": {"content": [{"text": text}]}}, "stopReason": stop}


def make(handler, token="tok"):
    return BedrockClient(token, client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_disabled_when_no_token():
    with pytest.raises(LlmDisabled):
        make(lambda r: httpx.Response(200), token="").converse("s", "u", 100)


def test_converse_sends_bearer_and_parses_text():
    def handler(req):
        assert str(req.url) == ENDPOINT
        assert req.headers["authorization"] == "Bearer tok"
        return httpx.Response(200, json=ok_payload())
    text, stop = make(handler).converse("시스템", "사용자", 100)
    assert text == "분석" and stop == "end_turn"


def test_upstream_error_hides_body():
    def handler(req):
        return httpx.Response(403, json={"message": "account-id-12345 denied"})
    with pytest.raises(LlmUpstreamError) as ei:
        make(handler).converse("s", "u", 100)
    assert ei.value.status == 403
    assert "account-id" not in str(ei.value)


def test_timeout_maps_to_upstream_error():
    def handler(req):
        raise httpx.ReadTimeout("slow")
    with pytest.raises(LlmUpstreamError) as ei:
        make(handler).converse("s", "u", 100)
    assert ei.value.status == 504


def test_non_json_200_maps_to_502():
    def handler(req):
        return httpx.Response(200, content=b"not json{{{")
    with pytest.raises(LlmUpstreamError) as ei:
        make(handler).converse("s", "u", 100)
    assert ei.value.status == 502


# ---- 스트리밍 (converse-stream, AWS eventstream 프레임) ----
import json as _json
from app.llm.bedrock import STREAM_ENDPOINT


def frame(event_type, payload: dict, message_type="event") -> bytes:
    """테스트용 eventstream 프레임 인코더 — 파서와 독립 구현."""
    def header(name: str, value: str) -> bytes:
        nb, vb = name.encode(), value.encode()
        return bytes([len(nb)]) + nb + bytes([7]) + len(vb).to_bytes(2, "big") + vb

    headers = header(":event-type", event_type) + header(":message-type", message_type)
    body = _json.dumps(payload).encode()
    total = 12 + len(headers) + len(body) + 4
    return (total.to_bytes(4, "big") + len(headers).to_bytes(4, "big")
            + b"\x00\x00\x00\x00" + headers + body + b"\x00\x00\x00\x00")


def stream_body(*frames: bytes) -> bytes:
    return b"".join(frames)


def test_converse_stream_yields_deltas_and_stop():
    content = stream_body(
        frame("messageStart", {"role": "assistant"}),
        frame("contentBlockDelta", {"contentBlockIndex": 0, "delta": {"text": "안녕"}}),
        frame("contentBlockDelta", {"contentBlockIndex": 0, "delta": {"text": "하세요"}}),
        frame("messageStop", {"stopReason": "end_turn"}),
    )

    def handler(req):
        assert str(req.url) == STREAM_ENDPOINT
        assert req.headers["authorization"] == "Bearer tok"
        return httpx.Response(200, content=content)

    events = list(make(handler).converse_stream("s", "u", 100))
    assert events == [("delta", "안녕"), ("delta", "하세요"), ("stop", "end_turn")]


def test_converse_stream_handles_split_frames():
    # 프레임이 청크 경계에서 쪼개져 도착해도 재조립된다
    content = stream_body(
        frame("contentBlockDelta", {"delta": {"text": "가나다"}}),
        frame("messageStop", {"stopReason": "max_tokens"}),
    )

    class OneByteStream(httpx.SyncByteStream):
        def __iter__(self):
            for i in range(len(content)):
                yield content[i:i + 1]

    def handler(req):
        return httpx.Response(200, stream=OneByteStream())

    events = list(make(handler).converse_stream("s", "u", 100))
    assert events == [("delta", "가나다"), ("stop", "max_tokens")]


def test_converse_stream_disabled_without_token():
    with pytest.raises(LlmDisabled):
        next(make(lambda r: httpx.Response(200), token="").converse_stream("s", "u", 10))


def test_converse_stream_non_200_raises_before_first_delta():
    def handler(req):
        return httpx.Response(429, json={"message": "arn:aws:secret"})
    gen = make(handler).converse_stream("s", "u", 10)
    with pytest.raises(LlmUpstreamError) as ei:
        next(gen)
    assert ei.value.status == 429
    assert "arn:aws" not in str(ei.value)


def test_converse_stream_exception_event_maps_to_502():
    content = stream_body(
        frame("contentBlockDelta", {"delta": {"text": "일부"}}),
        frame("throttlingException", {"message": "slow down"},
              message_type="exception"),
    )
    gen = make(lambda r: httpx.Response(200, content=content)).converse_stream("s", "u", 10)
    assert next(gen) == ("delta", "일부")
    with pytest.raises(LlmUpstreamError) as ei:
        list(gen)
    assert ei.value.status == 502


def test_converse_stream_truncated_header_block_maps_to_502():
    # name 직후 잘린 헤더 블록 — IndexError 없이 손상으로 처리돼야 한다
    headers = b"\x05:even"  # name_len=5, name 5바이트 뒤 vtype 없음
    body = b"{}"
    total = 12 + len(headers) + len(body) + 4
    corrupt = (total.to_bytes(4, "big") + len(headers).to_bytes(4, "big")
               + b"\x00\x00\x00\x00" + headers + body + b"\x00\x00\x00\x00")
    gen = make(lambda r: httpx.Response(200, content=corrupt)).converse_stream("s", "u", 10)
    with pytest.raises(LlmUpstreamError) as ei:
        list(gen)
    assert ei.value.status == 502  # messageStop 미수신 절단으로 판정


def test_converse_stream_corrupt_headers_len_maps_to_502():
    good = frame("contentBlockDelta", {"delta": {"text": "가"}})
    # headers_len을 프레임 밖을 가리키게 조작
    corrupt = good[:4] + (len(good)).to_bytes(4, "big") + good[8:]
    gen = make(lambda r: httpx.Response(200, content=corrupt)).converse_stream("s", "u", 10)
    with pytest.raises(LlmUpstreamError) as ei:
        list(gen)
    assert ei.value.status == 502


def test_converse_stream_missing_message_stop_maps_to_502():
    # messageStop 없이 정상 종료된 스트림 = 절단 — 정상 완료로 위장 금지
    content = stream_body(
        frame("contentBlockDelta", {"delta": {"text": "앞부분"}}),
    )
    gen = make(lambda r: httpx.Response(200, content=content)).converse_stream("s", "u", 10)
    assert next(gen) == ("delta", "앞부분")
    with pytest.raises(LlmUpstreamError) as ei:
        list(gen)
    assert ei.value.status == 502
