---
description: 전체 검증 실행 — backend pytest(92) → frontend tsc+build → infra synth → run-all.sh(있으면) → 라이브 스모크(배포 시)
allowed-tools: Read, Glob, Bash(cd backend && .venv/bin/pytest:*), Bash(cd frontend && npx tsc:*), Bash(cd frontend && npm run build:*), Bash(cd infra && npx aws-cdk@2 synth:*), Bash(tests/run-all.sh:*), Bash(./scripts/smoke.sh:*), Bash(ls:*), Bash(test:*)
---

# Test All

이 저장소의 검증 집합을 아래 순서대로 실행한다. 프레임워크 자동 감지는 하지 않는다 — 명령이 고정돼 있다. 앞 단계가 실패해도 뒤 단계를 계속 실행해 전체 상태를 파악한다 (단, 판정은 기록).

## Step 1: 백엔드 테스트

```bash
cd backend && .venv/bin/pytest tests/ -q
```

- venv는 `backend/.venv` 고정이다. 시스템 pytest를 쓰지 않는다.
- **판정 기준**: `92 passed`, failed/error 0. 수집 개수가 92 미만이면 통과처럼 보여도 수집 오류(import 실패 등)를 의심하고 FAIL로 다룬다.

## Step 2: 프론트엔드 게이트

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- **판정 기준**: 두 명령 모두 exit 0. tsc 오류가 하나라도 있으면 FAIL. 이 표면은 단위 테스트가 없어 이 게이트가 전부다.

## Step 3: 인프라 synth

```bash
cd infra && npx aws-cdk@2 synth
```

- **반드시 `npx aws-cdk@2`** — 시스템 cdk는 버전 비호환으로 실패한다. `cdk synth`로 바꿔 쓰지 않는다.
- **판정 기준**: 템플릿이 출력되고 exit 0. 자격 증명 없이도 synth는 동작해야 한다(VPC existing 모드 lookup 캐시 이슈 시 오류 메시지를 그대로 보고).

## Step 4: 통합 스크립트 (있으면)

```bash
test -x tests/run-all.sh && tests/run-all.sh
```

- `tests/run-all.sh`가 존재할 때만 실행한다. 없으면 SKIP으로 표기하고 넘어간다(실패 아님).

## Step 5: 라이브 스모크 (배포돼 있을 때만)

```bash
./scripts/smoke.sh <SiteUrl>
```

- 배포된 환경이 있을 때만 실행한다. SiteUrl은 CloudFormation 출력 또는 사용자 제공 값을 쓴다 (참고: 2026-08-04 배포분은 https://d2y73ug3aaah05.cloudfront.net — 계정 종속이라 재배포 시 변동).
- 배포 여부를 모르면 사용자에게 확인하고, 미배포면 SKIP.
- **판정 기준**: exit 0. 배포 직후라면 CloudFront 전파 지연으로 실패할 수 있다 — 수 분 후 1회 재시도 후 판정한다.

## Step 6: 리포트

| 단계 | 명령 | 결과 |
|---|---|---|
| backend pytest | ... | PASS / FAIL |
| frontend tsc+build | ... | PASS / FAIL |
| infra synth | ... | PASS / FAIL |
| run-all.sh | ... | PASS / FAIL / SKIP |
| 스모크 | ... | PASS / FAIL / SKIP |

- 전체 판정: FAIL이 하나라도 있으면 FAIL. SKIP은 실패로 치지 않는다.
- 실패 단계는 오류 원문 일부와 원인 추정, 수정 제안을 붙인다.

## 오류 복구

### pytest가 92개보다 적게 수집될 때
```bash
cd backend && .venv/bin/pytest tests/ -q --collect-only | tail -5
```
import 오류로 파일 단위가 통째로 빠졌을 가능성이 크다. 개별 테스트가 아니라 근본 원인(모듈 경로, 의존성)을 고친다.

### 여러 단계가 한꺼번에 실패할 때
구조 변경이 여러 전제를 깨뜨렸을 가능성이 크다:
1. `git log -1` — 마지막 변경 확인
2. `git diff HEAD~1` — 구체적 변경 확인
3. 단계별 개별 대응이 아니라 근본 원인을 고친다
