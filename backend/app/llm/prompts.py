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


def _line(c):
    return (f"{_pos(c.get('rank'))}위: {clean_text(c.get('title'))} — "
            f"{clean_text(c.get('channel'))} ({clean_text(c.get('category'), 30)}, "
            f"조회 {c.get('views') if isinstance(c.get('views'), int) else 0:,})")


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
