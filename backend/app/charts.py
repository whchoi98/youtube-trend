"""YouTube Music 공식 차트 수집 대상.

전부 "YouTube Music Global Charts" 채널(UCrKZcyOJVWnJ60zM1XWllNw)이 운영하는
공개 재생목록이며, 재생목록 순서가 곧 차트 순위다. 재생목록 id가 회전하면
해당 차트만 수집을 건너뛰고 행이 사라진다(안전 강등).

수집 비용: 차트당 쿼터 2유닛/시간(playlistItems + videos).
"""
MUSIC_CHARTS: list[tuple[str, str, str]] = [
    # (scope 접미사, 재생목록 id, 행 제목)
    ("songs", "PL4fGSI1pDJn6jXS_Tv_N9B8Z0HTRVJE0m",
     "YouTube Music · 인기곡 (주간)"),
    ("mv-daily", "PL4fGSI1pDJn6Q7vxp4-2ETPMtSuAPuZ8Y",
     "YouTube Music · 뮤직비디오 (일간)"),
    ("mv-weekly", "PL4fGSI1pDJn5S09aId3dUGp40ygUqmPGc",
     "YouTube Music · 뮤직비디오 (주간)"),
    ("shorts", "PL4fGSI1pDJn4mJcF9T0qw-h-gUobHcNVU",
     "YouTube Music · Shorts 인기곡 (주간)"),
    ("live", "PL4fGSI1pDJn6MANUMcMrfYVsDupx00ya1",
     "YouTube Music · 라이브 퍼포먼스"),
]

CHART_TITLES = {suffix: title for suffix, _pid, title in MUSIC_CHARTS}
