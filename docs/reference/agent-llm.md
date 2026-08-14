# Agent · LLM / Agent · LLM 구현 상세

[![English](https://img.shields.io/badge/Language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/Language-한국어-red)](#korean)

<a id="english"></a>
## English

### 1. Overview
LLM layer: direct REST calls to the Bedrock Converse API (`global.anthropic.claude-sonnet-4-6`, Seoul endpoint) with Bearer authentication generate the "brief now" / "daily comparison" / "trend report" texts, plus a batch AI tagging pipeline that labels the latest Top30 snapshot with fixed-vocabulary tags in a single call. A missing token degrades gracefully: the interactive endpoints answer 503 (`LlmDisabled`), and tagging silently skips — the rest of the service is unaffected. The quiz endpoint (`POST /api/quiz`) deliberately does NOT call the LLM; it scores deterministically over stored tags.

### 2. Components
| Component | Path | Purpose |
|---|---|---|
| Bedrock client | `backend/app/llm/bedrock.py` | `BedrockClient.converse(system, user, max_tokens)` — direct httpx POST to `bedrock-runtime.ap-northeast-2` Converse endpoint with `authorization: Bearer`; `MODEL_ID`, `TIMEOUT=25.0`, `LlmDisabled`/`LlmUpstreamError` |
| Prompt builders | `backend/app/llm/prompts.py` | `build_brief` (current list), `build_daily` (entered/exited vs baseline), `build_trend_report` (series + movers), `build_tags` (tagging, paired with the JSON-only `TAGS_SYSTEM` persona); shared `SYSTEM` persona, `clean_text` laundering, `MAX_ITEMS=50`, `TRUNCATION_NOTICE`; fixed vocabularies `TOPIC_VOCAB` (8 topics, disjoint from the 8 category names), `AGE_VOCAB` (4), `VIBE_VOCAB` (6, identical to the quiz answer space) |
| Brief/report endpoints | `backend/app/api/brief.py` | `POST /api/brief {scope, mode}` and `POST /api/trends/report {scope}`; `_cached_or_generate` checks the hour-bucket report cache first; `MAX_TOKENS = {brief-now: 1200, brief-daily: 600, trend: 1500}`; Korean error map `ERR` (503 disabled, 409 no baseline/snapshot, 5xx upstream) |
| Tagging pipeline | `backend/app/tagging.py` | `ensure_tags(store, llm, now)` — one Converse call (`TAGS_MAX_TOKENS=2400`) per untagged latest ALL-snapshot bucket; `parse_tags` slices first `{` to last `}` then `json.loads`; `_norm_tags` drops out-of-vocabulary values and unknown videoIds; any failure returns `None` without storing |
| Tagging triggers | `backend/app/main.py` | lifespan scheduler: hourly `_collect_and_tag` (collect then `_tag_quietly`) plus a one-shot `startup-tags` job right after boot |
| Report cache | `backend/app/store/table.py` | `get_report`/`put_report` keyed `REPORT#{kind}#{scope}` + hour bucket, `REPORT_TTL_DAYS=2`; responses carry `cached: true/false` |
| Tag storage | `backend/app/store/table.py` | `get_tags`/`put_tags` keyed `TAGS#ALL` (pk, `keys.tags_pk()`) + `TS#{bucket}` (sk); tags stored as a JSON string, `TAGS_TTL_DAYS=2` |

### 3. Key Decisions
- Bearer-only auth against the Converse REST endpoint — no boto3/SigV4, because the org SCP denies InvokeModel in this region and the key is issued outside the org.
- Cache-first per hour bucket: at most one generation per (kind, scope, hour); repeat clicks within the hour are served from DynamoDB with `cached: true`.
- Missing token raises `LlmDisabled` → 503 with a Korean notice; LLM absence never breaks trending/trends endpoints.
- Prompt inputs are laundered (`clean_text`: newline collapse + length caps) even though data comes from our own store — titles/channel names originate from YouTube and are untrusted.
- `stopReason == "max_tokens"` appends `TRUNCATION_NOTICE` so truncated output is visibly marked instead of silently cut.
- Token budgets are per kind (`MAX_TOKENS`), keeping daily comparisons short and trend reports longer.
- Tagging is constrained to fixed vocabularies and JSON-only output (`TAGS_SYSTEM`): the parser tolerates code fences/prose by slicing the first `{` to the last `}`, and normalization discards anything outside the vocabularies or referencing unknown videoIds — the model can never invent a tag value.
- `ensure_tags` is idempotent per ALL-snapshot hour bucket: if tags already exist it is a no-op, so the hourly job and the startup job overlapping costs at most one LLM call per bucket.
- Tagging degrades silently: `LlmDisabled`, upstream errors, and parse failures all return `None` and store nothing, so the next collection cycle retries — tags are additive metadata and never block the home response.
- The quiz endpoint does NOT call the LLM by design (latency/cost/non-determinism — ADR-001): it scores deterministically from stored tags plus category weights.

### 4. Code Pointers
- `backend/app/llm/bedrock.py` — endpoint, auth header, error taxonomy
- `backend/app/llm/prompts.py` — four builders (brief/daily/trend/tags), vocabularies, laundering rules
- `backend/app/api/brief.py` — `_cached_or_generate`, error-to-status mapping
- `backend/app/tagging.py` — `ensure_tags`, `parse_tags`, `_norm_tags`, `TAGS_MAX_TOKENS`
- `backend/app/main.py` — lifespan jobs `hourly-collect` (`_collect_and_tag`) and `startup-tags`
- `backend/tests/test_bedrock.py`, `backend/tests/test_prompts.py`, `backend/tests/test_api_brief.py`, `backend/tests/test_tagging.py` — behavior specs

### 5. Cross-references
- Related modules: `backend/app/llm/`, `backend/app/api/`, `backend/app/tagging.py`, `frontend/src/components/BriefPanel.tsx` (consumer)
- Related ADRs: [ADR-001](../decisions/ADR-001-trend-radar-single-page-redesign.md) (quiz LLM personalization rejected)
- Related runbooks: none yet
- Related layers: [api.md](api.md), [data.md](data.md) (report cache, tag storage), [security.md](security.md) (prompt laundering, Bearer decision)

<a id="korean"></a>
## 한국어

### 1. 개요
LLM 계층이다. Bedrock Converse API(`global.anthropic.claude-sonnet-4-6`, 서울 엔드포인트)를 Bearer 인증 REST로 직접 호출해 "오늘의 브리핑"/"어제와 비교"/"추이 리포트" 텍스트를 생성하고, 추가로 배치 AI 태깅 파이프라인이 최신 Top30 스냅샷을 고정 어휘 태그로 1콜에 라벨링한다. 토큰 미설정 시 우아하게 격하된다: 대화형 엔드포인트는 503(`LlmDisabled`)을 답하고 태깅은 조용히 건너뛰며, 나머지 서비스에는 영향이 없다. 퀴즈 엔드포인트(`POST /api/quiz`)는 의도적으로 LLM을 호출하지 않는다 — 저장된 태그 위에서 결정적으로 점수를 계산한다.

### 2. 구성요소
| 구성요소 | 경로 | 목적 |
|---|---|---|
| Bedrock 클라이언트 | `backend/app/llm/bedrock.py` | `BedrockClient.converse(system, user, max_tokens)` — `bedrock-runtime.ap-northeast-2` Converse 엔드포인트에 httpx POST + `authorization: Bearer`. `MODEL_ID`, `TIMEOUT=25.0`, `LlmDisabled`/`LlmUpstreamError` |
| 프롬프트 빌더 | `backend/app/llm/prompts.py` | `build_brief`(현재 목록), `build_daily`(기준 대비 진입/이탈), `build_trend_report`(시계열+무버), `build_tags`(태깅 — JSON만 출력하는 `TAGS_SYSTEM` 페르소나와 짝). 공통 `SYSTEM` 페르소나, `clean_text` 세탁, `MAX_ITEMS=50`, `TRUNCATION_NOTICE`. 고정 어휘 `TOPIC_VOCAB`(8개 주제, 8개 분야명과 불겹침), `AGE_VOCAB`(4개), `VIBE_VOCAB`(6개, 퀴즈 답변 공간과 동일) |
| 브리핑/리포트 엔드포인트 | `backend/app/api/brief.py` | `POST /api/brief {scope, mode}`, `POST /api/trends/report {scope}`. `_cached_or_generate`가 시간 버킷 캐시를 먼저 조회. `MAX_TOKENS = {brief-now: 1200, brief-daily: 600, trend: 1500}`, 한국어 오류 맵 `ERR`(503 미설정, 409 기준/스냅샷 없음, 5xx 상류) |
| 태깅 파이프라인 | `backend/app/tagging.py` | `ensure_tags(store, llm, now)` — 태그 없는 최신 ALL 스냅샷 버킷당 Converse 1콜(`TAGS_MAX_TOKENS=2400`). `parse_tags`가 첫 `{`부터 마지막 `}`까지 잘라 `json.loads`, `_norm_tags`가 어휘 밖 값과 모르는 videoId를 제거. 어떤 실패든 저장 없이 `None` 반환 |
| 태깅 트리거 | `backend/app/main.py` | lifespan 스케줄러: 매시 `_collect_and_tag`(수집 후 `_tag_quietly`) + 기동 직후 1회 `startup-tags` 잡 |
| 리포트 캐시 | `backend/app/store/table.py` | `REPORT#{kind}#{scope}` + 시간 버킷 키의 `get_report`/`put_report`, `REPORT_TTL_DAYS=2`. 응답에 `cached: true/false` 포함 |
| 태그 저장 | `backend/app/store/table.py` | pk `TAGS#ALL`(`keys.tags_pk()`) + sk `TS#{bucket}` 키의 `get_tags`/`put_tags`. tags는 JSON 문자열로 저장, `TAGS_TTL_DAYS=2` |

### 3. 주요 결정
- Converse REST 엔드포인트에 Bearer 인증 전용으로 호출한다 — 조직 SCP가 이 리전 InvokeModel을 거부하고 키가 조직 밖 발급이므로 boto3/SigV4를 쓰지 않는다.
- 시간 버킷 단위 캐시 우선: (kind, scope, 시각)당 생성은 최대 1회, 같은 시각의 반복 클릭은 DynamoDB에서 `cached: true`로 서빙한다.
- 토큰 미설정은 `LlmDisabled` → 503 + 한국어 안내다. LLM 부재가 trending/trends 엔드포인트를 깨뜨리지 않는다.
- 데이터가 자체 저장소에서 오더라도 프롬프트 입력은 세탁한다(`clean_text`: 개행 제거 + 길이 상한) — 제목·채널명은 YouTube발 비신뢰 문자열이다.
- `stopReason == "max_tokens"`면 `TRUNCATION_NOTICE`를 덧붙여 잘림을 가시화한다 — 조용히 끊긴 출력을 남기지 않는다.
- 토큰 예산은 kind별(`MAX_TOKENS`)로, 일간 비교는 짧게·추이 리포트는 길게 유지한다.
- 태깅은 고정 어휘와 JSON 전용 출력(`TAGS_SYSTEM`)으로 제약한다: 파서는 첫 `{`부터 마지막 `}`까지 잘라내 코드 펜스/산문을 허용하고, 정규화가 어휘 밖 값이나 모르는 videoId 참조를 전부 버린다 — 모델이 태그 값을 지어낼 수 없다.
- `ensure_tags`는 ALL 스냅샷 시간 버킷 단위로 멱등이다: 태그가 이미 있으면 no-op이므로, 매시 잡과 기동 잡이 겹쳐도 버킷당 LLM 호출은 최대 1회다.
- 태깅은 조용히 격하된다: `LlmDisabled`·상류 오류·파싱 실패 모두 `None`을 반환하고 아무것도 저장하지 않아 다음 수집 사이클에 재시도된다 — 태그는 부가 메타데이터이며 홈 응답을 절대 막지 않는다.
- 퀴즈 엔드포인트는 설계상 LLM을 호출하지 않는다(지연/비용/비결정성 — ADR-001): 저장된 태그와 카테고리 가중치로 결정적으로 점수를 계산한다.

### 4. 코드 포인터
- `backend/app/llm/bedrock.py` — 엔드포인트, 인증 헤더, 오류 분류
- `backend/app/llm/prompts.py` — 빌더 4종(brief/daily/trend/tags), 어휘, 세탁 규칙
- `backend/app/api/brief.py` — `_cached_or_generate`, 오류→상태 코드 매핑
- `backend/app/tagging.py` — `ensure_tags`, `parse_tags`, `_norm_tags`, `TAGS_MAX_TOKENS`
- `backend/app/main.py` — lifespan 잡 `hourly-collect`(`_collect_and_tag`)와 `startup-tags`
- `backend/tests/test_bedrock.py`, `backend/tests/test_prompts.py`, `backend/tests/test_api_brief.py`, `backend/tests/test_tagging.py` — 동작 명세

### 5. 상호 참조
- 관련 모듈: `backend/app/llm/`, `backend/app/api/`, `backend/app/tagging.py`, `frontend/src/components/BriefPanel.tsx`(소비자)
- 관련 ADR: [ADR-001](../decisions/ADR-001-trend-radar-single-page-redesign.md)(퀴즈 LLM 개인화 기각)
- 관련 런북: 아직 없음
- 관련 레이어: [api.md](api.md), [data.md](data.md)(리포트 캐시, 태그 저장), [security.md](security.md)(프롬프트 세탁, Bearer 결정)

Last updated: 2026-08-14
