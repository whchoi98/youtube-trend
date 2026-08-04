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
