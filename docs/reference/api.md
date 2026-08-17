# API / API 구성 상세

[![English](https://img.shields.io/badge/Language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/Language-한국어-red)](#korean)

<a id="english"></a>
## English

### 1. Overview
FastAPI router layer exposing read endpoints for trending snapshots and time series, a single-call home composition endpoint and a deterministic taste quiz for the Trend Radar page, plus LLM brief/report endpoints — POST for one-shot generation and an SSE streaming GET (`/api/brief/stream`). Every error response follows the single contract `{"error": <Korean message>}` with a 4xx/5xx status — including validation errors, which are remapped from FastAPI's default 422 detail array.

### 2. Components
| Component | Path | Purpose |
|---|---|---|
| App factory / error contract | `backend/app/main.py` | `create_app` factory; `RequestValidationError` handler returns `{"error": "잘못된 요청입니다"}` + 400; router registration; `/healthz`; SPA catch-all keeps unregistered `/api/*` at 404 JSON |
| Dependency providers | `backend/app/api/deps.py` | `get_settings`/`get_store`/`get_yt`/`get_llm` read from `app.state` — tests inject fakes through `create_app(...)` arguments |
| Trending router | `backend/app/api/trending.py` | `GET /api/trending?scope=all|{catId}` (validates against `VALID_SCOPES`, derives badges via baseline), `GET /api/categories` |
| Video history router | `backend/app/api/videos.py` | `GET /api/videos/{id}/history?hours` (default 168, range 1-720) returning `{videoId, points}` |
| Trends router | `backend/app/api/trends.py` | `GET /api/trends/categories?hours` (default 48, range 2-96 — capped to stay inside the DynamoDB 1MB Query limit without pagination) |
| Chart history router | `backend/app/api/charts.py` | `GET /api/charts/{chartId}/videos/{videoId}/history?hours` (default 48, range 2-72 — chart snapshots carry the full Top 20 card JSON (~14KB/bucket), so the cap sits below the 96-hour cap for the same 1MB-Query reason) returning `{chartId, videoId, points}` derived from the chart snapshot range — no separate time-series writes; hours where the song is off the chart get `rank`/`views` null (never conflated with measured values); unknown `chartId` -> 400 `{"error": "지원하지 않는 차트입니다"}`; no snapshots -> 200 with empty `points` |
| Brief/report router | `backend/app/api/brief.py` | `POST /api/brief {scope, mode}` and `POST /api/trends/report {scope}`; cache-first generation per hour bucket; `MAX_TOKENS` per kind; Korean error map `ERR`. `GET /api/brief/stream?scope&mode=now\|daily\|trend` — SSE (`text/event-stream`) events `step({label, ms\|null}` pipeline trace`)` → `delta({text})`* → `done({cached, baseline?})`; errors before the stream starts keep the HTTP contract (400 invalid / 409 no snapshot·baseline / 503 `LlmDisabled` / 502 upstream — mapped by an eager first-event pull), and only post-start upstream failure is delivered as an in-band `error({error, code})` event; shares the UTC hour-bucket kind×scope cache with the POST paths (hit → "캐시 히트" step + one full-text `delta` + `done cached:true`) |
| Home/quiz router | `backend/app/api/home.py` | `GET /api/home` returning `{capturedAt, channels, tagged (bucket has AI tags), llmEnabled (Bedrock token configured), insights (LLM-free chips), hero, rows}` composed from stored snapshots — no new collection; hero adds `tenureHours` (consecutive hourly buckets over the last 72h, gaps up to 2h count as consecutive, always >= 1) and `heroThumbnail`; `channels` is the latest `chan-top` ranking (`[...]` or `null` — raw stored items, no derived fields); rows ordered top10 (carries up to 20 cards — the frontend trims the home strip to 10) -> accel -> new ("오늘 첫 진입" — baseline present with `prevRank` null, min `DERIVED_ROW_MIN=2` tiles) -> climb ("순위 역주행" — positive `delta` descending, top 10, min 2) -> chart (the 5 YouTube Music charts in `MUSIC_CHARTS` definition order, each with `chartId`) -> topic (tagged, >= 3 tiles, max 4 rows) -> vibe (2 mood rows from the vibe tag — "힐링이 필요할 때"/"도파민 충전소", >= 3 tiles) -> category (8 rows, with `categoryId`) -> region (US/JP/GB/IN, with `regionCode`) -> spotlight (the `SPOTLIGHTS` channels AWS/Anthropic/OpenAI in definition order at the bottom, each with `spotId`), empty rows omitted (the former age row was removed — age tags remain for popover chips); region/spotlight/chart/channel snapshots surface only here — `/api/trending` scopes stay `all` plus the 8 categories; no snapshot -> 409 `{"error": "표시할 목록이 아직 없습니다"}`. `POST /api/quiz {mood: 힐링\|도파민, time: 낮\|심야, style: 몰입\|가볍게}` returning `{type, items}` (type from the fixed 8-combination `QUIZ_TYPES` map, items = top 10 cards; deterministic, no LLM call); invalid answer -> 400 `{"error": "잘못된 요청입니다"}`, no snapshot -> same 409; pure composition/scoring logic lives in `backend/app/home.py` |

### 3. Key Decisions
- All errors are `{"error": Korean}` + status code; the frontend renders `body.error` directly, so no endpoint may leak FastAPI's detail array.
- Dependencies resolve via `app.state`, guarded in lifespan so injected test doubles are never overwritten by production builders.
- `GET /api/trending` returns a bare array; snapshot-level attributes (such as `degraded`) intentionally stay out of the card contract.
- Missing data is not an error: no snapshot yields `[]`, missing baseline yields cards with null derived fields.
- `channels` items follow the same null-vs-0 contract: a hidden subscriber count ships `subscribers: null` (never 0), which the frontend renders as "구독자 비공개".
- Card objects carry an optional `description` (collector-truncated to 200 chars, whitespace-collapsed) — the home hero uses it as a short synopsis. Snapshots stored before the field was introduced lack it, so `/api/trending` cards and `/api/home` items/hero may omit the field; clients treat it as optional.
- `hours` bounds are enforced with `Query(ge=..., le=...)` so out-of-range input hits the 400 contract, not a 422.
- `GET /api/home` and `POST /api/quiz` deviate from the empty-result convention: without an ALL snapshot they return 409 `{"error": "표시할 목록이 아직 없습니다"}` instead of an empty body.
- The quiz is deterministic and LLM-free: vibe tag match +3, `MOOD_CATS`/`STYLE_CATS` category weights, rank tiebreak `(31-rank)/30`; answers are validated in-router against the fixed vocabularies and reuse the same 400 message as the global validation remap.
- `heroThumbnail` is an assembled `i.ytimg.com` maxresdefault URL, not a stored value, so `videoId` is validated against `^[A-Za-z0-9_-]{5,20}$` and falls back to the stored `thumbnail` on mismatch.
- The streaming endpoint splits errors by phase: before any bytes are streamed, failures return real HTTP statuses (the first Bedrock event is pulled eagerly so 503/502 can still be proper responses); once streaming has begun the status is already 200, so upstream failure becomes an in-band `error` event. In `trend` mode the cache check runs before the 48-hour range query and aggregation (the most expensive work is skipped on a hit), and text whose stream ended without `messageStop` is never cached (`if text and stop`) so a truncated response cannot poison the hour bucket; client disconnect cancels the async generator and a `finally` closes the Bedrock stream.

### 4. Code Pointers
- `backend/app/main.py` — `create_app`, validation-error remap, router wiring
- `backend/app/api/trending.py` — `VALID_SCOPES`, baseline-derived response
- `backend/app/api/brief.py` — `_cached_or_generate`, `brief_stream` (SSE), `STREAM_MODES`, `MAX_TOKENS`, `ERR`
- `backend/app/api/charts.py` — `VALID_CHART_IDS`, `MAX_HOURS=72`, snapshot-derived chart history
- `backend/app/api/deps.py` — `app.state` dependency providers
- `backend/app/api/home.py` — `ERR_NO_SNAPSHOT`, videoId regex guard, hero/tenure assembly
- `backend/app/home.py` — `build_rows`, `build_insights`, `tenure_hours`, `QUIZ_TYPES`, `quiz_pick`
- `backend/tests/test_api_read.py`, `backend/tests/test_api_brief.py` — endpoint contract specs
- `backend/tests/test_api_home.py`, `backend/tests/test_api_quiz.py` — home/quiz contract specs

### 5. Cross-references
- Related modules: `backend/app/api/`, `frontend/src/api.ts` (client-side contract)
- Related ADRs: [ADR-001-trend-radar-single-page-redesign](../decisions/ADR-001-trend-radar-single-page-redesign.md)
- Related runbooks: none yet
- Related layers: [data.md](data.md), [agent-llm.md](agent-llm.md), [frontend.md](frontend.md)

<a id="korean"></a>
## 한국어

### 1. 개요
급상승 스냅샷·시계열 읽기 엔드포인트, Trend Radar 페이지를 위한 단일 호출 홈 조합 엔드포인트와 결정적 취향 퀴즈, LLM 브리핑/리포트 엔드포인트(단발 생성 POST + SSE 스트리밍 GET `/api/brief/stream`)를 제공하는 FastAPI 라우터 계층이다. 모든 오류 응답은 `{"error": 한국어 메시지}` + 4xx/5xx 단일 계약을 따르며, 검증 오류도 FastAPI 기본 422 detail 배열 대신 이 계약으로 재매핑한다.

### 2. 구성요소
| 구성요소 | 경로 | 목적 |
|---|---|---|
| 앱 팩토리·오류 계약 | `backend/app/main.py` | `create_app` 팩토리. `RequestValidationError` 핸들러가 `{"error": "잘못된 요청입니다"}` + 400 반환. 라우터 등록, `/healthz`, 미등록 `/api/*`를 404 JSON으로 유지하는 SPA catch-all |
| 의존성 공급자 | `backend/app/api/deps.py` | `get_settings`/`get_store`/`get_yt`/`get_llm`이 `app.state`에서 읽는다 — 테스트는 `create_app(...)` 인자로 페이크를 주입한다 |
| 급상승 라우터 | `backend/app/api/trending.py` | `GET /api/trending?scope=all|{catId}`(`VALID_SCOPES` 검증, 기준 스냅샷으로 배지 파생), `GET /api/categories` |
| 영상 이력 라우터 | `backend/app/api/videos.py` | `GET /api/videos/{id}/history?hours`(기본 168, 범위 1~720) — `{videoId, points}` 반환 |
| 추이 라우터 | `backend/app/api/trends.py` | `GET /api/trends/categories?hours`(기본 48, 범위 2~96 — 페이지네이션 없이 DynamoDB 1MB Query 한도 내 안전 마진) |
| 차트 이력 라우터 | `backend/app/api/charts.py` | `GET /api/charts/{chartId}/videos/{videoId}/history?hours`(기본 48, 범위 2~72 — 차트 스냅샷은 Top 20 카드 전체 JSON(버킷당 ~14KB)이라 같은 1MB Query 근거로 96 캡보다 낮게 캡) — `{chartId, videoId, points}` 반환. 별도 시계열 쓰기 없이 차트 스냅샷 범위 조회로 파생하며, 곡이 차트에 없던 시각은 `rank`/`views` null(실측값과 혼용 금지). 잘못된 `chartId` -> 400 `{"error": "지원하지 않는 차트입니다"}`, 스냅샷 없으면 200 + 빈 `points` |
| 브리핑/리포트 라우터 | `backend/app/api/brief.py` | `POST /api/brief {scope, mode}`, `POST /api/trends/report {scope}`. 시간 버킷 단위 캐시 우선 생성, kind별 `MAX_TOKENS`, 한국어 오류 맵 `ERR`. `GET /api/brief/stream?scope&mode=now\|daily\|trend` — SSE(`text/event-stream`) 이벤트 `step({label, ms\|null}` 파이프라인 트레이스`)` → `delta({text})`* → `done({cached, baseline?})`. 스트림 시작 전 오류는 기존 HTTP 계약 그대로(400 잘못된 요청 / 409 스냅샷·기준선 없음 / 503 `LlmDisabled` / 502 상류 — 첫 이벤트를 eager로 당겨 매핑), 시작 후 상류 실패만 in-band `error({error, code})` 이벤트로 전달. UTC 시간 버킷 kind×scope 캐시를 POST 경로와 공유(히트 시 "캐시 히트" step + 전체 텍스트 `delta` 1건 + `done cached:true`) |
| 홈/퀴즈 라우터 | `backend/app/api/home.py` | `GET /api/home` — 저장된 스냅샷만 재조합해(새 수집 없음) `{capturedAt, channels, tagged(버킷 태그 존재 여부), llmEnabled(Bedrock 토큰 설정 여부), insights(LLM 미사용 칩), hero, rows}` 반환. hero에 `tenureHours`(최근 72h 연속 시간 버킷 수, 간격 2h까지 연속 인정, 항상 1 이상)·`heroThumbnail` 추가. `channels`는 최신 `chan-top` 랭킹(`[...]` 또는 `null` — 저장 원본 items, 파생 미적용). rows는 top10(최대 20개 운반 — 홈 스트립 표시는 프론트가 10개로 절단) -> accel -> new("오늘 첫 진입" — baseline 있음 + `prevRank` null, 최소 `DERIVED_ROW_MIN=2`개) -> climb("순위 역주행" — `delta` 양수 내림차순 상위 10, 최소 2개) -> chart(`MUSIC_CHARTS` 정의 순서의 YouTube Music 차트 5행, 각각 `chartId` 포함) -> topic(태그, 3개 이상, 최대 4행) -> vibe(무드 태그 행 2종 — "힐링이 필요할 때"/"도파민 충전소", 3개 이상) -> category(8행, `categoryId` 포함) -> region(미/일/영/인, `regionCode` 포함) -> spotlight(`SPOTLIGHTS` 채널 3행 — AWS/Anthropic/OpenAI 정의 순서, 맨 하단, 각각 `spotId` 포함) 순서이고 빈 행은 생략(기존 age 행은 삭제 — age 태그 자체는 팝오버 칩용으로 유지). 국가/스포트라이트/차트/채널 스냅샷은 여기서만 노출된다 — `/api/trending` 스코프는 `all` + 8분야 유지. 스냅샷 없음 -> 409 `{"error": "표시할 목록이 아직 없습니다"}`. `POST /api/quiz {mood: 힐링\|도파민, time: 낮\|심야, style: 몰입\|가볍게}` — `{type, items}` 반환(type은 8조합 고정 `QUIZ_TYPES` 매핑, items는 상위 10 카드 — 결정적, LLM 미호출). 허용 밖 답변 -> 400 `{"error": "잘못된 요청입니다"}`, 스냅샷 없음 -> 동일 409. 순수 조합/점수 로직은 `backend/app/home.py` |

### 3. 주요 결정
- 모든 오류는 `{"error": 한국어}` + 상태 코드다. 프론트가 `body.error`를 그대로 렌더하므로 어떤 엔드포인트도 FastAPI detail 배열을 노출하면 안 된다.
- 의존성은 `app.state`로 해석하고 lifespan에서 개별 가드한다 — 테스트가 주입한 더블을 프로덕션 빌더가 덮어쓰지 않는다.
- `GET /api/trending`은 순수 배열을 반환한다. 스냅샷 속성(`degraded` 등)은 의도적으로 카드 계약에서 제외한다.
- 데이터 부재는 오류가 아니다: 스냅샷 없음 → `[]`, 기준 스냅샷 없음 → 파생 필드 null 카드.
- `channels` 항목도 동일한 null vs 0 계약을 따른다: 구독자 수 비공개는 `subscribers: null`이며(절대 0 아님), 프론트는 "구독자 비공개"로 표기한다.
- 카드 객체는 선택적 `description` 필드(수집기가 공백 정리 후 200자로 절단)를 싣는다 — 홈 히어로가 간단한 소개문으로 쓴다. 도입 이전에 저장된 스냅샷에는 없으므로 `/api/trending` 카드와 `/api/home`의 items/hero에서 빠질 수 있고, 클라이언트는 optional로 취급한다.
- `hours` 범위는 `Query(ge=..., le=...)`로 강제한다 — 범위 밖 입력은 422가 아니라 400 계약에 걸린다.
- `GET /api/home`·`POST /api/quiz`는 빈 응답 규칙에서 벗어난다: ALL 스냅샷이 없으면 빈 본문 대신 409 `{"error": "표시할 목록이 아직 없습니다"}`를 반환한다.
- 퀴즈 추천은 결정적이며 LLM을 호출하지 않는다: 태그 vibe 일치 +3, `MOOD_CATS`/`STYLE_CATS` 분야 가중치, 순위 타이브레이크 `(31-rank)/30`. 답변은 라우터에서 고정 어휘로 검증하며 전역 검증 재매핑과 동일한 400 메시지를 쓴다.
- `heroThumbnail`은 저장값이 아니라 조립한 `i.ytimg.com` maxresdefault URL이다 — `videoId`를 `^[A-Za-z0-9_-]{5,20}$`로 검증하고 불일치 시 저장된 `thumbnail`로 폴백한다.
- 스트리밍 엔드포인트는 오류를 국면으로 나눈다: 바이트가 흐르기 전 실패는 진짜 HTTP 상태로 돌려주고(첫 Bedrock 이벤트를 eager로 당겨 503/502를 정상 응답으로 매핑), 스트림이 시작되면 상태가 이미 200이므로 상류 실패는 in-band `error` 이벤트가 된다. `trend` 모드는 캐시 확인을 48시간 범위 조회·집계보다 먼저 수행해 히트 시 가장 비싼 작업을 생략하고, `messageStop` 없이 끝난(절단) 텍스트는 캐시하지 않아(`if text and stop`) 시간 버킷 전체가 오염되지 않는다. 클라이언트 disconnect 시 async 제너레이터가 취소되고 `finally`가 Bedrock 스트림을 닫는다.

### 4. 코드 포인터
- `backend/app/main.py` — `create_app`, 검증 오류 재매핑, 라우터 배선
- `backend/app/api/trending.py` — `VALID_SCOPES`, 기준 스냅샷 파생 응답
- `backend/app/api/brief.py` — `_cached_or_generate`, `brief_stream`(SSE), `STREAM_MODES`, `MAX_TOKENS`, `ERR`
- `backend/app/api/charts.py` — `VALID_CHART_IDS`, `MAX_HOURS=72`, 스냅샷 파생 차트 이력
- `backend/app/api/deps.py` — `app.state` 의존성 공급자
- `backend/app/api/home.py` — `ERR_NO_SNAPSHOT`, videoId 정규식 가드, 히어로/tenure 조립
- `backend/app/home.py` — `build_rows`, `build_insights`, `tenure_hours`, `QUIZ_TYPES`, `quiz_pick`
- `backend/tests/test_api_read.py`, `backend/tests/test_api_brief.py` — 엔드포인트 계약 명세
- `backend/tests/test_api_home.py`, `backend/tests/test_api_quiz.py` — 홈/퀴즈 계약 명세

### 5. 상호 참조
- 관련 모듈: `backend/app/api/`, `frontend/src/api.ts`(클라이언트 측 계약)
- 관련 ADR: [ADR-001-trend-radar-single-page-redesign](../decisions/ADR-001-trend-radar-single-page-redesign.md)
- 관련 런북: 아직 없음
- 관련 레이어: [data.md](data.md), [agent-llm.md](agent-llm.md), [frontend.md](frontend.md)

Last updated: 2026-08-17
