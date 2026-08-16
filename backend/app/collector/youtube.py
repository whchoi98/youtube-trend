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

    def _get(self, path, params):
        try:
            res = self.client.get(f"{BASE}/{path}", params={**params, "key": self.api_key})
        except httpx.HTTPError as e:
            log.error("youtube request failed: %s", type(e).__name__)
            raise UpstreamError(502) from e
        if res.status_code != 200:
            log.error("youtube status=%s body=%s", res.status_code, res.text[:500])
            raise UpstreamError(res.status_code)
        return res.json()

    def _card(self, rank, it):
        sn, st = it.get("snippet", {}), it.get("statistics", {})
        cat_id = sn.get("categoryId", "")
        return {
            "rank": rank, "videoId": it.get("id", ""),
            "title": sn.get("title", ""), "channel": sn.get("channelTitle", ""),
            "views": _stat_int(st.get("viewCount", 0)), "likes": _stat_int(st.get("likeCount", 0)),
            "category": self.category_names.get(cat_id, "기타"), "categoryId": cat_id,
            "thumbnail": sn.get("thumbnails", {}).get("high", {}).get("url", ""),
            "publishedAt": sn.get("publishedAt", ""),
            # 개행·공백 정리 후 상한 — 히어로 소개문 용도라 앞부분만 필요
            "description": " ".join(
                str(sn.get("description") or "").split())[:DESCRIPTION_MAX],
        }

    def most_popular(self, category_id, max_results, region_code="KR"):
        params = {"part": "snippet,statistics", "chart": "mostPopular",
                  "regionCode": region_code, "maxResults": str(max_results)}
        if category_id:
            params["videoCategoryId"] = category_id
        data = self._get("videos", params)
        return [self._card(i, it)
                for i, it in enumerate(data.get("items", []), start=1)]

    def channel_top(self, handle, max_results):
        """채널 핸들의 최근 업로드(최대 50개)를 조회수 내림차순 랭킹으로 반환.

        쿼터: channels 1 + playlistItems 1 + videos 1 = 3유닛/호출
        (search.list의 100유닛을 피하려고 uploads 재생목록 경로를 쓴다).
        업로드 재생목록 id는 인스턴스에 캐시한다 — 채널당 기동 후 1회만 조회.
        """
        if not hasattr(self, "_uploads_cache"):
            self._uploads_cache = {}
        playlist = self._uploads_cache.get(handle)
        if not playlist:
            data = self._get("channels",
                             {"part": "contentDetails", "forHandle": handle})
            items = data.get("items", [])
            playlist = (items[0].get("contentDetails", {})
                        .get("relatedPlaylists", {}).get("uploads", "")) if items else ""
            if not playlist:
                log.error("channel_top: uploads playlist not found handle=%s", handle)
                raise UpstreamError(404)
            self._uploads_cache[handle] = playlist

        data = self._get("playlistItems", {
            "part": "contentDetails", "playlistId": playlist, "maxResults": "50"})
        video_ids = [it.get("contentDetails", {}).get("videoId", "")
                     for it in data.get("items", [])]
        video_ids = [v for v in video_ids if v]
        if not video_ids:
            return []

        data = self._get("videos", {
            "part": "snippet,statistics", "id": ",".join(video_ids[:50])})
        ranked = sorted(data.get("items", []),
                        key=lambda it: _stat_int(
                            it.get("statistics", {}).get("viewCount", 0)),
                        reverse=True)[:max_results]
        return [self._card(i, it) for i, it in enumerate(ranked, start=1)]

    def playlist_top(self, playlist_id, max_results):
        """재생목록 상위 항목을 목록 순서 그대로 랭킹으로 반환.

        YouTube Music 공식 차트 재생목록은 항목 순서가 곧 차트 순위다 —
        channel_top과 달리 조회수로 재정렬하지 않는다.
        쿼터: playlistItems 1 + videos 1 = 2유닛/호출.
        """
        data = self._get("playlistItems", {
            "part": "contentDetails", "playlistId": playlist_id,
            "maxResults": str(min(max_results, 50))})
        video_ids = [it.get("contentDetails", {}).get("videoId", "")
                     for it in data.get("items", [])]
        video_ids = [v for v in video_ids if v][:max_results]
        if not video_ids:
            return []

        data = self._get("videos", {
            "part": "snippet,statistics", "id": ",".join(video_ids)})
        # videos.list는 순서를 보존하지 않는다 — 재생목록 순서로 재배열
        by_id = {it.get("id", ""): it for it in data.get("items", [])}
        return [self._card(i, by_id[v])
                for i, v in enumerate((v for v in video_ids if v in by_id),
                                      start=1)]
