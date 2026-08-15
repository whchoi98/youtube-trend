---
name: refactor
description: 동작을 바꾸지 않고 코드 구조를 개선한다. 리팩토링, 코드 정리, 구조 개선 요청 시 사용. 이 저장소 특유의 함정 두 가지(Docker 이미지 동시 반영, CDK 논리 ID 교체)를 반드시 확인한다.
---

# Refactor Skill

동작을 바꾸지 않고 코드 품질을 개선한다.

## 원칙

- 동작 보존이 최우선 — 구조만 바꾼다
- 단일 책임 원칙 (SRP)
- 중복 제거 (DRY)
- 작은 단계로 나누고 매 단계 검증한다

## 이 저장소의 두 가지 함정 (착수 전 필독)

### 함정 1: Docker 이미지 재빌드 = frontend/backend 동시 반영

`backend/Dockerfile`은 멀티스테이지이고 빌드 컨텍스트가 **저장소 루트**다. 이미지 하나에 frontend 빌드 산출물과 backend 코드가 함께 들어간다.

- backend만 리팩토링해도 재배포 시 frontend의 미완성 변경분이 같이 나간다 (역방향도 동일)
- 리팩토링 중 다른 표면에 작업 중 변경이 있는지 `git status`로 먼저 확인하고, 섞이면 안 되는 변경은 커밋/스태시로 분리한 뒤 진행한다
- 파일 이동·이름 변경 시 Dockerfile의 COPY 경로가 루트 기준임을 잊지 않는다

### 함정 2: CDK construct 논리 ID 변경 = 리소스 교체

`infra/`(스택 YoutubeTrendsStack)에서 construct의 ID 문자열이나 트리 상 위치를 바꾸면 CloudFormation 논리 ID가 바뀌고, **리소스가 삭제 후 재생성**된다.

- DynamoDB 테이블 교체 = 수집 데이터(TTL 30일치) 전부 소실
- CloudFront/ALB 교체 = SiteUrl 변경, 서비스 중단
- infra 리팩토링(변수명·클래스 분리 등)은 논리 ID에 영향이 없는지 `npx aws-cdk@2 synth` 결과(또는 `diff`)로 교체 여부를 반드시 확인한다. 시스템 cdk는 버전 비호환 — 반드시 `npx aws-cdk@2`
- 논리 ID 변경이 불가피하면 사용자에게 리소스 교체 사실을 알리고 승인받는다

## 절차

### 1. 분석
- 대상 코드와 그 테스트를 파악한다
- 호출자와 의존 관계를 모두 나열한다
- backend는 pytest 93개가 커버하는지 확인한다. frontend/infra는 **테스트가 없다** — 동작 보존을 기계적으로 증명할 수 없으므로 단계를 더 잘게 나누고, 가능하면 backend 쪽에 계약 테스트를 먼저 추가한다

### 2. 계획
사용자에게 제시한다:
- 무엇이 바뀌는가
- 무엇이 바뀌지 않는가 (동작 보존 범위, API 오류 계약 `{"error"}` 포함)
- 위험도 (low/medium/high) — 위 두 함정에 해당하면 최소 medium

### 3. 실행
- 작고 검증 가능한 단계로 진행한다
- 매 단계 표면별 검증을 돌린다:
  - backend: `cd backend && .venv/bin/pytest tests/ -q` (93 passed 유지)
  - frontend: `cd frontend && npx tsc --noEmit && npm run build`
  - infra: `cd infra && npx aws-cdk@2 synth` + 논리 ID 비교
- 커밋은 원자적으로 유지한다

### 4. 검증
- 전체 테스트 통과 확인
- API 응답 스키마·오류 계약 불변 확인
- 리팩토링 목표 달성 여부 확인
