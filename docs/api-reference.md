# API Reference

YouTube Trends 백엔드 API 명세다. 소스 기준: `backend/app/api/`(라우터), `backend/app/derive.py`(파생 필드), `backend/app/main.py`(오류 핸들러·`/healthz`). 코드와 이 문서가 다르면 코드가 우선한다.

## Base URL

| 환경 | URL |
|------|-----|
| 라이브 | `https://d2y73ug3aaah05.cloudfront.net` (계정 종속 — 재배포 시 변동, 스택 출력 `SiteUrl` 참조) |
| 로컬 | `http://localhost:8000` |

## 인증

뷰어 인증은 없다(공개 API). CloudFront → ALB 구간의 `X-Origin-Verify` 헤더 검사는 인프라 계층 방어이며, ALB DNS로 직접 접근하면 헤더 불일치로 `403 forbidden`(text/plain)이 반환된다. 정상 경로는 항상 CloudFront 도메인이다.

## 공통 오류 계약

모든 오류 응답은 `{"error": "<한국어 메시지>"}` JSON + 4xx/5xx 상태 코드다. FastAPI 기본 422 검증 오류(detail 배열)는 노출되지 않고 400으로 변환된다.

| 코드 | 의미 | 예시 body |
|------|------|-----------|
| 400 | 잘못된 파라미터/요청 body (scope 오류, hours 범위 초과, 검증 실패) | `{"error": "지원하지 않는 분야입니다"}`, `{"error": "잘못된 요청입니다"}` |
| 404 | 미등록 `/api/*` 경로 (SPA 폴백 대상이 아님) | `{"error": "찾을 수 없습니다"}` |
| 409 | 아직 데이터가 없어 처리 불가 (수집 전, 어제 기준 없음) | `{"error": "표시할 목록이 아직 없습니다"}` |
| 502 | LLM 상류(Bedrock) 오류 | `{"error": "분석 생성에 실패했습니다", "code": 500}` |
| 503 | LLM 미설정 (`AWS_BEARER_TOKEN_BEDROCK` 없음) | `{"error": "브리핑 기능이 설정되지 않았습니다", "enabled": false}` |

## scope 값

`scope`를 받는 엔드포인트의 유효값은 `all` 또는 고정 8개 카테고리 id다: `10`(음악), `20`(게임), `24`(엔터테인먼트), `25`(뉴스/정치), `17`(스포츠), `1`(영화/애니메이션), `28`(과학기술), `23`(코미디). 그 외 값은 400이다.

## 카드 스키마 (14필드)

`GET /api/trending` 배열 원소의 스키마다. 수집 원본 10필드 + 파생 4필드로 구성된다.

| 필드 | 타입 | 출처 | 설명 |
|------|------|------|------|
| `rank` | int | 수집 | 현재 순위 (1부터) |
| `videoId` | string | 수집 | YouTube 영상 ID |
| `title` | string | 수집 | 제목 |
| `channel` | string | 수집 | 채널명 |
| `views` | int | 수집 | 조회수. 상류 값이 비정상이면 `0` (절대 null 아님) |
| `likes` | int | 수집 | 좋아요 수. 상류 값이 비정상이면 `0` (절대 null 아님) |
| `category` | string | 수집 | 카테고리 한글명 (미지정 시 `"기타"`) |
| `categoryId` | string | 수집 | YouTube videoCategoryId |
| `thumbnail` | string | 수집 | 고화질 썸네일 URL |
| `publishedAt` | string | 수집 | 게시 시각 (ISO 8601) |
| `baseline` | string \| null | 파생 | 비교 기준 스냅샷의 `capturedAt` (ISO 8601) |
| `prevRank` | int \| null | 파생 | 기준 스냅샷에서의 순위 |
| `delta` | int \| null | 파생 | `prevRank - rank` (양수 = 상승) |
| `viewsPerHour` | int \| null | 파생 | 실제 경과 시간으로 나눈 시간당 조회수 증가 |

### null vs 0 계약

