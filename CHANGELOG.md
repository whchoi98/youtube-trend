# Changelog

<a href="#english"><img src="https://img.shields.io/badge/lang-English-blue.svg" alt="English"></a>
<a href="#korean"><img src="https://img.shields.io/badge/lang-한국어-red.svg" alt="Korean"></a>

---

<a id="english"></a>

# English

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Add Trend Radar single-page home: hero for the current #1 video (maxres backdrop, chart tenure), horizontally scrolling strips (Top-10 with big rank numerals, accelerating-now, per-category), computed insight chips, and 60-second auto refresh
- Add `GET /api/home` server-side composition endpoint (hero, insights, rows, tag join) and `POST /api/quiz` deterministic taste-quiz recommendations
- Add batch AI tagging pipeline (one Bedrock call per collection bucket, idempotent, silently skipped without a token) powering topic/age rows and tag chips
- Add ten selectable UI themes as CSS variable sets with a theme picker modal and localStorage persistence (legacy light/dark values migrated)
- Add video detail modal preserving per-video rank/views history charts; tiles show NEW/rank-delta badges and views-per-hour velocity

- Add video time-series panel with a top selector, restoring the old Trends-tab drill-down flow
- Add Netflix-style content selection: clicking any tile swaps the hero into a billboard (title, category chip, short description, YouTube link) with the video's trend charts right below
- Add per-tile rank chips (top-left) and an unchanged "-" state to the top-right delta badges; collect a 200-character description per video for the hero synopsis
- Add Netflix-style hover preview popover on tiles (portal-based, 350ms delay, precise-pointer only): thumbnail, meta, short description, per-video AI briefing line, and tag chips; the hero billboard shows the AI line too
- Add country rankings (US/JP/GB/IN Top-20), the official YouTube Music "Top 100 Songs South Korea" weekly chart (playlist order = chart rank), and an AWS Korea channel popular-videos row; category collection deepened from Top-10 to Top-20
- Expand YouTube Music to five official charts (weekly songs, daily/weekly music videos, weekly Shorts songs, live performances) with a dedicated sidebar group; move the AWS row to the very bottom
- Add a "trending channels" ranking: contributors to the Top-30 aggregated by summed views and joined with channel statistics (subscribers - null when hidden - and total views) via one channels.list unit per hour
- Add a Netflix-style left sidebar listing every topic (overall, surging, YT Music, AWS, AI topics/ages, categories, countries); selecting one shows its TOP 20 in the big-rank-numeral style
- Rename the "accelerating now" row to a clearer label with an explanatory hint (hourly view growth)
- Add token streaming for AI briefings: `GET /api/brief/stream` relays Bedrock converse-stream deltas over SSE end-to-end (Bearer-only AWS eventstream parser, no boto3), with a live pipeline trace (DynamoDB reads, cache check, prompt build, Bedrock call, cache store) rendered in the panel; truncated streams are never cached

- Add a YouTube Music time-series panel on the trends screen: pick a chart and a song to see hourly rank/views derived from chart snapshots (`GET /api/charts/{chartId}/videos/{videoId}/history`, hours capped at 72)
- Add "first entry today" and "rank climbers" rows plus AI-mood rows (healing / dopamine) in place of the removed age-group rows; sidebar font weight increased

- Add Anthropic and OpenAI channel popular-video rows alongside AWS (channel spotlights generalized in app/spotlights.py, per-channel failure isolation)
- Route YouTube Music content to music.youtube.com: selecting a chart tile switches the hero CTA to "Listen on YouTube Music", and the chart time-series panel gains a listen link (regular videos keep youtube.com)

