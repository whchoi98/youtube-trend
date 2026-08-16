"""스냅샷 목록 → 카테고리 점유율/진입이탈 시계열, 채널 랭킹. 순수 함수."""

CHANNEL_RANK_MAX = 12


def rank_channels(cards, stats):
    """급상승 카드 + 채널 통계 → '지금 뜨는 채널' 랭킹.

    정렬 기준은 급상승 목록 기여(합산 조회수 → 등장 편수). subscribers는
    비공개 채널이 None일 수 있다(실측 0과 혼용 금지).
    """
    by_id = {}
    for c in cards:
        cid = c.get("channelId")
        if not cid:
            continue
        e = by_id.setdefault(cid, {
            "channel": c.get("channel", ""), "trendingCount": 0,
            "trendingViews": 0, "topVideoId": "", "topVideoTitle": "",
            "_best": -1,
        })
        views = c.get("views") or 0
        e["trendingCount"] += 1
        e["trendingViews"] += views
        if views > e["_best"]:
            e["_best"] = views
            e["topVideoId"] = c.get("videoId", "")
            e["topVideoTitle"] = c.get("title", "")

    stat_map = {s.get("channelId"): s for s in stats}
    out = []
    for cid, e in by_id.items():
        s = stat_map.get(cid, {})
        out.append({
            "channelId": cid,
            "name": s.get("name") or e["channel"],
            "thumbnail": s.get("thumbnail", ""),
            "subscribers": s.get("subscribers"),
            "totalViews": s.get("totalViews"),
            "trendingCount": e["trendingCount"],
            "trendingViews": e["trendingViews"],
            "topVideoId": e["topVideoId"],
            "topVideoTitle": e["topVideoTitle"],
        })
    out.sort(key=lambda x: (-x["trendingViews"], -x["trendingCount"]))
    out = out[:CHANNEL_RANK_MAX]
    for i, o in enumerate(out, start=1):
        o["rank"] = i
    return out


def category_series(snapshots):
    out, prev_ids = [], None
    for s in snapshots:
        ids = {c.get("videoId") for c in s["items"]}
        shares = {}
        for c in s["items"]:
            cid = c.get("categoryId", "")
            shares[cid] = shares.get(cid, 0) + 1
        entered = len(ids - prev_ids) if prev_ids is not None else 0
        exited = len(prev_ids - ids) if prev_ids is not None else 0
        out.append({"ts": s["bucket"], "shares": shares,
                    "entered": entered, "exited": exited})
        prev_ids = ids
    return out
