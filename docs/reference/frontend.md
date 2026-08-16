# Frontend / Frontend 구현 상세

[![English](https://img.shields.io/badge/Language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/Language-한국어-red)](#korean)

<a id="english"></a>
## English

### 1. Overview
React 18 + Vite + TypeScript SPA — no router (logo and page title are now "YOUTUBE TREND MONITOR", renamed from TREND RADAR; the layout concept is unchanged): the top bar (logo, top menu, capture time in KST, refresh, theme button) carries a tab-style top menu that switches three views via a single `view` state: "홈" (hero billboard — overall #1 by default or the tile-selected card — plus selected-content trend panel, insight chips, and a topic sidebar beside horizontal strip rows top10 / accel / chart / spotlight / topic / age / category / region with a client-inserted quiz row), "시계열 추이" (video series panel), and "점유율 · 리포트" (category share trends plus LLM brief). It consumes the backend `/api/*` contract only; the gate is `npx tsc --noEmit && npm run build` (no test runner).

### 2. Components
| Component | Path | Purpose |
|---|---|---|
| App shell | `frontend/src/App.tsx` | Top bar with the `.nav-tabs` top menu (`VIEWS`/`view` state, `role="tablist"`, no router; switching scrolls to top), `/api/home` load with 60-second silent polling plus generation guard, `selected` card state (tile click swaps the hero billboard and scrolls to top), sidebar `focus` state (`focusRow` memo reuses the `top10` kind for a TOP 20 big-numeral view; when polling drops the topic an effect returns to home), modal state, `panelKey` remount for the sub-view panels |
| API client | `frontend/src/api.ts` | `fetchJson`/`postJson` plus `ApiError` carrying `status` and the `{error}` body from the backend contract |
| Hero | `frontend/src/components/Hero.tsx` | Netflix-style billboard — overall #1 by default; a tile-selected card swaps in its title, category chip (`.hero-cat`), short `description` synopsis (`.hero-desc`), YouTube link, and a "✕ 1위 화면으로" clear button; a "🤖" AI one-liner (`.hero-ai`) renders whenever the shown card has `tags.comment`; maxres background `img` with per-videoId `onError` fallback, chart-in tenure hours, NEW chip, watch / quiz CTAs |
| Insight chips | `frontend/src/components/InsightChips.tsx` | Rule-based insight strings from `/api/home` (no LLM) |
| Strip row | `frontend/src/components/Row.tsx` | Scroll-snap strip with hover arrows; `Tile`/`TopTile` (large rank numerals, `-webkit-text-stroke`) with an always-visible stats line; `limit` prop trims display (the top10 row carries 20 cards, home shows 10); hint chip next to the title (topic/age "AI 태깅", accel "시간당 증가 기준", spotlight "AWS Korea 채널", chart "YouTube Music 공식 주간 차트"); top-left rank chip (`.tile-rank`, accent style when rank <= 3; category rows show the within-category rank, other rows the overall rank); tile hover/focus opens the `PreviewCard` popover after a 350ms delay, precision pointers only (`(hover: hover) and (pointer: fine)`, evaluated at call time); badges — `baseline === null` renders nothing, `prevRank === null` renders NEW, `delta` renders ▲/▼, `delta === 0` renders "–" (`badge same`), `viewsPerHour > 0` renders "+N/시" |
| Sidebar | `frontend/src/components/Sidebar.tsx` | Netflix-style left topic list derived from the home rows themselves (`rowKey`/`sideLabel`, quiz row excluded — only topics with data appear); selecting one shows its TOP 20 focus view, "🏠 홈" clears it; below 1024px it becomes a horizontal chip bar |
| Preview popover | `frontend/src/components/PreviewCard.tsx` | Netflix-style tile preview — `createPortal` to `document.body` (escapes strip overflow), `position: fixed`, visual-only (`pointer-events: none`), width 340 clamped to the viewport, `max-height: min(392px, 100vh - 16px)`; thumbnail, title, meta, `description` (`.pv-desc`), "AI 브리핑" label + `tags.comment` (`.pv-ai`), tag chips; closes on mouseleave/blur, capture-phase window scroll, resize, Escape, or when polling drops the hovered card |
| Quiz modal | `frontend/src/components/QuizModal.tsx` | 3 questions → `POST /api/quiz` → type name plus a `kind='quiz'` row inserted at the top of the home rows |
| Theme modal | `frontend/src/components/ThemeModal.tsx` | 10 theme swatches from `src/themes.ts` |
| Selected trend | `frontend/src/components/SelectedTrend.tsx` | "선택한 콘텐츠 추이" panel right under the hero — rank/views charts for the selected card; empty history shows a notice (only videos that entered the overall Top 30 are recorded) |
| History charts | `frontend/src/components/HistoryCharts.tsx` | Shared rank + views `LineChart` pair with a log/linear toggle — rendered by `SelectedTrend` and `VideoSeriesPanel` (replaces the deleted `DetailModal.tsx`) |
| Video series panel | `frontend/src/components/VideoSeriesPanel.tsx` | "시계열 추이" view panel — video selector over `/api/trending?scope=all` plus history charts (`hours=168`); restores the old Trends-tab flow |
| History hook | `frontend/src/useVideoHistory.ts` | Generation-guarded `/api/videos/{id}/history?hours=168` fetch shared by `SelectedTrend` and `VideoSeriesPanel` |
| Trends panel | `frontend/src/components/TrendsPanel.tsx` | Category share stacked `AreaChart` plus entered/exited `BarChart` (`hours=48`) |
| Brief panel | `frontend/src/components/BriefPanel.tsx` | Consumes `GET /api/brief/stream` (fetch + `ReadableStream` SSE parsing) instead of the POST endpoints (their contracts are unchanged — the frontend just no longer calls them); pipeline trace UI (`.brief-steps` — running ⋯ / done ✓ / failed ✗ plus ms), deltas batched per `requestAnimationFrame` to limit markdown re-parsing, in-band `error` shows a partial-result warning (`.brief-error`), 503 keeps the panel locked; react-markdown render |
| Modal shell | `frontend/src/components/Modal.tsx` | Shared shell — backdrop click or Escape closes |
| Contract types | `frontend/src/types.ts` | `Card`/`HomeCard`/`HomeRow`/`HomeHero`/`HomeData`/`QuizAnswers`/`QuizResult` plus `Category`/`HistoryPoint`/`TrendBucket`/`Loadable` (nullable derived fields; optional `description` and `Tags.comment` — absent on snapshots/tag buckets stored before each field was introduced; `RowKind` includes `chart`/`spotlight`/`region`, `HomeRow` carries optional `regionCode`) |
| Formatting | `frontend/src/format.ts` | `formatCount` (Korean 만/억 abbreviation), `formatTsKst` (UTC hour bucket to KST wall clock), `formatClockKst` (ISO to KST HH:MM), `youtubeUrl` |
| Theme state | `frontend/src/theme.ts` | `getTheme`/`setTheme` over `documentElement.dataset.theme` + localStorage `yt-theme`; first paint handled by an `index.html` bootstrap script |
| Chart colors | `frontend/src/chartColors.ts` | Theme-independent fixed 8-color palette (slot-bound) — recharts does not reliably apply CSS `var()` to SVG fill/stroke |

### 3. Key Decisions
- No router: the tab-style top menu (`.nav-tabs`/`.nav-tab.active` accent underline, `role="tablist"`) switches the three views through the single `VIEWS`/`view` state in `App.tsx`, scrolling to top on every switch; sub views render inside a `.page` container (class renamed from `.bottom`). The home view is composed from one `GET /api/home` response; the quiz row is the only client-made row (`kind='quiz'`).
- Tile clicks select content instead of opening a modal (`DetailModal.tsx` was deleted): `App.tsx` keeps a `selected` state, the hero becomes a Netflix-style billboard for the selected card, the page scrolls to top, and the "선택한 콘텐츠 추이" panel (`SelectedTrend`) appears right under the hero; "✕ 1위 화면으로" clears the selection back to the overall #1.
- Optional card fields degrade gracefully: a card without `description` (pre-field snapshot) or `tags.comment` (pre-field tag bucket) simply omits the corresponding popover / hero line — no placeholder.
- The sidebar is derived, not fetched: its topics come from the home rows (`rowKey`/`sideLabel`), so only topics with data appear and no extra request is made. The focus view reuses the `top10` row kind for TOP 20 big numerals; if polling drops the focused topic, the memoized `focusRow` turns null and an effect falls back to home.
- Tile previews are a body-portal popover, not an inline expansion: the tile keeps its always-visible stats and click behavior (the popover is `pointer-events: none`), touch taps never trigger it (precision-pointer media query), and stale anchors are avoided by closing on scroll/resize/Escape and on polling-driven card loss.
- `/api/home` is polled every 60 seconds in silent mode, regardless of the active view. A generation token (a sequence ref captured per request) discards late responses; a failed silent poll keeps the current screen instead of showing an error. This generation-token race guard must be kept on any new async-fetch-then-setState code.
- Loading/error/ready are modeled as a discriminated union (`HomeState`) — no boolean flag combinations.
- `ApiError` surfaces the backend's Korean `error` message directly; fallbacks are local Korean strings.
- KST conversion shifts the Date by +9h and reads `getUTC*` accessors, so rendering is identical regardless of the viewer's local timezone.
- Refresh reloads home and bumps `panelKey` to remount the panels of all three views (video series, category share trends, LLM brief) — those panels are excluded from polling and refetch only on manual refresh.
- Themes are CSS-variable sets: the 10 `[data-theme]` blocks in `styles.css` are the single truth (default `neon-hunter`; `cotton-candy` is the light theme). `src/themes.ts` swatches and the `index.html` bootstrap valid-id list are kept in sync. Legacy localStorage values are migrated at bootstrap: `dark` → `neon-hunter`, `light` → `cotton-candy`.
- Chart colors bypass the theme system — the fixed palette in `chartColors.ts` is used because recharts SVG cannot take CSS `var()`.
- `rehype-raw` stays banned in react-markdown — rendering raw HTML from LLM output would open an XSS path.
- Frontend gate is compile plus build only (`npx tsc --noEmit && npm run build`); behavior is covered by backend tests and smoke checks.

### 4. Code Pointers
- `frontend/src/App.tsx` — top bar and `VIEWS`/`view` switching, 60-second polling plus generation guard, selected-card state, modal state, panel remount
- `frontend/src/api.ts` — fetch wrapper and error contract
- `frontend/src/components/Row.tsx`, `frontend/src/components/PreviewCard.tsx` — strip/tile/rank-chip/badge rendering and the hover popover
- `frontend/src/components/Sidebar.tsx` — `rowKey`/`sideLabel`, topic list and focus selection
- `frontend/src/components/BriefPanel.tsx` — SSE stream consumption and pipeline trace
- `frontend/src/components/TrendsPanel.tsx`, `frontend/src/components/HistoryCharts.tsx` — chart composition
- `frontend/src/useVideoHistory.ts` — shared generation-guarded history fetch
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
React 18 + Vite + TypeScript SPA다. 라우터는 없고(로고·페이지 타이틀은 "YOUTUBE TREND MONITOR"로 개명 — 구 TREND RADAR, 레이아웃 콘셉트는 그대로다), 톱바(로고, 상단 메뉴, 수집 시각 KST, 새로고침, 테마 버튼)의 기존 탭 스타일 상단 메뉴가 `view` 상태 하나로 3화면을 전환한다: "홈"(히어로 빌보드 — 기본 전체 1위, 타일 선택 시 그 콘텐츠 — + 선택 콘텐츠 추이 패널 + 인사이트 칩 + 주제 사이드바 옆 가로 스트립 행들 top10/accel/chart/spotlight/topic/age/category/region + 클라이언트 삽입 퀴즈 행), "시계열 추이"(영상 시계열 패널), "점유율 · 리포트"(카테고리 점유율 추이 + AI 브리핑). 백엔드 `/api/*` 계약만 소비하며, 게이트는 `npx tsc --noEmit && npm run build`다(테스트 러너 없음).

### 2. 구성요소
| 구성요소 | 경로 | 목적 |
|---|---|---|
| 앱 셸 | `frontend/src/App.tsx` | 톱바 + `.nav-tabs` 상단 메뉴(`VIEWS`/`view` 상태, `role="tablist"`, 라우터 없음. 전환 시 최상단 스크롤), `/api/home` 로드(60초 silent 폴링 + 세대 가드), `selected` 카드 상태(타일 클릭 → 히어로 빌보드 전환 + 최상단 스크롤), 사이드바 `focus` 상태(`focusRow` 메모가 `top10` kind를 재사용해 TOP 20 빅넘버 뷰 렌더 — 폴링으로 주제 소실 시 effect가 홈 복귀), 모달 상태, 서브 화면 패널 `panelKey` 리마운트 |
| API 클라이언트 | `frontend/src/api.ts` | `fetchJson`/`postJson`과 백엔드 계약의 `{error}` 본문·`status`를 싣는 `ApiError` |
| 히어로 | `frontend/src/components/Hero.tsx` | 넷플릭스식 빌보드 — 기본은 전체 1위, 타일 선택 시 그 카드의 제목·카테고리 칩(`.hero-cat`)·간단한 소개 `description`(`.hero-desc`)·YouTube 링크·"✕ 1위 화면으로" 해제 버튼으로 전환. 표시 중인 카드에 `tags.comment`가 있으면 "🤖" AI 한 줄 분석(`.hero-ai`)을 렌더. maxres 배경 `img` + videoId 단위 `onError` 폴백, 차트인 시간, NEW 칩, 보러가기/내 취향 찾기 |
| 인사이트 칩 | `frontend/src/components/InsightChips.tsx` | `/api/home`의 규칙 기반 인사이트 문자열(LLM 미사용) |
| 스트립 행 | `frontend/src/components/Row.tsx` | 스크롤 스냅 스트립 + hover 화살표. `Tile`/`TopTile`(큰 순위 숫자, `-webkit-text-stroke`) — 통계 줄은 상시 표시. `limit` prop으로 표시 절단(top10 행은 20개 운반, 홈은 10개 표시). 제목 옆 힌트 칩(topic/age "AI 태깅", accel "시간당 증가 기준", spotlight "AWS Korea 채널", chart "YouTube Music 공식 주간 차트"). 좌상단 순위 칩(`.tile-rank`, rank <= 3이면 액센트 스타일 — 분야 행은 분야 내 순위, 나머지 행은 전체 순위). 타일 hover/focus는 350ms 지연 후 `PreviewCard` 팝오버를 연다 — 정밀 포인터 전용(`(hover: hover) and (pointer: fine)`, 호출 시점 평가). 배지 — `baseline === null`이면 미렌더, `prevRank === null`이면 NEW, `delta`는 ▲/▼, `delta === 0`이면 "–"(`badge same`), `viewsPerHour > 0`이면 "+N/시" |
| 사이드바 | `frontend/src/components/Sidebar.tsx` | 홈 행에서 파생된 넷플릭스식 좌측 주제 목록(`rowKey`/`sideLabel`, 퀴즈 행 제외 — 데이터 있는 주제만 표시). 선택 시 그 주제의 TOP 20 포커스 뷰, "🏠 홈"으로 해제. 1024px 미만에서는 가로 칩 바로 전환 |
| 미리보기 팝오버 | `frontend/src/components/PreviewCard.tsx` | 넷플릭스식 타일 미리보기 — `createPortal`로 `document.body`에 렌더(스트립 overflow에 안 잘림), `position: fixed`, 시각 전용(`pointer-events: none`), 폭 340(뷰포트 클램프), `max-height: min(392px, 100vh - 16px)`. 썸네일·제목·메타·`description`(`.pv-desc`)·"AI 브리핑" 라벨 + `tags.comment`(`.pv-ai`)·태그 칩. 닫힘: mouseleave/blur, 캡처 단계 window scroll, resize, Escape, 폴링으로 hover 중 카드 소실 시 |
| 퀴즈 모달 | `frontend/src/components/QuizModal.tsx` | 3문항 → `POST /api/quiz` → 유형명 + 홈 행 상단에 `kind='quiz'` 행 삽입 |
| 테마 모달 | `frontend/src/components/ThemeModal.tsx` | `src/themes.ts` 기반 10종 스와치 |
| 선택 콘텐츠 추이 | `frontend/src/components/SelectedTrend.tsx` | 히어로 바로 아래 "선택한 콘텐츠 추이" 패널 — 선택 카드의 순위/조회수 차트. 시계열 없으면 안내(전체 Top30 진입 영상만 기록) |
| 시계열 차트 | `frontend/src/components/HistoryCharts.tsx` | 공용 순위+조회수 `LineChart` 쌍 + 로그/선형 토글 — `SelectedTrend`·`VideoSeriesPanel`이 렌더(삭제된 `DetailModal.tsx` 대체) |
| 영상 시계열 패널 | `frontend/src/components/VideoSeriesPanel.tsx` | "시계열 추이" 화면 패널 — `/api/trending?scope=all` 기반 영상 셀렉터 + 시계열 차트(`hours=168`). 구 추이 분석 탭 흐름 복원 |
| 시계열 훅 | `frontend/src/useVideoHistory.ts` | 세대 가드 포함 `/api/videos/{id}/history?hours=168` 로드 훅 — `SelectedTrend`·`VideoSeriesPanel`이 공유 |
| 추이 패널 | `frontend/src/components/TrendsPanel.tsx` | 점유율 스택 `AreaChart` + 진입/이탈 `BarChart`(`hours=48`) |
| 브리핑 패널 | `frontend/src/components/BriefPanel.tsx` | POST 대신 `GET /api/brief/stream` 소비(fetch + `ReadableStream` SSE 파싱 — POST 계약은 불변, 프론트만 미사용). 파이프라인 트레이스 UI(`.brief-steps` — 실행 중 ⋯/완료 ✓/실패 ✗ + ms), 델타는 `requestAnimationFrame` 배칭으로 마크다운 재파싱 빈도 제한, in-band `error` 시 부분 결과 경고(`.brief-error`), 503이면 패널 잠금 유지. react-markdown 렌더 |
| 모달 셸 | `frontend/src/components/Modal.tsx` | 공통 셸 — 배경 클릭/Escape로 닫기 |
| 계약 타입 | `frontend/src/types.ts` | `Card`/`HomeCard`/`HomeRow`/`HomeHero`/`HomeData`/`QuizAnswers`/`QuizResult` + `Category`/`HistoryPoint`/`TrendBucket`/`Loadable`(파생 필드 nullable, `description`·`Tags.comment`는 optional — 각 필드 도입 이전 스냅샷/태그 버킷에는 없음. `RowKind`에 `chart`/`spotlight`/`region` 포함, `HomeRow`는 optional `regionCode` 운반) |
| 포매팅 | `frontend/src/format.ts` | `formatCount`(만/억 축약), `formatTsKst`(UTC 시 버킷 → KST 벽시계), `formatClockKst`(ISO → KST HH:MM), `youtubeUrl` |
| 테마 상태 | `frontend/src/theme.ts` | `documentElement.dataset.theme` + localStorage `yt-theme` 기반 `getTheme`/`setTheme`. 첫 페인트는 `index.html` 부트스트랩 스크립트가 처리 |
| 차트 색 | `frontend/src/chartColors.ts` | 테마 무관 고정 8색 팔레트(슬롯 귀속) — recharts는 SVG fill/stroke에 CSS `var()`를 안정적으로 반영하지 않는다 |

### 3. 주요 결정
- 라우터가 없다: 기존 탭 스타일 상단 메뉴(`.nav-tabs`/`.nav-tab.active` 액센트 언더라인, `role="tablist"`)가 `App.tsx`의 `VIEWS`/`view` 상태 하나로 3화면을 전환하고, 전환 시마다 최상단으로 스크롤한다. 서브 화면은 `.page` 컨테이너(구 `.bottom`에서 개명)에 렌더한다. 홈 화면은 `GET /api/home` 응답 하나로 조합되고, 퀴즈 행(`kind='quiz'`)만 클라이언트가 만든다.
- 타일 클릭은 모달이 아니라 콘텐츠 선택이다(`DetailModal.tsx` 삭제): `App.tsx`가 `selected` 상태를 들고, 히어로가 선택 카드의 넷플릭스식 빌보드로 바뀌며, 페이지가 최상단으로 스크롤되고, 히어로 바로 아래 "선택한 콘텐츠 추이" 패널(`SelectedTrend`)이 나타난다. "✕ 1위 화면으로"가 선택을 해제해 전체 1위로 되돌린다.
- 카드의 optional 필드는 우아하게 강등된다: `description` 없는 카드(도입 이전 스냅샷)나 `tags.comment` 없는 카드(도입 이전 태그 버킷)는 해당 팝오버/히어로 줄만 생략한다 — 플레이스홀더 없음.
- 사이드바는 조회가 아니라 파생이다: 주제 목록이 홈 행 자체에서 나오므로(`rowKey`/`sideLabel`) 데이터 있는 주제만 나타나고 추가 요청이 없다. 포커스 뷰는 `top10` kind를 재사용해 TOP 20 빅넘버로 렌더하고, 폴링으로 포커스 주제가 사라지면 메모된 `focusRow`가 null이 되어 effect가 홈으로 복귀시킨다.
- 타일 미리보기는 인라인 확장이 아니라 body 포털 팝오버다: 타일은 상시 통계 줄과 클릭 동작을 유지하고(팝오버는 `pointer-events: none`), 터치 탭은 트리거하지 않으며(정밀 포인터 미디어 쿼리), scroll/resize/Escape·폴링에 의한 카드 소실 시 닫아 낡은 앵커 좌표를 피한다.
- `/api/home`은 활성 화면과 무관하게 60초마다 silent 모드로 폴링한다. 요청 시점에 캡처한 세대 토큰(시퀀스 ref)이 늦게 도착한 응답을 폐기하고, silent 폴링 실패는 오류 표시 대신 기존 화면을 유지한다. 비동기 fetch 후 setState 하는 코드를 추가할 때 이 세대 토큰 레이스 가드 패턴을 유지한다.
- 로딩/오류/준비 상태를 판별 유니온(`HomeState`)으로 모델링한다 — 불리언 플래그 조합을 쓰지 않는다.
- `ApiError`는 백엔드의 한국어 `error` 메시지를 그대로 노출하고, 폴백도 로컬 한국어 문구다.
- KST 변환은 Date를 +9h 이동한 뒤 `getUTC*` 접근자로 읽는다 — 조회자의 로컬 타임존과 무관하게 동일하게 렌더된다.
- 새로고침은 홈 재로드 + `panelKey` 증가로 세 화면의 패널(영상 시계열, 카테고리 점유율 추이, AI 브리핑)을 모두 리마운트한다 — 이 패널들은 폴링 대상이 아니고 수동 새로고침 때만 재조회한다.
- 테마는 CSS 변수 세트다: `styles.css`의 `[data-theme]` 10종이 단일 진실이다(기본 `neon-hunter`, 라이트는 `cotton-candy`). `src/themes.ts`의 스와치와 `index.html` 부트스트랩의 유효 id 목록을 함께 동기 유지한다. 구버전 localStorage 값은 부트스트랩에서 마이그레이션한다: `dark` → `neon-hunter`, `light` → `cotton-candy`.
- 차트 색은 테마 시스템을 우회한다 — recharts SVG가 CSS `var()`를 받지 못하므로 `chartColors.ts`의 고정 팔레트를 쓴다.
- react-markdown에 `rehype-raw`를 추가하지 않는다 — LLM 출력의 raw HTML 렌더는 XSS 경로다.
- 프론트 게이트는 컴파일+빌드뿐이다(`npx tsc --noEmit && npm run build`). 동작 검증은 백엔드 테스트와 스모크가 담당한다.

### 4. 코드 포인터
- `frontend/src/App.tsx` — 톱바와 `VIEWS`/`view` 전환, 60초 폴링 + 세대 가드, 선택 카드 상태, 모달 상태, 패널 리마운트
- `frontend/src/api.ts` — fetch 래퍼와 오류 계약
- `frontend/src/components/Row.tsx`, `frontend/src/components/PreviewCard.tsx` — 스트립/타일/순위 칩/배지 렌더와 hover 팝오버
- `frontend/src/components/Sidebar.tsx` — `rowKey`/`sideLabel`, 주제 목록과 포커스 선택
- `frontend/src/components/BriefPanel.tsx` — SSE 스트림 소비와 파이프라인 트레이스
- `frontend/src/components/TrendsPanel.tsx`, `frontend/src/components/HistoryCharts.tsx` — 차트 구성
- `frontend/src/useVideoHistory.ts` — 공용 세대 가드 시계열 로드 훅
- `frontend/src/theme.ts`, `frontend/src/themes.ts`, `frontend/src/styles.css`, `frontend/index.html` — 테마 시스템과 마이그레이션 부트스트랩
- `frontend/src/types.ts` — API 계약 타입

### 5. 상호 참조
- 관련 모듈: `frontend/src/`, `backend/app/api/`(계약의 원천 — `/api/home`·`/api/quiz`는 `home.py`)
- 관련 ADR: [ADR-001](../decisions/ADR-001-trend-radar-single-page-redesign.md) (Trend Radar 단일 페이지 개편 — 범위 제외 결정)
- 관련 런북: 아직 없음
- 관련 레이어: [ui.md](ui.md), [api.md](api.md), [infrastructure.md](infrastructure.md)(정적 서빙)

Last updated: 2026-08-16
