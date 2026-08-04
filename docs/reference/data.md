# Data / 데이터 구성 상세

[![English](https://img.shields.io/badge/Language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/Language-한국어-red)](#korean)

<a id="english"></a>
## English

### 1. Overview
Single DynamoDB table (`pk`/`sk`) stores hourly trending snapshots, per-video time series, and LLM report caches, all expired by TTL (snapshots 30 days, reports 2 days). Key rules live in exactly one module so every reader and writer computes identical keys.

### 2. Components
| Component | Path | Purpose |
|---|---|---|
| Key rules (single source) | `backend/app/store/keys.py` | `snap_pk` (`SNAP#ALL` / `SNAP#CAT#{id}`), `vid_pk` (`VID#{videoId}`), `report_pk` (`REPORT#{kind}#{scope}`), `ts_sk` (`TS#YYYY-MM-DDTHH`), `hour_bucket`, `ttl_epoch`; fallback constants `RECENT_OFFSETS`/`DAILY_OFFSETS`/`MIN_AGE_HOURS` |
| Store access layer | `backend/app/store/table.py` | `TrendStore`: `put_snapshot` (conditional write), `latest_snapshot`, `baseline_snapshot` (offset fallback, never raises), `snapshots_range`, `put_video_points`, `video_history`, `get_report`/`put_report`; Decimal-to-int normalization |
| Collection orchestration | `backend/app/collector/run.py` | `collect_all`: overall Top 30 plus per-category Top 10; category failure falls back to derivation from the overall list (`degraded` flag) |
| YouTube client | `backend/app/collector/youtube.py` | YouTube Data API v3 `mostPopular` fetch; injectable `httpx.Client`; string statistics coerced via `_stat_int` (partial-failure isolation) |
| Category catalog | `backend/app/categories.py` | Fixed 8 categories (`videoCategoryId`); Korean names refreshed at startup via `videoCategories.list(hl=ko)` with defaults on failure |
| Derived fields | `backend/app/derive.py` | Pure function `with_derived`: `prevRank`/`delta`/`viewsPerHour` against a baseline snapshot; divides by actual elapsed hours |
| Aggregation | `backend/app/aggregate.py` | Pure function `category_series`: snapshot list to category share / entered / exited time series |

### 3. Key Decisions
- Hour buckets are UTC-hour strings aligned with the collector cron (`minute=0`), so "the snapshot at hour X" is a single computed key lookup — no scan.
- `put_snapshot` uses `attribute_not_exists(pk)` conditional writes; a losing concurrent task is a normal flow, not an error.
- Empty item lists are never stored — an empty snapshot would make every card show as NEW against it.
- Baseline lookup falls back through past-only offsets (1-4h for badges, 24-26h for daily) with `MIN_AGE_HOURS=0.75`; comparing against a too-young snapshot inflates per-hour rates severalfold.
- `items` are stored as a JSON string (`ensure_ascii=False`); numbers read back from DynamoDB are normalized from Decimal to int on the query path.
- TTL attribute `expireAt`: snapshots 30 days, LLM reports 2 days.

### 4. Code Pointers
- `backend/app/store/keys.py` — every key format and fallback constant
- `backend/app/store/table.py` — `TrendStore` (all DynamoDB I/O)
- `backend/app/collector/run.py` — `collect_all` write path
- `backend/app/derive.py` — `with_derived` read-path derivation contract
- `backend/tests/test_keys.py`, `backend/tests/test_table.py` — key/store behavior specs

### 5. Cross-references
- Related modules: `backend/app/store/`, `backend/app/collector/`
- Related ADRs: none yet
- Related runbooks: none yet
- Related layers: [api.md](api.md), [iac.md](iac.md) (table definition), [agent-llm.md](agent-llm.md) (report cache)

<a id="korean"></a>
## 한국어

### 1. 개요
DynamoDB 단일 테이블(`pk`/`sk`)에 시간별 급상승 스냅샷, 영상별 시계열, LLM 리포트 캐시를 저장하고 TTL로 만료한다(스냅샷 30일, 리포트 2일). 키 규칙은 단일 모듈에만 정의해 모든 읽기·쓰기 경로가 동일한 키를 계산한다.

### 2. 구성요소
| 구성요소 | 경로 | 목적 |
|---|---|---|
| 키 규칙(단일 정의) | `backend/app/store/keys.py` | `snap_pk`(`SNAP#ALL`/`SNAP#CAT#{id}`), `vid_pk`(`VID#{videoId}`), `report_pk`(`REPORT#{kind}#{scope}`), `ts_sk`(`TS#YYYY-MM-DDTHH`), `hour_bucket`, `ttl_epoch`와 폴백 상수 `RECENT_OFFSETS`/`DAILY_OFFSETS`/`MIN_AGE_HOURS` |
| 저장소 접근 계층 | `backend/app/store/table.py` | `TrendStore`: `put_snapshot`(조건부 쓰기), `latest_snapshot`, `baseline_snapshot`(오프셋 폴백, 예외 없음), `snapshots_range`, `put_video_points`, `video_history`, `get_report`/`put_report`. Decimal→int 정규화 포함 |
| 수집 오케스트레이션 | `backend/app/collector/run.py` | `collect_all`: 전체 Top 30 + 카테고리별 Top 10 수집. 카테고리 실패 시 전체 목록 파생으로 폴백(`degraded` 플래그) |
| YouTube 클라이언트 | `backend/app/collector/youtube.py` | YouTube Data API v3 `mostPopular` 조회. `httpx.Client` 주입 가능, 문자열 통계는 `_stat_int`로 변환(부분 실패 격리) |
| 카테고리 목록 | `backend/app/categories.py` | 고정 8개 분야(`videoCategoryId`). 한글명은 기동 시 `videoCategories.list(hl=ko)`로 갱신하고 실패하면 기본값을 쓴다 |
| 파생 필드 | `backend/app/derive.py` | 순수 함수 `with_derived`: 기준 스냅샷 대비 `prevRank`/`delta`/`viewsPerHour` 계산. 실제 경과 시간으로 나눈다 |
| 집계 | `backend/app/aggregate.py` | 순수 함수 `category_series`: 스냅샷 목록 → 카테고리 점유율/진입/이탈 시계열 |

### 3. 주요 결정
- 시간 버킷은 UTC 시 단위 문자열로, 수집 cron(`minute=0`)과 경계가 정렬된다 — "그 시각의 스냅샷"을 스캔 없이 계산된 키 하나로 조회한다.
- `put_snapshot`은 `attribute_not_exists(pk)` 조건부 쓰기다. 동시 태스크 경쟁에서 지는 쪽은 오류가 아니라 정상 흐름이다.
- 빈 목록은 저장하지 않는다 — 빈 스냅샷을 기준으로 삼으면 전 카드가 NEW로 오탐된다.
- 기준 스냅샷은 과거 방향으로만 폴백한다(배지 1~4h, 일간 24~26h) + `MIN_AGE_HOURS=0.75`. 너무 어린 스냅샷과 비교하면 시간당 환산이 수 배 왜곡된다.
- `items`는 JSON 문자열(`ensure_ascii=False`)로 저장하고, 조회 경로에서 DynamoDB Decimal을 int로 정규화한다.
- TTL 속성은 `expireAt`이다 — 스냅샷 30일, LLM 리포트 2일.

### 4. 코드 포인터
- `backend/app/store/keys.py` — 모든 키 형식과 폴백 상수
- `backend/app/store/table.py` — `TrendStore`(DynamoDB I/O 전부)
- `backend/app/collector/run.py` — `collect_all` 쓰기 경로
- `backend/app/derive.py` — `with_derived` 읽기 경로 파생 계약
- `backend/tests/test_keys.py`, `backend/tests/test_table.py` — 키/저장소 동작 명세

### 5. 상호 참조
- 관련 모듈: `backend/app/store/`, `backend/app/collector/`
- 관련 ADR: 아직 없음
- 관련 런북: 아직 없음
- 관련 레이어: [api.md](api.md), [iac.md](iac.md)(테이블 정의), [agent-llm.md](agent-llm.md)(리포트 캐시)

Last updated: 2026-08-04
