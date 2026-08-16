# Data / 데이터 구성 상세

[![English](https://img.shields.io/badge/Language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/Language-한국어-red)](#korean)

<a id="english"></a>
## English

### 1. Overview
Single DynamoDB table (`pk`/`sk`) stores hourly trending snapshots, per-video time series, LLM report caches, and AI tag results, all expired by TTL (snapshots 30 days, reports 2 days, tags 2 days). Key rules live in exactly one module so every reader and writer computes identical keys.

### 2. Components
| Component | Path | Purpose |
|---|---|---|
| Key rules (single source) | `backend/app/store/keys.py` | `snap_pk` resolves scope strings by prefix: `all` → `SNAP#ALL`, `rgn-{CODE}` → `SNAP#RGN#{CODE}`, `spot-{name}` → `SNAP#SPOT#{name}`, `chart-{name}` → `SNAP#CHART#{name}`, `chan-{name}` → `SNAP#CHAN#{name}`, anything else → `SNAP#CAT#{id}`; `vid_pk` (`VID#{videoId}`), `report_pk` (`REPORT#{kind}#{scope}`), `tags_pk` (`TAGS#ALL`), `ts_sk` (`TS#YYYY-MM-DDTHH`), `hour_bucket`, `ttl_epoch`; fallback constants `RECENT_OFFSETS`/`DAILY_OFFSETS`/`MIN_AGE_HOURS` |
| Store access layer | `backend/app/store/table.py` | `TrendStore`: `put_snapshot` (conditional write), `latest_snapshot`, `baseline_snapshot` (offset fallback, never raises), `snapshots_range`, `put_video_points`, `video_history` (also serves `/api/home` hero tenure over a 72h window), `get_report`/`put_report`, `get_tags`/`put_tags`; Decimal-to-int normalization |
| AI tagging pipeline | `backend/app/tagging.py` | `ensure_tags`: tags the latest ALL snapshot bucket via one Bedrock call; idempotent per bucket, silently skips on LLM absence/failure; writes via `keys.tags_pk()` |
| Collection orchestration | `backend/app/collector/run.py` | `collect_all`: overall Top 30, per-category Top 20 (`RANK_DEPTH=20`; category failure falls back to derivation from the overall list, `degraded` flag), per-country Top 20 for `REGIONS` (US/JP/GB/IN, scope `rgn-{CODE}` — a failed country is skipped alone), the 5 official YouTube Music charts from `app/charts.py` `MUSIC_CHARTS` (songs/mv-daily/mv-weekly/shorts/live, scope `chart-{suffix}` — per-chart failure isolation, a rotated playlist id skips only that chart), the AWS Korea channel spotlight (`spot-aws`), and the trending-channel ranking (`chan-top` — `channels_stats` over the overall list's `channelId`s, then `rank_channels`) |
| Music chart catalog | `backend/app/charts.py` | `MUSIC_CHARTS` single definition — (scope suffix, playlist id, row title "YouTube Music · …") 5 entries, all playlists of the YouTube Music Global Charts channel; playlist order is the chart rank; 2 quota units per chart per hour; replaces the old single-chart constants in `run.py` |
| YouTube client | `backend/app/collector/youtube.py` | YouTube Data API v3 client — `most_popular` (`mostPopular`, optional `region_code`), `channel_top` (`channels(forHandle)` → uploads playlist → `playlistItems` → `videos`, ranked by view count desc; 3 quota units, uploads-playlist id cached per instance), `playlist_top` (playlist order kept as the chart rank — no view-count re-sort; 2 quota units), `channels_stats` (up to 50 channels per 1 quota unit; `hiddenSubscriberCount` → `subscribers: null` — the null-vs-0 contract); injectable `httpx.Client`; string statistics coerced via `_stat_int` (partial-failure isolation); each card stores `channelId` and a `description` — `snippet.description` whitespace-collapsed and truncated to `DESCRIPTION_MAX=200` chars |
| Category catalog | `backend/app/categories.py` | Fixed 8 categories (`videoCategoryId`); Korean names refreshed at startup via `videoCategories.list(hl=ko)` with defaults on failure |
| Derived fields | `backend/app/derive.py` | Pure function `with_derived`: `prevRank`/`delta`/`viewsPerHour` against a baseline snapshot; divides by actual elapsed hours |
| Aggregation | `backend/app/aggregate.py` | Pure functions — `category_series`: snapshot list to category share / entered / exited time series; `rank_channels`: trending cards + channel stats to the "지금 뜨는 채널" ranking (sorted by summed trending views, then appearance count; top `CHANNEL_RANK_MAX=12`, each entry carries `topVideoId`/`topVideoTitle`) |

### 3. Key Decisions
- Hour buckets are UTC-hour strings aligned with the collector cron (`minute=0`), so "the snapshot at hour X" is a single computed key lookup — no scan.
- `put_snapshot` uses `attribute_not_exists(pk)` conditional writes; a losing concurrent task is a normal flow, not an error.
- Empty item lists are never stored — an empty snapshot would make every card show as NEW against it.
- Baseline lookup falls back through past-only offsets (1-4h for badges, 24-26h for daily) with `MIN_AGE_HOURS=0.75`; comparing against a too-young snapshot inflates per-hour rates severalfold.
- `items` are stored as a JSON string (`ensure_ascii=False`); numbers read back from DynamoDB are normalized from Decimal to int on the query path.
- Snapshot card items include a `description` field (collector-truncated to 200 chars); items from snapshots stored before the field was introduced lack it — there is no backfill, and readers (the frontend included) treat it as optional.
- Tag items: `pk=TAGS#ALL`, `sk=TS#<hour bucket>`, attribute `tags` as a JSON string of `{videoId: {topics, age, vibe}}` — one item per ALL-snapshot bucket, written by `app/tagging.py`.
- TTL attribute `expireAt`: snapshots 30 days, LLM reports 2 days, tags 2 days (`TAGS_TTL_DAYS`).
- Scope strings are interpreted only in `keys.snap_pk` (prefixes `rgn-`/`spot-`/`chart-`/`chan-`, `all`, else category id) — adding a new ranking source is a prefix-compatible scope plus a collector step; no reader changes.

### 4. Code Pointers
- `backend/app/store/keys.py` — every key format and fallback constant
- `backend/app/store/table.py` — `TrendStore` (all DynamoDB I/O)
- `backend/app/collector/run.py` — `collect_all` write path
- `backend/app/derive.py` — `with_derived` read-path derivation contract
- `backend/app/tagging.py` — `ensure_tags` tag write path
- `backend/tests/test_keys.py`, `backend/tests/test_table.py`, `backend/tests/test_tagging.py` — key/store/tagging behavior specs

### 5. Cross-references
- Related modules: `backend/app/store/`, `backend/app/collector/`
- Related ADRs: none yet
- Related runbooks: none yet
- Related layers: [api.md](api.md), [iac.md](iac.md) (table definition), [agent-llm.md](agent-llm.md) (report cache)

<a id="korean"></a>
## 한국어

### 1. 개요
DynamoDB 단일 테이블(`pk`/`sk`)에 시간별 급상승 스냅샷, 영상별 시계열, LLM 리포트 캐시, AI 태그 결과를 저장하고 TTL로 만료한다(스냅샷 30일, 리포트 2일, 태그 2일). 키 규칙은 단일 모듈에만 정의해 모든 읽기·쓰기 경로가 동일한 키를 계산한다.

### 2. 구성요소
| 구성요소 | 경로 | 목적 |
|---|---|---|
| 키 규칙(단일 정의) | `backend/app/store/keys.py` | `snap_pk`가 스코프 문자열을 접두로 해석한다: `all` → `SNAP#ALL`, `rgn-{CODE}` → `SNAP#RGN#{CODE}`, `spot-{name}` → `SNAP#SPOT#{name}`, `chart-{name}` → `SNAP#CHART#{name}`, `chan-{name}` → `SNAP#CHAN#{name}`, 그 외 → `SNAP#CAT#{id}`. `vid_pk`(`VID#{videoId}`), `report_pk`(`REPORT#{kind}#{scope}`), `tags_pk`(`TAGS#ALL`), `ts_sk`(`TS#YYYY-MM-DDTHH`), `hour_bucket`, `ttl_epoch`와 폴백 상수 `RECENT_OFFSETS`/`DAILY_OFFSETS`/`MIN_AGE_HOURS` |
| 저장소 접근 계층 | `backend/app/store/table.py` | `TrendStore`: `put_snapshot`(조건부 쓰기), `latest_snapshot`, `baseline_snapshot`(오프셋 폴백, 예외 없음), `snapshots_range`, `put_video_points`, `video_history`(`/api/home` 히어로 차트인 시간 계산에도 사용 — 72h 윈도), `get_report`/`put_report`, `get_tags`/`put_tags`. Decimal→int 정규화 포함 |
| AI 태깅 파이프라인 | `backend/app/tagging.py` | `ensure_tags`: 최신 ALL 스냅샷 버킷을 Bedrock 1콜로 태깅. 버킷 단위 멱등, LLM 미설정·실패 시 조용히 스킵. `keys.tags_pk()`로 쓴다 |
| 수집 오케스트레이션 | `backend/app/collector/run.py` | `collect_all`: 전체 Top 30, 카테고리별 Top 20(`RANK_DEPTH=20` — 실패 시 전체 목록 파생 폴백, `degraded` 플래그), 국가별 Top 20(`REGIONS` 미/일/영/인, 스코프 `rgn-{CODE}` — 실패한 국가만 건너뜀), `app/charts.py` `MUSIC_CHARTS`의 YouTube Music 공식 차트 5종(songs/mv-daily/mv-weekly/shorts/live, 스코프 `chart-{suffix}` — 차트별 실패 격리, 재생목록 id 회전 시 그 차트만 건너뜀), AWS Korea 채널 스포트라이트(`spot-aws`), 급상승 채널 랭킹(`chan-top` — 전체 목록의 `channelId`로 `channels_stats` 후 `rank_channels`) |
| 뮤직 차트 목록 | `backend/app/charts.py` | `MUSIC_CHARTS` 단일 정의 — (scope 접미사, 재생목록 id, 행 제목 "YouTube Music · …") 5개 항목, 전부 YouTube Music Global Charts 채널의 재생목록. 재생목록 순서가 곧 차트 순위, 차트당 쿼터 2유닛/시간. `run.py`의 구 단일 차트 상수를 대체한다 |
| YouTube 클라이언트 | `backend/app/collector/youtube.py` | YouTube Data API v3 클라이언트 — `most_popular`(`mostPopular`, `region_code` 선택), `channel_top`(`channels(forHandle)` → uploads 재생목록 → `playlistItems` → `videos`, 조회수 내림차순 랭킹 — 쿼터 3유닛, uploads 재생목록 id는 인스턴스 캐시), `playlist_top`(재생목록 순서가 곧 차트 순위 — 조회수 재정렬 금지, 쿼터 2유닛), `channels_stats`(50채널당 쿼터 1유닛. `hiddenSubscriberCount`는 `subscribers: null` — null vs 0 계약). `httpx.Client` 주입 가능, 문자열 통계는 `_stat_int`로 변환(부분 실패 격리). 카드마다 `channelId`와 `description`(`snippet.description` 공백 정리 후 `DESCRIPTION_MAX=200`자 절단)을 저장한다 |
| 카테고리 목록 | `backend/app/categories.py` | 고정 8개 분야(`videoCategoryId`). 한글명은 기동 시 `videoCategories.list(hl=ko)`로 갱신하고 실패하면 기본값을 쓴다 |
| 파생 필드 | `backend/app/derive.py` | 순수 함수 `with_derived`: 기준 스냅샷 대비 `prevRank`/`delta`/`viewsPerHour` 계산. 실제 경과 시간으로 나눈다 |
| 집계 | `backend/app/aggregate.py` | 순수 함수 — `category_series`: 스냅샷 목록 → 카테고리 점유율/진입/이탈 시계열. `rank_channels`: 급상승 카드 + 채널 통계 → "지금 뜨는 채널" 랭킹(합산 급상승 조회수 → 등장 편수 정렬, 상위 `CHANNEL_RANK_MAX=12`, 항목마다 `topVideoId`/`topVideoTitle` 포함) |

### 3. 주요 결정
- 시간 버킷은 UTC 시 단위 문자열로, 수집 cron(`minute=0`)과 경계가 정렬된다 — "그 시각의 스냅샷"을 스캔 없이 계산된 키 하나로 조회한다.
- `put_snapshot`은 `attribute_not_exists(pk)` 조건부 쓰기다. 동시 태스크 경쟁에서 지는 쪽은 오류가 아니라 정상 흐름이다.
- 빈 목록은 저장하지 않는다 — 빈 스냅샷을 기준으로 삼으면 전 카드가 NEW로 오탐된다.
- 기준 스냅샷은 과거 방향으로만 폴백한다(배지 1~4h, 일간 24~26h) + `MIN_AGE_HOURS=0.75`. 너무 어린 스냅샷과 비교하면 시간당 환산이 수 배 왜곡된다.
- `items`는 JSON 문자열(`ensure_ascii=False`)로 저장하고, 조회 경로에서 DynamoDB Decimal을 int로 정규화한다.
- 스냅샷 카드 아이템은 `description` 필드(수집기가 200자로 절단)를 포함한다. 도입 이전에 저장된 스냅샷 아이템에는 없다 — 백필하지 않으며, 읽는 쪽(프론트 포함)은 optional로 취급한다.
- 태그 아이템: `pk=TAGS#ALL`, `sk=TS#<hour bucket>`, 속성 `tags`는 `{videoId: {topics, age, vibe}}`의 JSON 문자열이다 — ALL 스냅샷 버킷당 1개, `app/tagging.py`가 쓴다.
- TTL 속성은 `expireAt`이다 — 스냅샷 30일, LLM 리포트 2일, 태그 2일(`TAGS_TTL_DAYS`).
- 스코프 문자열 해석은 `keys.snap_pk`에서만 한다(접두 `rgn-`/`spot-`/`chart-`/`chan-`, `all`, 그 외 분야 id) — 새 랭킹 소스 추가는 접두 규약에 맞는 스코프 + 수집 단계 추가로 끝나고, 읽기 경로는 바뀌지 않는다.

### 4. 코드 포인터
- `backend/app/store/keys.py` — 모든 키 형식과 폴백 상수
- `backend/app/store/table.py` — `TrendStore`(DynamoDB I/O 전부)
- `backend/app/collector/run.py` — `collect_all` 쓰기 경로
- `backend/app/derive.py` — `with_derived` 읽기 경로 파생 계약
- `backend/app/tagging.py` — `ensure_tags` 태그 쓰기 경로
- `backend/tests/test_keys.py`, `backend/tests/test_table.py`, `backend/tests/test_tagging.py` — 키/저장소/태깅 동작 명세

### 5. 상호 참조
- 관련 모듈: `backend/app/store/`, `backend/app/collector/`
- 관련 ADR: 아직 없음
- 관련 런북: 아직 없음
- 관련 레이어: [api.md](api.md), [iac.md](iac.md)(테이블 정의), [agent-llm.md](agent-llm.md)(리포트 캐시)

Last updated: 2026-08-16
