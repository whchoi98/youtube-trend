# ADR-001: Trend Radar single-page redesign with server-composed home and batch AI tagging

<a href="#english"><img src="https://img.shields.io/badge/lang-English-blue.svg" alt="English"></a>
<a href="#한국어"><img src="https://img.shields.io/badge/lang-한국어-red.svg" alt="Korean"></a>

---

<a id="english"></a>

# English

## Status
Accepted (2026-08-14)

## Context
The reference scenario site (capstone `시나리오05`, "Trend Radar") presents a Netflix-style single-page dashboard: a hero for the current #1 video, horizontally scrolling strips, ten CSS-variable themes, computed insight chips, a taste quiz, and AI-tagged topic/age rows. The request was to bring that design and feature set into this project, which had a three-tab SPA and a snapshot/derived-field data model that already matched the reference's field semantics (`delta`, `prevRank`, `viewsPerHour`, null-vs-0 contract).

## Options Considered

### Option 1: Client-side composition over existing endpoints
- **Pros**: No backend change; reuses `/api/trending` per scope.
- **Cons**: 9+ requests per refresh; hero tenure and tag joins impossible without new endpoints anyway; row logic duplicated in TypeScript where it cannot be unit-tested against store semantics.

### Option 2: Server-composed `GET /api/home` + deterministic `POST /api/quiz` + batch tagging (chosen)
- **Pros**: One request per refresh; row/insight/quiz logic lives in a pure Python module (`app/home.py`) tested with the existing moto suite; tagging is one Bedrock call per collection bucket, idempotent, and degrades silently when the token is absent (existing 503 philosophy).
- **Cons**: New endpoint surface to document; home response recomputes derived fields per call.

### Option 3: Per-request LLM personalization for the quiz
- **Pros**: Richer recommendations.
- **Cons**: 25 s worst-case latency and per-click cost for a 3-question quiz; non-deterministic, hard to test. Rejected.

## Decision
Adopt Option 2. The frontend becomes a single-page Trend Radar (hero, insight chips, strips for top10/accel/topic/age/category plus a client-side quiz row, bottom panels reusing the existing recharts and react-markdown components). Multi-region rows and the channel-spotlight row from the reference were excluded: the product is defined as YouTube KR and multi-region collection would multiply YouTube API quota by the number of regions. Tags are stored under `TAGS#ALL` / `TS#<hour bucket>` (TTL 2 days) via `keys.tags_pk()`; vibe vocabulary equals the quiz answer space so matching is a set lookup.

## Consequences

### Positive
- Home renders from one request; all composition logic is unit-tested Python (92 tests total).
- LLM tagging cost is bounded to at most one Converse call per hour regardless of viewers.
- Existing endpoints keep their contracts; the old tabs' features survive as bottom panels and a detail modal.

### Negative
- Theme swatches and the index.html bootstrap list duplicate the CSS theme ids (three places to keep in sync).
- Quiz recommendations are heuristic; quality depends on tag availability.

## References
- Reference site: https://capstone.atomai.click/시나리오05/
- Design spec: `docs/superpowers/specs/2026-08-14-trend-radar-redesign-design.md`

---

<a id="한국어"></a>

# 한국어

## 상태
승인됨 (2026-08-14)

## 배경
참조 시나리오 사이트(capstone `시나리오05`, "Trend Radar")는 넷플릭스형 단일 페이지 대시보드다: 1위 영상 히어로, 가로 스크롤 스트립, CSS 변수 테마 10종, 계산형 인사이트 칩, 취향 퀴즈, AI 태깅 주제/연령 행. 이 디자인과 기능을 본 프로젝트에 이식하라는 요청이 있었고, 기존 3탭 SPA의 스냅샷·파생 필드 모델(`delta`, `prevRank`, `viewsPerHour`, null-vs-0 계약)은 참조와 의미가 일치했다.

## 검토한 옵션

### 옵션 1: 기존 엔드포인트 위 클라이언트 조합
- **장점**: 백엔드 무변경, scope별 `/api/trending` 재사용.
- **단점**: 새로고침마다 9회 이상 요청. 히어로 차트인 시간·태그 조인은 어차피 새 엔드포인트 필요. 행 구성 로직이 TypeScript로 넘어가 스토어 의미론에 대한 단위 테스트 불가.

### 옵션 2: 서버 조합 `GET /api/home` + 결정적 `POST /api/quiz` + 배치 태깅 (채택)
- **장점**: 새로고침당 1요청. 행/인사이트/퀴즈 로직이 순수 파이썬 모듈(`app/home.py`)로 기존 moto 스위트에서 테스트됨. 태깅은 수집 버킷당 Bedrock 1콜로 멱등이며 토큰 부재 시 조용히 강등(기존 503 철학).
- **단점**: 문서화할 엔드포인트 표면 증가. 홈 응답이 호출마다 파생 필드를 재계산.

### 옵션 3: 퀴즈의 요청별 LLM 개인화
- **장점**: 더 풍부한 추천.
- **단점**: 3문항 퀴즈에 최악 25초 지연·클릭당 비용, 비결정적이라 테스트 곤란. 기각.

## 결정
옵션 2를 채택한다. 프론트는 단일 페이지 Trend Radar(히어로, 인사이트 칩, top10/accel/topic/age/category 스트립 + 클라이언트 퀴즈 행, 기존 recharts·react-markdown 컴포넌트를 재사용하는 하단 패널)가 된다. 참조의 멀티리전 행과 채널 스포트라이트 행은 제외했다: 제품 정의가 YouTube KR이고 멀티리전 수집은 YouTube API 쿼터를 리전 수만큼 곱절로 만든다. 태그는 `keys.tags_pk()`를 통해 `TAGS#ALL` / `TS#<시간 버킷>`(TTL 2일)에 저장하며, vibe 어휘를 퀴즈 답변 공간과 동일하게 두어 매칭을 집합 조회로 끝낸다.

## 영향

### 긍정적
- 홈이 1요청으로 렌더되고 조합 로직 전부가 단위 테스트된 파이썬이다(총 92개).
- LLM 태깅 비용이 조회자 수와 무관하게 시간당 최대 1콜로 상한된다.
- 기존 엔드포인트 계약 불변. 구 탭 기능은 하단 패널과 상세 모달로 생존.

### 부정적
- 테마 스와치와 index.html 부트스트랩 목록이 CSS 테마 id를 중복한다(동기 유지 3곳).
- 퀴즈 추천은 휴리스틱이라 품질이 태그 유무에 좌우된다.

## 참고 자료
- 참조 사이트: https://capstone.atomai.click/시나리오05/
- 설계 스펙: `docs/superpowers/specs/2026-08-14-trend-radar-redesign-design.md`
