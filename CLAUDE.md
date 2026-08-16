# Project Context

## Overview

YouTube Trends — YouTube KR 급상승 동영상을 수집·분석하는 서비스다. Trend Radar 단일 페이지 홈(히어로·가로 스트립 행·인사이트 칩·테마 10종), 전체 Top30/분야별 Top10(8개 카테고리), 가속 행(시간당 조회), AI 태깅 기반 주제·연령 행, 취향 퀴즈 추천, 추이 분석(시계열 차트·카테고리 점유율), LLM 브리핑/추이 리포트(마크다운 렌더)를 제공한다.

라이브: https://d2y73ug3aaah05.cloudfront.net (2026-08-04 배포, 계정 종속 — 재배포 시 URL 변동)

## Tech Stack

- Backend: Python 3.12 + FastAPI (`backend/` — pytest 94개, venv는 `backend/.venv`)
- Frontend: React 18 + Vite + TypeScript (`frontend/` — recharts, react-markdown)
- IaC: AWS CDK Python (`infra/` — 스택 `YoutubeTrendsStack`, VPC existing/new 2모드)
- Container: Docker 멀티스테이지 (`backend/Dockerfile`, 빌드 컨텍스트 = 저장소 루트)
- Data: DynamoDB 단일 테이블 (pk/sk, TTL 30일)
- LLM: Bedrock `global.anthropic.claude-sonnet-4-6` (서울 엔드포인트, Bearer 인증 — SigV4/IAM 금지)
- Runtime: ECS Fargate ARM64 + ALB (prefix SG `pl-22a6434b` + `X-Origin-Verify` 헤더) + CloudFront

## Project Structure

```text
backend/            - FastAPI 앱 + 테스트
  app/api/          - 라우터 (trending, trends, videos, brief, home, deps)
  app/collector/    - YouTube API 수집 (youtube.py, run.py)
  app/llm/          - Bedrock 호출·프롬프트 (bedrock.py, prompts.py)
  app/store/        - DynamoDB 접근 (table.py, keys.py — 키 규칙 단일 정의)
  app/derive.py     - 파생 지표 계산
  app/aggregate.py  - 카테고리 집계
  app/home.py       - 홈 행 구성·인사이트·퀴즈 추천 (순수 로직)
  app/tagging.py    - 수집 후 AI 태깅 파이프라인 (버킷당 Bedrock 1콜, 멱등)
  tests/            - pytest 94개 (moto 기반)
frontend/           - React SPA (로고 YOUTUBE TREND MONITOR — 상단 메뉴 3화면:
                      홈 / 시계열 추이 / 점유율·리포트)
  src/components/   - Hero(선택 빌보드), Row(타일/순위 칩/배지), QuizModal, ThemeModal,
                      SelectedTrend, VideoSeriesPanel, HistoryCharts, TrendsPanel,
                      BriefPanel, InsightChips, Modal
  src/api.ts        - 단일 API 클라이언트
  src/themes.ts     - 테마 10종 정의 (CSS 변수 세트는 styles.css와 동기)
infra/              - CDK Python (app.py, stacks/network.py, stacks/service.py)
scripts/            - deploy.sh, smoke.sh
docs/               - 문서 (reference/ 구현 레퍼런스, decisions/ ADR, runbooks/)
```

## Key Commands

- 백엔드 테스트: `cd backend && .venv/bin/pytest tests/ -q` (94개)
- 프론트 게이트: `cd frontend && npx tsc --noEmit && npm run build`
- 배포: `./scripts/deploy.sh`
- 스모크: `./scripts/smoke.sh <SiteUrl>`
- CDK synth: `cd infra && npx aws-cdk@2 synth` (시스템 cdk는 버전 비호환 — 반드시 `npx aws-cdk@2` 사용)

## API Surface

- `GET /api/home` — 홈 조합: 히어로(1위+차트인 시간)·인사이트 칩·행 구성(top10/accel/topic/age/category)·태그 병합
- `POST /api/quiz {mood, time, style}` — 취향 퀴즈 → 유형명 + 맞춤 추천 카드 (결정적, LLM 미호출)
- `GET /api/trending?scope=all|{catId}` — 전체 Top30 / 카테고리 Top10
- `GET /api/categories` — 카테고리 목록
- `GET /api/videos/{id}/history?hours` — 개별 영상 시계열
- `GET /api/trends/categories?hours` — 카테고리 점유율 추이 (hours 2~96)
- `POST /api/brief {scope, mode}` — LLM 브리핑
- `POST /api/trends/report {scope}` — LLM 추이 리포트
- `GET /healthz` — 헬스체크

## Conventions

