# Frontend / Frontend 구현 상세

[![English](https://img.shields.io/badge/Language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/Language-한국어-red)](#korean)

<a id="english"></a>
## English

### 1. Overview
React 18 + Vite + TypeScript SPA with three tabs — overall Top 30, per-category Top 10, and trend analysis (recharts time series plus LLM brief panel). It consumes the backend `/api/*` contract only; the gate is `npx tsc --noEmit && npm run build` (no test runner).

### 2. Components
| Component | Path | Purpose |
|---|---|---|
| App shell | `frontend/src/App.tsx` | Tab bar (`all`/`category`/`trend`), theme toggle, refresh button bumping `reloadKey` to remount the active tab |
| API client | `frontend/src/api.ts` | `fetchJson`/`postJson` plus `ApiError` carrying `status` and the `{error}` body from the backend contract |
| Overall Top 30 tab | `frontend/src/tabs/TopAll.tsx` | Card grid with computed stats (total views, distinct channels, top category); discriminated-union `LoadState` |
| Category tab | `frontend/src/tabs/ByCategory.tsx` | Category selector (`GET /api/categories`) plus per-category Top 10 grid; snapshot-level `degraded` intentionally not shown (array contract) |
| Trends tab | `frontend/src/tabs/Trends.tsx` | recharts charts — category share `AreaChart`, entered/exited `BarChart`, per-video rank/views `LineChart` — plus `BriefPanel` |
| Contract types | `frontend/src/types.ts` | `Card`/`Category`/`HistoryPoint`/`TrendBucket` mirroring backend responses (nullable derived fields) |
| Formatting | `frontend/src/format.ts` | `formatCount` (Korean 만/억 abbreviation), `formatTsKst` (UTC hour bucket to KST wall clock, timezone-independent) |
| Theme state | `frontend/src/theme.ts` | `getTheme`/`setTheme`/`toggleTheme` over `documentElement.dataset.theme` + localStorage; first paint handled by an `index.html` bootstrap script |

### 3. Key Decisions
- Loading/error/ready are modeled as discriminated unions per tab — no boolean flag combinations.
- `ApiError` surfaces the backend's Korean `error` message directly; fallbacks are local Korean strings.
- KST conversion shifts the Date by +9h and reads `getUTC*` accessors, so rendering is identical regardless of the viewer's local timezone.
- Refresh remounts via `reloadKey` instead of per-tab refetch plumbing.
- Frontend gate is compile plus build only (`npx tsc --noEmit && npm run build`); behavior is covered by backend tests and smoke checks.

### 4. Code Pointers
- `frontend/src/App.tsx` — shell, tabs, theme wiring
- `frontend/src/api.ts` — fetch wrapper and error contract
- `frontend/src/tabs/Trends.tsx` — all chart composition and data loading
- `frontend/src/types.ts` — API contract types

### 5. Cross-references
- Related modules: `frontend/src/`, `backend/app/api/` (contract source)
- Related ADRs: none yet
- Related runbooks: none yet
- Related layers: [ui.md](ui.md), [api.md](api.md), [infrastructure.md](infrastructure.md) (static serving)

<a id="korean"></a>
## 한국어

### 1. 개요
React 18 + Vite + TypeScript SPA로, 전체 Top 30·분야별 Top 10·추이 분석(recharts 시계열 + LLM 브리핑 패널) 3탭을 제공한다. 백엔드 `/api/*` 계약만 소비하며, 게이트는 `npx tsc --noEmit && npm run build`다(테스트 러너 없음).

### 2. 구성요소
| 구성요소 | 경로 | 목적 |
|---|---|---|
| 앱 셸 | `frontend/src/App.tsx` | 탭바(`all`/`category`/`trend`), 테마 토글, `reloadKey`를 올려 활성 탭을 리마운트하는 새로고침 버튼 |
| API 클라이언트 | `frontend/src/api.ts` | `fetchJson`/`postJson`과 백엔드 계약의 `{error}` 본문·`status`를 싣는 `ApiError` |
| 전체 Top 30 탭 | `frontend/src/tabs/TopAll.tsx` | 카드 그리드 + 통계(총 조회수, 채널 수, 최다 분야). 판별 유니온 `LoadState` 사용 |
| 분야별 탭 | `frontend/src/tabs/ByCategory.tsx` | 카테고리 선택(`GET /api/categories`) + 분야별 Top 10 그리드. 스냅샷 단위 `degraded`는 의도적으로 미표시(배열 계약) |
| 추이 탭 | `frontend/src/tabs/Trends.tsx` | recharts 차트 — 카테고리 점유율 `AreaChart`, 진입/이탈 `BarChart`, 영상별 순위/조회수 `LineChart` — 와 `BriefPanel` |
| 계약 타입 | `frontend/src/types.ts` | 백엔드 응답을 그대로 반영한 `Card`/`Category`/`HistoryPoint`/`TrendBucket`(파생 필드 nullable) |
| 포매팅 | `frontend/src/format.ts` | `formatCount`(만/억 축약), `formatTsKst`(UTC 시 버킷 → KST 벽시계, 실행 타임존 무관) |
| 테마 상태 | `frontend/src/theme.ts` | `documentElement.dataset.theme` + localStorage 기반 `getTheme`/`setTheme`/`toggleTheme`. 첫 페인트는 `index.html` 부트스트랩 스크립트가 처리 |

### 3. 주요 결정
- 로딩/오류/준비 상태를 탭마다 판별 유니온으로 모델링한다 — 불리언 플래그 조합을 쓰지 않는다.
- `ApiError`는 백엔드의 한국어 `error` 메시지를 그대로 노출하고, 폴백도 로컬 한국어 문구다.
- KST 변환은 Date를 +9h 이동한 뒤 `getUTC*` 접근자로 읽는다 — 조회자의 로컬 타임존과 무관하게 동일하게 렌더된다.
- 새로고침은 탭별 refetch 배선 대신 `reloadKey` 리마운트로 처리한다.
- 프론트 게이트는 컴파일+빌드뿐이다(`npx tsc --noEmit && npm run build`). 동작 검증은 백엔드 테스트와 스모크가 담당한다.

### 4. 코드 포인터
- `frontend/src/App.tsx` — 셸, 탭, 테마 배선
- `frontend/src/api.ts` — fetch 래퍼와 오류 계약
- `frontend/src/tabs/Trends.tsx` — 차트 구성과 데이터 로딩 전부
- `frontend/src/types.ts` — API 계약 타입

### 5. 상호 참조
- 관련 모듈: `frontend/src/`, `backend/app/api/`(계약의 원천)
- 관련 ADR: 아직 없음
- 관련 런북: 아직 없음
- 관련 레이어: [ui.md](ui.md), [api.md](api.md), [infrastructure.md](infrastructure.md)(정적 서빙)

Last updated: 2026-08-04
