# Trend Radar 개편 설계 (시나리오05 디자인·기능 이식)

- 날짜: 2026-08-14
- 참조: https://capstone.atomai.click/시나리오05/ ("Trend Radar" — Netflix형 급상승 대시보드)
- 상태: 승인 대기 없이 자율 실행 모드로 진행 (사용자 지시: "디자인과 기능을 추가")

## 1. 목표

참조 사이트의 디자인 언어(넷플릭스형 히어로 + 가로 스트립 + 테마 10종)와 기능(홈 조합 API,
취향 퀴즈, AI 태깅 행, 인사이트 칩, 자동 새로고침)을 현재 YouTube Trends 서비스에 이식한다.
기존 기능(카테고리 점유율 추이, 개별 영상 시계열, LLM 브리핑/추이 리포트)은 전부 보존한다.

## 2. 범위 결정

포함:
- 프론트 전면 개편: 3탭 → 단일 페이지 (톱바 / 히어로 / 인사이트 칩 / 가로 스트립 행들 / 하단 패널)
- 테마 10종 (참조 CSS 변수 세트 채택) + 테마 모달 + localStorage 유지
- GET /api/home — 히어로·인사이트·행 구성을 서버에서 조합
- POST /api/quiz — 3문항 취향 퀴즈 → 유형명 + 맞춤 추천 행 (결정적 휴리스틱, LLM 미사용)
- AI 태깅 파이프라인 — 수집 후 Bedrock 1콜로 Top30 태깅(topics/age/vibe), 주제/연령 행 + 태그 칩
- 배지(NEW/▲/▼) + 시간당 조회 증가(viewsPerHour) 노출, 타일 hover 확장
- TOP10 큰 순위 숫자 행, 가속 중 행
- 60초 자동 새로고침 + 수동 새로고침
- 타일 클릭 → 상세 모달(기존 영상 시계열 차트 + YouTube 이동) — 기존 기능 보존 방식

제외(사유):
- 멀티리전 행(미/일/영/인): 제품 정의가 YouTube KR이고 수집 쿼터 5배 증가 — 별도 결정 필요
- 채널 스포트라이트 행("AWS Korea 최신"): 참조 시나리오 특화 데모
- 참조의 인라인 SVG 차트: 기존 recharts 스택 AreaChart가 상위 호환이라 유지

## 3. 백엔드 설계

### 3.1 GET /api/home

응답 (camelCase — 프로젝트 컨벤션, 참조의 snake_case 미채택):

```json
{
  "capturedAt": "ISO8601",
  "tagged": true,
  "llmEnabled": true,
  "insights": ["…", "…"],
  "hero": { "…카드+파생 필드", "heroThumbnail": "maxres URL", "tenureHours": 5 },
  "rows": [ { "kind": "top10|accel|topic|age|category", "title": "…", "categoryId": "10 (category만)", "items": ["카드+파생(+tags)"] } ]
}
```

- 스냅샷 없음 → 409 `{"error": "표시할 목록이 아직 없습니다"}` (brief와 동일 계약)
- hero = 전체 Top30의 rank 1 카드. `tenureHours`는 video_history 최근 72시간에서
  최신 버킷부터 연속 등장한 시간 버킷 수(항상 1 이상 — 실측값이므로 null 아님).
  `heroThumbnail`은 videoId로 조립한 maxresdefault URL(저장 안 함, 프론트가 onError 폴백).
