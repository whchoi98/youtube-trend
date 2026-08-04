# Infrastructure / 인프라 구현 상세

[![English](https://img.shields.io/badge/Language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/Language-한국어-red)](#korean)

<a id="english"></a>
## English

### 1. Overview
Container runtime and deployment pipeline. A multi-stage Docker build bundles the Vite-built SPA and the FastAPI backend into a single ARM64 image, which runs on ECS Fargate; `scripts/deploy.sh` drives the full path from secret push through CDK deploy to post-deploy smoke checks.

### 2. Components
| Component | Path | Purpose |
|---|---|---|
| Multi-stage Dockerfile | `backend/Dockerfile` | Stage 1 `node:22-slim` builds the frontend; stage 2 `python:3.12-slim` runs uvicorn as non-root user `app` with `STATIC_DIR=/srv/static`. Build context is the repository root |
| Deploy script | `scripts/deploy.sh` | Checks `.env` (exists, not git-tracked), pushes secrets to Secrets Manager, runs test gates (pytest, tsc+build), then `npx aws-cdk@2 deploy` and smoke |
| Smoke script | `scripts/smoke.sh` | Post-deploy status-code checks against `<SiteUrl>`: healthz, SPA index, API contract (400/404), brief status recorded as INFO only |
| App factory and SPA serving | `backend/app/main.py` | `create_app` factory, `/healthz` (no external dependency), static mount plus SPA catch-all with path-traversal guard and `no-cache` on `index.html` |
| Hourly collector scheduling | `backend/app/main.py` | Lifespan starts an APScheduler cron job (`minute=0`, `hourly-collect`); SIGTERM shuts it down with `wait=False` so drain is never blocked |

### 3. Key Decisions
- Single container serves both SPA and API — no separate S3 static hosting, so one deploy unit and one origin.
- ARM64 native build: the build host is aarch64 and CDK passes `platform=None`, avoiding emulation.
- `/healthz` checks process liveness only; DynamoDB outages must not trigger ECS task replacement storms.
- `index.html` is served with `Cache-Control: no-cache` — CloudFront's 24h TTL would otherwise pin a stale index referencing deleted hashed assets after redeploy.
- Container runs as non-root user `app`; uvicorn is started via `--factory` with `dev_app` reading `Settings.from_env()`.

### 4. Code Pointers
- `backend/Dockerfile` — two-stage build; frontend `dist/` is copied to `/srv/static`
- `scripts/deploy.sh` — end-to-end deploy pipeline including verification gates
- `scripts/smoke.sh` — endpoint contract checks (`check` helper, connection failure handled as 000)
- `backend/app/main.py` — `create_app`, lifespan scheduler, SPA catch-all

### 5. Cross-references
- Related modules: `backend/`, `frontend/`, `scripts/`
- Related ADRs: none yet (see `docs/decisions/` when added)
- Related runbooks: none yet — deploy flow lives in `scripts/deploy.sh`
- Related layers: [iac.md](iac.md), [security.md](security.md), [api.md](api.md)

<a id="korean"></a>
## 한국어

### 1. 개요
컨테이너 런타임과 배포 파이프라인 계층이다. Docker 멀티스테이지 빌드로 Vite 빌드 산출물(SPA)과 FastAPI 백엔드를 단일 ARM64 이미지로 묶어 ECS Fargate에서 구동하며, `scripts/deploy.sh`가 시크릿 push부터 CDK 배포·스모크 검증까지 전 과정을 주도한다.

### 2. 구성요소
| 구성요소 | 경로 | 목적 |
|---|---|---|
| 멀티스테이지 Dockerfile | `backend/Dockerfile` | 스테이지 1 `node:22-slim`에서 프론트 빌드, 스테이지 2 `python:3.12-slim`에서 non-root 사용자 `app`으로 uvicorn 실행(`STATIC_DIR=/srv/static`). 빌드 컨텍스트는 저장소 루트다 |
| 배포 스크립트 | `scripts/deploy.sh` | `.env` 검사(존재·비추적) → Secrets Manager push → 검증 게이트(pytest, tsc+build) → `npx aws-cdk@2 deploy` → 스모크 순으로 실행한다 |
| 스모크 스크립트 | `scripts/smoke.sh` | 배포 후 `<SiteUrl>` 대상 상태 코드 검증. healthz, SPA index, API 계약(400/404)을 확인하고 brief는 INFO로만 기록한다 |
| 앱 팩토리·SPA 서빙 | `backend/app/main.py` | `create_app` 팩토리, 외부 의존 없는 `/healthz`, 정적 마운트와 SPA catch-all(경로 traversal 가드, `index.html` no-cache) |
| 시간별 수집 스케줄링 | `backend/app/main.py` | lifespan에서 APScheduler cron(`minute=0`, `hourly-collect`) 기동. SIGTERM 시 `wait=False`로 종료해 drain을 막지 않는다 |

### 3. 주요 결정
- 단일 컨테이너가 SPA와 API를 함께 서빙한다 — 별도 S3 정적 호스팅 없이 배포 단위와 오리진을 하나로 유지한다.
- ARM64 네이티브 빌드: 빌드 호스트가 aarch64이므로 CDK가 `platform=None`으로 에뮬레이션 없이 빌드한다.
- `/healthz`는 프로세스 생존만 확인한다 — DynamoDB 장애가 ECS 태스크 교체 폭풍으로 번지지 않게 한다.
- `index.html`은 `Cache-Control: no-cache`로 서빙한다 — CloudFront 24h TTL이 낡은 index를 붙잡으면 재배포 후 사라진 해시 자산 참조로 사이트가 깨진다.
- 컨테이너는 non-root 사용자 `app`으로 실행하고, uvicorn은 `--factory`로 `dev_app`(`Settings.from_env()`)을 기동한다.

### 4. 코드 포인터
- `backend/Dockerfile` — 2스테이지 빌드, 프론트 `dist/`를 `/srv/static`으로 복사
- `scripts/deploy.sh` — 검증 게이트 포함 end-to-end 배포 파이프라인
- `scripts/smoke.sh` — 엔드포인트 계약 검사(`check` 헬퍼, 연결 실패는 000 처리)
- `backend/app/main.py` — `create_app`, lifespan 스케줄러, SPA catch-all

### 5. 상호 참조
- 관련 모듈: `backend/`, `frontend/`, `scripts/`
- 관련 ADR: 아직 없음 (`docs/decisions/` 추가 시 연결)
- 관련 런북: 아직 없음 — 배포 절차는 `scripts/deploy.sh`에 있다
- 관련 레이어: [iac.md](iac.md), [security.md](security.md), [api.md](api.md)

Last updated: 2026-08-04
