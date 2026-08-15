"""YouTube Data API v3 클라이언트. httpx.Client를 주입받는다(테스트는 MockTransport).

상류 오류 본문(GCP 프로젝트 번호·콘솔 URL 포함 가능)은 로그에만 남기고
예외에는 상태 코드만 싣는다.
"""
import logging

import httpx

from app.categories import CATEGORY_NAMES

log = logging.getLogger(__name__)
BASE = "https://www.googleapis.com/youtube/v3"
TIMEOUT = 10.0
# 카드에 싣는 소개문 길이 상한 — 홈 히어로의 '간단한 소개'용이며, 스냅샷
# items(JSON 문자열) 크기가 설명문 길이에 끌려가지 않도록 자른다.
DESCRIPTION_MAX = 200


def _stat_int(v) -> int:
    """YouTube statistics 값은 문자열 숫자다. 비정상 값은 0으로 — 카드 한 장의
    통계 오염이 수집 사이클 전체를 중단시키지 않는다(부분 실패 격리)."""
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


class UpstreamError(Exception):
    def __init__(self, status: int):
        super().__init__(f"youtube upstream status={status}")
        self.status = status


class YouTubeClient:
    def __init__(self, api_key, client=None, category_names=None):
        self.api_key = api_key
        self.client = client or httpx.Client(timeout=TIMEOUT)
        self.category_names = dict(category_names or CATEGORY_NAMES)

    def load_category_names(self):
        """기동 시 1회 호출. 실패해도 기본명으로 동작한다."""
        try:
            res = self.client.get(f"{BASE}/videoCategories", params={
                "part": "snippet", "regionCode": "KR", "hl": "ko", "key": self.api_key})
            if res.status_code == 200:
                for it in res.json().get("items", []):
                    self.category_names[it["id"]] = it["snippet"]["title"]
        except httpx.HTTPError:
            log.warning("videoCategories load failed; using defaults")

    def most_popular(self, category_id, max_results):
        params = {"part": "snippet,statistics", "chart": "mostPopular",
                  "regionCode": "KR", "maxResults": str(max_results), "key": self.api_key}
        if category_id:
            params["videoCategoryId"] = category_id
        try:
            res = self.client.get(f"{BASE}/videos", params=params)
        except httpx.HTTPError as e:
            log.error("youtube request failed: %s", type(e).__name__)
            raise UpstreamError(502) from e
        if res.status_code != 200:
            log.error("youtube status=%s body=%s", res.status_code, res.text[:500])
            raise UpstreamError(res.status_code)
        cards = []
        for i, it in enumerate(res.json().get("items", []), start=1):
            sn, st = it.get("snippet", {}), it.get("statistics", {})
            cat_id = sn.get("categoryId", "")
            cards.append({
                "rank": i, "videoId": it.get("id", ""),
                "title": sn.get("title", ""), "channel": sn.get("channelTitle", ""),
                "views": _stat_int(st.get("viewCount", 0)), "likes": _stat_int(st.get("likeCount", 0)),
                "category": self.category_names.get(cat_id, "기타"), "categoryId": cat_id,
                "thumbnail": sn.get("thumbnails", {}).get("high", {}).get("url", ""),
                "publishedAt": sn.get("publishedAt", ""),
                # 개행·공백 정리 후 상한 — 히어로 소개문 용도라 앞부분만 필요
                "description": " ".join(
                    str(sn.get("description") or "").split())[:DESCRIPTION_MAX],
            })
        return cards
