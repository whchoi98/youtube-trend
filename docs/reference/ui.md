# UI / UI 구현 상세

[![English](https://img.shields.io/badge/Language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/Language-한국어-red)](#korean)

<a id="english"></a>
## English

### 1. Overview
Presentation layer of the SPA (topbar logo and page title are now "YOUTUBE TREND MONITOR", renamed from TREND RADAR; the layout concept is unchanged). A tab-style top menu in the topbar switches three views without a router — "홈" (hero billboard, selected-content trend panel, insight chips, a Netflix-style topic sidebar beside the horizontal snap strips), "시계열 추이" (video series panel), "점유율 · 리포트" (category share trends plus AI brief) — plus two modals, styled by a 10-theme CSS custom property system plus a fixed theme-independent chart palette. The former 3-tab layout (`src/tabs/`, `Card`/`CardGrid`/`Badge` components) was removed in the 2026-08-14 redesign (ADR-001); the video detail modal (`DetailModal.tsx`) was removed in the selection-flow rework.

### 2. Components

Screen composition (the top menu switches three views; items 2-5 form the "홈" view):

1. **Topbar** — "YOUTUBE TREND MONITOR" gradient logo, top menu (three tab-style buttons "홈"/"시계열 추이"/"점유율 · 리포트" — `.nav-tabs`/`.nav-tab` with `.active` accent underline, `role="tablist"`, `VIEWS`/`view` state in `App.tsx`, no router; switching scrolls to top), capture time (`수집 HH:MM` KST via `formatClockKst`), refresh button, theme button (`App.tsx`)
2. **Hero billboard** — overall #1 video by default: `maxresdefault` background image with `onError` fallback to the stored thumbnail, chart-in tenure (`N시간째 차트인`), first-entry chip (`오늘 첫 진입`), watch link and quiz launcher; clicking any tile swaps in that card Netflix-billboard style — title, category chip (`.hero-cat`), short `description` synopsis (`.hero-desc`), YouTube link, and a "✕ 1위 화면으로" clear button — and the page scrolls to top; when the shown card has `tags.comment`, an AI one-liner (`.hero-ai`, prefixed by an "AI" `.ai-chip` text chip) appears (`Hero.tsx`)
3. **Selected trend panel** — "선택한 콘텐츠 추이" with rank/views charts for the selected card, shown right under the hero only while a card is selected (`SelectedTrend.tsx`)
4. **Insight chips** — backend-computed one-line summaries, no LLM (`InsightChips.tsx`)
5. **Sidebar + snap strips** — a sticky left sidebar (`Sidebar.tsx`, topics derived from the home rows: "홈" plus one entry per row, grouped under `.side-head` headers 랭킹/YouTube Music/AI 추천/분야/국가/채널; a horizontal chip bar below 1024px with headers hidden) sits beside `Row.tsx` strips rendered in `/api/home` order: top10 (big rank numerals; carries 20 cards, home shows 10) → accel → new ("오늘 첫 진입") → climb ("순위 역주행") → chart (5 YouTube Music rows) → topic → vibe ("힐링이 필요할 때"/"도파민 충전소") → category → region → spotlight (3 channel rows — AWS/Anthropic/OpenAI); a quiz result row (`kind: 'quiz'`) is inserted client-side above them, and the "지금 뜨는 채널" avatar strip (`ChannelStrip.tsx`) slots in after the accel row (after top10 when accel is absent); selecting a sidebar topic replaces the strips with that topic's TOP 20 big-numeral focus view; tiles carry a top-left rank chip (`.tile-rank`) and an always-visible stats line, and hover/focus (precision pointers only, 350ms delay) opens a Netflix-style preview popover (`PreviewCard.tsx` — thumbnail, title, meta, `description`, an "AI 브리핑" `.ai-chip` label + `tags.comment`, tag chips)
6. **Sub views** — "시계열 추이" holds the video series panel (`VideoSeriesPanel`) and the "YouTube Music 시계열" panel (`ChartSeriesPanel`); "점유율 · 리포트" holds category share trends (`TrendsPanel`) and AI brief (`BriefPanel`); each renders inside a `.page` container (class renamed from `.bottom`); refresh remounts the panels of all three views via `panelKey`
7. **Modals** — quiz and theme picker, both on a common shell (`Modal.tsx`: backdrop click / Escape to close)

| Component | Path | Purpose |
|---|---|---|
| App shell | `frontend/src/App.tsx` | Topbar with the `.nav-tabs` top menu (`VIEWS`/`view` state, scroll to top on switch), `/api/home` load with 60s silent polling + generation-token guard (silent failures keep the current screen; polling continues regardless of the active view), `selected` card state (tile click → hero billboard + scroll to top), sidebar `focus` state (TOP 20 focus view; falls back to home when polling drops the topic), modal state, `panelKey` remount for the sub-view panels |
| Hero | `frontend/src/components/Hero.tsx` | Billboard — overall #1 by default or the tile-selected card (title, `.hero-cat` chip, `.hero-desc` synopsis, AI one-liner `.hero-ai` with an "AI" `.ai-chip` when `tags.comment` exists, watch link, "✕ 1위 화면으로" clear button); the watch CTA routes by selection origin (`music` prop): chart-origin selections open YouTube Music ("▶ YouTube Music에서 듣기"), everything else YouTube ("▶ 보러가기"); maxres background with per-videoId `onError` fallback, tenure hours, NEW chip, watch/quiz actions |
| Insight chips | `frontend/src/components/InsightChips.tsx` | Renders `insights[]` strings; hidden when empty |
| Row / tiles | `frontend/src/components/Row.tsx` | Scroll-snap strip with hover arrows; `Tile` and `TopTile` (Netflix-style big rank numeral over the thumbnail) with always-visible stats; `limit` prop trims display (top10 carries 20, home shows 10); title hint chips (AI 태깅 · 추정 / 시간당 증가 기준 / 기준선에 없던 신규 차트인 / 순위 상승폭 기준 / 공식 채널 인기 영상 / YouTube Music 공식 차트); top-left rank chip (`.tile-rank`, accent when rank <= 3; within-category rank on category rows, overall rank elsewhere), badge, popover trigger (350ms delay, `(hover: hover) and (pointer: fine)` only; closed on mouseleave/blur, capture-phase scroll, resize, Escape, or polling-driven card loss), thumbnail soft fallback |
| Sidebar | `frontend/src/components/Sidebar.tsx` | Sticky left topic list (`.sidebar`/`.side-item` — 13.5px weight 700, active 800 with an accent left border) derived from home rows via `rowKey`/`sideLabel`, grouped by `GROUPS` under `.side-head` headers (랭킹(top10/accel/new/climb)/YouTube Music/AI 추천(topic/vibe — vibe labeled 힐링/도파민)/분야/국가/채널 — letter-spacing emphasis; chart labels drop the "YouTube Music · " prefix, spotlight labels drop " 인기 영상" (AWS/Anthropic/OpenAI)); below 1024px it becomes a horizontal scroll chip bar (pill-shaped `.side-item`, headers hidden, groups laid out horizontally) |
| Channel strip | `frontend/src/components/ChannelStrip.tsx` | "지금 뜨는 채널" row — circular-avatar cards (`.chan-card`, rank chip reused) linking to each channel's YouTube page in a new tab; shows 구독/총 조회수/급상승 기여, and "구독자 비공개" when `subscribers` is null |
| Preview popover | `frontend/src/components/PreviewCard.tsx` | Body-portal box over the hovered tile — `position: fixed`, visual-only (`pointer-events: none`), `max-height: min(392px, 100vh - 16px)`; thumbnail, title (`.pv-title`), meta (`.pv-meta`), synopsis (`.pv-desc`), "AI 브리핑" label + `tags.comment` (`.pv-ai`), tag chips |
| Quiz modal | `frontend/src/components/QuizModal.tsx` | 3 questions → `POST /api/quiz` → type name + a custom row added at the top of home |
| Theme modal | `frontend/src/components/ThemeModal.tsx` | 10 theme swatches from `themes.ts` |
| Selected trend | `frontend/src/components/SelectedTrend.tsx` | "선택한 콘텐츠 추이" panel under the hero — history charts for the selected card; empty history is a normal state (only overall Top30 entrants are recorded) |
| History charts | `frontend/src/components/HistoryCharts.tsx` | Shared rank + views chart pair with log/linear toggle, used by `SelectedTrend` and `VideoSeriesPanel` (replaces the deleted `DetailModal.tsx`) |
| Video series panel | `frontend/src/components/VideoSeriesPanel.tsx` | "시계열 추이" view — Top30 video selector (`/api/trending?scope=all`) + history charts (`hours=168`); restores the old Trends-tab flow |
| Chart series panel | `frontend/src/components/ChartSeriesPanel.tsx` | "YouTube Music 시계열" panel on the same view — chart + song selectors built from the `/api/home` chart rows; history charts over `/api/charts/{chartId}/videos/{videoId}/history?hours=72` with `maxRank={20}`; a `.music-link` "YouTube Music에서 듣기" link for the selected song |
| History hook | `frontend/src/useVideoHistory.ts` | Generation-guarded `/api/videos/{id}/history?hours=168` fetch shared by the two panels above |
| Trends panel | `frontend/src/components/TrendsPanel.tsx` | Category share stacked AreaChart + entered/exited BarChart (`hours=48`) |
| Brief panel | `frontend/src/components/BriefPanel.tsx` | Three-button LLM panel (`오늘의 브리핑`/`어제와 비교`/`추이 리포트`) streaming from `GET /api/brief/stream`: pipeline trace (`.brief-steps` — running ⋯ / done ✓ / failed ✗ plus ms), rAF-batched markdown streaming, partial-result warning (`.brief-error`) on in-band error, 503 lock (`.brief-locked`); LLM text renders as markdown, status/error strings as plain text |
| Modal shell | `frontend/src/components/Modal.tsx` | Shared dialog: `role="dialog"`, backdrop click and Escape close |
| Style tokens | `frontend/src/styles.css` | 10 `[data-theme]` CSS variable sets (default `neon-hunter`; `cotton-candy` is the light theme) plus derived aliases (`--bg-elevated`, `--border`, …); gradient accent bars on headings (`.row h2::before`/`.panel h2::before`, 3px accent→accent2) and the shared `.ai-chip` text chip |
| Chart palette | `frontend/src/chartColors.ts` | Fixed theme-independent 8-color palette; `seriesAccent`, `enteredColor`/`exitedColor` |
| Theme switch | `frontend/src/theme.ts`, `frontend/src/themes.ts` | `data-theme` on the root element + localStorage `yt-theme`; swatch hex copies live in `themes.ts` (kept in sync with `styles.css`); graceful no-op when localStorage is unavailable |

Chart inventory (all recharts):

- `TrendsPanel` — stacked share AreaChart over `/api/trends/categories?hours=48` plus an entered/exited BarChart
- `HistoryCharts` — rank LineChart (Y reversed, domain 1–`maxRank`, default 30) and views LineChart with a log/linear toggle; rendered in three places — `SelectedTrend` (under the hero) and `VideoSeriesPanel` (both over `/api/videos/{id}/history?hours=168` via `useVideoHistory`), and `ChartSeriesPanel` (over `/api/charts/{chartId}/videos/{videoId}/history?hours=72`, `maxRank={20}`; off-chart hours render as gaps — null points)
- Series colors come from the fixed `chartColors.ts` palette; chart chrome (grid, axes, tooltip) uses theme CSS variables

### 3. Key Decisions
- The chart palette is one fixed theme-independent 8-color array, not per-theme sets: all 10 themes put charts on card backgrounds where the same mid-saturation hexes keep contrast, and recharts does not reliably resolve `var()` in SVG fill/stroke, so series colors stay fixed hex. Colors bind to slots, not items; entered/exited reuses the blue/red pair (slots 1/4) validated for CVD.
- Badge rules follow the nullable derived-field contract: `baseline === null` → no badge (comparison impossible), `prevRank === null` → NEW, positive `delta` → `▲n`, negative → `▼n`, `delta === 0` → `–` (`badge.same`, measured no change). `viewsPerHour > 0` renders `+N/시`; null and 0 are never conflated.
- Every tile carries a top-left rank chip (`.tile-rank`, accent style when rank <= 3): category rows show the within-category rank, all other rows the overall rank.
- LLM text renders as markdown (`react-markdown` + `remark-gfm`) only when it actually came from the LLM; status and error strings render as plain text. `rehype-raw` stays banned — raw HTML from LLM output would open an XSS path.
- Theme truth lives in `styles.css` `[data-theme]` variable sets; `themes.ts` holds preview swatch copies, and the `index.html` bootstrap applies the theme before first paint and migrates legacy values (`dark` → `neon-hunter`, `light` → `cotton-candy`).
- Thumbnails fail soft: tiles swap a broken image for a neutral fallback block, and the hero falls back from `maxresdefault` to the stored thumbnail on `onError`.
- The preview popover and the hero AI line degrade gracefully: cards from pre-`description` snapshots or pre-`comment` tag buckets simply omit that line — no placeholder is shown.
- The tile preview is a body-portal popover rather than an inline expansion: `pointer-events: none` keeps clicks and hover on the tile underneath, the fixed-position box escapes the strip's overflow clipping, the precision-pointer gate (evaluated per call) keeps touch taps from sticking a popover open, and scroll (capture phase, so strip-internal scrolling counts)/resize/Escape/card-loss all close it before its anchor rect goes stale.
- The top menu keeps the old tab look (accent-underline `.nav-tab.active`) without a router: one `view` state switches the three views, every switch scrolls to top, and sub views sit in a `.page` container (renamed from `.bottom`); the 60s home polling runs regardless of the active view.
- The sidebar and the focus view add no new visual language: sidebar entries are short labels stripped from the row titles (`sideLabel`), and the focus view reuses the `top10` big-numeral row style for any topic's TOP 20 — one strip layout serves both home and focus.
- The UI is emoji-free by design: backend row titles ship plain text ("지금 한국 급상승 TOP 10", "조회수 급증 중", "오늘 첫 진입", "순위 역주행", the five "YouTube Music · …" chart titles, "힐링이 필요할 때"/"도파민 충전소", the "{name} 인기 영상" spotlight titles, category names verbatim, "미국은 지금" — the "추정" qualifier lives in the AI-row hint, not the title), insight chips carry no emoji, and frontend labels ("테마", "내 취향 찾기", "홈", the tagging notice) dropped theirs. Visual anchoring moved to the gradient heading bars, the `.side-head` group headers, and the `.ai-chip` text chip ("AI" on the hero line, "AI 브리핑" in the popover — `.pv-ai-label` was removed).

### 4. Code Pointers
- `frontend/src/App.tsx` — screen composition, polling and generation guard, selected-card state, modal state
- `frontend/src/components/Row.tsx`, `frontend/src/components/PreviewCard.tsx` — rank-chip/badge/velocity rules, `Tile`/`TopTile`, hover popover
- `frontend/src/components/Sidebar.tsx` — topic list, `rowKey`/`sideLabel`, chip-bar breakpoint
- `frontend/src/components/HistoryCharts.tsx`, `frontend/src/components/TrendsPanel.tsx` — chart inventory
- `frontend/src/components/SelectedTrend.tsx`, `frontend/src/components/VideoSeriesPanel.tsx`, `frontend/src/useVideoHistory.ts` — selection trend and video series flows
- `frontend/src/components/BriefPanel.tsx` — SSE stream consumption, `.brief-steps` trace, markdown vs plain-text rendering split
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
SPA의 프레젠테이션 계층이다(톱바 로고·페이지 타이틀은 "YOUTUBE TREND MONITOR"로 개명 — 구 TREND RADAR, 레이아웃 콘셉트는 그대로다). 톱바의 기존 탭 스타일 상단 메뉴가 라우터 없이 3화면을 전환한다 — "홈"(히어로 빌보드, 선택 콘텐츠 추이 패널, 인사이트 칩, 가로 스냅 스트립 옆 넷플릭스식 주제 사이드바), "시계열 추이"(영상 시계열 패널), "점유율 · 리포트"(카테고리 점유율 추이 + AI 브리핑) — 여기에 모달 2종이 더해지며, 테마 10종 CSS 커스텀 프로퍼티 시스템과 테마 무관 고정 차트 팔레트로 스타일링한다. 기존 3탭 레이아웃(`src/tabs/`, `Card`/`CardGrid`/`Badge` 컴포넌트)은 2026-08-14 개편(ADR-001)에서 삭제됐고, 영상 상세 모달(`DetailModal.tsx`)은 선택 흐름 개편에서 삭제됐다.

### 2. 구성요소

화면 구성(상단 메뉴가 3화면을 전환하며, 2~5항이 "홈" 화면이다):

1. **톱바** — "YOUTUBE TREND MONITOR" 그라디언트 로고, 상단 메뉴(기존 탭 스타일 버튼 3개 "홈"/"시계열 추이"/"점유율 · 리포트" — `.nav-tabs`/`.nav-tab` + `.active` 액센트 언더라인, `role="tablist"`, `App.tsx`의 `VIEWS`/`view` 상태, 라우터 없음. 전환 시 최상단 스크롤), 수집 시각(`수집 HH:MM` KST, `formatClockKst`), 새로고침 버튼, 테마 버튼 (`App.tsx`)
2. **히어로 빌보드** — 기본은 전체 1위 영상: `maxresdefault` 배경 이미지 + `onError` 시 저장된 썸네일 폴백, 차트인 시간(`N시간째 차트인`), 첫 진입 칩(`오늘 첫 진입`), 보러가기·퀴즈 버튼. 타일을 클릭하면 넷플릭스 빌보드처럼 그 카드로 전환된다 — 제목, 카테고리 칩(`.hero-cat`), 간단한 소개 `description`(`.hero-desc`), YouTube 링크, "✕ 1위 화면으로" 해제 버튼 — 그리고 페이지가 최상단으로 스크롤된다. 표시 중인 카드에 `tags.comment`가 있으면 AI 한 줄 분석(`.hero-ai` — "AI" `.ai-chip` 텍스트 칩이 앞에 붙는다)이 표시된다 (`Hero.tsx`)
3. **선택 콘텐츠 추이 패널** — 선택 카드의 순위/조회수 차트를 담은 "선택한 콘텐츠 추이". 카드가 선택된 동안에만 히어로 바로 아래 표시된다 (`SelectedTrend.tsx`)
4. **인사이트 칩** — 백엔드가 계산한 한 줄 요약, LLM 미사용 (`InsightChips.tsx`)
5. **사이드바 + 스냅 스트립** — 고정(sticky) 좌측 사이드바(`Sidebar.tsx`, 홈 행에서 파생된 주제 목록: "홈" + 행별 항목을 `.side-head` 헤더 랭킹/YouTube Music/AI 추천/분야/국가/채널로 묶음. 1024px 미만은 헤더를 숨긴 가로 칩 바)가 `Row.tsx` 스트립 옆에 붙고, 스트립은 `/api/home` 순서대로 렌더한다: top10(큰 순위 숫자 — 20개 운반, 홈은 10개 표시) → accel → new("오늘 첫 진입") → climb("순위 역주행") → chart(YouTube Music 5행) → topic → vibe("힐링이 필요할 때"/"도파민 충전소") → category → region → spotlight(채널 3행 — AWS/Anthropic/OpenAI). 퀴즈 결과 행(`kind: 'quiz'`)은 클라이언트에서 그 위에 삽입하고, "지금 뜨는 채널" 아바타 스트립(`ChannelStrip.tsx`)은 급증 행 뒤(급증 행이 없으면 top10 뒤)에 끼워진다. 사이드바 주제를 선택하면 스트립이 그 주제의 TOP 20 빅넘버 포커스 뷰로 바뀐다. 타일 좌상단에 순위 칩(`.tile-rank`)이 붙고 통계 줄은 상시 표시되며, hover/focus(정밀 포인터 전용, 350ms 지연) 시 넷플릭스식 미리보기 팝오버(`PreviewCard.tsx` — 썸네일·제목·메타·`description`·"AI 브리핑" `.ai-chip` 라벨 + `tags.comment`·태그 칩)가 뜬다
6. **서브 화면** — "시계열 추이"는 영상 시계열 패널(`VideoSeriesPanel`)과 "YouTube Music 시계열" 패널(`ChartSeriesPanel`), "점유율 · 리포트"는 카테고리 점유율 추이(`TrendsPanel`) + AI 브리핑(`BriefPanel`)을 담는다. 각각 `.page` 컨테이너(구 `.bottom`에서 개명)에 렌더하고, 새로고침이 `panelKey`로 세 화면의 패널을 모두 remount한다
7. **모달** — 퀴즈, 테마 선택. 공통 셸(`Modal.tsx`: 배경 클릭/Escape 닫기)을 공유한다

| 구성요소 | 경로 | 목적 |
|---|---|---|
| 앱 셸 | `frontend/src/App.tsx` | 톱바 + `.nav-tabs` 상단 메뉴(`VIEWS`/`view` 상태, 전환 시 최상단 스크롤), `/api/home` 60초 silent 폴링 + 세대 토큰 가드(silent 실패는 기존 화면 유지, 폴링은 활성 화면과 무관하게 지속), `selected` 카드 상태(타일 클릭 → 히어로 빌보드 + 최상단 스크롤), 사이드바 `focus` 상태(TOP 20 포커스 뷰 — 폴링으로 주제 소실 시 홈 복귀), 모달 상태, 서브 화면 패널 `panelKey` remount |
| 히어로 | `frontend/src/components/Hero.tsx` | 빌보드 — 기본은 전체 1위, 타일 선택 시 그 카드(제목, `.hero-cat` 칩, `.hero-desc` 소개문, `tags.comment` 있으면 "AI" `.ai-chip` 포함 AI 한 줄 분석 `.hero-ai`, 시청 링크, "✕ 1위 화면으로" 해제 버튼)로 전환. 시청 CTA는 선택 출처(`music` prop)로 분기한다 — 차트 유래 선택은 YouTube Music("▶ YouTube Music에서 듣기"), 그 외는 YouTube("▶ 보러가기"). maxres 배경 + videoId 단위 `onError` 폴백, 차트인 시간, NEW 칩, 보러가기/퀴즈 액션 |
| 인사이트 칩 | `frontend/src/components/InsightChips.tsx` | `insights[]` 문자열 렌더. 비어 있으면 숨김 |
| 행/타일 | `frontend/src/components/Row.tsx` | 스크롤 스냅 스트립 + hover 화살표. `Tile`·`TopTile`(넷플릭스식 큰 순위 숫자가 썸네일에 겹침) — 통계 줄 상시 표시. `limit` prop 표시 절단(top10은 20개 운반, 홈은 10개 표시). 제목 힌트 칩(AI 태깅 · 추정/시간당 증가 기준/기준선에 없던 신규 차트인/순위 상승폭 기준/공식 채널 인기 영상/YouTube Music 공식 차트). 좌상단 순위 칩(`.tile-rank`, rank <= 3이면 액센트 — 분야 행은 분야 내 순위, 나머지는 전체 순위), 배지, 팝오버 트리거(350ms 지연, `(hover: hover) and (pointer: fine)` 전용. mouseleave/blur·캡처 단계 scroll·resize·Escape·폴링에 의한 카드 소실 시 닫힘), 썸네일 소프트 폴백 |
| 사이드바 | `frontend/src/components/Sidebar.tsx` | 고정 좌측 주제 목록(`.sidebar`/`.side-item` — 13.5px 굵기 700, 활성은 800 + 액센트 좌측 보더) — `rowKey`/`sideLabel`로 홈 행에서 파생하고 `GROUPS`가 `.side-head` 헤더(랭킹(top10/accel/new/climb)/YouTube Music/AI 추천(topic/vibe — vibe 라벨은 힐링/도파민)/분야/국가/채널 — letter-spacing 강조. chart 라벨은 "YouTube Music · " 접두 제거, spotlight 라벨은 " 인기 영상" 제거(AWS/Anthropic/OpenAI))로 묶는다. 1024px 미만에서는 가로 스크롤 칩 바(알약형 `.side-item`, 헤더 숨김, 그룹 가로 배치)로 전환 |
| 채널 스트립 | `frontend/src/components/ChannelStrip.tsx` | "지금 뜨는 채널" 행 — 원형 아바타 카드(`.chan-card`, 순위 칩 재사용)가 채널 YouTube 페이지를 새 탭으로 연다. 구독/총 조회수/급상승 기여를 표기하고 `subscribers`가 null이면 "구독자 비공개" |
| 미리보기 팝오버 | `frontend/src/components/PreviewCard.tsx` | hover 중인 타일 위에 뜨는 body 포털 박스 — `position: fixed`, 시각 전용(`pointer-events: none`), `max-height: min(392px, 100vh - 16px)`. 썸네일, 제목(`.pv-title`), 메타(`.pv-meta`), 소개문(`.pv-desc`), "AI 브리핑" 라벨 + `tags.comment`(`.pv-ai`), 태그 칩 |
| 퀴즈 모달 | `frontend/src/components/QuizModal.tsx` | 3문항 → `POST /api/quiz` → 유형명 + 홈 맨 위 맞춤 행 추가 |
| 테마 모달 | `frontend/src/components/ThemeModal.tsx` | `themes.ts`의 테마 10종 스와치 |
| 선택 콘텐츠 추이 | `frontend/src/components/SelectedTrend.tsx` | 히어로 아래 "선택한 콘텐츠 추이" 패널 — 선택 카드의 시계열 차트. 빈 시계열은 정상 상태다(전체 Top30 진입 영상만 기록) |
| 시계열 차트 | `frontend/src/components/HistoryCharts.tsx` | 공용 순위+조회수 차트 쌍 + 로그/선형 토글 — `SelectedTrend`·`VideoSeriesPanel`이 사용(삭제된 `DetailModal.tsx` 대체) |
| 영상 시계열 패널 | `frontend/src/components/VideoSeriesPanel.tsx` | "시계열 추이" 화면 — Top30 영상 셀렉터(`/api/trending?scope=all`) + 시계열 차트(`hours=168`). 구 추이 분석 탭 흐름 복원 |
| 차트 시계열 패널 | `frontend/src/components/ChartSeriesPanel.tsx` | 같은 화면의 "YouTube Music 시계열" 패널 — `/api/home`의 chart 행으로 차트+곡 셀렉터 구성. `/api/charts/{chartId}/videos/{videoId}/history?hours=72` 기반 시계열 차트, `maxRank={20}`. 선택 곡의 "YouTube Music에서 듣기" 링크(`.music-link`) 포함 |
| 시계열 훅 | `frontend/src/useVideoHistory.ts` | 세대 가드 포함 `/api/videos/{id}/history?hours=168` 로드 — 위 두 패널이 공유 |
| 추이 패널 | `frontend/src/components/TrendsPanel.tsx` | 카테고리 점유율 스택 AreaChart + 진입/이탈 BarChart(`hours=48`) |
| 브리핑 패널 | `frontend/src/components/BriefPanel.tsx` | LLM 3버튼 패널(오늘의 브리핑/어제와 비교/추이 리포트) — `GET /api/brief/stream` 스트리밍 소비. 파이프라인 트레이스(`.brief-steps` — 실행 중 ⋯/완료 ✓/실패 ✗ + ms), rAF 배칭 마크다운 스트리밍, in-band error 시 부분 결과 경고(`.brief-error`), 503 잠금(`.brief-locked`). LLM 본문은 마크다운, 상태/오류 문구는 평문 렌더 |
| 모달 셸 | `frontend/src/components/Modal.tsx` | 공통 다이얼로그 — `role="dialog"`, 배경 클릭·Escape 닫기 |
| 스타일 토큰 | `frontend/src/styles.css` | `[data-theme]` CSS 변수 세트 10종(기본 `neon-hunter`, 라이트는 `cotton-candy`) + 파생 별칭(`--bg-elevated`, `--border` 등). 제목 그라디언트 액센트 바(`.row h2::before`/`.panel h2::before`, 3px accent→accent2)와 공용 `.ai-chip` 텍스트 칩 포함 |
| 차트 팔레트 | `frontend/src/chartColors.ts` | 테마 무관 고정 8색 팔레트. `seriesAccent`, `enteredColor`/`exitedColor` |
| 테마 전환 | `frontend/src/theme.ts`, `frontend/src/themes.ts` | 루트 요소 `data-theme` + localStorage `yt-theme`. 스와치 hex 사본은 `themes.ts`에 있다(`styles.css`와 동기 유지). localStorage 불가 시 조용히 무시 |

차트 인벤토리(전부 recharts):

- `TrendsPanel` — `/api/trends/categories?hours=48` 기반 점유율 스택 AreaChart + 진입/이탈 BarChart
- `HistoryCharts` — 순위 LineChart(Y 반전, 도메인 1–`maxRank`, 기본 30)와 조회수 LineChart(로그/선형 토글). 렌더 위치는 세 곳 — `SelectedTrend`(히어로 아래)와 `VideoSeriesPanel`(둘 다 `useVideoHistory` 경유 `/api/videos/{id}/history?hours=168`), `ChartSeriesPanel`(`/api/charts/{chartId}/videos/{videoId}/history?hours=72`, `maxRank={20}` — 차트 밖 시각은 null 포인트라 끊긴 선으로 표시)
- 계열 색은 `chartColors.ts` 고정 팔레트를 쓰고, 차트 크롬(그리드·축·툴팁)은 테마 CSS 변수를 쓴다

### 3. 주요 결정
- 차트 팔레트는 테마별 세트가 아닌 테마 무관 고정 8색 배열 하나다. 테마 10종 전부 카드 배경 위에 차트를 올리므로 동일한 중간 채도 hex가 양쪽에서 대비를 유지하고, recharts가 SVG fill/stroke에서 `var()`를 안정적으로 해석하지 않아 계열 색은 고정 hex를 유지한다. 색은 항목이 아닌 슬롯에 귀속되고, 진입/이탈은 CVD 검증을 통과한 blue/red 쌍(슬롯 1/4)을 재사용한다.
- 배지 규칙은 nullable 파생 필드 계약을 따른다: `baseline === null` → 배지 없음(비교 불가), `prevRank === null` → NEW, `delta` 양수 → `▲n`, 음수 → `▼n`, `delta === 0` → `–`(`badge.same`, 실측 변동 없음). `viewsPerHour > 0`이면 `+N/시`를 표기한다. null과 0을 절대 혼용하지 않는다.
- 모든 타일은 좌상단 순위 칩(`.tile-rank`, rank <= 3이면 액센트 스타일)을 단다: 분야 행은 분야 내 순위, 나머지 행은 전체 순위를 표시한다.
- LLM이 실제로 생성한 본문만 마크다운(`react-markdown` + `remark-gfm`)으로 렌더하고, 상태/오류 문구는 평문으로 렌더한다. `rehype-raw`는 계속 금지다 — LLM 출력의 raw HTML 렌더는 XSS 경로를 연다.
- 테마의 단일 진실은 `styles.css`의 `[data-theme]` 변수 세트다. `themes.ts`는 미리보기 스와치 사본을 들고, `index.html` 부트스트랩이 첫 페인트 전에 테마를 적용하며 구값을 마이그레이션한다(`dark` → `neon-hunter`, `light` → `cotton-candy`).
- 썸네일은 소프트 실패한다 — 타일은 깨진 이미지를 중립 폴백 블록으로 교체하고, 히어로는 `maxresdefault` 실패(`onError`) 시 저장된 썸네일로 폴백한다.
- 미리보기 팝오버와 히어로 AI 줄은 우아하게 강등된다: `description` 도입 이전 스냅샷이나 `comment` 도입 이전 태그 버킷의 카드는 해당 줄만 생략된다 — 플레이스홀더를 표시하지 않는다.
- 타일 미리보기는 인라인 확장이 아니라 body 포털 팝오버다: `pointer-events: none`으로 클릭·hover는 밑의 타일이 계속 받고, fixed 좌표 박스는 스트립 overflow 클리핑을 벗어난다. 정밀 포인터 게이트(호출 시점 평가)가 터치 탭에 팝오버가 붙어 떨어지지 않는 것을 막고, scroll(캡처 단계 — 스트립 내부 스크롤까지 커버)/resize/Escape/카드 소실이 전부 닫기 조건이라 앵커 rect가 낡기 전에 닫힌다.
- 상단 메뉴는 라우터 없이 기존 탭 룩(`.nav-tab.active` 액센트 언더라인)을 유지한다: `view` 상태 하나가 3화면을 전환하고, 전환 시마다 최상단으로 스크롤하며, 서브 화면은 `.page` 컨테이너(구 `.bottom`에서 개명)에 놓인다. 60초 홈 폴링은 활성 화면과 무관하게 돈다.
- 사이드바와 포커스 뷰는 새 시각 언어를 더하지 않는다: 사이드바 항목은 행 제목의 수식을 걷어낸 짧은 라벨(`sideLabel`)이고, 포커스 뷰는 어떤 주제든 `top10` 빅넘버 행 스타일을 재사용해 TOP 20을 보여준다 — 하나의 스트립 레이아웃이 홈과 포커스를 모두 담당한다.
- UI는 설계상 이모지를 쓰지 않는다: 백엔드 행 제목이 평문으로 온다("지금 한국 급상승 TOP 10", "조회수 급증 중", "오늘 첫 진입", "순위 역주행", "YouTube Music · …" 차트 제목 5행, "힐링이 필요할 때"/"도파민 충전소", 스포트라이트 제목 "{이름} 인기 영상", 분야명 원문, "미국은 지금" — "추정" 수식은 제목이 아니라 AI 행 힌트에 있다). 인사이트 칩에도 이모지가 없고, 프론트 라벨("테마", "내 취향 찾기", "홈", 태깅 안내문)도 이모지를 걷어냈다. 시각적 앵커는 제목 그라디언트 바, `.side-head` 그룹 헤더, `.ai-chip` 텍스트 칩(히어로 줄 "AI", 팝오버 "AI 브리핑" — `.pv-ai-label` 삭제)이 담당한다.

### 4. 코드 포인터
- `frontend/src/App.tsx` — 화면 구성, 폴링·세대 가드, 선택 카드 상태, 모달 상태
- `frontend/src/components/Row.tsx`, `frontend/src/components/PreviewCard.tsx` — 순위 칩/배지/속도 규칙, `Tile`/`TopTile`, hover 팝오버
- `frontend/src/components/Sidebar.tsx` — 주제 목록, `rowKey`/`sideLabel`, 칩 바 브레이크포인트
- `frontend/src/components/HistoryCharts.tsx`, `frontend/src/components/TrendsPanel.tsx` — 차트 인벤토리
- `frontend/src/components/SelectedTrend.tsx`, `frontend/src/components/VideoSeriesPanel.tsx`, `frontend/src/useVideoHistory.ts` — 선택 추이·영상 시계열 흐름
- `frontend/src/components/BriefPanel.tsx` — SSE 스트림 소비, `.brief-steps` 트레이스, 마크다운/평문 렌더 분기
- `frontend/src/styles.css` — 테마 토큰 세트 10종과 파생 별칭
- `frontend/src/chartColors.ts` — 고정 팔레트와 강조색 헬퍼
- `frontend/src/theme.ts`, `frontend/src/themes.ts`, `frontend/index.html` — 테마 지속화와 부트스트랩 마이그레이션

### 5. 상호 참조
- 관련 모듈: `frontend/src/components/`
- 관련 ADR: [ADR-001](../decisions/ADR-001-trend-radar-single-page-redesign.md) (단일 페이지 개편, 제외 행 결정)
- 관련 런북: 아직 없음
- 관련 레이어: [frontend.md](frontend.md), [api.md](api.md)(nullable 파생 필드 계약, `/api/home`·`/api/quiz` 계약)

Last updated: 2026-08-17
