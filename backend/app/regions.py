"""국가별 랭킹 수집 대상. code는 YouTube regionCode, 제목은 홈 행 표기다.

여기 목록을 늘리면 수집 호출이 국가당 시간당 1회씩 늘어난다
(videos.list mostPopular = 쿼터 1유닛 — 부담 낮음).
"""
REGIONS: list[tuple[str, str]] = [
    ("US", "미국"), ("JP", "일본"), ("GB", "영국"), ("IN", "인도"),
]

REGION_TITLES = {
    "US": "미국은 지금",
    "JP": "일본은 지금",
    "GB": "영국은 지금",
    "IN": "인도는 지금",
}
