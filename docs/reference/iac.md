# Infrastructure as Code / IaC 구현 상세

[![English](https://img.shields.io/badge/Language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/Language-한국어-red)](#korean)

<a id="english"></a>
## English

### 1. Overview
CDK Python app provisioning everything as the single stack `YoutubeTrendsStack`: DynamoDB table, ECS Fargate (ARM64) service, ALB with CloudFront-only ingress, and a CloudFront distribution. VPC resolution supports two modes — `existing` (lookup by Name tag) and `new` (self-contained VPC for other users of this repo).

### 2. Components
| Component | Path | Purpose |
|---|---|---|
| CDK entry | `infra/app.py` | Loads repo-root `.env` (`override=True` — file beats shell); reads `VPC_MODE`/`VPC_NAME`/`APP_SECRET_NAME`; region pinned to `ap-northeast-2` |
| VPC resolution | `infra/stacks/network.py` | `resolve_vpc`: `existing` looks up by Name tag (default `cc-on-bedrock-vpc`, reuses NAT); `new` builds 2AZ + 1 NAT + DynamoDB gateway endpoint |
| Main stack | `infra/stacks/service.py` | `YoutubeTrendsStack`: `TrendTable` (pk/sk, TTL `expireAt`, PAY_PER_REQUEST), Fargate ARM64 task (512/1024) with `from_asset` image, ALB + listener rule, CloudFront distribution, outputs `SiteUrl`/`AlbDns`/`TableName`/`ServiceName` |
| ALB ingress | `infra/stacks/service.py` | SG allows only CloudFront origin-facing prefix list `pl-22a6434b`; default listener action is fixed 403; the target rule requires the `X-Origin-Verify` header |
| CloudFront behaviors | `infra/stacks/service.py` | Default behavior CACHING_OPTIMIZED for static assets; `/api/*` CACHING_DISABLED + ALL_VIEWER_EXCEPT_HOST_HEADER + ALLOW_ALL methods |

### 3. Key Decisions
- Always run CDK as `npx aws-cdk@2` — the system-installed cdk is version-incompatible with this app.
- Secret values never enter the template: `scripts/deploy.sh` pushes them to Secrets Manager (`youtube-trends/app`) beforehand and the stack references the secret by name only.
- No Bedrock IAM policy is granted to the task role — Bedrock uses Bearer auth by design (org SCP denies SigV4 InvokeModel in this region).
- `ORIGIN_VERIFY_TOKEN` from `.env` pins the shared-secret header; without it a new token is generated per synth (harmless but churns CloudFront+ALB on each deploy).
- `RemovalPolicy.DESTROY` on the table — capstone scale, teardown convenience over retention.
- Deployment circuit breaker with rollback; `min_healthy_percent=100`, `max_healthy_percent=200`.

### 4. Code Pointers
- `infra/app.py` — entry, env-driven stack parameters
- `infra/stacks/network.py` — `resolve_vpc` two-mode logic
- `infra/stacks/service.py` — full stack definition and outputs
- `scripts/deploy.sh` — the only supported deploy path (`cd infra && npx aws-cdk@2 deploy`)

### 5. Cross-references
- Related modules: `infra/`, `scripts/`
- Related ADRs: none yet
- Related runbooks: none yet
- Related layers: [infrastructure.md](infrastructure.md), [security.md](security.md), [data.md](data.md)

<a id="korean"></a>
## 한국어

### 1. 개요
CDK Python 앱이 단일 스택 `YoutubeTrendsStack`으로 DynamoDB 테이블, ECS Fargate(ARM64) 서비스, CloudFront 전용 인바운드의 ALB, CloudFront 배포를 프로비저닝한다. VPC는 `existing`(Name 태그 조회)과 `new`(이 레포를 쓰는 다른 사용자용 독립 VPC) 2모드를 지원한다.

### 2. 구성요소
| 구성요소 | 경로 | 목적 |
|---|---|---|
| CDK 엔트리 | `infra/app.py` | 저장소 루트 `.env` 로드(`override=True` — 파일이 셸을 이긴다). `VPC_MODE`/`VPC_NAME`/`APP_SECRET_NAME`을 읽고 리전은 `ap-northeast-2` 고정 |
| VPC 해석 | `infra/stacks/network.py` | `resolve_vpc`: `existing`은 Name 태그 조회(기본 `cc-on-bedrock-vpc`, 기존 NAT 재사용), `new`는 2AZ + NAT 1 + DynamoDB 게이트웨이 엔드포인트 구성 |
| 메인 스택 | `infra/stacks/service.py` | `YoutubeTrendsStack`: `TrendTable`(pk/sk, TTL `expireAt`, PAY_PER_REQUEST), Fargate ARM64 태스크(512/1024)와 `from_asset` 이미지, ALB + 리스너 규칙, CloudFront 배포, 출력 `SiteUrl`/`AlbDns`/`TableName`/`ServiceName` |
| ALB 인바운드 | `infra/stacks/service.py` | SG는 CloudFront origin-facing prefix list `pl-22a6434b`만 허용. 리스너 기본 동작은 고정 403, 타깃 규칙은 `X-Origin-Verify` 헤더를 요구한다 |
| CloudFront 동작 | `infra/stacks/service.py` | 기본 동작은 정적 자산용 CACHING_OPTIMIZED, `/api/*`는 CACHING_DISABLED + ALL_VIEWER_EXCEPT_HOST_HEADER + ALLOW_ALL 메서드 |

### 3. 주요 결정
- CDK는 항상 `npx aws-cdk@2`로 실행한다 — 시스템 설치 cdk는 이 앱과 버전이 비호환이다.
- 시크릿 값은 템플릿에 절대 넣지 않는다: `scripts/deploy.sh`가 먼저 Secrets Manager(`youtube-trends/app`)에 push하고 스택은 이름 참조만 한다.
- 태스크 롤에 Bedrock IAM 정책을 부여하지 않는다 — Bedrock은 설계상 Bearer 인증이다(조직 SCP가 이 리전의 SigV4 InvokeModel을 거부).
- `.env`의 `ORIGIN_VERIFY_TOKEN`으로 공유 비밀 헤더를 고정한다. 없으면 synth마다 새로 생성된다(무해하나 배포마다 CloudFront·ALB가 갱신된다).
- 테이블은 `RemovalPolicy.DESTROY`다 — 캡스톤 규모라 보존보다 정리 편의를 우선한다.
- 배포 서킷브레이커 + 롤백, `min_healthy_percent=100`, `max_healthy_percent=200`.

### 4. 코드 포인터
- `infra/app.py` — 엔트리, 환경 변수 기반 스택 파라미터
- `infra/stacks/network.py` — `resolve_vpc` 2모드 로직
- `infra/stacks/service.py` — 스택 전체 정의와 출력
- `scripts/deploy.sh` — 유일하게 지원되는 배포 경로(`cd infra && npx aws-cdk@2 deploy`)

### 5. 상호 참조
- 관련 모듈: `infra/`, `scripts/`
- 관련 ADR: 아직 없음
- 관련 런북: 아직 없음
- 관련 레이어: [infrastructure.md](infrastructure.md), [security.md](security.md), [data.md](data.md)

Last updated: 2026-08-04
