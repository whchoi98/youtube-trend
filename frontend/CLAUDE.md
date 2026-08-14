# Frontend Module (React SPA)

## Role

React + Vite + TypeScript 단일 페이지 앱(Trend Radar)이다. 넷플릭스형 홈 한 화면에서 백엔드 API를 소비한다: 히어로(전체 1위) → 인사이트 칩 → 가로 스트립 행들(top10/accel/topic/age/category/퀴즈 맞춤) → 하단 패널(카테고리 점유율 추이, AI 브리핑). 60초 폴링으로 `/api/home`을 자동 갱신한다.

- `src/App.tsx` — 톱바·홈 로드(60초 폴링 + 세대 가드)·모달 상태·하단 패널 배치
- `src/components/Hero.tsx` — 1위 히어로 (maxres 배경, onError 폴백, 차트인 시간)
- `src/components/Row.tsx` — 스트립 행 + Tile/TopTile(큰 순위 숫자)·배지·태그 칩
- `src/components/QuizModal.tsx` — 취향 퀴즈 3문항 → `/api/quiz` → 맞춤 행 추가
- `src/components/ThemeModal.tsx` — 테마 10종 선택 (`src/themes.ts`와 styles.css 동기)
- `src/components/DetailModal.tsx` — 타일 클릭 상세: 영상 시계열 차트 + YouTube 이동
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
