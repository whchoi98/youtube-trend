---
description: .env 확인 → ./scripts/deploy.sh 배포 → SiteUrl 확인 → CloudFront 전파 유의 및 스모크
allowed-tools: Read, Glob, Bash(./scripts/deploy.sh:*), Bash(./scripts/smoke.sh:*), Bash(grep -c:*), Bash(grep -q:*), Bash(test:*), Bash(ls:*), Bash(git status:*), Bash(aws cloudformation describe-stacks:*)
---

# Deploy

`./scripts/deploy.sh`로 배포한다. 스크립트가 .env를 Secrets Manager(`youtube-trends/app`)로 push하고, Docker 이미지 빌드(멀티스테이지 — frontend/backend 동시 반영, 빌드 컨텍스트=저장소 루트) 후 CDK 배포까지 수행한다.

## Step 1: .env 확인

시크릿은 `.env` 단일 공급이다. **키 존재만 확인하고 값은 절대 출력·기록하지 않는다** (`grep -c '^KEY=' .env` 방식만 사용, `cat .env` 금지).

| 키 | 필수 여부 | 없을 때 |
|---|---|---|
| `YT_API_KEY` | 필수 | 배포 중단 — 사용자에게 요청 |
| `AWS_BEARER_TOKEN_BEDROCK` | 선택 | 배포 가능하나 LLM 라우트(/api/brief, /api/trends/report)만 503 — 사용자에게 고지 후 진행 여부 확인 |
| `ORIGIN_VERIFY_TOKEN` | 고정 권장 | 미고정 시 재배포마다 값이 바뀔 수 있음 — 고정을 권장 |
| `VPC_MODE` / `VPC_NAME` / `APP_SECRET_NAME` | 선택 | 기본값으로 진행 |

추가 확인:
- `git status`로 의도치 않은 변경분이 이미지에 섞여 나가지 않는지 확인 (이미지 하나에 frontend+backend가 함께 들어간다)
- 배포 전 검증 권장: `/test-all` 통과 후 배포

## Step 2: 배포 실행

```bash
./scripts/deploy.sh
```

- 첫 배포나 인프라 변경 시 CloudFormation(스택 YoutubeTrendsStack) 반영으로 수십 분까지 걸릴 수 있다.
- 출력에 시크릿 값이 나타나면 안 된다 — 나타나는 경우 스크립트 버그로 보고한다.

## Step 3: SiteUrl 확인

- deploy.sh 출력(CloudFormation Outputs)에서 `SiteUrl`을 확인한다.
- 필요 시: `aws cloudformation describe-stacks --stack-name YoutubeTrendsStack --query "Stacks[0].Outputs"`
- **SiteUrl은 계정 종속이고 CloudFront 배포가 교체되면 바뀐다.** 이전 URL(예: https://d2y73ug3aaah05.cloudfront.net)을 그대로 신뢰하지 말고 매번 출력값으로 확인한다.

## Step 4: 재배포 후 유의사항 및 검증

- **CloudFront 전파는 수 분 걸린다.** 배포 직후 이전 프론트 자산이 보이거나 스모크가 실패하면 전파 지연일 수 있다 — 수 분 후 재시도한다.
- 스모크 실행:

```bash
./scripts/smoke.sh <SiteUrl>
```

- 헬스 체크 단건 확인이 필요하면 `GET /healthz`.

## Step 5: 요약

- 배포 대상(스택·리전)과 SiteUrl
- LLM 라우트 활성 여부 (AWS_BEARER_TOKEN_BEDROCK 유무)
- 스모크 결과
- 다음 단계 (전파 대기 중이면 재확인 시점)

## 오류 복구

### deploy.sh 실패
- CloudFormation 이벤트에서 실패 리소스 확인 (롤백은 CloudFormation이 자동 수행)
- ECS 서비스 안정화 실패면 태스크 로그 확인 — 흔한 원인: Secrets Manager 값 누락, `/healthz` 실패, ARM64 이미지 아키텍처 불일치
- VPC existing 모드면 `VPC_NAME` lookup 실패 여부 확인

### 스모크 실패
1. 전파 지연 가능성 — 수 분 후 재시도
2. `GET /healthz` 직접 확인으로 백엔드/CloudFront 어느 쪽 문제인지 분리
3. ALB 직접 접근은 prefix SG(pl-22a6434b)와 X-Origin-Verify 헤더로 차단된다 — CloudFront 경유가 아닌 테스트는 실패가 정상
