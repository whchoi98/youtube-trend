"""Bedrock Converse REST 직접 호출. Bearer 인증 전용(SigV4/boto3 금지 —
조직 SCP가 서울 리전 InvokeModel을 거부하므로 조직 밖 발급 키가 전제).

스트리밍(converse-stream)은 AWS eventstream 바이너리 프레임으로 온다.
boto3를 쓸 수 없으므로 프레임을 직접 파싱한다 — 구조는
[총길이 u32][헤더길이 u32][프렐류드 CRC u32][헤더들][페이로드][메시지 CRC u32].
"""
import json
import logging

import httpx

log = logging.getLogger(__name__)

MODEL_ID = "global.anthropic.claude-sonnet-4-6"
_BASE = "https://bedrock-runtime.ap-northeast-2.amazonaws.com/model"
ENDPOINT = f"{_BASE}/{MODEL_ID}/converse"
STREAM_ENDPOINT = f"{_BASE}/{MODEL_ID}/converse-stream"
TIMEOUT = 25.0
# 프레임당 페이로드는 토큰 몇 개 수준 — 방어적 상한(비정상 스트림 차단)
_MAX_FRAME = 1_000_000

# eventstream 헤더 값 타입별 고정 길이(가변 길이 타입은 -1)
_HEADER_VALUE_SIZES = {0: 0, 1: 0, 2: 1, 3: 2, 4: 4, 5: 8, 6: -1, 7: -1, 8: 8, 9: 16}


def _parse_headers(raw: bytes) -> dict:
    """eventstream 헤더 블록 파싱. 문자열(타입 7) 값만 담고 나머지는 건너뛴다.

    잘린/손상 블록에서도 예외 없이 멈춘다 — 각 읽기 전에 잔여 길이를 검증한다."""
    out, i = {}, 0
    while i < len(raw):
        name_len = raw[i]
        i += 1
        if i + name_len + 1 > len(raw):  # name + vtype 1바이트가 남아 있어야 한다
            break
        name = raw[i:i + name_len].decode("utf-8", "replace")
        i += name_len
        vtype = raw[i]
        i += 1
        size = _HEADER_VALUE_SIZES.get(vtype)
        if size is None:
            break  # 알 수 없는 타입 — 이후 오프셋을 신뢰할 수 없다
        if size == -1:  # 가변 길이(바이트열/문자열): u16 길이 접두
            if i + 2 > len(raw):
                break
            vlen = int.from_bytes(raw[i:i + 2], "big")
            i += 2
            if i + vlen > len(raw):
                break
            if vtype == 7:
                out[name] = raw[i:i + vlen].decode("utf-8", "replace")
            i += vlen
        else:
            i += size
    return out


def _iter_eventstream(byte_iter):
    """바이트 청크 스트림에서 (headers, payload) 프레임을 꺼낸다."""
    buf = b""
    for chunk in byte_iter:
        buf += chunk
        while len(buf) >= 12:
            total = int.from_bytes(buf[:4], "big")
            if total < 16 or total > _MAX_FRAME:
                raise LlmUpstreamError(502)  # 프레임 구조 붕괴
            if len(buf) < total:
                break
            frame, buf = buf[:total], buf[total:]
            headers_len = int.from_bytes(frame[4:8], "big")
            if headers_len > total - 16:
                raise LlmUpstreamError(502)  # 헤더 길이가 프레임을 벗어남 — 손상
            headers = _parse_headers(frame[12:12 + headers_len])
            payload = frame[12 + headers_len:total - 4]  # 마지막 4B는 CRC
            yield headers, payload


class LlmDisabled(Exception):
    """토큰 미설정 — 503 graceful degradation 신호."""


class LlmUpstreamError(Exception):
    def __init__(self, status: int):
        super().__init__(f"bedrock upstream status={status}")
        self.status = status


class BedrockClient:
    def __init__(self, token: str, client: httpx.Client | None = None):
        self.token = token
        self.client = client or httpx.Client(timeout=TIMEOUT)

    def converse(self, system: str, user: str, max_tokens: int):
        if not self.token:
            raise LlmDisabled()
        body = {
            "system": [{"text": system}],
            "messages": [{"role": "user", "content": [{"text": user}]}],
            "inferenceConfig": {"maxTokens": max_tokens},
        }
        try:
            res = self.client.post(ENDPOINT, json=body, headers={
                "authorization": f"Bearer {self.token}",
                "content-type": "application/json"})
        except httpx.HTTPError as e:
            log.error("bedrock request failed: %s", type(e).__name__)
            raise LlmUpstreamError(504) from e
        if res.status_code != 200:
            # 오류 본문에 계정 ID·모델 ARN이 올 수 있다 — 로그에만 남긴다.
            log.error("bedrock status=%s body=%s", res.status_code, res.text[:500])
            raise LlmUpstreamError(res.status_code)
        try:
            data = res.json()
            text = data["output"]["message"]["content"][0]["text"]
        except (ValueError, KeyError, IndexError, TypeError):
            log.error("bedrock unexpected body (first 200 chars): %s", res.text[:200])
            raise LlmUpstreamError(502)
        return text, data.get("stopReason", "")

    def converse_stream(self, system: str, user: str, max_tokens: int):
        """토큰 단위 스트리밍 제너레이터.

        ("delta", 텍스트조각)들을 내보내고 마지막에 ("stop", stopReason)을
        내보낸다. 첫 yield 전에 요청·상태 검증이 끝나므로, 호출부가 첫
        이벤트를 눈앞에서 당기면(next) 오류를 HTTP 상태로 매핑할 수 있다.
        """
        if not self.token:
            raise LlmDisabled()
        body = {
            "system": [{"text": system}],
            "messages": [{"role": "user", "content": [{"text": user}]}],
            "inferenceConfig": {"maxTokens": max_tokens},
        }
        try:
            with self.client.stream("POST", STREAM_ENDPOINT, json=body, headers={
                    "authorization": f"Bearer {self.token}",
                    "content-type": "application/json"}) as res:
                if res.status_code != 200:
                    res.read()
                    # 오류 본문에 계정 ID·모델 ARN이 올 수 있다 — 로그에만 남긴다.
                    log.error("bedrock stream status=%s body=%s",
                              res.status_code, res.text[:500])
                    raise LlmUpstreamError(res.status_code)
                stop, got_stop = "", False
                for headers, payload in _iter_eventstream(res.iter_bytes()):
                    if (headers.get(":message-type") == "exception"
                            or ":exception-type" in headers):
                        log.error("bedrock stream exception headers=%s", headers)
                        raise LlmUpstreamError(502)
                    event_type = headers.get(":event-type", "")
                    try:
                        data = json.loads(payload) if payload else {}
                    except ValueError:
                        continue  # 페이로드가 JSON이 아닌 이벤트는 건너뛴다
                    if event_type == "contentBlockDelta":
                        text = (data.get("delta") or {}).get("text")
                        if text:
                            yield ("delta", text)
                    elif event_type == "messageStop":
                        stop = data.get("stopReason", "")
                        got_stop = True
                if not got_stop:
                    # messageStop 없이 끝난 스트림 = 절단 — 정상 완료로 위장해
                    # 잘린 텍스트가 시간 버킷 캐시를 오염시키는 것을 막는다
                    log.error("bedrock stream ended without messageStop")
                    raise LlmUpstreamError(502)
                yield ("stop", stop)
        except httpx.HTTPError as e:
            log.error("bedrock stream failed: %s", type(e).__name__)
            raise LlmUpstreamError(504) from e
