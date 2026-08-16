"""수집 오케스트레이션. 부분 실패 허용 — scope 하나의 실패가 나머지를 막지 않는다."""
import logging

from app.aggregate import rank_channels
from app.categories import CATEGORIES
from app.charts import MUSIC_CHARTS
from app.collector.youtube import UpstreamError
from app.regions import REGIONS
from app.store import keys

log = logging.getLogger(__name__)

# 채널 스포트라이트 — AWS Korea 공식 채널 인기 영상 랭킹
SPOTLIGHT_HANDLE = "AWSKorea"
SPOTLIGHT_SCOPE = "spot-aws"
# YouTube Music 공식 차트 목록은 app/charts.py 단일 정의를 따른다
# 분야/국가/스포트라이트 랭킹 깊이 — 사이드바 주제 뷰가 TOP 20을 보여준다
RANK_DEPTH = 20


def collect_all(store, yt, now):
    written, skipped, degraded = 0, [], []
    bucket = keys.hour_bucket(now)

    # 1) 전체 Top 30 — 실패하면 이번 사이클 전체를 접는다(파생 폴백의 원천이므로)
    try:
        all_cards = yt.most_popular(None, 30)
    except UpstreamError as e:
        log.error("collect: ALL scope failed status=%s", e.status)
        return {"written": 0, "skipped": ["all"], "degraded": []}
    if store.put_snapshot("all", now, all_cards):
        written += 1
    store.put_video_points(bucket, now, [
        {"videoId": c["videoId"], "rank": c["rank"], "views": c["views"],
         "likes": c["likes"], "categoryId": c["categoryId"], "title": c["title"]}
        for c in all_cards])

    # 2) 카테고리별 Top 20 — 미지원/실패 카테고리는 전체 목록 파생으로 폴백
    for cat_id, _name in CATEGORIES:
        try:
            cards = yt.most_popular(cat_id, RANK_DEPTH)
            is_degraded = False
        except UpstreamError as e:
            log.warning("collect: category %s failed status=%s; deriving", cat_id, e.status)
            cards = [dict(c, rank=i) for i, c in enumerate(
                (c for c in all_cards if c["categoryId"] == cat_id), start=1)][:RANK_DEPTH]
            is_degraded = True
        if not cards:
            skipped.append(cat_id)
            continue
        if store.put_snapshot(cat_id, now, cards, degraded=is_degraded):
            written += 1
        if is_degraded:
            degraded.append(cat_id)

    # 3) 국가별 Top 20 — 실패한 국가만 건너뛴다
    for code, _name in REGIONS:
        scope = f"rgn-{code}"
        try:
            cards = yt.most_popular(None, RANK_DEPTH, region_code=code)
        except UpstreamError as e:
            log.warning("collect: region %s failed status=%s", code, e.status)
            skipped.append(scope)
            continue
        if cards and store.put_snapshot(scope, now, cards):
            written += 1

    # 4) 채널 스포트라이트 — AWS Korea 최근 업로드의 조회수 랭킹
    try:
        cards = yt.channel_top(SPOTLIGHT_HANDLE, RANK_DEPTH)
    except UpstreamError as e:
        log.warning("collect: spotlight failed status=%s", e.status)
        skipped.append(SPOTLIGHT_SCOPE)
    else:
        if cards and store.put_snapshot(SPOTLIGHT_SCOPE, now, cards):
            written += 1

    # 5) YouTube Music 공식 차트 5종 — 재생목록 순서 = 차트 순위, 차트별 실패 격리
    for suffix, playlist_id, _title in MUSIC_CHARTS:
        scope = f"chart-{suffix}"
        try:
            cards = yt.playlist_top(playlist_id, RANK_DEPTH)
        except UpstreamError as e:
            log.warning("collect: music chart %s failed status=%s", suffix, e.status)
            skipped.append(scope)
            continue
        if cards and store.put_snapshot(scope, now, cards):
            written += 1

    # 6) 채널 분석 — 전체 Top30 기여 채널의 구독자·총조회수 결합 랭킹
    chan_ids = list({c.get("channelId") for c in all_cards if c.get("channelId")})
    if chan_ids:
        try:
            stats = yt.channels_stats(chan_ids)
        except UpstreamError as e:
            log.warning("collect: channel stats failed status=%s", e.status)
            skipped.append("chan-top")
        else:
            ranking = rank_channels(all_cards, stats)
            if ranking and store.put_snapshot("chan-top", now, ranking):
                written += 1

    log.info("collect done bucket=%s written=%s skipped=%s degraded=%s",
             bucket, written, skipped, degraded)
    return {"written": written, "skipped": skipped, "degraded": degraded}
