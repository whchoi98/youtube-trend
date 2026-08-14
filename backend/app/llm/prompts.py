"""프롬프트 빌더. 입력은 서버가 DynamoDB에서 읽은 데이터지만, 제목·채널명은
YouTube를 거친 외부 문자열이므로 세탁을 유지한다(개행 주입으로 목록 구조
위조 방지, 길이 상한으로 토큰 증폭 방지).
"""
MAX_ITEMS = 50
MAX_LIST = 8
TRUNCATION_NOTICE = "\n\n⚠ 토큰 한도에 도달해 내용이 잘렸습니다."

SYSTEM = (
    "당신은 YouTube 한국 트렌드 분석가다. 주어진 자료에 없는 사실을 만들지 마라. "
    "한국어로, 소제목 있는 간결한 문단으로 답하라."
)


def clean_text(s, max_len=120):
    if not isinstance(s, str):
        return ""
    return " ".join(s.split())[:max_len]


def _pos(v):
    return str(v) if isinstance(v, int) and not isinstance(v, bool) else "?"


def _int_or_zero(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else 0


def _line(c):
    return (f"{_pos(c.get('rank'))}위: {clean_text(c.get('title'))} — "
            f"{clean_text(c.get('channel'))} ({clean_text(c.get('category'), 30)}, "
            f"조회 {_int_or_zero(c.get('views')):,})")


def build_brief(cards):
    lines = [_line(c) for c in cards[:MAX_ITEMS]]
    user = "다음은 현재 YouTube 한국 급상승 목록이다.\n" + "\n".join(lines) + \
           "\n\n오늘의 트렌드 흐름을 3개 소제목으로 브리핑하라."
    return SYSTEM, user


def build_daily(cards, baseline):
    cur_ids = {c.get("videoId") for c in cards}
    prev_items = baseline.get("items", [])
    prev_ids = {c.get("videoId") for c in prev_items}
    entered = [c for c in cards if c.get("videoId") not in prev_ids][:MAX_LIST]
    exited = [c for c in prev_items if c.get("videoId") not in cur_ids][:MAX_LIST]
    user = (
        f"기준 시각: {clean_text(baseline.get('capturedAt'), 40)}\n"
        "== 새로 진입 ==\n" + "\n".join(_line(c) for c in entered) +
        "\n== 이탈 ==\n" + "\n".join(_line(c) for c in exited) +
        "\n== 현재 상위 ==\n" + "\n".join(_line(c) for c in cards[:10]) +
        "\n\n어제와 비교해 무엇이 달라졌는지 브리핑하라."
    )
    return SYSTEM, user


# AI 태깅 고정 어휘. topics는 8개 분야명과 겹치지 않는 교차 주제만 담는다
# (겹치면 홈의 주제 행이 분야 행과 중복된다). vibe는 취향 퀴즈 선택지 공간과
# 동일해 퀴즈 매칭에 직접 쓰인다.
TOPIC_VOCAB = ["먹방", "브이로그", "챌린지", "커버·댄스", "리뷰·정보", "키즈", "이슈", "하이라이트"]
AGE_VOCAB = ["10대", "20대", "3040", "전연령"]
VIBE_VOCAB = ["힐링", "도파민", "낮", "심야", "몰입", "가볍게"]

TAGS_SYSTEM = (
    "당신은 YouTube 한국 트렌드 분류기다. 반드시 유효한 JSON 객체 하나만 출력한다. "
    "코드 펜스·설명·주석을 붙이지 마라."
)


def build_tags(cards):
    lines = [
        f"{clean_text(c.get('videoId'), 20)}: {clean_text(c.get('title'))} — "
        f"{clean_text(c.get('channel'))} ({clean_text(c.get('category'), 30)})"
        for c in cards[:MAX_ITEMS]
    ]
    user = (
        "다음은 현재 YouTube 한국 급상승 영상 목록이다(형식: videoId: 제목 — 채널 (분야)).\n"
        + "\n".join(lines) +
        "\n\n각 영상을 아래 고정 어휘로만 태깅해 JSON 객체 하나로 답하라.\n"
        f"- topics: {', '.join(TOPIC_VOCAB)} 중 0~2개 배열 (해당 없으면 빈 배열)\n"
        f"- age: 주 시청 연령 추정 — {', '.join(AGE_VOCAB)} 중 1개\n"
        f"- vibe: 시청 무드 — {', '.join(VIBE_VOCAB)} 중 가장 어울리는 1개\n"
        '출력 형식: {"<videoId>": {"topics": [], "age": "", "vibe": ""}, ...}'
    )
    return TAGS_SYSTEM, user


def build_trend_report(series, movers):
    share_lines = [
        f"{s['ts']}: 점유 {s['shares']} 진입 {s['entered']} 이탈 {s['exited']}"
        for s in series[-24:]  # 최근 24버킷으로 입력 상한
    ]
    user = (
        "== 시간대별 카테고리 점유/진입이탈 ==\n" + "\n".join(share_lines) +
        "\n== 조회 속도 상위 ==\n" + "\n".join(_line(c) for c in movers[:MAX_LIST]) +
        "\n\n최근 트렌드의 추이(상승세 분야, 순위 교체 양상)를 분석하라."
    )
    return SYSTEM, user
