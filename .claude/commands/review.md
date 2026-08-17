---
description: git diff 기준 코드 리뷰 — 신뢰도 75 이상만 보고 (code-review 스킬 적용)
allowed-tools: Read, Glob, Grep, Bash(git diff:*), Bash(git log:*), Bash(git status:*), Bash(git branch:*)
---

# Code Review

현재 변경분을 code-review 스킬 기준으로 리뷰한다. 상세 기준은 `.claude/skills/code-review/SKILL.md`를 따른다.

## Step 1: 변경분 확보

- $ARGUMENTS로 파일이 지정되면 해당 파일을 리뷰한다
- 아니면 미스테이징 변경분: `git diff`
- 미스테이징 변경이 없으면 스테이징 변경분: `git diff --cached`

## Step 2: 리뷰

변경 파일마다 code-review 스킬 기준을 적용한다. 특히:

- **두 검증 표면 구분**: `frontend/`(tsc)·`infra/`(synth)는 타입/문법 검사만 받는다 — 런타임 로직을 정독한다. `backend/`는 pytest 131개가 있으므로 테스트가 못 잡는 계약·경계·외부 호출 오류 경로에 집중한다
- **API 오류 계약 회귀**: 모든 오류 응답은 `{"error": "<한국어>"}` + 4xx/5xx — backend 변경마다 확인
- infra 변경이면 construct 논리 ID 변경(리소스 교체) 여부 확인
- 시크릿 값 유입 여부 확인 (발견 시 무조건 CRITICAL, 값은 출력하지 않는다)

## Step 3: 채점과 필터

각 이슈를 0-100으로 채점하고 **75 이상만 보고**한다.

## Step 4: 출력

파일 경로·줄 번호·수정안을 갖춘 구조화 형식으로 제시한다. 고신뢰 이슈가 없으면 표면별 확인 내역을 요약하고 통과를 알린다.

## 오류 복구

### 변경분이 없을 때 (Step 1)
- 이미 커밋됐는지 확인: `git log -1 --oneline` — 커밋분 리뷰는 `/review HEAD~1..HEAD` 등 범위 지정 안내
- 브랜치 확인: `git branch --show-current`
- 파일 직접 지정 안내: `/review backend/app/main.py`

### diff가 500줄을 넘을 때
위험 높은 파일부터 본다:
1. `infra/` (리소스 교체·보안 방어 변경)
2. `backend/` 라우트·캐시·외부 호출
3. `frontend/` 로직 (테스트 부재 표면)
4. 문서 (문체 규칙만 확인)
