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
                "views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)),
                "category": self.category_names.get(cat_id, "기타"), "categoryId": cat_id,
                "thumbnail": sn.get("thumbnails", {}).get("high", {}).get("url", ""),
                "publishedAt": sn.get("publishedAt", ""),
            })
        return cards
