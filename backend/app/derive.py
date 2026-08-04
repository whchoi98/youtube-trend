"""스냅샷 대비 파생 필드 계산. 순수 함수 — I/O 없음.

계약: baseline=None → 4필드 전부 None("비교 불가"). prevRank=None +
baseline!=None → 신규 진입(NEW). viewsPerHour는 실제 경과 시간으로
나눈다(1시간 간격 가정 금지 — 수집 간격은 폴백 때문에 1~4시간으로 흔들린다).
"""
from datetime import datetime


def _is_int(v):
    """int 검증 — bool 제외 (bool은 int의 서브클래스라서 함정)."""
    return isinstance(v, int) and not isinstance(v, bool)


def with_derived(cards, baseline, now):
    captured = None
    prev_by_id = {}
    if baseline:
        try:
            captured = datetime.fromisoformat(baseline["capturedAt"])
        except (ValueError, KeyError, TypeError):
            captured = None
        if captured is not None:
            prev_by_id = {c.get("videoId"): c for c in baseline.get("items", [])}

    out = []
    for c in cards:
        d = dict(c)
        if captured is None:
            d.update(baseline=None, prevRank=None, delta=None, viewsPerHour=None)
            out.append(d)
            continue
        d["baseline"] = captured.isoformat()
        prev = prev_by_id.get(c.get("videoId"))
        if prev is None:
            d.update(prevRank=None, delta=None, viewsPerHour=None)
            out.append(d)
            continue
        prev_rank = prev.get("rank")
        d["prevRank"] = prev_rank if _is_int(prev_rank) else None
        d["delta"] = (d["prevRank"] - c["rank"]) if d["prevRank"] is not None else None
        prev_views = prev.get("views")
        hours = (now - captured).total_seconds() / 3600
        if _is_int(prev_views) and _is_int(c.get("views")) and hours > 0:
            d["viewsPerHour"] = round((c["views"] - prev_views) / hours)
        else:
            d["viewsPerHour"] = None
        out.append(d)
    return out
