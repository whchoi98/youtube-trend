---
name: sync-docs
description: 코드 현재 상태에 맞춰 프로젝트 문서를 동기화한다. 문서 동기화, 문서 갱신, CLAUDE.md 갱신 요청 시 사용. 코드→문서 연동표를 기준으로 갱신 대상을 결정한다.
---

# Sync Docs Skill

프로젝트 문서를 코드의 현재 상태와 동기화한다.

## 코드 → 문서 연동표

변경된 코드 영역을 기준으로 갱신할 문서를 결정한다. 시작 전에 `ls docs/ docs/reference/ docs/runbooks/`로 실제 문서 구성을 확인하고, 표의 대상 문서가 없으면 생성 여부를 사용자에게 확인한다.

| 코드 변경 | 갱신 대상 문서 |
|---|---|
| backend API 라우트·응답 스키마·오류 계약 (`/api/trending`, `/api/categories`, `/api/videos/{id}/history`, `/api/trends/categories`, `/api/brief`, `/api/trends/report`, `/healthz`) | `docs/api-reference.md` + `README.md` (영/한 두 절 모두) |
| infra 스택 변경 (YoutubeTrendsStack, VPC existing/new 모드, ECS/ALB/CloudFront, DynamoDB, prefix SG·X-Origin-Verify) | `docs/architecture.md` + `docs/reference/iac.md` |
| backend 수집·캐시·Bedrock 연동 로직 (DynamoDB pk/sk·TTL, LLM 브리핑/리포트) | `docs/reference/backend.md`(있으면) + `docs/architecture.md`의 데이터 흐름 절 |
| frontend 화면·차트 구성 (Top30/Top10, 시계열 차트, 마크다운 렌더) | `docs/reference/frontend.md`(있으면) + `README.md` 기능 절 |
| `scripts/deploy.sh`·`scripts/smoke.sh`·`.env` 키 구성 (YT_API_KEY, AWS_BEARER_TOKEN_BEDROCK, ORIGIN_VERIFY_TOKEN, VPC_MODE 등 키 이름만 — 값 금지) | `README.md` 배포 절 + `docs/runbooks/` 배포 런북(있으면) |
| 빌드·테스트 명령 변화 (pytest, tsc+build, npx aws-cdk@2 synth) | 루트 `CLAUDE.md` 핵심 명령 절 |

## 문서 문체 규칙 (모든 갱신에 적용)

- 내부 문서(docs/, CLAUDE.md): 한국어 평서형(-다)
- README.md, CHANGELOG.md: 영/한 이중 언어, 한국어 절은 경어체
- 이모지 금지, 코드 블록에 언어 태그, 날짜는 ISO 8601
- 시크릿 값은 어떤 문서에도 절대 기록하지 않는다 (키 이름과 용도만 기술)

## 작업 순서

### 1. 품질 평가
각 CLAUDE.md를 0-100으로 채점한다:
- 명령/워크플로 (20점), 아키텍처 명료성 (20점), 비자명 패턴 (15점), 간결성 (15점), 최신성 (15점), 실행 가능성 (15점)

감점 항목: 500줄 초과 (-15), 모호한 지시 (-10), 문서 중복 (-10), 테스트 지침 부재 (-10), 시크릿 포함 (-20, 즉시 제거)

변경 전에 등급(A-F) 리포트를 출력한다.

### 2. 루트 CLAUDE.md 동기화
- 개요, 스택, 규약, 핵심 명령 갱신
- 명령이 실제로 복사-실행 가능한지 스크립트와 대조한다 (특히 `npx aws-cdk@2` — 시스템 cdk로 바꿔 쓰지 않는다)

### 3. 아키텍처 문서 동기화
- `docs/architecture.md`를 현재 구조에 맞춘다: CloudFront → ALB(prefix SG + X-Origin-Verify) → ECS Fargate ARM64 → DynamoDB/Bedrock 흐름
- 새 컴포넌트 추가, 데이터 흐름 갱신

### 4. 모듈 CLAUDE.md 점검
- `backend/`, `frontend/`, `infra/` 하위 CLAUDE.md 유무와 최신성 확인, 없으면 생성 제안

### 5. ADR·런북 점검
- 최근 커밋에서 문서화되지 않은 아키텍처 결정 확인 (예: Bearer 인증 채택, VPC 2모드)
- 배포/장애 런북 커버리지 확인, 낡은 문서 표시

### 6. README.md 동기화
- 프로젝트 구조 절을 실제 디렉토리와 일치시킨다 — 영/한 두 절을 함께 갱신한다 (한쪽만 고치면 이중 언어 불일치)
- 라이브 URL은 계정 종속·재배포 시 변동임을 문서에 유지한다

### 7. 리포트
변경 전/후 점수, 발견된 안티패턴, 변경 파일 목록을 출력한다.
