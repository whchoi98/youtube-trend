"""홈 화면 조합·퀴즈 추천 로직. 순수 함수 — I/O 없음(라우터가 스냅샷·태그·
시계열을 읽어 넘긴다).

파생 필드 계약을 그대로 따른다: null=계산 불가, 0=실측 0. 정렬·집계는 전부
null 안전이어야 한다(첫 스냅샷은 파생 4필드가 전원 null이다).
"""
from datetime import datetime, timedelta

from app.categories import CATEGORIES, CATEGORY_NAMES
from app.charts import MUSIC_CHARTS
from app.regions import REGIONS, REGION_TITLES
from app.spotlights import SPOTLIGHTS

TOPIC_ROW_MIN = 3      # 주제/무드 행 최소 타일 수 — 이보다 적으면 행이 초라하다
TOPIC_ROW_MAX = 4      # 주제 행 최대 개수
DERIVED_ROW_MIN = 2    # 신규 진입/역주행 행 최소 타일 수
# 무드 행 — AI 태깅의 vibe 값 중 행으로 만들 무드와 제목
VIBE_ROWS = [("힐링", "힐링이 필요할 때"), ("도파민", "도파민 충전소")]

# 취향 퀴즈: (mood, time, style) 8조합 → 유형명. 결정적 매핑 — LLM 미사용.
QUIZ_MOODS = ("힐링", "도파민")
QUIZ_TIMES = ("낮", "심야")
QUIZ_STYLES = ("몰입", "가볍게")
QUIZ_TYPES = {
    ("힐링", "낮", "몰입"): "한낮의 힐링 다이버",
    ("힐링", "낮", "가볍게"): "산책길 무드 컬렉터",
    ("힐링", "심야", "몰입"): "새벽 감성 항해사",
    ("힐링", "심야", "가볍게"): "야간 힐링 유랑러",
    ("도파민", "낮", "몰입"): "정오의 트렌드 헌터",
    ("도파민", "낮", "가볍게"): "점심시간 파도타기러",
    ("도파민", "심야", "몰입"): "심야 몰아보기 장인",
    ("도파민", "심야", "가볍게"): "새벽 도파민 스나이퍼",
}
# mood/style별 분야 가중치 — 태그가 없어도(LLM 미설정) 추천이 동작하는 바닥선.
MOOD_CATS = {
    "힐링": {"10": 3, "1": 2, "28": 1},
    "도파민": {"20": 3, "24": 3, "23": 2, "17": 2, "25": 1},
}
STYLE_CATS = {
    "몰입": {"1": 2, "10": 2, "20": 1},
    "가볍게": {"23": 2, "24": 2},
}
QUIZ_ITEMS = 10
VIBE_MATCH_SCORE = 3


def _pos_int(v):
    """양의 int만 통과 (bool 제외). null 안전 정렬·필터용."""
    return isinstance(v, int) and not isinstance(v, bool) and v > 0


def merge_tags(cards, tags):
    """카드 목록에 태그를 병합한 새 목록을 돌려준다. tags가 없으면 원본 그대로."""
    if not tags:
        return cards
    out = []
    for c in cards:
        t = tags.get(c.get("videoId"))
        out.append(dict(c, tags=t) if t else c)
    return out


def build_rows(all_items, cat_items, region_items=None, spotlight_items=None,
               chart_items=None):
    """홈 행 구성. 인자들은 파생·태그 병합이 끝난 카드 목록이다.

    순서: top10 → accel → new(첫 진입) → climb(역주행) → chart(YT Music 5종)
    → topic(태그) → vibe(무드 태그) → 분야 → 국가 → spotlight(채널들, 맨 하단).
    빈 행은 넣지 않는다. top10 행은 사이드바 주제 뷰(TOP 20)를 위해 20개까지
    싣는다 — 홈 스트립은 프론트가 10개로 잘라 표시한다. chart_items와
    spotlight_items는 {접미사: 카드 목록} dict다.
    """
    rows = []
    if all_items:
        rows.append({"kind": "top10", "title": "지금 한국 급상승 TOP 10",
                     "items": all_items[:20]})

    accel = [c for c in all_items if _pos_int(c.get("viewsPerHour"))]
    accel.sort(key=lambda c: (-c["viewsPerHour"], c.get("rank") or 999))
    if accel:
        rows.append({"kind": "accel", "title": "조회수 급증 중",
                     "items": accel[:10]})

    # 오늘 첫 진입 — 기준선에 없던 신규 차트인 (baseline 있음 + prevRank null)
    fresh = [c for c in all_items
             if c.get("baseline") is not None and c.get("prevRank") is None]
    if len(fresh) >= DERIVED_ROW_MIN:
        rows.append({"kind": "new", "title": "오늘 첫 진입", "items": fresh})

    # 순위 역주행 — 기준선 대비 순위 상승폭 상위
    climbers = [c for c in all_items if _pos_int(c.get("delta"))]
    climbers.sort(key=lambda c: (-c["delta"], c.get("rank") or 999))
    if len(climbers) >= DERIVED_ROW_MIN:
        rows.append({"kind": "climb", "title": "순위 역주행",
                     "items": climbers[:10]})

    for suffix, _pid, title in MUSIC_CHARTS:
        cards = (chart_items or {}).get(suffix)
        if cards:
            rows.append({"kind": "chart", "chartId": suffix,
                         "title": title, "items": cards})

    by_topic = {}
    for c in all_items:
        for t in (c.get("tags") or {}).get("topics") or []:
            by_topic.setdefault(t, []).append(c)
    topic_rows = [
        {"kind": "topic", "title": f"#{t}", "items": cs}
        for t, cs in by_topic.items() if len(cs) >= TOPIC_ROW_MIN
    ]
    # 타일 수 내림차순, 동수면 제목순(결정적)
    topic_rows.sort(key=lambda r: (-len(r["items"]), r["title"]))
    rows.extend(topic_rows[:TOPIC_ROW_MAX])

    for vibe, title in VIBE_ROWS:
        cs = [c for c in all_items if (c.get("tags") or {}).get("vibe") == vibe]
        if len(cs) >= TOPIC_ROW_MIN:
            rows.append({"kind": "vibe", "title": title, "items": cs})

    for cid, _name in CATEGORIES:
        cards = cat_items.get(cid)
        if cards:
            rows.append({"kind": "category", "categoryId": cid,
                         "title": CATEGORY_NAMES[cid], "items": cards})

    for code, _name in REGIONS:
        cards = (region_items or {}).get(code)
        if cards:
            rows.append({"kind": "region", "regionCode": code,
                         "title": REGION_TITLES[code], "items": cards})

    # 채널 스포트라이트들은 맨 하단에 정의 순서대로 배치한다
    for suffix, _handle, title in SPOTLIGHTS:
        cards = (spotlight_items or {}).get(suffix)
        if cards:
            rows.append({"kind": "spotlight", "spotId": suffix,
                         "title": title, "items": cards})
    return rows


