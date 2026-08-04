# Frontend Module (React SPA)

## Role

React 18 + Vite + TypeScript 단일 페이지 앱이다. 3탭 구성으로 백엔드 API를 소비한다.

- `src/tabs/TopAll.tsx` — 전체 급상승 Top30
- `src/tabs/ByCategory.tsx` — 분야별 Top10 (8개 카테고리)
- `src/tabs/Trends.tsx` — 추이 분석 (recharts 시계열·점유율 차트)
- `src/components/` — Badge, BriefPanel(LLM 마크다운 렌더), Card, CardGrid
- `src/api.ts` — 단일 API 클라이언트. 모든 백엔드 호출은 이 파일을 거친다.

## Rules

- 게이트 명령: `cd frontend && npx tsc --noEmit && npm run build`. 이 두 단계가 모두 통과해야 변경 완료다.
- 세대 토큰 레이스 가드 패턴: 탭/스코프 전환으로 새 요청을 보낼 때 세대 토큰(요청 시점의 세대 값)을 캡처하고, 응답 도착 시 현재 세대와 다르면 상태 반영을 건너뛴다. 비동기 fetch 후 setState 하는 코드를 추가할 때 이 패턴을 유지한다.
- react-markdown에 `rehype-raw`를 추가하지 않는다. LLM 출력의 raw HTML을 렌더하면 XSS 경로가 열린다 — 마크다운 문법만 렌더한다.
- API 오류는 `{"error": "<한국어>"}` 본문으로 온다. 오류 표시 시 이 필드를 그대로 사용자에게 보여준다.
