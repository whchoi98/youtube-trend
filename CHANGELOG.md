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

### Changed
- Replace the three-tab layout with the single-page home; category share and LLM briefing/report panels moved to the bottom of the home page
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

### Changed
- 3탭 레이아웃을 단일 페이지 홈으로 교체, 카테고리 점유율·LLM 브리핑/리포트 패널은 홈 하단으로 이동
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
