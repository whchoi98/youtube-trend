"""채널 스포트라이트 수집 대상 — 공식 채널의 최근 업로드를 조회수 랭킹으로.

scope는 "spot-{suffix}"(pk SNAP#SPOT#{suffix})이고 홈 맨 하단에 정의 순서로
표시된다. 채널당 수집 비용은 쿼터 3유닛/시간(channels+playlistItems+videos —
uploads 재생목록 id는 인스턴스 캐시로 기동 후 1회만 조회).
"""
SPOTLIGHTS: list[tuple[str, str, str]] = [
    # (scope 접미사, 채널 핸들, 행 제목)
    ("aws", "AWSKorea", "AWS 인기 영상"),
    ("anthropic", "anthropic-ai", "Anthropic 인기 영상"),
    ("openai", "OpenAI", "OpenAI 인기 영상"),
]
