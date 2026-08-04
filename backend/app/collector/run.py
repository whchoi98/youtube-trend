"""수집 오케스트레이션. 부분 실패 허용 — scope 하나의 실패가 나머지를 막지 않는다."""
import logging

from app.categories import CATEGORIES
from app.collector.youtube import UpstreamError
from app.store import keys

log = logging.getLogger(__name__)


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

    # 2) 카테고리별 Top 10 — 미지원/실패 카테고리는 전체 목록 파생으로 폴백
    for cat_id, _name in CATEGORIES:
        try:
            cards = yt.most_popular(cat_id, 10)
            is_degraded = False
        except UpstreamError as e:
            log.warning("collect: category %s failed status=%s; deriving", cat_id, e.status)
            cards = [dict(c, rank=i) for i, c in enumerate(
                (c for c in all_cards if c["categoryId"] == cat_id), start=1)][:10]
            is_degraded = True
        if not cards:
            skipped.append(cat_id)
            continue
        if store.put_snapshot(cat_id, now, cards, degraded=is_degraded):
            written += 1
        if is_degraded:
            degraded.append(cat_id)

    log.info("collect done bucket=%s written=%s skipped=%s degraded=%s",
             bucket, written, skipped, degraded)
    return {"written": written, "skipped": skipped, "degraded": degraded}
