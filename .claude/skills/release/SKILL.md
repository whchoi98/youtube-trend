---
name: release
description: semver와 이중 언어 CHANGELOG로 릴리스를 진행한다. 릴리스, 버전 태깅, CHANGELOG 갱신 요청 시 사용.
---

# Release Skill

검증을 거쳐 릴리스를 만든다. 이 프로젝트는 v0.1.0부터 시작하며 이후 Semantic Versioning을 따른다.

## 절차

### 1. 사전 점검
- 작업 트리가 깨끗한지 확인: `git status`
- 전체 검증 통과 확인 (/test-all 순서와 동일):
  - `cd backend && .venv/bin/pytest tests/ -q` — 120 passed
  - `cd frontend && npx tsc --noEmit && npm run build`
  - `cd infra && npx aws-cdk@2 synth` (반드시 npx aws-cdk@2)
- CHANGELOG.md의 Unreleased 절에 누락된 변경이 없는지 커밋 로그와 대조

### 2. 버전 결정
- 마지막 태그 이후 변경 검토: `git log $(git describe --tags --abbrev=0)..HEAD --oneline` (태그가 없으면 전체 로그 — 첫 릴리스는 v0.1.0)
- semver 규칙:
  - MAJOR: API 계약 파괴 (엔드포인트 제거, `{"error"}` 오류 계약 변경, 응답 스키마 비호환 변경)
  - MINOR: 기능 추가 (새 엔드포인트, 새 카테고리 분석, 새 화면) — 하위 호환
  - PATCH: 버그 수정만
- 인프라 리소스 교체(DynamoDB 테이블, CloudFront 등)를 유발하는 릴리스는 버전과 무관하게 릴리스 노트에 명시한다

### 3. CHANGELOG 갱신 (이중 언어)
CHANGELOG.md는 Keep a Changelog 형식이며 **영어/한국어 이중 언어**다. 한국어 절은 경어체를 쓴다. 이모지는 쓰지 않는다. 날짜는 ISO 8601(YYYY-MM-DD).

```markdown
## [0.2.0] - 2026-08-04

### Added
- Category share chart on the trends page.

### Added (한국어)
- 추이 페이지에 카테고리 점유율 차트를 추가했습니다.
```

- 유형별 그룹: Added / Changed / Fixed / Removed
- 각 항목에 관련 커밋 또는 PR 참조를 포함한다

### 4. 릴리스 생성
- 버전 기록 위치 갱신 (해당 파일이 있는 경우): `frontend/package.json`, `backend/pyproject.toml`
- 릴리스 커밋 후 태그: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
- 릴리스 노트 생성 (CHANGELOG 해당 절 기반, 영/한 병기)
- 원격이 미설정 상태다 — push가 필요하면 사용자에게 원격 설정을 확인한다. 링크 표기가 필요하면 `https://github.com/whchoi98/youtube-trends`를 가정한다

### 5. 요약
- 버전 변화 (이전 → 신규)와 근거 (MAJOR/MINOR/PATCH 판정 이유)
- 핵심 변경 목록
- 다음 단계: 태그 push(원격 설정 시), `./scripts/deploy.sh` 배포, 배포 후 `./scripts/smoke.sh <SiteUrl>`
