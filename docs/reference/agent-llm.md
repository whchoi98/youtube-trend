# Agent · LLM / Agent · LLM 구현 상세

[![English](https://img.shields.io/badge/Language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/Language-한국어-red)](#korean)

<a id="english"></a>
## English

### 1. Overview
LLM briefing layer: direct REST calls to the Bedrock Converse API (`global.anthropic.claude-sonnet-4-6`, Seoul endpoint) with Bearer authentication generate the "brief now" / "daily comparison" / "trend report" texts. A missing token degrades gracefully to 503 (`LlmDisabled`) — the rest of the service is unaffected.

### 2. Components
| Component | Path | Purpose |
|---|---|---|
| Bedrock client | `backend/app/llm/bedrock.py` | `BedrockClient.converse(system, user, max_tokens)` — direct httpx POST to `bedrock-runtime.ap-northeast-2` Converse endpoint with `authorization: Bearer`; `MODEL_ID`, `TIMEOUT=25.0`, `LlmDisabled`/`LlmUpstreamError` |
| Prompt builders | `backend/app/llm/prompts.py` | `build_brief` (current list), `build_daily` (entered/exited vs baseline), `build_trend_report` (series + movers); shared `SYSTEM` persona, `clean_text` laundering, `MAX_ITEMS=50`, `TRUNCATION_NOTICE` |
| Brief/report endpoints | `backend/app/api/brief.py` | `POST /api/brief {scope, mode}` and `POST /api/trends/report {scope}`; `_cached_or_generate` checks the hour-bucket report cache first; `MAX_TOKENS = {brief-now: 1200, brief-daily: 600, trend: 1500}`; Korean error map `ERR` (503 disabled, 409 no baseline/snapshot, 5xx upstream) |
| Report cache | `backend/app/store/table.py` | `get_report`/`put_report` keyed `REPORT#{kind}#{scope}` + hour bucket, `REPORT_TTL_DAYS=2`; responses carry `cached: true/false` |

### 3. Key Decisions
- Bearer-only auth against the Converse REST endpoint — no boto3/SigV4, because the org SCP denies InvokeModel in this region and the key is issued outside the org.
- Cache-first per hour bucket: at most one generation per (kind, scope, hour); repeat clicks within the hour are served from DynamoDB with `cached: true`.
- Missing token raises `LlmDisabled` → 503 with a Korean notice; LLM absence never breaks trending/trends endpoints.
- Prompt inputs are laundered (`clean_text`: newline collapse + length caps) even though data comes from our own store — titles/channel names originate from YouTube and are untrusted.
- `stopReason == "max_tokens"` appends `TRUNCATION_NOTICE` so truncated output is visibly marked instead of silently cut.
- Token budgets are per kind (`MAX_TOKENS`), keeping daily comparisons short and trend reports longer.

### 4. Code Pointers
- `backend/app/llm/bedrock.py` — endpoint, auth header, error taxonomy
- `backend/app/llm/prompts.py` — three builders and laundering rules
- `backend/app/api/brief.py` — `_cached_or_generate`, error-to-status mapping
- `backend/tests/test_bedrock.py`, `backend/tests/test_prompts.py`, `backend/tests/test_api_brief.py` — behavior specs

### 5. Cross-references
- Related modules: `backend/app/llm/`, `backend/app/api/`, `frontend/src/components/BriefPanel.tsx` (consumer)
- Related ADRs: none yet
- Related runbooks: none yet
- Related layers: [api.md](api.md), [data.md](data.md) (report cache), [security.md](security.md) (prompt laundering, Bearer decision)

<a id="korean"></a>
## 한국어

### 1. 개요
LLM 브리핑 계층이다. Bedrock Converse API(`global.anthropic.claude-sonnet-4-6`, 서울 엔드포인트)를 Bearer 인증 REST로 직접 호출해 "오늘의 브리핑"/"어제와 비교"/"추이 리포트" 텍스트를 생성한다. 토큰 미설정 시 503(`LlmDisabled`)으로 우아하게 격하되며 나머지 서비스에는 영향이 없다.

### 2. 구성요소
| 구성요소 | 경로 | 목적 |
|---|---|---|
| Bedrock 클라이언트 | `backend/app/llm/bedrock.py` | `BedrockClient.converse(system, user, max_tokens)` — `bedrock-runtime.ap-northeast-2` Converse 엔드포인트에 httpx POST + `authorization: Bearer`. `MODEL_ID`, `TIMEOUT=25.0`, `LlmDisabled`/`LlmUpstreamError` |
| 프롬프트 빌더 | `backend/app/llm/prompts.py` | `build_brief`(현재 목록), `build_daily`(기준 대비 진입/이탈), `build_trend_report`(시계열+무버). 공통 `SYSTEM` 페르소나, `clean_text` 세탁, `MAX_ITEMS=50`, `TRUNCATION_NOTICE` |
| 브리핑/리포트 엔드포인트 | `backend/app/api/brief.py` | `POST /api/brief {scope, mode}`, `POST /api/trends/report {scope}`. `_cached_or_generate`가 시간 버킷 캐시를 먼저 조회. `MAX_TOKENS = {brief-now: 1200, brief-daily: 600, trend: 1500}`, 한국어 오류 맵 `ERR`(503 미설정, 409 기준/스냅샷 없음, 5xx 상류) |
| 리포트 캐시 | `backend/app/store/table.py` | `REPORT#{kind}#{scope}` + 시간 버킷 키의 `get_report`/`put_report`, `REPORT_TTL_DAYS=2`. 응답에 `cached: true/false` 포함 |

### 3. 주요 결정
- Converse REST 엔드포인트에 Bearer 인증 전용으로 호출한다 — 조직 SCP가 이 리전 InvokeModel을 거부하고 키가 조직 밖 발급이므로 boto3/SigV4를 쓰지 않는다.
- 시간 버킷 단위 캐시 우선: (kind, scope, 시각)당 생성은 최대 1회, 같은 시각의 반복 클릭은 DynamoDB에서 `cached: true`로 서빙한다.
- 토큰 미설정은 `LlmDisabled` → 503 + 한국어 안내다. LLM 부재가 trending/trends 엔드포인트를 깨뜨리지 않는다.
- 데이터가 자체 저장소에서 오더라도 프롬프트 입력은 세탁한다(`clean_text`: 개행 제거 + 길이 상한) — 제목·채널명은 YouTube발 비신뢰 문자열이다.
- `stopReason == "max_tokens"`면 `TRUNCATION_NOTICE`를 덧붙여 잘림을 가시화한다 — 조용히 끊긴 출력을 남기지 않는다.
- 토큰 예산은 kind별(`MAX_TOKENS`)로, 일간 비교는 짧게·추이 리포트는 길게 유지한다.

### 4. 코드 포인터
- `backend/app/llm/bedrock.py` — 엔드포인트, 인증 헤더, 오류 분류
- `backend/app/llm/prompts.py` — 빌더 3종과 세탁 규칙
- `backend/app/api/brief.py` — `_cached_or_generate`, 오류→상태 코드 매핑
- `backend/tests/test_bedrock.py`, `backend/tests/test_prompts.py`, `backend/tests/test_api_brief.py` — 동작 명세

### 5. 상호 참조
- 관련 모듈: `backend/app/llm/`, `backend/app/api/`, `frontend/src/components/BriefPanel.tsx`(소비자)
- 관련 ADR: 아직 없음
- 관련 런북: 아직 없음
- 관련 레이어: [api.md](api.md), [data.md](data.md)(리포트 캐시), [security.md](security.md)(프롬프트 세탁, Bearer 결정)

Last updated: 2026-08-04
