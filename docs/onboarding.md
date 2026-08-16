# 개발자 온보딩

신규 개발자가 로컬 개발 환경을 갖추고 첫 배포까지 도달하기 위한 문서다.

## 빠른 시작

### 1. 사전 요건

- [ ] Python 3.12 — 백엔드 실행/테스트 (Docker 런타임 스테이지와 동일 버전)
- [ ] Node.js 22 이상 — 프론트엔드 빌드 (Docker 빌드 스테이지와 동일 버전)
- [ ] Docker — `cdk deploy`가 백엔드 컨테이너 이미지를 로컬에서 빌드한다
- [ ] AWS CLI v2 + `ap-northeast-2` 리전 자격 증명 (배포·로컬 DynamoDB 접근에 필요)
- [ ] YouTube Data API v3 키 — https://console.cloud.google.com 에서 발급
- [ ] (선택) Bedrock Bearer 토큰 — 없으면 LLM 기능만 503으로 비활성화된다

### 2. 셋업

셋업 스크립트가 있으면 그것을 먼저 사용한다(`scripts/setup.sh` 참조). 수동 셋업은 다음과 같다.

```bash
# 백엔드: venv 생성 + 의존성 설치
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
cd ..

# 프론트엔드
cd frontend && npm ci && cd ..

# 인프라 (CDK Python)
cd infra && python3.12 -m pip install -r requirements.txt && cd ..
```

CDK는 시스템에 설치된 `cdk`가 아니라 반드시 `npx aws-cdk@2`로 실행한다. 시스템 `cdk`는 이 프로젝트의 CDK 라이브러리 버전과 호환되지 않는다.

### 3. .env 준비

시크릿은 `.env` 단일 공급이다. 예시 파일을 복사해 작성한다.

```bash
cp .env.example .env
```

| 변수 | 필수 여부 | 설명 |
|------|-----------|------|
| `YT_API_KEY` | 필수 | YouTube Data API v3 키. 비어 있으면 `deploy.sh`가 중단한다 |
| `AWS_BEARER_TOKEN_BEDROCK` | 선택 | 없으면 LLM 엔드포인트만 503 (`{"error": ..., "enabled": false}`) |
| `ORIGIN_VERIFY_TOKEN` | 고정 권장 | 미설정 시 배포마다 재생성되어 CloudFront 전파 동안 403 창이 생긴다 |
| `VPC_MODE` / `VPC_NAME` | 기본값 있음 | `existing`(태그 조회) 또는 `new`(신규 생성) |
| `APP_SECRET_NAME` | 기본값 있음 | Secrets Manager 시크릿 이름 (기본 `youtube-trends/app`) |

`.env`는 절대 git에 커밋하지 않는다. `deploy.sh`가 추적 여부를 검사해 추적 중이면 배포를 거부한다. 시크릿 값은 어떤 파일이나 출력에도 기록하지 않는다.

### 4. 로컬 실행

백엔드는 `dev_app` 팩토리로 실행한다. `TABLE_NAME`이 필수이며, 로컬에서 수집을 돌리지 않으려면 `COLLECT_ENABLED=false`로 끈다(배포된 DynamoDB 테이블을 읽기 전용으로 쓰는 구성).

```bash
# 배포된 테이블 이름 조회 (스택이 이미 배포된 경우)
aws cloudformation describe-stacks --region ap-northeast-2 \
  --stack-name YoutubeTrendsStack \
  --query "Stacks[0].Outputs[?OutputKey=='TableName'].OutputValue" --output text

# 백엔드 (포트 8000)
cd backend
set -a; source ../.env; set +a
TABLE_NAME=<위에서 조회한 테이블> COLLECT_ENABLED=false \
  .venv/bin/uvicorn app.main:dev_app --factory --reload --port 8000
```

```bash
# 프론트엔드 (vite dev server — /api 요청을 localhost:8000으로 프록시)
cd frontend
npm run dev
```

