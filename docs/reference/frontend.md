# Frontend / Frontend 구현 상세

[![English](https://img.shields.io/badge/Language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/Language-한국어-red)](#korean)

<a id="english"></a>
## English

### 1. Overview
React 18 + Vite + TypeScript SPA — a single-page "Trend Radar" home with no router or tabs: top bar (TREND RADAR logo, capture time in KST, refresh, theme button), hero (overall #1), insight chips, horizontal strip rows (top10 / accel / topic / age / category, plus a client-inserted quiz row), and two bottom panels (category share trends, LLM brief). It consumes the backend `/api/*` contract only; the gate is `npx tsc --noEmit && npm run build` (no test runner).

### 2. Components
| Component | Path | Purpose |
|---|---|---|
| App shell | `frontend/src/App.tsx` | Top bar, `/api/home` load with 60-second silent polling plus generation guard, modal state, `panelKey` remount for the bottom panels |
| API client | `frontend/src/api.ts` | `fetchJson`/`postJson` plus `ApiError` carrying `status` and the `{error}` body from the backend contract |
| Hero | `frontend/src/components/Hero.tsx` | Overall #1 card — maxres background `img` with `onError` fallback, chart-in tenure hours, NEW chip, watch / quiz CTAs |
| Insight chips | `frontend/src/components/InsightChips.tsx` | Rule-based insight strings from `/api/home` (no LLM) |
| Strip row | `frontend/src/components/Row.tsx` | Scroll-snap strip with hover arrows; `Tile`/`TopTile` (large rank numerals, `-webkit-text-stroke`); badges — `baseline === null` renders nothing, `prevRank === null` renders NEW, `delta` renders ▲/▼, `viewsPerHour > 0` renders "+N/시" |
| Quiz modal | `frontend/src/components/QuizModal.tsx` | 3 questions → `POST /api/quiz` → type name plus a `kind='quiz'` row inserted at the top of the home rows |
| Theme modal | `frontend/src/components/ThemeModal.tsx` | 10 theme swatches from `src/themes.ts` |
| Detail modal | `frontend/src/components/DetailModal.tsx` | Per-video rank/views `LineChart` with log/linear toggle plus YouTube link; shows a notice when no history exists (only videos that entered the overall Top 30 are recorded) |
| Trends panel | `frontend/src/components/TrendsPanel.tsx` | Category share stacked `AreaChart` plus entered/exited `BarChart` (`hours=48`) |
| Brief panel | `frontend/src/components/BriefPanel.tsx` | LLM brief/report, react-markdown render (logic unchanged from before the redesign) |
| Modal shell | `frontend/src/components/Modal.tsx` | Shared shell — backdrop click or Escape closes |
| Contract types | `frontend/src/types.ts` | `Card`/`HomeCard`/`HomeRow`/`HomeHero`/`HomeData`/`QuizAnswers`/`QuizResult` plus `Category`/`HistoryPoint`/`TrendBucket` (nullable derived fields) |
| Formatting | `frontend/src/format.ts` | `formatCount` (Korean 만/억 abbreviation), `formatTsKst` (UTC hour bucket to KST wall clock), `formatClockKst` (ISO to KST HH:MM), `youtubeUrl` |
| Theme state | `frontend/src/theme.ts` | `getTheme`/`setTheme` over `documentElement.dataset.theme` + localStorage `yt-theme`; first paint handled by an `index.html` bootstrap script |
| Chart colors | `frontend/src/chartColors.ts` | Theme-independent fixed 8-color palette (slot-bound) — recharts does not reliably apply CSS `var()` to SVG fill/stroke |

### 3. Key Decisions
- Single page, no router: every section is composed from one `GET /api/home` response; the quiz row is the only client-made row (`kind='quiz'`).
- `/api/home` is polled every 60 seconds in silent mode. A generation token (a sequence ref captured per request) discards late responses; a failed silent poll keeps the current screen instead of showing an error. This generation-token race guard must be kept on any new async-fetch-then-setState code.
- Loading/error/ready are modeled as a discriminated union (`HomeState`) — no boolean flag combinations.
- `ApiError` surfaces the backend's Korean `error` message directly; fallbacks are local Korean strings.
- KST conversion shifts the Date by +9h and reads `getUTC*` accessors, so rendering is identical regardless of the viewer's local timezone.
- Refresh reloads home and bumps `panelKey` to remount the two bottom panels — they are excluded from polling and refetch only on manual refresh.
- Themes are CSS-variable sets: the 10 `[data-theme]` blocks in `styles.css` are the single truth (default `neon-hunter`; `cotton-candy` is the light theme). `src/themes.ts` swatches and the `index.html` bootstrap valid-id list are kept in sync. Legacy localStorage values are migrated at bootstrap: `dark` → `neon-hunter`, `light` → `cotton-candy`.
- Chart colors bypass the theme system — the fixed palette in `chartColors.ts` is used because recharts SVG cannot take CSS `var()`.
- `rehype-raw` stays banned in react-markdown — rendering raw HTML from LLM output would open an XSS path.
- Frontend gate is compile plus build only (`npx tsc --noEmit && npm run build`); behavior is covered by backend tests and smoke checks.

### 4. Code Pointers
- `frontend/src/App.tsx` — top bar, 60-second polling plus generation guard, modal state, panel remount
- `frontend/src/api.ts` — fetch wrapper and error contract
- `frontend/src/components/Row.tsx` — strip/tile/badge rendering
- `frontend/src/components/TrendsPanel.tsx`, `frontend/src/components/DetailModal.tsx` — chart composition
- `frontend/src/theme.ts`, `frontend/src/themes.ts`, `frontend/src/styles.css`, `frontend/index.html` — theme system and migration bootstrap
- `frontend/src/types.ts` — API contract types

### 5. Cross-references
- Related modules: `frontend/src/`, `backend/app/api/` (contract source — `home.py` for `/api/home` and `/api/quiz`)
- Related ADRs: [ADR-001](../decisions/ADR-001-trend-radar-single-page-redesign.md) (Trend Radar single-page redesign — scope exclusions)
- Related runbooks: none yet
- Related layers: [ui.md](ui.md), [api.md](api.md), [infrastructure.md](infrastructure.md) (static serving)

<a id="korean"></a>
## 한국어

### 1. 개요
React 18 + Vite + TypeScript SPA로, 라우터·탭 없는 단일 페이지 "Trend Radar" 홈을 제공한다: 톱바(TREND RADAR 로고, 수집 시각 KST, 새로고침, 테마 버튼) → 히어로(전체 1위) → 인사이트 칩 → 가로 스트립 행들(top10/accel/topic/age/category + 클라이언트 삽입 퀴즈 행) → 하단 패널 2개(카테고리 점유율 추이, AI 브리핑). 백엔드 `/api/*` 계약만 소비하며, 게이트는 `npx tsc --noEmit && npm run build`다(테스트 러너 없음).

### 2. 구성요소
| 구성요소 | 경로 | 목적 |
|---|---|---|
| 앱 셸 | `frontend/src/App.tsx` | 톱바, `/api/home` 로드(60초 silent 폴링 + 세대 가드), 모달 상태, 하단 패널 `panelKey` 리마운트 |
| API 클라이언트 | `frontend/src/api.ts` | `fetchJson`/`postJson`과 백엔드 계약의 `{error}` 본문·`status`를 싣는 `ApiError` |
| 히어로 | `frontend/src/components/Hero.tsx` | 전체 1위 카드 — maxres 배경 `img` + `onError` 폴백, 차트인 시간, NEW 칩, 보러가기/내 취향 찾기 |
| 인사이트 칩 | `frontend/src/components/InsightChips.tsx` | `/api/home`의 규칙 기반 인사이트 문자열(LLM 미사용) |
| 스트립 행 | `frontend/src/components/Row.tsx` | 스크롤 스냅 스트립 + hover 화살표. `Tile`/`TopTile`(큰 순위 숫자, `-webkit-text-stroke`). 배지 — `baseline === null`이면 미렌더, `prevRank === null`이면 NEW, `delta`는 ▲/▼, `viewsPerHour > 0`이면 "+N/시" |
| 퀴즈 모달 | `frontend/src/components/QuizModal.tsx` | 3문항 → `POST /api/quiz` → 유형명 + 홈 행 상단에 `kind='quiz'` 행 삽입 |
| 테마 모달 | `frontend/src/components/ThemeModal.tsx` | `src/themes.ts` 기반 10종 스와치 |
| 상세 모달 | `frontend/src/components/DetailModal.tsx` | 영상 시계열 순위/조회수 `LineChart` + 로그/선형 토글 + YouTube 링크. 시계열 없으면 안내(전체 Top30 진입 영상만 기록) |
| 추이 패널 | `frontend/src/components/TrendsPanel.tsx` | 점유율 스택 `AreaChart` + 진입/이탈 `BarChart`(`hours=48`) |
| 브리핑 패널 | `frontend/src/components/BriefPanel.tsx` | LLM 브리핑/리포트, react-markdown 렌더(개편 전 로직 유지) |
| 모달 셸 | `frontend/src/components/Modal.tsx` | 공통 셸 — 배경 클릭/Escape로 닫기 |
| 계약 타입 | `frontend/src/types.ts` | `Card`/`HomeCard`/`HomeRow`/`HomeHero`/`HomeData`/`QuizAnswers`/`QuizResult` + `Category`/`HistoryPoint`/`TrendBucket`(파생 필드 nullable) |
| 포매팅 | `frontend/src/format.ts` | `formatCount`(만/억 축약), `formatTsKst`(UTC 시 버킷 → KST 벽시계), `formatClockKst`(ISO → KST HH:MM), `youtubeUrl` |
| 테마 상태 | `frontend/src/theme.ts` | `documentElement.dataset.theme` + localStorage `yt-theme` 기반 `getTheme`/`setTheme`. 첫 페인트는 `index.html` 부트스트랩 스크립트가 처리 |
| 차트 색 | `frontend/src/chartColors.ts` | 테마 무관 고정 8색 팔레트(슬롯 귀속) — recharts는 SVG fill/stroke에 CSS `var()`를 안정적으로 반영하지 않는다 |

### 3. 주요 결정
- 라우터 없는 단일 페이지다: 모든 섹션이 `GET /api/home` 응답 하나로 조합되고, 퀴즈 행(`kind='quiz'`)만 클라이언트가 만든다.
- `/api/home`은 60초마다 silent 모드로 폴링한다. 요청 시점에 캡처한 세대 토큰(시퀀스 ref)이 늦게 도착한 응답을 폐기하고, silent 폴링 실패는 오류 표시 대신 기존 화면을 유지한다. 비동기 fetch 후 setState 하는 코드를 추가할 때 이 세대 토큰 레이스 가드 패턴을 유지한다.
- 로딩/오류/준비 상태를 판별 유니온(`HomeState`)으로 모델링한다 — 불리언 플래그 조합을 쓰지 않는다.
- `ApiError`는 백엔드의 한국어 `error` 메시지를 그대로 노출하고, 폴백도 로컬 한국어 문구다.
- KST 변환은 Date를 +9h 이동한 뒤 `getUTC*` 접근자로 읽는다 — 조회자의 로컬 타임존과 무관하게 동일하게 렌더된다.
- 새로고침은 홈 재로드 + `panelKey` 증가로 하단 패널 2개를 리마운트한다 — 하단 패널은 폴링 대상이 아니고 수동 새로고침 때만 재조회한다.
- 테마는 CSS 변수 세트다: `styles.css`의 `[data-theme]` 10종이 단일 진실이다(기본 `neon-hunter`, 라이트는 `cotton-candy`). `src/themes.ts`의 스와치와 `index.html` 부트스트랩의 유효 id 목록을 함께 동기 유지한다. 구버전 localStorage 값은 부트스트랩에서 마이그레이션한다: `dark` → `neon-hunter`, `light` → `cotton-candy`.
- 차트 색은 테마 시스템을 우회한다 — recharts SVG가 CSS `var()`를 받지 못하므로 `chartColors.ts`의 고정 팔레트를 쓴다.
- react-markdown에 `rehype-raw`를 추가하지 않는다 — LLM 출력의 raw HTML 렌더는 XSS 경로다.
- 프론트 게이트는 컴파일+빌드뿐이다(`npx tsc --noEmit && npm run build`). 동작 검증은 백엔드 테스트와 스모크가 담당한다.

### 4. 코드 포인터
- `frontend/src/App.tsx` — 톱바, 60초 폴링 + 세대 가드, 모달 상태, 패널 리마운트
- `frontend/src/api.ts` — fetch 래퍼와 오류 계약
- `frontend/src/components/Row.tsx` — 스트립/타일/배지 렌더
- `frontend/src/components/TrendsPanel.tsx`, `frontend/src/components/DetailModal.tsx` — 차트 구성
- `frontend/src/theme.ts`, `frontend/src/themes.ts`, `frontend/src/styles.css`, `frontend/index.html` — 테마 시스템과 마이그레이션 부트스트랩
- `frontend/src/types.ts` — API 계약 타입

### 5. 상호 참조
- 관련 모듈: `frontend/src/`, `backend/app/api/`(계약의 원천 — `/api/home`·`/api/quiz`는 `home.py`)
- 관련 ADR: [ADR-001](../decisions/ADR-001-trend-radar-single-page-redesign.md) (Trend Radar 단일 페이지 개편 — 범위 제외 결정)
- 관련 런북: 아직 없음
- 관련 레이어: [ui.md](ui.md), [api.md](api.md), [infrastructure.md](infrastructure.md)(정적 서빙)

Last updated: 2026-08-14
