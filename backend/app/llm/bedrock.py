"""Bedrock Converse REST 직접 호출. Bearer 인증 전용(SigV4/boto3 금지 —
조직 SCP가 서울 리전 InvokeModel을 거부하므로 조직 밖 발급 키가 전제).
"""
import logging

import httpx

log = logging.getLogger(__name__)

MODEL_ID = "global.anthropic.claude-sonnet-4-6"
ENDPOINT = f"https://bedrock-runtime.ap-northeast-2.amazonaws.com/model/{MODEL_ID}/converse"
TIMEOUT = 25.0


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