- Add a 24h / 1-week / 1-month period toggle to both time-series panels; chart series now read per-song points written at collection time (CVID# items), raising the chart history window from 72h to 720h with far cheaper queries
- Embed the NanumSquare webfont (self-hosted woff2, weights 400/700/800, font-display swap) for better Korean readability

### Changed
- Refine the UI toward a more premium look: emoji removed from row titles, insights, sidebar, and buttons in favor of gradient accent bars on headings, sidebar section headers, and a small "AI" text chip
- Replace the three-tab layout with a Netflix-style home, then reintroduce a top menu in the classic tab style: home / video time-series / share·report screens (charts and LLM briefing live on their own screens)
- Rename the top logo/title to YOUTUBE TREND MONITOR; the video detail modal is superseded by hero selection

## [0.1.0] - 2026-08-04

### Added
- Add hourly YouTube KR trending collection (overall Top-30 plus Top-10 for 8 categories) into DynamoDB with TTL cleanup
- Add read APIs for trending lists, fixed categories, per-video history, and per-category share/entered-exited time series
- Add React SPA with three tabs: overall Top-30 with rank delta badges, category filter view, and trend charts
- Add LLM briefing (`now`/`daily`) and 48-hour trend report endpoints backed by Bedrock Claude with hourly response cache
- Add AWS CDK stack `YoutubeTrendsStack` (CloudFront, ALB, ECS Fargate ARM64, DynamoDB, Secrets Manager) with existing/new VPC modes
- Add one-command deploy pipeline `scripts/deploy.sh` (secret push, test gates, CDK deploy) with post-deploy smoke test `scripts/smoke.sh`

### Fixed
- Fix SPA fallback to serve files only from the static directory, blocking path traversal
- Fix SPA `index.html` to be served with no-cache headers so redeployed frontends are picked up immediately
- Fix race between overlapping API responses with sequence-token guards so late responses cannot overwrite newer UI state

### Security
- Keep secret values out of process argv and command output during deployment
- Restrict ALB ingress to the CloudFront origin-facing managed prefix list and verify a fixed `X-Origin-Verify` header as a second layer

[Unreleased]: https://github.com/whchoi98/youtube-trends/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/whchoi98/youtube-trends/releases/tag/v0.1.0

---

<a id="korean"></a>

# 한국어

이 프로젝트의 모든 주요 변경 사항은 이 파일에 기록됩니다.
이 문서는 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)를 기반으로 하며,
[Semantic Versioning](https://semver.org/spec/v2.0.0.html)을 따릅니다.

## [Unreleased]

### Added
- Trend Radar 단일 페이지 홈 추가: 현재 1위 영상 히어로(maxres 배경, 차트인 시간), 가로 스크롤 스트립(큰 순위 숫자 Top-10, 지금 가속 중, 분야별), 계산형 인사이트 칩, 60초 자동 새로고침
- 서버 조합 엔드포인트 `GET /api/home`(히어로·인사이트·행 구성·태그 조인)과 결정적 취향 퀴즈 추천 `POST /api/quiz` 추가
- 배치 AI 태깅 파이프라인 추가(수집 버킷당 Bedrock 1콜, 멱등, 토큰 부재 시 조용히 생략) — 주제/연령 행과 태그 칩 제공
- CSS 변수 세트 기반 UI 테마 10종과 테마 선택 모달, localStorage 유지 추가(기존 light/dark 값 마이그레이션)
- 영상 상세 모달 추가(영상별 순위/조회수 히스토리 차트 보존), 타일에 NEW/순위 델타 배지와 시간당 조회 속도 표시

- 상단 셀렉터로 영상을 골라 추이를 보는 영상 시계열 패널 추가(구 추이 분석 탭 방식 복원)
- 넷플릭스식 콘텐츠 선택 추가: 타일 클릭 시 히어로가 해당 콘텐츠의 빌보드(제목·카테고리 칩·간단한 소개·YouTube 링크)로 전환되고 바로 아래에 추이 차트 표시
- 타일 좌측 상단 순위 칩과 우측 상단 델타 배지의 유지("-") 상태 추가, 히어로 소개문용 영상 설명(200자) 수집 추가
- 타일에 넷플릭스식 hover 미리보기 팝오버 추가(포털 기반, 350ms 지연, 정밀 포인터 전용): 썸네일·메타·간단한 소개·영상별 AI 브리핑 한 줄·태그 칩, 히어로 빌보드에도 AI 분석 표시
- 국가별 랭킹(미·일·영·인 Top-20), YouTube Music 공식 주간 차트 "Top 100 Songs South Korea"(재생목록 순서 = 차트 순위), AWS Korea 채널 인기 영상 행 추가, 분야별 수집을 Top-10에서 Top-20으로 확대
- YouTube Music을 공식 차트 5종(주간 인기곡, 일간/주간 뮤직비디오, 주간 Shorts 인기곡, 라이브 퍼포먼스)으로 확장하고 사이드바 전용 그룹 신설, AWS 행은 맨 하단으로 이동
- "지금 뜨는 채널" 랭킹 추가: Top-30 기여 채널을 합산 조회수로 집계하고 채널 통계(구독자 — 비공개는 null — 및 총조회수)를 시간당 channels.list 1유닛으로 결합
- 넷플릭스식 좌측 사이드바 추가(전체·급증·YT Music·AWS·AI 주제/연령·분야·국가) — 주제 선택 시 큰 순위 숫자 스타일의 TOP 20 뷰 표시
- "지금 가속 중" 행을 더 읽기 쉬운 이름("조회수 급증 중")과 설명 힌트(시간당 증가 기준)로 변경
- AI 브리핑 토큰 스트리밍 추가: `GET /api/brief/stream`이 Bedrock converse-stream 델타를 SSE로 전 구간 중계(Bearer 전용 AWS eventstream 파서, boto3 미사용), 파이프라인 트레이스(DynamoDB 조회·캐시 확인·프롬프트 구성·Bedrock 호출·캐시 저장)를 패널에 실시간 표시, 절단된 스트림은 캐시하지 않음

- 추이 화면에 YouTube Music 시계열 패널 추가: 차트·곡을 골라 차트 스냅샷에서 파생한 시간별 순위/조회수 확인(`GET /api/charts/{chartId}/videos/{videoId}/history`, hours 상한 72)
- 연령대 행을 제거하고 "오늘 첫 진입"·"순위 역주행" 행과 AI 무드 행(힐링/도파민)으로 대체, 사이드바 폰트 굵기 강화

- AWS 외 Anthropic·OpenAI 채널 인기 영상 행 추가(채널 스포트라이트를 app/spotlights.py로 일반화, 채널별 실패 격리)
- YouTube Music 콘텐츠는 music.youtube.com으로 연결: 차트 타일 선택 시 히어로 버튼이 "YouTube Music에서 듣기"로 전환, 차트 시계열 패널에 듣기 링크 추가(일반 영상은 youtube.com 유지)

- 두 시계열 패널에 24시간/일주일/한 달 기간 토글 추가, 차트 시계열은 수집 시 적재하는 곡별 포인트(CVID#)를 읽도록 전환해 조회 창을 72시간→720시간으로 확장(쿼리 비용도 대폭 절감)
- 나눔스퀘어 웹폰트 임베딩(자체 호스팅 woff2, 400/700/800, font-display swap)으로 한글 가독성 개선

### Changed
- UI 고급화: 행 제목·인사이트·사이드바·버튼의 이모지를 제거하고 제목 그라디언트 액센트 바, 사이드바 섹션 헤더, "AI" 텍스트 칩으로 대체
- 3탭 레이아웃을 넷플릭스형 홈으로 교체한 뒤, 기존 탭 스타일의 상단 메뉴를 재도입: 홈 / 시계열 추이 / 점유율·리포트 화면 분리(차트·LLM 브리핑은 각자 화면에서 표시)
- 상단 로고/타이틀을 YOUTUBE TREND MONITOR로 변경, 영상 상세 모달은 히어로 선택 방식으로 대체

## [0.1.0] - 2026-08-04

### Added
- YouTube KR 인기 급상승 시간별 수집(전체 Top-30 + 8개 카테고리별 Top-10, DynamoDB 저장·TTL 자동 정리) 추가
- 조회 API(트렌딩 목록, 고정 카테고리, 영상별 히스토리, 카테고리별 점유율·진입/이탈 시계열) 추가
- React SPA 3탭(순위 델타 배지를 포함한 전체 Top-30, 카테고리 필터 뷰, 트렌드 차트) 추가
- Bedrock Claude 기반 LLM 브리핑(`now`/`daily`)·48시간 트렌드 리포트 엔드포인트와 시간 단위 응답 캐시 추가
- AWS CDK 스택 `YoutubeTrendsStack`(CloudFront, ALB, ECS Fargate ARM64, DynamoDB, Secrets Manager)과 existing/new VPC 모드 추가
- 원커맨드 배포 파이프라인 `scripts/deploy.sh`(시크릿 push, 테스트 게이트, CDK 배포)와 배포 후 스모크 테스트 `scripts/smoke.sh` 추가

### Fixed
- SPA 폴백이 정적 디렉토리 안의 파일만 서빙하도록 제한해 path traversal 봉쇄
- SPA `index.html`을 no-cache 헤더로 서빙해 재배포된 프론트엔드가 즉시 반영되도록 수정
- 겹치는 API 응답 간 레이스를 시퀀스 토큰 가드로 차단해 늦게 도착한 응답이 최신 UI 상태를 덮어쓰지 못하도록 수정

### Security
- 배포 과정에서 시크릿 값이 프로세스 argv와 명령 출력에 노출되지 않도록 처리
- ALB 인바운드를 CloudFront origin-facing 관리형 prefix list로 제한하고 2차 방어로 고정 `X-Origin-Verify` 헤더 검증 적용

[Unreleased]: https://github.com/whchoi98/youtube-trends/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/whchoi98/youtube-trends/releases/tag/v0.1.0