- **`views`/`likes`의 `0`** — "값 없음이 0으로 정규화됨" 또는 실제 0. 이 두 필드는 null이 되지 않는다.
- **파생 4필드의 `null`** — "비교 불가"를 뜻한다. 경우별로:
  - `baseline=null` → 기준 스냅샷 자체가 없음(수집 초기, 또는 1~4시간 전 스냅샷이 전부 부재/최소 연령 0.75h 미달). 이때 나머지 3필드도 전부 null이다.
  - `baseline!=null` + `prevRank=null` → **신규 진입(NEW)**. 기준 스냅샷에 이 영상이 없었다.
  - `viewsPerHour=null` → 계산 불가(신규 진입이거나 정수 검증 실패). `0`은 계산된 실제 값(성장 정체)이므로 구분해야 한다.
  - `delta=0`도 유효한 값이다(순위 유지). null("비교 불가")과 혼동하지 않는다.

---

## 엔드포인트

### 1. GET /api/trending

급상승 목록(전체 Top 30 또는 카테고리 Top 10)을 파생 필드와 함께 반환한다.

| 파라미터 | 위치 | 타입 | 필수 | 설명 |
|----------|------|------|------|------|
| `scope` | query | string | 아니오 | 기본 `all`. 유효값은 위 "scope 값" 참조 |

**응답** `200 OK` — 카드 배열(14필드). 첫 수집 전이면 빈 배열 `[]`을 반환한다(오류 아님).

```json
[
  {
    "rank": 1, "videoId": "abc123XYZ", "title": "예시 영상", "channel": "예시 채널",
    "views": 1234567, "likes": 45678, "category": "음악", "categoryId": "10",
    "thumbnail": "https://i.ytimg.com/vi/abc123XYZ/hqdefault.jpg",
    "publishedAt": "2026-08-03T09:00:00Z",
    "baseline": "2026-08-04T02:00:05+00:00", "prevRank": 3, "delta": 2, "viewsPerHour": 51234
  }
]
```

**오류** — `400` `{"error": "지원하지 않는 분야입니다"}` (scope가 유효값 밖)

```bash
curl "https://d2y73ug3aaah05.cloudfront.net/api/trending?scope=10"
```

### 2. GET /api/categories

고정 8개 카테고리 목록. 파라미터 없음. 한글명은 기동 시 YouTube `videoCategories.list(hl=ko)`로 갱신을 시도하며 실패하면 기본값을 쓴다.

**응답** `200 OK`

```json
[
  {"id": "10", "name": "음악"}, {"id": "20", "name": "게임"},
  {"id": "24", "name": "엔터테인먼트"}, {"id": "25", "name": "뉴스/정치"},
  {"id": "17", "name": "스포츠"}, {"id": "1", "name": "영화/애니메이션"},
  {"id": "28", "name": "과학기술"}, {"id": "23", "name": "코미디"}
]
```

```bash
curl "https://d2y73ug3aaah05.cloudfront.net/api/categories"
```

### 3. GET /api/videos/{videoId}/history

영상 하나의 순위·조회수 시계열이다.

| 파라미터 | 위치 | 타입 | 필수 | 설명 |
|----------|------|------|------|------|
| `videoId` | path | string | 예 | YouTube 영상 ID |
| `hours` | query | int | 아니오 | 조회 구간(시간). 기본 `168`, 범위 `1`~`720` |

**응답** `200 OK` — `points[].ts`는 UTC 시간 버킷(`YYYY-MM-DDTHH`), `rank`는 null 가능, `views`는 int. 존재하지 않는 `videoId`도 `200` + 빈 `points`다(404 아님).

```json
{
  "videoId": "abc123XYZ",
  "points": [
    {"ts": "2026-08-04T02", "rank": 3, "views": 1180000},
    {"ts": "2026-08-04T03", "rank": 1, "views": 1234567}
  ]
}
```

**오류** — `400` `{"error": "잘못된 요청입니다"}` (`hours` 범위 초과 등 검증 실패)

```bash
curl "https://d2y73ug3aaah05.cloudfront.net/api/videos/abc123XYZ/history?hours=72"
```

### 4. GET /api/trends/categories

전체(`all`) 스냅샷 시계열에서 카테고리 점유율과 진입/이탈 수를 집계한다.

| 파라미터 | 위치 | 타입 | 필수 | 설명 |
|----------|------|------|------|------|
| `hours` | query | int | 아니오 | 조회 구간(시간). 기본 `48`, 범위 `2`~`96` (96h 캡은 DynamoDB 1MB Query 한도 내 안전 마진) |

**응답** `200 OK` — `shares`는 `{categoryId: Top30 내 개수}`, `entered`/`exited`는 직전 버킷 대비 진입/이탈 영상 수(첫 버킷은 둘 다 `0`).