def _fmt_count(n):
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}억"
    if n >= 10_000:
        return f"{n / 10_000:.1f}만"
    return f"{n:,}"


def _short(title, max_len=14):
    s = " ".join(str(title or "").split())
    return s[:max_len] + "…" if len(s) > max_len else s


def build_insights(items):
    """LLM 없이 계산하는 인사이트 칩 2~4개. 파생 null이면 해당 칩을 생략한다."""
    out = []
    risers = [c for c in items if _pos_int(c.get("delta"))]
    if risers:
        top = max(risers, key=lambda c: c["delta"])
        out.append(f"「{_short(top.get('title'))}」 {top['delta']}계단 상승")
    fast = [c for c in items if _pos_int(c.get("viewsPerHour"))]
    if fast:
        top = max(fast, key=lambda c: c["viewsPerHour"])
        out.append(f"「{_short(top.get('title'))}」 시간당 +{_fmt_count(top['viewsPerHour'])}회")
    new_count = sum(1 for c in items
                    if c.get("baseline") is not None and c.get("prevRank") is None)
    if new_count:
        out.append(f"새 진입 {new_count}편")
    if items:
        counts = {}
        for c in items:
            cid = c.get("categoryId") or ""
            counts[cid] = counts.get(cid, 0) + 1
        cid, cnt = max(counts.items(), key=lambda kv: kv[1])
        name = CATEGORY_NAMES.get(cid)
        if name and cnt >= 2:
            pct = round(cnt / len(items) * 100)
            out.append(f"{name} 점유 {pct}% — Top{len(items)} 최다")
    return out


def tenure_hours(history):
    """최신 버킷부터 연속 등장한 시간 버킷 수(1 이상 — 실측값).

    history는 /video_history 결과(ts "YYYY-MM-DDTHH" 오름차순). 수집이 한 시간
    빠진 정도(간격 2h 이하)는 연속으로 본다 — 수집 폴백 허용치와 맞춘다.
    """
    buckets = []
    for p in history:
        try:
            buckets.append(datetime.strptime(p["ts"], "%Y-%m-%dT%H"))
        except (ValueError, KeyError, TypeError):
            continue
    if not buckets:
        return 1
    buckets.sort()
    n = 1
    for i in range(len(buckets) - 1, 0, -1):
        if buckets[i] - buckets[i - 1] <= timedelta(hours=2):
            n += 1
        else:
            break
    return n


def quiz_type(mood, time, style):
    return QUIZ_TYPES[(mood, time, style)]


def quiz_pick(items, mood, time, style):
    """결정적 추천: 태그 vibe 일치 > 분야 가중치 > 순위 타이브레이크."""
    answers = {mood, time, style}

    def score(c):
        s = 0.0
        vibe = (c.get("tags") or {}).get("vibe")
        if vibe in answers:
            s += VIBE_MATCH_SCORE
        cid = c.get("categoryId")
        s += MOOD_CATS.get(mood, {}).get(cid, 0)
        s += STYLE_CATS.get(style, {}).get(cid, 0)
        rank = c.get("rank") if _pos_int(c.get("rank")) else 999
        s += (31 - min(rank, 31)) / 30.0
        return s

    ranked = sorted(items, key=lambda c: (-score(c), c.get("rank") or 999))
    return ranked[:QUIZ_ITEMS]
