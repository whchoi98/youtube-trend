"""DynamoDB 키 규칙의 단일 정의.

스냅샷 시각 키는 UTC 시 단위 버킷이다. 수집 cron(minute=0)과 버킷 경계가
정렬되므로 "그 시각의 스냅샷"을 계산된 키 하나로 조회할 수 있다.
"""
from datetime import datetime, timezone

# 파생 필드 기준 스냅샷 폴백 오프셋(시간). 배지/속도는 1~4시간 전, 일간 비교는
# 24~26시간 전(과거로만 — 미래 방향 폴백은 "어제와 비교"의 의미를 깨뜨린다).
RECENT_OFFSETS = [1, 2, 3, 4]
DAILY_OFFSETS = [24, 25, 26]
# 기준 스냅샷 최소 연령. 너무 어린 스냅샷과 비교하면 시간당 환산이 수 배로
# 확대된다(선행 프로젝트 실측 0.11h → 9배 왜곡).
MIN_AGE_HOURS = 0.75

# 정렬 키 형식: 시간 버킷 앞에 접두어가 붙는다
TS_PREFIX = "TS#"


def hour_bucket(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H")


def snap_pk(scope: str) -> str:
    """스냅샷 스코프 → pk. 스코프 규약: "all"=전체 KR Top30,
    "rgn-{CODE}"=국가별(예: rgn-US), "spot-{name}"=채널 스포트라이트(예: spot-aws),
    그 외=카테고리 id."""
    if scope == "all":
        return "SNAP#ALL"
    if scope.startswith("rgn-"):
        return f"SNAP#RGN#{scope[4:]}"
    if scope.startswith("spot-"):
        return f"SNAP#SPOT#{scope[5:]}"
    if scope.startswith("chart-"):
        return f"SNAP#CHART#{scope[6:]}"
    return f"SNAP#CAT#{scope}"


def vid_pk(video_id: str) -> str:
    return f"VID#{video_id}"


def report_pk(kind: str, scope: str) -> str:
    return f"REPORT#{kind}#{scope}"


def tags_pk() -> str:
    """AI 태깅 결과. 전체 Top30 스냅샷 버킷 단위로 저장한다."""
    return "TAGS#ALL"


def ts_sk(bucket: str) -> str:
    return f"{TS_PREFIX}{bucket}"


def bucket_from_sk(sk: str) -> str:
    """정렬 키에서 시간 버킷 추출 (접두어 제거)."""
    return sk.removeprefix(TS_PREFIX)


def ttl_epoch(now: datetime, days: int) -> int:
    return int(now.timestamp()) + days * 86400