```json
{
  "hours": 48,
  "series": [
    {"ts": "2026-08-03T03", "shares": {"10": 8, "24": 7, "20": 5}, "entered": 0, "exited": 0},
    {"ts": "2026-08-03T04", "shares": {"10": 9, "24": 6, "20": 5}, "entered": 3, "exited": 3}
  ]
}
```

**오류** — `400` `{"error": "잘못된 요청입니다"}` (`hours` 범위 초과)

```bash
curl "https://d2y73ug3aaah05.cloudfront.net/api/trends/categories?hours=96"
```

### 5. POST /api/brief

현재 스냅샷 기반 LLM 브리핑(`now`) 또는 전일 대비 비교 브리핑(`daily`)이다. (kind, scope, 시간 버킷)당 1회 생성 후 캐시된다(TTL 2일). 토큰 한도 도달로 잘린 경우 본문 끝에 잘림 안내 문구가 덧붙는다.

**요청 body** (`application/json`)

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `scope` | string | 아니오 | 기본 `"all"`. 유효값은 "scope 값" 참조 |
| `mode` | string | 아니오 | 기본 `"now"`. `"now"` 또는 `"daily"` |

**응답** `200 OK` — `brief`는 마크다운 텍스트, `cached`는 캐시 적중 여부. `daily` 성공 시 `baseline`(기준 스냅샷 `capturedAt`)이 추가된다.

```json
{"brief": "## 지금 급상승 요약\n...", "cached": false, "baseline": "2026-08-03T03:00:05+00:00"}
```

**오류**

| 코드 | 조건 | body |
|------|------|------|
| 400 | scope/mode 유효값 밖, body 검증 실패 | `{"error": "잘못된 요청입니다"}` |
| 409 | 스냅샷이 아직 없음 | `{"error": "표시할 목록이 아직 없습니다"}` |
| 409 | `daily`인데 24~26시간 전 기준 스냅샷 없음 | `{"error": "비교할 어제 데이터가 아직 없습니다", "baseline": null}` |
| 502 | Bedrock 상류 오류 | `{"error": "분석 생성에 실패했습니다", "code": <상류 상태>}` |
| 503 | Bedrock 토큰 미설정 | `{"error": "브리핑 기능이 설정되지 않았습니다", "enabled": false}` |

```bash
curl -X POST "https://d2y73ug3aaah05.cloudfront.net/api/brief" \
  -H "content-type: application/json" \
  -d '{"scope": "all", "mode": "daily"}'
```

### 6. POST /api/trends/report

최근 48시간 스냅샷의 카테고리 점유율 시계열과 최신 상위 영상을 근거로 LLM 추이 리포트를 생성한다. 캐시 규칙은 `/api/brief`와 동일하다.

**요청 body** (`application/json`)

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `scope` | string | 아니오 | 기본 `"all"`. 유효값은 "scope 값" 참조 |

**응답** `200 OK`

```json
{"report": "## 48시간 트렌드 리포트\n...", "cached": true}
```

**오류** — 400(`scope` 오류) / 409(48시간 내 스냅샷 없음) / 502 / 503, body는 `/api/brief`와 동일한 계약.

```bash
curl -X POST "https://d2y73ug3aaah05.cloudfront.net/api/trends/report" \
  -H "content-type: application/json" \
  -d '{"scope": "all"}'
```

### 7. GET /healthz

ALB 헬스체크용이다. 프로세스 생존만 확인하며 DynamoDB 등 어떤 외부 의존에도 접근하지 않는다(의존 장애가 태스크 교체 폭풍으로 번지지 않게 하는 의도적 설계).

**응답** `200 OK` — `text/plain`

```text
ok
```

```bash
curl "https://d2y73ug3aaah05.cloudfront.net/healthz"
```

---

## 기타 계약

- **미등록 `/api/*` 경로** — SPA 폴백이 아니라 `404` + `{"error": "찾을 수 없습니다"}`를 반환한다. 등록된 라우트가 catch-all보다 먼저 매칭된다.
- **레이트 리밋** — 애플리케이션 계층 레이트 리밋은 없다. `/api/*`는 CloudFront에서 캐시가 비활성화되어 있으므로 매 요청이 오리진에 도달하고, LLM 엔드포인트만 시간당 캐시로 상류 호출이 제한된다.
- **캐시 헤더** — 정적 해시 자산은 CloudFront `CACHING_OPTIMIZED`, `index.html`은 `Cache-Control: no-cache`, `/api/*`는 `CACHING_DISABLED`다.
