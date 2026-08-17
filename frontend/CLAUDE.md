# Frontend Module (React SPA)

## Role

React + Vite + TypeScript SPA(로고: YOUTUBE TREND MONITOR)다. 상단 메뉴(라운드 세그먼트 박스 — 활성 탭은 액센트 필)로 3화면을 전환한다: **홈**(히어로 빌보드 → 선택 콘텐츠 추이 → 인사이트 칩 → 가로 스트립 행들 top10/accel/topic/age/category/퀴즈 맞춤), **시계열 추이**(영상 시계열 패널), **점유율·리포트**(카테고리 점유율 추이 + AI 브리핑). 라우터 없이 view 상태 하나로 전환하며, 60초 폴링으로 `/api/home`을 자동 갱신한다.

- `src/App.tsx` — 톱바(로고·상단 메뉴·새로고침·테마)·view 전환·홈 로드(60초 폴링 + 세대 가드)·선택 콘텐츠 상태·모달 상태
- `src/components/Hero.tsx` — 빌보드: 기본은 전체 1위, 타일 선택 시 해당 콘텐츠의 제목·카테고리 칩·간단한 소개(description)·YouTube 링크로 전환 (maxres 배경 + onError 폴백)
- `src/components/Row.tsx` — 스트립 행 + Tile(좌상단 순위 칩, 우상단 ▲/▼/NEW/– 배지)·TopTile(큰 순위 숫자)·태그 칩. 타일 클릭은 히어로 선택으로 이어진다
- `src/components/SelectedTrend.tsx` — 선택 콘텐츠의 시계열 차트 (히어로 아래 패널)
- `src/components/VideoSeriesPanel.tsx` — 상단 셀렉터로 전체 Top30 중 영상을 골라 추이를 보는 하단 패널 (구 추이 분석 탭 복원)
- `src/components/HistoryCharts.tsx` — 순위/조회수 차트 쌍 + 로그/선형 토글 (공용)
- `src/useVideoHistory.ts` — 시계열 로드 훅 (세대 가드 포함, 위 두 곳이 공유)
- `src/components/QuizModal.tsx` — 취향 퀴즈 3문항 → `/api/quiz` → 맞춤 행 추가
- `src/components/ThemeModal.tsx` — 테마 10종 선택 (`src/themes.ts`와 styles.css 동기)
- `src/components/TrendsPanel.tsx` — 점유율 스택 AreaChart + 진입/이탈 BarChart
- `src/components/BriefPanel.tsx` — LLM 브리핑/리포트 (react-markdown 렌더)
- `src/api.ts` — 단일 API 클라이언트. 모든 백엔드 호출은 이 파일을 거친다.

## Rules

- 게이트 명령: `cd frontend && npx tsc --noEmit && npm run build`. 이 두 단계가 모두 통과해야 변경 완료다.
- 세대 토큰 레이스 가드 패턴: 폴링/스코프 전환/모달 전환으로 새 요청을 보낼 때 세대 토큰(요청 시점의 세대 값)을 캡처하고, 응답 도착 시 현재 세대와 다르면 상태 반영을 건너뛴다. 비동기 fetch 후 setState 하는 코드를 추가할 때 이 패턴을 유지한다.
- react-markdown에 `rehype-raw`를 추가하지 않는다. LLM 출력의 raw HTML을 렌더하면 XSS 경로가 열린다 — 마크다운 문법만 렌더한다.
- API 오류는 `{"error": "<한국어>"}` 본문으로 온다. 오류 표시 시 이 필드를 그대로 사용자에게 보여준다.
- 테마는 CSS 변수 세트다: styles.css의 `[data-theme=...]` 10종이 단일 진실이고, `src/themes.ts`의 스와치 hex와 index.html 부트스트랩의 유효 id 목록을 함께 갱신한다. localStorage 키는 `yt-theme`.
- recharts 계열 색은 CSS var() 불가 — `src/chartColors.ts`의 테마 무관 고정 팔레트(슬롯 귀속)를 쓴다.
- 파생 필드 null vs 0 계약: 배지는 `baseline===null`이면 미렌더, `prevRank===null`이면 NEW다. 혼용하지 않는다.