브라우저에서 vite가 안내하는 주소(기본 http://localhost:5173)를 열면 프론트가 로컬 백엔드 API를 사용한다.

### 5. 검증

```bash
# 백엔드 테스트 (94개)
cd backend && .venv/bin/pytest tests/ -q

# 프론트엔드 게이트 (타입 체크 + 빌드)
cd frontend && npx tsc --noEmit && npm run build

# CDK synth (배포 없이 템플릿 생성 확인)
cd infra && npx aws-cdk@2 synth
```

## 프로젝트 개요

- `CLAUDE.md` — 프로젝트 컨텍스트와 규칙
- [docs/architecture.md](architecture.md) — 시스템 설계 (레이어, 다이어그램, 설계 결정)
- [docs/api-reference.md](api-reference.md) — API 엔드포인트 상세
- [docs/decisions/](decisions/) — 아키텍처 결정 기록(ADR)
- [docs/runbooks/](runbooks/) — 운영 절차

핵심 구조는 단일 컨테이너다. FastAPI(`backend/app/`)가 SPA 정적 파일과 `/api`를 함께 서빙하고, 같은 프로세스의 APScheduler가 매시 정각 YouTube 데이터를 수집해 DynamoDB 단일 테이블(pk/sk, TTL 30일)에 쓴다. LLM 브리핑은 Bedrock Converse를 Bearer 토큰으로 직접 호출하며(SigV4/IAM 금지) 시간 버킷 단위로 캐시된다.

## 개발 워크플로

- 브랜치 네이밍: `feat/`, `fix/`, `docs/`, `refactor/`
- 커밋 규약: Conventional Commits
- 머지 전 게이트: 백엔드 pytest 94개 전체 통과 + 프론트 `tsc --noEmit && npm run build` 통과

## 배포

```bash
./scripts/deploy.sh
```

`deploy.sh`는 다음을 순서대로 수행한다: `.env` 존재·비추적 검사 → Secrets Manager(`youtube-trends/app`)에 시크릿 push → 백엔드 테스트 + 프론트 게이트 → `npx aws-cdk@2 deploy YoutubeTrendsStack` → `./scripts/smoke.sh <SiteUrl>` 스모크 테스트.

수동 스모크 테스트는 다음과 같다.

```bash
./scripts/smoke.sh https://<distribution-domain>.cloudfront.net
```

## 핵심 개념

- **시간 버킷(hour bucket)** — 모든 시계열 키는 UTC 시 단위(`TS#YYYY-MM-DDTHH`)다. 수집 cron(minute=0)과 버킷 경계가 정렬되어 계산된 키 하나로 특정 시각 스냅샷을 조회한다.
- **기준 스냅샷(baseline)과 파생 필드** — 순위 변동(delta)·시간당 조회수(viewsPerHour)는 1~4시간 전 스냅샷과 비교해 계산한다. 기준이 없으면 파생 필드는 전부 `null`이다(오류가 아닌 정상 상태).
- **degraded 폴백** — 카테고리별 수집이 실패하면 전체 Top 30에서 해당 카테고리를 파생하고 스냅샷에 `degraded=true`로 표시한다.
- **LLM 캐시** — 브리프/리포트는 (kind, scope, 시간 버킷)당 1회 생성 후 DynamoDB에 캐시된다(TTL 2일). 응답의 `cached` 필드로 구분한다.

## 트러블슈팅

| 증상 | 원인 / 해결 |
|------|-------------|
| `cdk` 실행 시 버전 오류 | 시스템 cdk 버전 비호환 — 항상 `npx aws-cdk@2 <command>`로 실행한다 |
| `deploy.sh`가 ".env가 git에 추적되고 있습니다"로 중단 | `git rm --cached .env` 후 노출된 키를 회전한다 |
| `POST /api/brief`가 503 | `AWS_BEARER_TOKEN_BEDROCK` 미설정 — LLM 기능만 꺼진 정상 상태 |
| `GET /api/trending`이 `[]` | 첫 수집(매시 정각) 전 — 오류가 아니다. 다음 정각까지 대기 |
| 백엔드 기동 시 `KeyError: 'TABLE_NAME'` | `dev_app`은 `TABLE_NAME` 환경변수가 필수다 — 로컬 실행 절 참조 |
| 배포 직후 사이트 403 | `ORIGIN_VERIFY_TOKEN` 미고정 시 CloudFront 전파(수 분) 동안 발생 — 토큰을 `.env`에 고정한다 |

## 참고 자료

- 라이브 사이트: https://d2y73ug3aaah05.cloudfront.net (계정 종속 — 재배포 시 변동)
- 저장소: https://github.com/whchoi98/youtube-trends
- YouTube Data API v3: https://developers.google.com/youtube/v3
- Bedrock Converse API: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html
