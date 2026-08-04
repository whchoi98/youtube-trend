# API / API 구성 상세

[![English](https://img.shields.io/badge/Language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/Language-한국어-red)](#korean)

<a id="english"></a>
## English

### 1. Overview
FastAPI router layer exposing read endpoints for trending snapshots and time series, plus POST endpoints for LLM briefs/reports. Every error response follows the single contract `{"error": <Korean message>}` with a 4xx/5xx status — including validation errors, which are remapped from FastAPI's default 422 detail array.

### 2. Components
| Component | Path | Purpose |
|---|---|---|
| App factory / error contract | `backend/app/main.py` | `create_app` factory; `RequestValidationError` handler returns `{"error": "잘못된 요청입니다"}` + 400; router registration; `/healthz`; SPA catch-all keeps unregistered `/api/*` at 404 JSON |
| Dependency providers | `backend/app/api/deps.py` | `get_settings`/`get_store`/`get_yt`/`get_llm` read from `app.state` — tests inject fakes through `create_app(...)` arguments |
| Trending router | `backend/app/api/trending.py` | `GET /api/trending?scope=all|{catId}` (validates against `VALID_SCOPES`, derives badges via baseline), `GET /api/categories` |
| Video history router | `backend/app/api/videos.py` | `GET /api/videos/{id}/history?hours` (default 168, range 1-720) returning `{videoId, points}` |
| Trends router | `backend/app/api/trends.py` | `GET /api/trends/categories?hours` (default 48, range 2-96 — capped to stay inside the DynamoDB 1MB Query limit without pagination) |
| Brief/report router | `backend/app/api/brief.py` | `POST /api/brief {scope, mode}` and `POST /api/trends/report {scope}`; cache-first generation per hour bucket; `MAX_TOKENS` per kind; Korean error map `ERR` |

### 3. Key Decisions
- All errors are `{"error": Korean}` + status code; the frontend renders `body.error` directly, so no endpoint may leak FastAPI's detail array.
- Dependencies resolve via `app.state`, guarded in lifespan so injected test doubles are never overwritten by production builders.
- `GET /api/trending` returns a bare array; snapshot-level attributes (such as `degraded`) intentionally stay out of the card contract.
- Missing data is not an error: no snapshot yields `[]`, missing baseline yields cards with null derived fields.
- `hours` bounds are enforced with `Query(ge=..., le=...)` so out-of-range input hits the 400 contract, not a 422.

### 4. Code Pointers
- `backend/app/main.py` — `create_app`, validation-error remap, router wiring
- `backend/app/api/trending.py` — `VALID_SCOPES`, baseline-derived response
- `backend/app/api/brief.py` — `_cached_or_generate`, `MAX_TOKENS`, `ERR`
- `backend/app/api/deps.py` — `app.state` dependency providers
- `backend/tests/test_api_read.py`, `backend/tests/test_api_brief.py` — endpoint contract specs

### 5. Cross-references
- Related modules: `backend/app/api/`, `frontend/src/api.ts` (client-side contract)
- Related ADRs: none yet
- Related runbooks: none yet
- Related layers: [data.md](data.md), [agent-llm.md](agent-llm.md), [frontend.md](frontend.md)

<a id="korean"></a>
## 한국어

### 1. 개요
급상승 스냅샷·시계열 읽기 엔드포인트와 LLM 브리핑/리포트 POST 엔드포인트를 제공하는 FastAPI 라우터 계층이다. 모든 오류 응답은 `{"error": 한국어 메시지}` + 4xx/5xx 단일 계약을 따르며, 검증 오류도 FastAPI 기본 422 detail 배열 대신 이 계약으로 재매핑한다.

### 2. 구성요소
| 구성요소 | 경로 | 목적 |
|---|---|---|
| 앱 팩토리·오류 계약 | `backend/app/main.py` | `create_app` 팩토리. `RequestValidationError` 핸들러가 `{"error": "잘못된 요청입니다"}` + 400 반환. 라우터 등록, `/healthz`, 미등록 `/api/*`를 404 JSON으로 유지하는 SPA catch-all |
| 의존성 공급자 | `backend/app/api/deps.py` | `get_settings`/`get_store`/`get_yt`/`get_llm`이 `app.state`에서 읽는다 — 테스트는 `create_app(...)` 인자로 페이크를 주입한다 |
| 급상승 라우터 | `backend/app/api/trending.py` | `GET /api/trending?scope=all|{catId}`(`VALID_SCOPES` 검증, 기준 스냅샷으로 배지 파생), `GET /api/categories` |
| 영상 이력 라우터 | `backend/app/api/videos.py` | `GET /api/videos/{id}/history?hours`(기본 168, 범위 1~720) — `{videoId, points}` 반환 |
| 추이 라우터 | `backend/app/api/trends.py` | `GET /api/trends/categories?hours`(기본 48, 범위 2~96 — 페이지네이션 없이 DynamoDB 1MB Query 한도 내 안전 마진) |
| 브리핑/리포트 라우터 | `backend/app/api/brief.py` | `POST /api/brief {scope, mode}`, `POST /api/trends/report {scope}`. 시간 버킷 단위 캐시 우선 생성, kind별 `MAX_TOKENS`, 한국어 오류 맵 `ERR` |

### 3. 주요 결정
- 모든 오류는 `{"error": 한국어}` + 상태 코드다. 프론트가 `body.error`를 그대로 렌더하므로 어떤 엔드포인트도 FastAPI detail 배열을 노출하면 안 된다.
- 의존성은 `app.state`로 해석하고 lifespan에서 개별 가드한다 — 테스트가 주입한 더블을 프로덕션 빌더가 덮어쓰지 않는다.
- `GET /api/trending`은 순수 배열을 반환한다. 스냅샷 속성(`degraded` 등)은 의도적으로 카드 계약에서 제외한다.
- 데이터 부재는 오류가 아니다: 스냅샷 없음 → `[]`, 기준 스냅샷 없음 → 파생 필드 null 카드.
- `hours` 범위는 `Query(ge=..., le=...)`로 강제한다 — 범위 밖 입력은 422가 아니라 400 계약에 걸린다.

### 4. 코드 포인터
- `backend/app/main.py` — `create_app`, 검증 오류 재매핑, 라우터 배선
- `backend/app/api/trending.py` — `VALID_SCOPES`, 기준 스냅샷 파생 응답
- `backend/app/api/brief.py` — `_cached_or_generate`, `MAX_TOKENS`, `ERR`
- `backend/app/api/deps.py` — `app.state` 의존성 공급자
- `backend/tests/test_api_read.py`, `backend/tests/test_api_brief.py` — 엔드포인트 계약 명세

### 5. 상호 참조
- 관련 모듈: `backend/app/api/`, `frontend/src/api.ts`(클라이언트 측 계약)
- 관련 ADR: 아직 없음
- 관련 런북: 아직 없음
- 관련 레이어: [data.md](data.md), [agent-llm.md](agent-llm.md), [frontend.md](frontend.md)

Last updated: 2026-08-04
