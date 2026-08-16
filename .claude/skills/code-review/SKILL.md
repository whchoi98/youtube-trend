---
name: code-review
description: 변경분을 신뢰도 점수 기반으로 리뷰한다. 코드 리뷰, PR 리뷰, 품질 점검 요청 시 사용. backend는 pytest가 받쳐주지만 frontend/infra는 타입 검사뿐이므로 리뷰가 유일한 로직 관문이다.
---

# Code Review Skill

변경된 코드를 신뢰도 점수 기반으로 리뷰해 오탐을 걸러낸다.

## 리뷰 범위

기본은 미스테이징 변경분(`git diff`)이다. 없으면 스테이징 변경분(`git diff --cached`)을 본다. 사용자가 파일이나 범위를 지정하면 그것을 따른다.

## 이 프로젝트의 두 검증 표면 — 리뷰 강도 배분

이 저장소는 표면마다 자동 검증의 깊이가 다르다. 리뷰 강도를 그에 맞춰 배분한다.

| 표면 | 자동 검증 | 리뷰 초점 |
|---|---|---|
| `backend/` (Python 3.12 + FastAPI) | pytest 94개 (`cd backend && .venv/bin/pytest tests/ -q`) | 테스트가 못 잡는 것: API 오류 계약, DynamoDB pk/sk·TTL 설계, YouTube/Bedrock 외부 호출 오류 경로, 캐시 키 설계 |
| `frontend/` (React 18 + Vite + TS) | `npx tsc --noEmit && npm run build` — **타입 검사와 빌드뿐, 단위 테스트 없음** | 런타임 로직 오류는 리뷰가 유일하게 잡는다. recharts 데이터 변환, react-markdown 입력 처리, API 응답 `{"error"}` 분기 처리를 정독한다 |
| `infra/` (CDK Python) | `cd infra && npx aws-cdk@2 synth` — **synth 통과 = 문법 확인일 뿐** | construct 논리 ID 변경(리소스 교체 유발), SG/prefix list(pl-22a6434b)·X-Origin-Verify 헤더 방어 유지, DynamoDB 테이블 교체 여부 |

타입이 통과했다는 사실을 frontend/infra 변경의 정당성 근거로 삼지 않는다.

## API 오류 계약 회귀 확인 (필수 점검)

모든 API 오류 응답은 `{"error": "<한국어 메시지>"}` 본문 + 4xx/5xx 상태 코드다. backend 변경분마다 확인한다.

- 새/수정 라우트의 오류 경로가 이 형태를 유지하는가 (FastAPI 기본 `{"detail": ...}` 노출은 회귀)
- 오류 메시지가 한국어인가
- 422 검증 오류·예외 핸들러를 우회하는 raise가 없는가
- frontend는 `error` 키를 파싱한다 — 키 이름 변경은 즉시 회귀
- LLM 미설정 시 `POST /api/brief`, `POST /api/trends/report`는 503 + 계약 형태여야 한다

## 리뷰 기준

### 프로젝트 규약 준수
- CLAUDE.md의 명명·구조 규약
- 시크릿은 `.env` 단일 공급 — 코드/문서에 시크릿 값 하드코딩은 즉시 CRITICAL
- Bedrock은 Bearer 인증(서울 엔드포인트) — SigV4/IAM 방식 코드 유입은 회귀
- 문서 변경 시: 내부 문서 한국어 평서형, 이모지 금지, 코드 블록 언어 태그

### 버그 탐지
- 로직 오류, None/undefined 처리
- 경쟁 조건, 리소스 누수
- 보안 취약점 (OWASP Top 10, SPA 정적 서빙의 path traversal)
- 성능 문제 (무인증 라우트의 Bedrock 호출 비용 폭주 여지 포함)

### 코드 품질
- 중복과 불필요한 복잡도
- 누락된 핵심 오류 처리
- backend 변경인데 테스트 추가/수정이 없는 경우 (94개 기준선 유지)
- frontend 접근성

## 신뢰도 점수

각 이슈를 0-100으로 채점한다.
- **0-24**: 오탐 또는 기존 이슈일 가능성 높음. 보고하지 않는다.
- **25-49**: 실재할 수 있으나 트집 수준. 보고하지 않는다.
- **50-74**: 실재하나 경미. 치명적일 때만 보고한다.
- **75-89**: 검증된 중요 이슈. 수정안과 함께 보고한다.
- **90-100**: 확인된 치명적 이슈. 반드시 보고한다.

**신뢰도 75 이상만 보고한다.**

## 출력 형식

각 이슈마다:

```text
### [CRITICAL|IMPORTANT] <이슈 제목> (confidence: XX)
**File:** `path/to/file.ext:line`
**Issue:** 문제 설명
**Guideline:** 근거 (CLAUDE.md 규약, API 오류 계약, 보안 표준 등)
**Fix:** 구체적 수정안
```

고신뢰 이슈가 없으면 표면별로 무엇을 확인했는지 요약하고 통과를 알린다.
