"""스냅샷 목록 → 카테고리 점유율/진입이탈 시계열. 순수 함수."""


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
