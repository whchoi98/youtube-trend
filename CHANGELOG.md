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