- rows 구성 순서: top10(전체 상위 10) → accel(viewsPerHour>0 내림차순 상위 10) →
  topic(태그 주제별, 3개 이상만, 최대 4행) → age(10대/20대/3040, 3개 이상만) → category(8개, SNAP#CAT 최신).
- insights: LLM 미사용 계산값 2~4개 — 최고 순위 상승, 최고 시간당 조회, 신규 진입 수, 최다 카테고리 점유율.
  파생 필드 null 안전(첫 스냅샷이면 해당 칩 생략).
- 순수 조합 로직은 `app/home.py`(derive/aggregate와 같은 층), 라우터는 `app/api/home.py`.

### 3.2 AI 태깅 파이프라인

- `app/tagging.py`의 `ensure_tags(store, llm, now)`: 최신 ALL 스냅샷 버킷에 태그가 없고
  LLM 토큰이 있으면 Bedrock 1콜(build_tags 프롬프트, maxTokens 1800)로 Top30을 일괄 태깅.
- 태그 스키마: `{videoId: {"topics": [고정 어휘 1~2개], "age": "10대|20대|3040|전연령", "vibe": "힐링|도파민|낮|심야|몰입|가볍게"}}`
  - topics 어휘는 8개 카테고리명과 겹치지 않는 교차 주제(먹방, 브이로그, 챌린지, 커버·댄스, 리뷰·정보, 키즈, 이슈, 하이라이트)
  - vibe는 퀴즈 선택지 공간과 동일 — 퀴즈 매칭에 직접 사용
- 저장: pk=`TAGS#ALL`, sk=`TS#{bucket}`(keys.py에 tags_pk 추가), tags JSON 문자열, TTL 2일.
- 트리거: (1) 매시 수집 잡 성공 직후, (2) 앱 기동 시 1회(최신 스냅샷이 미태깅이면).
- 실패/미설정 시 조용히 스킵 — 홈은 tagged=false로 topic/age 행만 생략.
- LLM 응답 JSON 파싱은 코드펜스 제거 후 json.loads, 실패 시 태그 없음 처리(예외 전파 금지).

### 3.3 POST /api/quiz

- 요청: `{"mood": "힐링|도파민", "time": "낮|심야", "style": "몰입|가볍게"}` — 위반 시 400.
- 응답: `{"type": "유형명", "items": [카드…]}` — 스냅샷 없음 409.
- 유형명: 8조합 고정 매핑(결정적). 추천: 태그 vibe가 답변과 일치(+3/개), mood·style별
  카테고리 가중치, rank 미세 타이브레이크 — 상위 10개. 태그 없어도 카테고리 가중치만으로 동작.
- LLM 미호출(무료·즉답·결정적 → 테스트 가능).

## 4. 프론트 설계

- App.tsx 재작성: 톱바(TREND RADAR 로고/수집시각/새로고침/테마) + Hero + InsightChips +
  Row 스트립들 + 하단 패널(카테고리 점유율 추이, AI 브리핑) + 모달 3종(퀴즈/테마/상세).
- 컴포넌트: Hero, InsightChips, Row(스트립+화살표), Tile, TopTile(큰 숫자), QuizModal,
  ThemeModal, DetailModal(영상 시계열 차트 재사용), TrendsPanel(기존 CategoryShareSection 이식),
  HistoryCharts(기존 VideoSeriesSection 차트 이식), BriefPanel(로직 유지, 필 버튼 재스타일).
- tabs/ 3파일 삭제. Card/CardGrid/StatTiles 삭제(타일로 대체). Badge 로직은 Tile에 통합.
- 테마: 참조 10종 CSS 변수 세트 채택(styles.css 재작성). localStorage 키 `yt-theme` 유지,
  구값 마이그레이션(dark→neon-hunter, light→cotton-candy). index.html 부트스트랩 갱신.
- 차트: recharts 유지, 팔레트는 테마 무관 고정 9색(참조 방식) — chartColors.ts 단순화.
- 갱신: 60초 폴링 + 새로고침 버튼, 모든 fetch에 세대 토큰 레이스 가드 유지.
- 시간 표기 formatTsKst / 축약 formatCount 유지. rehype-raw 금지 유지.

## 5. 오류·계약 준수 사항

- 모든 오류 `{"error": "<한국어>"}` + 4xx/5xx, 검증 실패는 전역 핸들러의 400.
- 파생 null(계산 불가) vs 0(실측 0) 계약 유지 — 인사이트/배지/정렬 전부 null 안전.
- pk/sk는 keys.py에서만 조립(tags_pk 추가 시 test_keys.py 동반 갱신).
- Bedrock Bearer 전용, 태깅 프롬프트 입력도 clean_text 세탁, MAX_TOKENS dict에 kind 등록 불필요
  (태깅은 리포트 캐시 경로와 별개 저장).
- 기존 엔드포인트 계약 불변(/api/trending 등 유지 — 프론트만 /api/home으로 전환).

## 6. 테스트

- backend: test_api_home.py(행 구성/히어로/인사이트/409/tagged 플래그), test_api_quiz.py
  (400/409/유형 매핑/태그 유무 추천), test_tagging.py(FakeLlm JSON/미설정 스킵/파싱 실패 내성),
  test_home_logic.py(가속 정렬 null 안전, 인사이트), test_keys.py에 tags_pk 추가.
- frontend 게이트: tsc --noEmit + npm run build.
- 완료 후 다중 관점 리뷰 워크플로(find → adversarial verify) 실행.

## 7. 문서 동기화

CLAUDE.md(API Surface·테스트 수), backend/frontend CLAUDE.md, docs/reference/{api,frontend,ui,agent-llm,data}.md,
docs/architecture.md, ADR-001(단일 페이지 개편 + AI 태깅/퀴즈 결정), CHANGELOG.md.
