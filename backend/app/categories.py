"""고정 8개 분야. id는 YouTube videoCategoryId. 한글명은 기동 시
videoCategories.list(hl=ko)로 갱신을 시도하고 실패하면 이 기본값을 쓴다.
mostPopular 미지원 카테고리는 collect_all이 전체 목록 파생으로 폴백한다."""
CATEGORIES: list[tuple[str, str]] = [
    ("10", "음악"), ("20", "게임"), ("24", "엔터테인먼트"), ("25", "뉴스/정치"),
    ("17", "스포츠"), ("1", "영화/애니메이션"), ("28", "과학기술"), ("23", "코미디"),
]
CATEGORY_NAMES = dict(CATEGORIES)
