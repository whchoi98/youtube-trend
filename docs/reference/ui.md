# UI / UI 구현 상세

[![English](https://img.shields.io/badge/Language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/Language-한국어-red)](#korean)

<a id="english"></a>
## English

### 1. Overview
Presentation components and style tokens: video cards, ranking/velocity badges, skeleton loading, the LLM brief panel, and the light/dark theme system built on CSS custom properties plus a fixed chart palette.

### 2. Components
| Component | Path | Purpose |
|---|---|---|
| Video card | `frontend/src/components/Card.tsx` | Thumbnail with `onError` fallback block, `rank-1..3` accent classes, badges and velocity text, whole card links to the YouTube watch URL |
| Card grid / skeleton | `frontend/src/components/CardGrid.tsx` | `CardGrid` plus `CardSkeletonGrid` (CSS pulse skeleton, `aria-hidden`) shown while loading |
| Badges | `frontend/src/components/Badge.tsx` | `DeltaBadge` (NEW / up / down / same from nullable derived fields), `velocityText` (`+n/시`, ASCII signs for glyph coverage), `CategoryBadge` |
| Brief panel | `frontend/src/components/BriefPanel.tsx` | Three-button LLM panel (now / daily / report); renders LLM output as markdown via `react-markdown` + `remark-gfm`, status/errors as plain text (`kind: 'llm' | 'status'`) |
| Style tokens | `frontend/src/styles.css` | CSS custom properties — light defaults on `:root`, dark overrides via `data-theme="dark"`; badge color tokens, card, skeleton, tab styles |
| Chart palette | `frontend/src/chartColors.ts` | Fixed 8-color categorical palettes per theme (contrast/CVD validated), `seriesAccent`, `enteredColor`/`exitedColor`; fixed hex because recharts does not reliably resolve `var()` in SVG fill/stroke |
| Theme switch | `frontend/src/theme.ts` | `data-theme` on the root element plus localStorage persistence; graceful no-op when localStorage is unavailable |

### 3. Key Decisions
- Chart colors are fixed hex arrays per theme rather than CSS variables — recharts SVG fill/stroke does not reliably resolve `var()`.
- Palette colors bind to slots, not items, so series keep stable colors across reloads; entered/exited uses the blue/red pair validated for CVD in both themes.
- Badge rendering distinguishes "no baseline" (render nothing) from "baseline exists but new entry" (NEW) using the nullable contract from `derive.py`.
- LLM text renders as markdown only when it actually came from the LLM; status and error strings render as plain text to avoid interpreting user-facing notices as markup.
- Thumbnails fail soft: a broken image swaps to a neutral fallback block instead of a broken-image icon.

### 4. Code Pointers
- `frontend/src/components/Card.tsx` — card layout and fallback logic
- `frontend/src/components/Badge.tsx` — badge/velocity rules
- `frontend/src/components/BriefPanel.tsx` — markdown vs plain-text rendering split
- `frontend/src/styles.css` — theme token definitions
- `frontend/src/chartColors.ts` — palette and accent helpers

### 5. Cross-references
- Related modules: `frontend/src/components/`, `frontend/src/tabs/`
- Related ADRs: none yet
- Related runbooks: none yet
- Related layers: [frontend.md](frontend.md), [api.md](api.md) (nullable derived-field contract)

<a id="korean"></a>
## 한국어

### 1. 개요
프레젠테이션 컴포넌트와 스타일 토큰 계층이다. 영상 카드, 순위/속도 배지, 스켈레톤 로딩, LLM 브리핑 패널, 그리고 CSS 커스텀 프로퍼티 + 고정 차트 팔레트 기반의 라이트/다크 테마 시스템으로 구성된다.

### 2. 구성요소
| 구성요소 | 경로 | 목적 |
|---|---|---|
| 영상 카드 | `frontend/src/components/Card.tsx` | `onError` 폴백 블록이 있는 썸네일, `rank-1..3` 강조 클래스, 배지·속도 텍스트, 카드 전체가 YouTube 시청 URL로 링크 |
| 카드 그리드/스켈레톤 | `frontend/src/components/CardGrid.tsx` | `CardGrid`와 로딩 중 표시하는 `CardSkeletonGrid`(CSS pulse, `aria-hidden`) |
| 배지 | `frontend/src/components/Badge.tsx` | `DeltaBadge`(nullable 파생 필드 기반 NEW/상승/하락/유지), `velocityText`(`+n/시`, 글리프 커버리지용 ASCII 부호), `CategoryBadge` |
| 브리핑 패널 | `frontend/src/components/BriefPanel.tsx` | LLM 3버튼 패널(오늘의 브리핑/어제와 비교/추이 리포트). LLM 본문은 `react-markdown` + `remark-gfm`으로, 상태/오류 문구는 평문으로 렌더(`kind: 'llm' | 'status'`) |
| 스타일 토큰 | `frontend/src/styles.css` | CSS 커스텀 프로퍼티 — `:root` 라이트 기본값 + `data-theme="dark"` 오버라이드. 배지 색 토큰, 카드·스켈레톤·탭 스타일 |
| 차트 팔레트 | `frontend/src/chartColors.ts` | 테마별 고정 8색 카테고리 팔레트(대비·CVD 검증), `seriesAccent`, `enteredColor`/`exitedColor`. recharts가 SVG fill/stroke에서 `var()`를 안정적으로 반영하지 않아 고정 hex 사용 |
| 테마 전환 | `frontend/src/theme.ts` | 루트 요소 `data-theme` + localStorage 지속화. localStorage 불가 시 조용히 무시 |

### 3. 주요 결정
- 차트 색상은 CSS 변수 대신 테마별 고정 hex 배열이다 — recharts SVG fill/stroke가 `var()`를 안정적으로 해석하지 않는다.
- 팔레트 색은 항목이 아닌 슬롯에 귀속되어 리로드 간 계열 색이 안정적이다. 진입/이탈은 두 테마 모두 CVD 검증을 통과한 blue/red 쌍을 쓴다.
- 배지는 `derive.py`의 nullable 계약으로 "기준 없음"(미표시)과 "기준 있음 + 신규 진입"(NEW)을 구분한다.
- LLM이 실제로 생성한 본문만 마크다운으로 렌더하고, 상태/오류 문구는 평문으로 렌더해 안내문이 마크업으로 해석되는 것을 막는다.
- 썸네일은 소프트 실패한다 — 깨진 이미지 아이콘 대신 중립 폴백 블록으로 교체한다.

### 4. 코드 포인터
- `frontend/src/components/Card.tsx` — 카드 레이아웃과 폴백 로직
- `frontend/src/components/Badge.tsx` — 배지/속도 규칙
- `frontend/src/components/BriefPanel.tsx` — 마크다운/평문 렌더 분기
- `frontend/src/styles.css` — 테마 토큰 정의
- `frontend/src/chartColors.ts` — 팔레트와 강조색 헬퍼

### 5. 상호 참조
- 관련 모듈: `frontend/src/components/`, `frontend/src/tabs/`
- 관련 ADR: 아직 없음
- 관련 런북: 아직 없음
- 관련 레이어: [frontend.md](frontend.md), [api.md](api.md)(nullable 파생 필드 계약)

Last updated: 2026-08-04
