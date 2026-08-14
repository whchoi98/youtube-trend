# UI / UI 구현 상세

[![English](https://img.shields.io/badge/Language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/Language-한국어-red)](#korean)

<a id="english"></a>
## English

### 1. Overview
Presentation layer of the Trend Radar single page. The screen is one vertical composition — topbar, hero, insight chips, horizontal snap strips, two bottom panels, and three modals — styled by a 10-theme CSS custom property system plus a fixed theme-independent chart palette. The former 3-tab layout (`src/tabs/`, `Card`/`CardGrid`/`Badge` components) was removed in the 2026-08-14 redesign (ADR-001).

### 2. Components

Screen composition, top to bottom:

1. **Topbar** — "TREND RADAR" gradient logo, capture time (`수집 HH:MM` KST via `formatClockKst`), refresh button, theme button (`App.tsx`)
2. **Hero** — overall #1 video: `maxresdefault` background image with `onError` fallback to the stored thumbnail, chart-in tenure (`N시간째 차트인`), first-entry chip (`오늘 첫 진입`), watch link and quiz launcher (`Hero.tsx`)
3. **Insight chips** — backend-computed one-line summaries, no LLM (`InsightChips.tsx`)
4. **Snap strips** — `Row.tsx` renders `/api/home` rows in order: top10 (big rank numerals) → accel → topic → age → category; a quiz result row (`kind: 'quiz'`) is inserted client-side above them
5. **Bottom panels** — category share trends (`TrendsPanel`) and AI brief (`BriefPanel`); remounted only on manual refresh
6. **Modals** — quiz, theme picker, video detail, all on a common shell (`Modal.tsx`: backdrop click / Escape to close)

| Component | Path | Purpose |
|---|---|---|
| App shell | `frontend/src/App.tsx` | Topbar, `/api/home` load with 60s silent polling + generation-token guard (silent failures keep the current screen), modal state, bottom-panel remount key |
| Hero | `frontend/src/components/Hero.tsx` | #1 video hero with maxres background and `onError` fallback, tenure hours, NEW chip, watch/quiz actions |
| Insight chips | `frontend/src/components/InsightChips.tsx` | Renders `insights[]` strings; hidden when empty |
| Row / tiles | `frontend/src/components/Row.tsx` | Scroll-snap strip with hover arrows; `Tile` and `TopTile` (Netflix-style big rank numeral over the thumbnail); badge, velocity text, tag chips, thumbnail soft fallback |
| Quiz modal | `frontend/src/components/QuizModal.tsx` | 3 questions → `POST /api/quiz` → type name + a custom row added at the top of home |
| Theme modal | `frontend/src/components/ThemeModal.tsx` | 10 theme swatches from `themes.ts` |
| Detail modal | `frontend/src/components/DetailModal.tsx` | Per-video history charts (`hours=168`) and a YouTube link; empty history is a normal state (only overall Top30 entrants are recorded) |
| Trends panel | `frontend/src/components/TrendsPanel.tsx` | Category share stacked AreaChart + entered/exited BarChart (`hours=48`) |
| Brief panel | `frontend/src/components/BriefPanel.tsx` | Three-button LLM panel (`오늘의 브리핑`/`어제와 비교`/`추이 리포트`); markdown vs plain-text split (`kind: 'llm' | 'status'`) |
| Modal shell | `frontend/src/components/Modal.tsx` | Shared dialog: `role="dialog"`, backdrop click and Escape close |
| Style tokens | `frontend/src/styles.css` | 10 `[data-theme]` CSS variable sets (default `neon-hunter`; `cotton-candy` is the light theme) plus derived aliases (`--bg-elevated`, `--border`, …) |
| Chart palette | `frontend/src/chartColors.ts` | Fixed theme-independent 8-color palette; `seriesAccent`, `enteredColor`/`exitedColor` |
| Theme switch | `frontend/src/theme.ts`, `frontend/src/themes.ts` | `data-theme` on the root element + localStorage `yt-theme`; swatch hex copies live in `themes.ts` (kept in sync with `styles.css`); graceful no-op when localStorage is unavailable |

Chart inventory (all recharts):

- `TrendsPanel` — stacked share AreaChart over `/api/trends/categories?hours=48` plus an entered/exited BarChart
- `DetailModal` — rank LineChart (Y reversed, domain 1–30) and views LineChart with a log/linear toggle, over `/api/videos/{id}/history?hours=168`
- Series colors come from the fixed `chartColors.ts` palette; chart chrome (grid, axes, tooltip) uses theme CSS variables

### 3. Key Decisions
- The chart palette is one fixed theme-independent 8-color array, not per-theme sets: all 10 themes put charts on card backgrounds where the same mid-saturation hexes keep contrast, and recharts does not reliably resolve `var()` in SVG fill/stroke, so series colors stay fixed hex. Colors bind to slots, not items; entered/exited reuses the blue/red pair (slots 1/4) validated for CVD.
- Badge rules follow the nullable derived-field contract: `baseline === null` → no badge (comparison impossible), `prevRank === null` → NEW, positive `delta` → `▲n`, negative → `▼n`, zero → no badge. `viewsPerHour > 0` renders `+N/시`; null and 0 are never conflated.
- LLM text renders as markdown (`react-markdown` + `remark-gfm`) only when it actually came from the LLM; status and error strings render as plain text. `rehype-raw` stays banned — raw HTML from LLM output would open an XSS path.
- Theme truth lives in `styles.css` `[data-theme]` variable sets; `themes.ts` holds preview swatch copies, and the `index.html` bootstrap applies the theme before first paint and migrates legacy values (`dark` → `neon-hunter`, `light` → `cotton-candy`).
- Thumbnails fail soft: tiles swap a broken image for a neutral fallback block, and the hero falls back from `maxresdefault` to the stored thumbnail on `onError`.

### 4. Code Pointers
- `frontend/src/App.tsx` — screen composition, polling and generation guard, modal state
- `frontend/src/components/Row.tsx` — badge/velocity/tag-chip rules, `Tile`/`TopTile`
- `frontend/src/components/DetailModal.tsx`, `frontend/src/components/TrendsPanel.tsx` — chart inventory
- `frontend/src/components/BriefPanel.tsx` — markdown vs plain-text rendering split
- `frontend/src/styles.css` — 10 theme token sets and derived aliases
- `frontend/src/chartColors.ts` — fixed palette and accent helpers
- `frontend/src/theme.ts`, `frontend/src/themes.ts`, `frontend/index.html` — theme persistence and bootstrap migration

### 5. Cross-references
- Related modules: `frontend/src/components/`
- Related ADRs: [ADR-001](../decisions/ADR-001-trend-radar-single-page-redesign.md) (single-page redesign, excluded rows)
- Related runbooks: none yet
- Related layers: [frontend.md](frontend.md), [api.md](api.md) (nullable derived-field contract, `/api/home` and `/api/quiz` contracts)

<a id="korean"></a>
## 한국어

### 1. 개요
Trend Radar 단일 페이지의 프레젠테이션 계층이다. 화면은 톱바, 히어로, 인사이트 칩, 가로 스냅 스트립, 하단 패널 2개, 모달 3종의 세로 구성 하나이며, 테마 10종 CSS 커스텀 프로퍼티 시스템과 테마 무관 고정 차트 팔레트로 스타일링한다. 기존 3탭 레이아웃(`src/tabs/`, `Card`/`CardGrid`/`Badge` 컴포넌트)은 2026-08-14 개편(ADR-001)에서 삭제됐다.

### 2. 구성요소

화면 구성(위에서 아래로):

1. **톱바** — "TREND RADAR" 그라디언트 로고, 수집 시각(`수집 HH:MM` KST, `formatClockKst`), 새로고침 버튼, 테마 버튼 (`App.tsx`)
2. **히어로** — 전체 1위 영상: `maxresdefault` 배경 이미지 + `onError` 시 저장된 썸네일 폴백, 차트인 시간(`N시간째 차트인`), 첫 진입 칩(`오늘 첫 진입`), 보러가기·퀴즈 버튼 (`Hero.tsx`)
3. **인사이트 칩** — 백엔드가 계산한 한 줄 요약, LLM 미사용 (`InsightChips.tsx`)
4. **스냅 스트립** — `Row.tsx`가 `/api/home` 행을 순서대로 렌더한다: top10(큰 순위 숫자) → accel → topic → age → category. 퀴즈 결과 행(`kind: 'quiz'`)은 클라이언트에서 그 위에 삽입한다
5. **하단 패널** — 카테고리 점유율 추이(`TrendsPanel`)와 AI 브리핑(`BriefPanel`). 수동 새로고침 때만 remount로 재조회한다
6. **모달** — 퀴즈, 테마 선택, 영상 상세. 공통 셸(`Modal.tsx`: 배경 클릭/Escape 닫기)을 공유한다

| 구성요소 | 경로 | 목적 |
|---|---|---|
| 앱 셸 | `frontend/src/App.tsx` | 톱바, `/api/home` 60초 silent 폴링 + 세대 토큰 가드(silent 실패는 기존 화면 유지), 모달 상태, 하단 패널 remount 키 |
| 히어로 | `frontend/src/components/Hero.tsx` | 1위 히어로 — maxres 배경 + `onError` 폴백, 차트인 시간, NEW 칩, 보러가기/퀴즈 액션 |
| 인사이트 칩 | `frontend/src/components/InsightChips.tsx` | `insights[]` 문자열 렌더. 비어 있으면 숨김 |
| 행/타일 | `frontend/src/components/Row.tsx` | 스크롤 스냅 스트립 + hover 화살표. `Tile`·`TopTile`(넷플릭스식 큰 순위 숫자가 썸네일에 겹침), 배지·속도 텍스트·태그 칩, 썸네일 소프트 폴백 |
| 퀴즈 모달 | `frontend/src/components/QuizModal.tsx` | 3문항 → `POST /api/quiz` → 유형명 + 홈 맨 위 맞춤 행 추가 |
| 테마 모달 | `frontend/src/components/ThemeModal.tsx` | `themes.ts`의 테마 10종 스와치 |
| 상세 모달 | `frontend/src/components/DetailModal.tsx` | 영상 시계열 차트(`hours=168`)와 YouTube 링크. 빈 시계열은 정상 상태다(전체 Top30 진입 영상만 기록) |
| 추이 패널 | `frontend/src/components/TrendsPanel.tsx` | 카테고리 점유율 스택 AreaChart + 진입/이탈 BarChart(`hours=48`) |
| 브리핑 패널 | `frontend/src/components/BriefPanel.tsx` | LLM 3버튼 패널(오늘의 브리핑/어제와 비교/추이 리포트). 마크다운/평문 분기(`kind: 'llm' | 'status'`) |
| 모달 셸 | `frontend/src/components/Modal.tsx` | 공통 다이얼로그 — `role="dialog"`, 배경 클릭·Escape 닫기 |
| 스타일 토큰 | `frontend/src/styles.css` | `[data-theme]` CSS 변수 세트 10종(기본 `neon-hunter`, 라이트는 `cotton-candy`) + 파생 별칭(`--bg-elevated`, `--border` 등) |
| 차트 팔레트 | `frontend/src/chartColors.ts` | 테마 무관 고정 8색 팔레트. `seriesAccent`, `enteredColor`/`exitedColor` |
| 테마 전환 | `frontend/src/theme.ts`, `frontend/src/themes.ts` | 루트 요소 `data-theme` + localStorage `yt-theme`. 스와치 hex 사본은 `themes.ts`에 있다(`styles.css`와 동기 유지). localStorage 불가 시 조용히 무시 |

차트 인벤토리(전부 recharts):

- `TrendsPanel` — `/api/trends/categories?hours=48` 기반 점유율 스택 AreaChart + 진입/이탈 BarChart
- `DetailModal` — 순위 LineChart(Y 반전, 도메인 1–30)와 조회수 LineChart(로그/선형 토글), `/api/videos/{id}/history?hours=168` 기반
- 계열 색은 `chartColors.ts` 고정 팔레트를 쓰고, 차트 크롬(그리드·축·툴팁)은 테마 CSS 변수를 쓴다

### 3. 주요 결정
- 차트 팔레트는 테마별 세트가 아닌 테마 무관 고정 8색 배열 하나다. 테마 10종 전부 카드 배경 위에 차트를 올리므로 동일한 중간 채도 hex가 양쪽에서 대비를 유지하고, recharts가 SVG fill/stroke에서 `var()`를 안정적으로 해석하지 않아 계열 색은 고정 hex를 유지한다. 색은 항목이 아닌 슬롯에 귀속되고, 진입/이탈은 CVD 검증을 통과한 blue/red 쌍(슬롯 1/4)을 재사용한다.
- 배지 규칙은 nullable 파생 필드 계약을 따른다: `baseline === null` → 배지 없음(비교 불가), `prevRank === null` → NEW, `delta` 양수 → `▲n`, 음수 → `▼n`, 0 → 배지 없음. `viewsPerHour > 0`이면 `+N/시`를 표기한다. null과 0을 절대 혼용하지 않는다.
- LLM이 실제로 생성한 본문만 마크다운(`react-markdown` + `remark-gfm`)으로 렌더하고, 상태/오류 문구는 평문으로 렌더한다. `rehype-raw`는 계속 금지다 — LLM 출력의 raw HTML 렌더는 XSS 경로를 연다.
- 테마의 단일 진실은 `styles.css`의 `[data-theme]` 변수 세트다. `themes.ts`는 미리보기 스와치 사본을 들고, `index.html` 부트스트랩이 첫 페인트 전에 테마를 적용하며 구값을 마이그레이션한다(`dark` → `neon-hunter`, `light` → `cotton-candy`).
- 썸네일은 소프트 실패한다 — 타일은 깨진 이미지를 중립 폴백 블록으로 교체하고, 히어로는 `maxresdefault` 실패(`onError`) 시 저장된 썸네일로 폴백한다.

### 4. 코드 포인터
- `frontend/src/App.tsx` — 화면 구성, 폴링·세대 가드, 모달 상태
- `frontend/src/components/Row.tsx` — 배지/속도/태그 칩 규칙, `Tile`/`TopTile`
- `frontend/src/components/DetailModal.tsx`, `frontend/src/components/TrendsPanel.tsx` — 차트 인벤토리
- `frontend/src/components/BriefPanel.tsx` — 마크다운/평문 렌더 분기
- `frontend/src/styles.css` — 테마 토큰 세트 10종과 파생 별칭
- `frontend/src/chartColors.ts` — 고정 팔레트와 강조색 헬퍼
- `frontend/src/theme.ts`, `frontend/src/themes.ts`, `frontend/index.html` — 테마 지속화와 부트스트랩 마이그레이션

### 5. 상호 참조
- 관련 모듈: `frontend/src/components/`
- 관련 ADR: [ADR-001](../decisions/ADR-001-trend-radar-single-page-redesign.md) (단일 페이지 개편, 제외 행 결정)
- 관련 런북: 아직 없음
- 관련 레이어: [frontend.md](frontend.md), [api.md](api.md)(nullable 파생 필드 계약, `/api/home`·`/api/quiz` 계약)

Last updated: 2026-08-14