- 오류 계약: 모든 오류 응답은 `{"error": "<한국어 메시지>"}` 본문 + 4xx/5xx 상태 코드다. 예외 없음.
- 파생 필드 null vs 0 계약: 계산 불가(예: 비교할 이전 스냅샷 없음)는 `null`, 실측 0은 `0`이다. 둘을 절대 혼용하지 않는다.
- DynamoDB 키 규칙(pk/sk 포맷)은 `backend/app/store/keys.py` 단일 정의다. 다른 파일에서 키 문자열을 직접 조립하지 않는다.
- 시크릿은 `.env` 단일 공급이다: `YT_API_KEY`(필수), `AWS_BEARER_TOKEN_BEDROCK`(선택 — 없으면 LLM 엔드포인트만 503), `ORIGIN_VERIFY_TOKEN`(고정 권장), `VPC_MODE`/`VPC_NAME`/`APP_SECRET_NAME`. `deploy.sh`가 Secrets Manager(`youtube-trends/app`)로 push 하고 스택은 이름 참조만 한다. 시크릿 값은 어떤 파일·로그·출력에도 기록하지 않는다.
- Bedrock 호출은 Bearer 토큰 인증 전용이다. SigV4/IAM 인증 코드를 추가하지 않는다.
- `hours` 파라미터 상한은 96이다 — DynamoDB Query 응답 1MB 한도를 넘지 않기 위한 캡이며, 늘리려면 페이지네이션부터 설계한다.
- 문서 문체: 내부 문서는 한국어 평서형(-다), README/CHANGELOG는 영/한 이중 언어(한국어 절은 경어체), 이모지 금지, 코드 블록에 언어 태그, 날짜는 ISO 8601.

---

## Auto-Sync Rules

Plan mode 종료 후와 주요 코드 변경 시 아래 규칙을 자동 적용한다.

### Post-Plan Mode Actions

Plan mode(`/plan`) 종료 후, 구현 시작 전에:

1. 아키텍처 결정이 있었다면 -> `docs/architecture.md` 갱신
2. 기술 선택/트레이드오프가 있었다면 -> `docs/decisions/ADR-NNN-title.md` 생성
3. 새 모듈이 추가된다면 -> 해당 모듈 디렉토리에 `CLAUDE.md` 생성
4. 운영 절차가 정의됐다면 -> `docs/runbooks/`에 런북 생성
5. 이 파일에 반영할 변화가 있다면 -> 위 관련 섹션 갱신

### Code Change Sync Rules

- `backend/app/`, `frontend/src/`, `infra/` 하위에 새 최상위 모듈 디렉토리 추가 -> 함께 `CLAUDE.md` 생성
- API 엔드포인트 추가/변경 -> 이 파일의 API Surface 섹션과 `backend/CLAUDE.md` 갱신
- DynamoDB 키/스키마 변경 -> `backend/app/store/keys.py`를 먼저 고치고 `backend/CLAUDE.md` 갱신
- 인프라 변경 -> `infra/CLAUDE.md`와 `docs/architecture.md` Infrastructure 섹션 갱신

### ADR Numbering

`docs/decisions/ADR-*.md`에서 최대 번호를 찾아 +1 한다.
형식: `ADR-NNN-concise-title.md`

---

<!-- AUTO-MANAGED:references -->
## Implementation References

구현 상세는 `docs/reference/`의 레이어별 문서를 따른다.

- [infrastructure](docs/reference/infrastructure.md) — ECS Fargate ARM64 + ALB + CloudFront 실행 계층과 배포 토폴로지를 설명한다.
- [data](docs/reference/data.md) — DynamoDB 단일 테이블 설계(pk/sk, TTL 30일)와 스냅샷/시계열 데이터 모델을 설명한다.
- [api](docs/reference/api.md) — FastAPI 엔드포인트 계약, 파라미터 검증, `{"error"}` 오류 규칙을 설명한다.
- [iac](docs/reference/iac.md) — CDK 구성(stacks/network·service), VPC existing/new 2모드, synth/deploy 절차를 설명한다.
- [frontend](docs/reference/frontend.md) — React SPA 구조, `api.ts` 클라이언트, 세대 토큰 레이스 가드 패턴을 설명한다.
- [ui](docs/reference/ui.md) — 3탭 화면 구성, recharts 차트, react-markdown 렌더 규칙을 설명한다.
- [security](docs/reference/security.md) — 시크릿 공급 경로(.env -> Secrets Manager), prefix SG + `X-Origin-Verify` 이중 경계를 설명한다.
- [agent-llm](docs/reference/agent-llm.md) — Bedrock Bearer 호출, 프롬프트 설계, 브리핑/추이 리포트 파이프라인을 설명한다.
<!-- /AUTO-MANAGED:references -->
