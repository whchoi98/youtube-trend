# Agent · LLM / Agent · LLM 구현 상세

[![English](https://img.shields.io/badge/Language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/Language-한국어-red)](#korean)

<a id="english"></a>
## English

### 1. Overview
LLM layer: direct REST calls to the Bedrock Converse API (`global.anthropic.claude-sonnet-4-6`, Seoul endpoint) with Bearer authentication generate the "brief now" / "daily comparison" / "trend report" texts, plus a batch AI tagging pipeline that labels the latest Top30 snapshot in a single call with fixed-vocabulary tags and a laundered free-text one-line `comment` analysis. A missing token degrades gracefully: the interactive endpoints answer 503 (`LlmDisabled`), and tagging silently skips — the rest of the service is unaffected. The quiz endpoint (`POST /api/quiz`) deliberately does NOT call the LLM; it scores deterministically over stored tags.

### 2. Components
| Component | Path | Purpose |
|---|---|---|
| Bedrock client | `backend/app/llm/bedrock.py` | `BedrockClient.converse(system, user, max_tokens)` — direct httpx POST to `bedrock-runtime.ap-northeast-2` Converse endpoint with `authorization: Bearer`; `MODEL_ID`, `TIMEOUT=25.0`, `LlmDisabled`/`LlmUpstreamError`. `converse_stream(system, user, max_tokens)` generator — calls the converse-stream REST endpoint with Bearer and parses the AWS eventstream binary frames directly (`_parse_headers`/`_iter_eventstream`, keeping the no-boto3 policy); yields `("delta", str)`* then `("stop", stopReason)`; corrupt frames (headers_len overflow, truncated headers), exception frames, and a stream ending without `messageStop` all raise `LlmUpstreamError` (502) |
| Prompt builders | `backend/app/llm/prompts.py` | `build_brief` (current list), `build_daily` (entered/exited vs baseline), `build_trend_report` (series + movers), `build_tags` (tagging, paired with the JSON-only `TAGS_SYSTEM` persona; alongside the fixed vocabularies it asks for a free-text `comment` — "a one-line analysis of why this video is trending, within 40 chars"); shared `SYSTEM` persona, `clean_text` laundering, `MAX_ITEMS=50`, `TRUNCATION_NOTICE`; fixed vocabularies `TOPIC_VOCAB` (8 topics, disjoint from the 8 category names), `AGE_VOCAB` (4), `VIBE_VOCAB` (6, identical to the quiz answer space) |
| Brief/report endpoints | `backend/app/api/brief.py` | `POST /api/brief {scope, mode}` and `POST /api/trends/report {scope}`; `_cached_or_generate` checks the hour-bucket report cache first; `MAX_TOKENS = {brief-now: 1200, brief-daily: 600, trend: 1500}`; Korean error map `ERR` (503 disabled, 409 no baseline/snapshot, 5xx upstream). `GET /api/brief/stream` streams the same generations over SSE (`step`/`delta`/`done`, in-band `error` after start) and shares the same hour-bucket cache; only complete text (`messageStop` received) is cached |
| Tagging pipeline | `backend/app/tagging.py` | `ensure_tags(store, llm, now)` — one Converse call (`TAGS_MAX_TOKENS=4000`, raised from 2400 for the per-entry token growth from `comment`) per untagged latest ALL-snapshot bucket; `parse_tags` slices first `{` to last `}` then `json.loads`; `_norm_tags` drops out-of-vocabulary values and unknown videoIds, launders `comment` through `prompts.clean_text` (newline removal) truncated to `COMMENT_MAX=80` (non-strings become `None`), and always emits the 4-key shape `{topics, age, vibe, comment}`; any failure returns `None` without storing |
| Tagging triggers | `backend/app/main.py` | lifespan scheduler: hourly `_collect_and_tag` (collect then `_tag_quietly`) plus a one-shot `startup-tags` job right after boot |
| Report cache | `backend/app/store/table.py` | `get_report`/`put_report` keyed `REPORT#{kind}#{scope}` + hour bucket, `REPORT_TTL_DAYS=2`; responses carry `cached: true/false` |
| Tag storage | `backend/app/store/table.py` | `get_tags`/`put_tags` keyed `TAGS#ALL` (pk, `keys.tags_pk()`) + `TS#{bucket}` (sk); tags stored as a JSON string, `TAGS_TTL_DAYS=2` |

### 3. Key Decisions
- Bearer-only auth against the Converse REST endpoint — no boto3/SigV4, because the org SCP denies InvokeModel in this region and the key is issued outside the org.
- Streaming keeps the same policy: `converse_stream` parses the AWS eventstream binary framing by hand instead of pulling in boto3's eventstream codec; a stream that ends without `messageStop` is treated as truncation and raised as `LlmUpstreamError` (502) rather than disguised as a normal completion. The SSE route caches only complete text (`if text and stop`), and client disconnect cancels the generator with a `finally` closing the Bedrock stream so tokens stop being consumed.
- Cache-first per hour bucket: at most one generation per (kind, scope, hour); repeat clicks within the hour are served from DynamoDB with `cached: true`.
- Missing token raises `LlmDisabled` → 503 with a Korean notice; LLM absence never breaks trending/trends endpoints.
- Prompt inputs are laundered (`clean_text`: newline collapse + length caps) even though data comes from our own store — titles/channel names originate from YouTube and are untrusted.
- `stopReason == "max_tokens"` appends `TRUNCATION_NOTICE` so truncated output is visibly marked instead of silently cut.
- Token budgets are per kind (`MAX_TOKENS`), keeping daily comparisons short and trend reports longer.
- Tagging is constrained to fixed vocabularies and JSON-only output (`TAGS_SYSTEM`): the parser tolerates code fences/prose by slicing the first `{` to the last `}`, and normalization discards anything outside the vocabularies or referencing unknown videoIds — the model can never invent a tag value.
- `comment` is the only free-text tag field (a one-line why-is-it-trending analysis, instructed to stay within 40 chars), so it is laundered instead of vocabulary-checked: `_norm_tags` runs it through `prompts.clean_text` and truncates to `COMMENT_MAX=80`, mapping non-strings to `None`. Normalized entries always carry the 4 keys `{topics, age, vibe, comment}`; tags written before the field was introduced lack it, and the frontend treats it as optional.
- `ensure_tags` is idempotent per ALL-snapshot hour bucket: if tags already exist it is a no-op, so the hourly job and the startup job overlapping costs at most one LLM call per bucket.
- Tagging degrades silently: `LlmDisabled`, upstream errors, and parse failures all return `None` and store nothing, so the next collection cycle retries — tags are additive metadata and never block the home response.
- The quiz endpoint does NOT call the LLM by design (latency/cost/non-determinism — ADR-001): it scores deterministically from stored tags plus category weights.

### 4. Code Pointers
- `backend/app/llm/bedrock.py` — endpoint, auth header, error taxonomy, `converse_stream`/`_iter_eventstream`
- `backend/app/llm/prompts.py` — four builders (brief/daily/trend/tags), vocabularies, laundering rules
- `backend/app/api/brief.py` — `_cached_or_generate`, `brief_stream` (SSE), error-to-status mapping
- `backend/app/tagging.py` — `ensure_tags`, `parse_tags`, `_norm_tags`, `TAGS_MAX_TOKENS`
- `backend/app/main.py` — lifespan jobs `hourly-collect` (`_collect_and_tag`) and `startup-tags`
- `backend/tests/test_bedrock.py`, `backend/tests/test_prompts.py`, `backend/tests/test_api_brief.py`, `backend/tests/test_tagging.py` — behavior specs

### 5. Cross-references
- Related modules: `backend/app/llm/`, `backend/app/api/`, `backend/app/tagging.py`, `frontend/src/components/BriefPanel.tsx` (consumer), `frontend/src/components/Row.tsx`/`Hero.tsx` (`tags.comment` consumers)
- Related ADRs: [ADR-001](../decisions/ADR-001-trend-radar-single-page-redesign.md) (quiz LLM personalization rejected)
- Related runbooks: none yet
- Related layers: [api.md](api.md), [data.md](data.md) (report cache, tag storage), [security.md](security.md) (prompt laundering, Bearer decision)

<a id="korean"></a>
## 한국어

### 1. 개요
LLM 계층이다. Bedrock Converse API(`global.anthropic.claude-sonnet-4-6`, 서울 엔드포인트)를 Bearer 인증 REST로 직접 호출해 "오늘의 브리핑"/"어제와 비교"/"추이 리포트" 텍스트를 생성하고, 추가로 배치 AI 태깅 파이프라인이 최신 Top30 스냅샷을 고정 어휘 태그 + 세탁된 자유 텍스트 한 줄 분석 `comment`로 1콜에 라벨링한다. 토큰 미설정 시 우아하게 격하된다: 대화형 엔드포인트는 503(`LlmDisabled`)을 답하고 태깅은 조용히 건너뛰며, 나머지 서비스에는 영향이 없다. 퀴즈 엔드포인트(`POST /api/quiz`)는 의도적으로 LLM을 호출하지 않는다 — 저장된 태그 위에서 결정적으로 점수를 계산한다.

### 2. 구성요소
| 구성요소 | 경로 | 목적 |
|---|---|---|
| Bedrock 클라이언트 | `backend/app/llm/bedrock.py` | `BedrockClient.converse(system, user, max_tokens)` — `bedrock-runtime.ap-northeast-2` Converse 엔드포인트에 httpx POST + `authorization: Bearer`. `MODEL_ID`, `TIMEOUT=25.0`, `LlmDisabled`/`LlmUpstreamError`. `converse_stream(system, user, max_tokens)` 제너레이터 — converse-stream REST를 Bearer로 호출하고 AWS eventstream 바이너리 프레임을 직접 파싱한다(`_parse_headers`/`_iter_eventstream`, boto3 금지 유지). `("delta", 텍스트조각)`* 후 `("stop", stopReason)`을 낸다. 손상 프레임(headers_len 초과·잘린 헤더)·exception 프레임·`messageStop` 미수신은 전부 `LlmUpstreamError`(502) |
| 프롬프트 빌더 | `backend/app/llm/prompts.py` | `build_brief`(현재 목록), `build_daily`(기준 대비 진입/이탈), `build_trend_report`(시계열+무버), `build_tags`(태깅 — JSON만 출력하는 `TAGS_SYSTEM` 페르소나와 짝. 고정 어휘 외에 자유 텍스트 `comment`도 요청한다 — "이 영상이 왜 급상승 중인지 짚는 한 줄 분석, 40자 이내"). 공통 `SYSTEM` 페르소나, `clean_text` 세탁, `MAX_ITEMS=50`, `TRUNCATION_NOTICE`. 고정 어휘 `TOPIC_VOCAB`(8개 주제, 8개 분야명과 불겹침), `AGE_VOCAB`(4개), `VIBE_VOCAB`(6개, 퀴즈 답변 공간과 동일) |
| 브리핑/리포트 엔드포인트 | `backend/app/api/brief.py` | `POST /api/brief {scope, mode}`, `POST /api/trends/report {scope}`. `_cached_or_generate`가 시간 버킷 캐시를 먼저 조회. `MAX_TOKENS = {brief-now: 1200, brief-daily: 600, trend: 1500}`, 한국어 오류 맵 `ERR`(503 미설정, 409 기준/스냅샷 없음, 5xx 상류). `GET /api/brief/stream`은 같은 생성을 SSE로 스트리밍하고(`step`/`delta`/`done`, 시작 후엔 in-band `error`) 같은 시간 버킷 캐시를 공유한다 — 완결 텍스트(`messageStop` 수신)만 캐시한다 |
| 태깅 파이프라인 | `backend/app/tagging.py` | `ensure_tags(store, llm, now)` — 태그 없는 최신 ALL 스냅샷 버킷당 Converse 1콜(`TAGS_MAX_TOKENS=4000` — `comment`로 늘어난 엔트리당 토큰을 반영해 2400에서 상향). `parse_tags`가 첫 `{`부터 마지막 `}`까지 잘라 `json.loads`, `_norm_tags`가 어휘 밖 값과 모르는 videoId를 제거하고 `comment`는 `prompts.clean_text`로 세탁(개행 제거) 후 `COMMENT_MAX=80`자로 절단한다(비문자열은 `None`). 정규화 출력은 항상 `{topics, age, vibe, comment}` 4키다. 어떤 실패든 저장 없이 `None` 반환 |
| 태깅 트리거 | `backend/app/main.py` | lifespan 스케줄러: 매시 `_collect_and_tag`(수집 후 `_tag_quietly`) + 기동 직후 1회 `startup-tags` 잡 |
| 리포트 캐시 | `backend/app/store/table.py` | `REPORT#{kind}#{scope}` + 시간 버킷 키의 `get_report`/`put_report`, `REPORT_TTL_DAYS=2`. 응답에 `cached: true/false` 포함 |
| 태그 저장 | `backend/app/store/table.py` | pk `TAGS#ALL`(`keys.tags_pk()`) + sk `TS#{bucket}` 키의 `get_tags`/`put_tags`. tags는 JSON 문자열로 저장, `TAGS_TTL_DAYS=2` |

### 3. 주요 결정
- Converse REST 엔드포인트에 Bearer 인증 전용으로 호출한다 — 조직 SCP가 이 리전 InvokeModel을 거부하고 키가 조직 밖 발급이므로 boto3/SigV4를 쓰지 않는다.
- 스트리밍도 같은 정책을 지킨다: `converse_stream`은 boto3의 eventstream 코덱을 끌어오는 대신 AWS eventstream 바이너리 프레이밍을 직접 파싱한다. `messageStop` 없이 끝난 스트림은 절단으로 간주해 정상 완료로 위장하지 않고 `LlmUpstreamError`(502)를 던진다. SSE 경로는 완결 텍스트만 캐시하고(`if text and stop`), 클라이언트 disconnect 시 제너레이터가 취소되며 `finally`가 Bedrock 스트림을 닫아 토큰 소비를 멈춘다.
- 시간 버킷 단위 캐시 우선: (kind, scope, 시각)당 생성은 최대 1회, 같은 시각의 반복 클릭은 DynamoDB에서 `cached: true`로 서빙한다.
- 토큰 미설정은 `LlmDisabled` → 503 + 한국어 안내다. LLM 부재가 trending/trends 엔드포인트를 깨뜨리지 않는다.
- 데이터가 자체 저장소에서 오더라도 프롬프트 입력은 세탁한다(`clean_text`: 개행 제거 + 길이 상한) — 제목·채널명은 YouTube발 비신뢰 문자열이다.
- `stopReason == "max_tokens"`면 `TRUNCATION_NOTICE`를 덧붙여 잘림을 가시화한다 — 조용히 끊긴 출력을 남기지 않는다.
- 토큰 예산은 kind별(`MAX_TOKENS`)로, 일간 비교는 짧게·추이 리포트는 길게 유지한다.
- 태깅은 고정 어휘와 JSON 전용 출력(`TAGS_SYSTEM`)으로 제약한다: 파서는 첫 `{`부터 마지막 `}`까지 잘라내 코드 펜스/산문을 허용하고, 정규화가 어휘 밖 값이나 모르는 videoId 참조를 전부 버린다 — 모델이 태그 값을 지어낼 수 없다.
- `comment`는 유일한 자유 텍스트 태그 필드다(왜 급상승 중인지 짚는 한 줄 분석, 40자 이내 지시). 어휘 검증 대신 세탁한다: `_norm_tags`가 `prompts.clean_text`를 거쳐 `COMMENT_MAX=80`자로 절단하고 비문자열은 `None`으로 처리한다. 정규화 엔트리는 항상 `{topics, age, vibe, comment}` 4키를 갖는다. 도입 이전에 쓰인 태그에는 없으며 프론트는 optional로 취급한다.
- `ensure_tags`는 ALL 스냅샷 시간 버킷 단위로 멱등이다: 태그가 이미 있으면 no-op이므로, 매시 잡과 기동 잡이 겹쳐도 버킷당 LLM 호출은 최대 1회다.
- 태깅은 조용히 격하된다: `LlmDisabled`·상류 오류·파싱 실패 모두 `None`을 반환하고 아무것도 저장하지 않아 다음 수집 사이클에 재시도된다 — 태그는 부가 메타데이터이며 홈 응답을 절대 막지 않는다.
- 퀴즈 엔드포인트는 설계상 LLM을 호출하지 않는다(지연/비용/비결정성 — ADR-001): 저장된 태그와 카테고리 가중치로 결정적으로 점수를 계산한다.

### 4. 코드 포인터
- `backend/app/llm/bedrock.py` — 엔드포인트, 인증 헤더, 오류 분류, `converse_stream`/`_iter_eventstream`
- `backend/app/llm/prompts.py` — 빌더 4종(brief/daily/trend/tags), 어휘, 세탁 규칙
- `backend/app/api/brief.py` — `_cached_or_generate`, `brief_stream`(SSE), 오류→상태 코드 매핑
- `backend/app/tagging.py` — `ensure_tags`, `parse_tags`, `_norm_tags`, `TAGS_MAX_TOKENS`
- `backend/app/main.py` — lifespan 잡 `hourly-collect`(`_collect_and_tag`)와 `startup-tags`
- `backend/tests/test_bedrock.py`, `backend/tests/test_prompts.py`, `backend/tests/test_api_brief.py`, `backend/tests/test_tagging.py` — 동작 명세

### 5. 상호 참조
- 관련 모듈: `backend/app/llm/`, `backend/app/api/`, `backend/app/tagging.py`, `frontend/src/components/BriefPanel.tsx`(소비자), `frontend/src/components/Row.tsx`/`Hero.tsx`(`tags.comment` 소비자)
- 관련 ADR: [ADR-001](../decisions/ADR-001-trend-radar-single-page-redesign.md)(퀴즈 LLM 개인화 기각)
- 관련 런북: 아직 없음
- 관련 레이어: [api.md](api.md), [data.md](data.md)(리포트 캐시, 태그 저장), [security.md](security.md)(프롬프트 세탁, Bearer 결정)

Last updated: 2026-08-16
