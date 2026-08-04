# YouTube Trends 설계 문서

- 날짜: 2026-08-04
- 상태: 사용자 승인 대기 (브레인스토밍 세션에서 섹션별 구두 승인 완료)
- 선행 프로젝트: capstone-4 (Trend Radar, Lambda 기반) — 코드 이식 없이 아이디어만 차용한다

## 1. 목적

YouTube 한국(KR) 트렌드를 보여주는 웹사이트를 만든다. 전체 급상승 Top 30과 주요 분야별 Top 10을 제공하고, 시간 축 데이터(스냅샷)를 축적해 트렌드 추이 분석을 제공한다. Sonnet 4.6 LLM이 트렌드 브리핑과 추이 분석 리포트를 생성한다.

## 2. 확정 요구사항

| 항목 | 결정 | 결정 주체 |
|---|---|---|
| 프로젝트 위치 | `/home/ec2-user/my-project/youtube-trends` 신규 저장소 | 사용자 |
| 아키텍처 | CloudFront → (prefix list SG) → ALB → ECS Fargate | 사용자 |
| 리전 | ap-northeast-2 | 사용자 |
| 백엔드 | Python + FastAPI | 사용자 |
| 프론트엔드 | React + Vite SPA, Fargate가 정적 파일도 서빙 | 사용자 |
| 데이터 저장소 | DynamoDB 단일 테이블 | 사용자 |
| LLM | Sonnet 4.6, 서울 리전 엔드포인트 + global inference ID, API key는 .env | 사용자 |
| 시크릿 | YT_API_KEY, AWS_BEARER_TOKEN_BEDROCK를 .env로 입력받아 노출 회피 | 사용자 |
| 분야 구성 | 고정 8개 카테고리 | 사용자 |
| 추이 기능 | 영상별 시계열 차트, 카테고리 점유율/진입이탈, LLM 추이 리포트, 순위 변동 배지 + 조회 속도 (4종 전부) | 사용자 |
| VPC | 기존 `cc-on-bedrock-vpc` 활용(기존 NAT 재사용) + 신규 VPC 생성 옵션 병행 | 사용자 |
| 오케스트레이션 | 접근 A: 단일 서비스 모놀리스 (컨테이너 내 스케줄러) | 사용자 |
| IaC | AWS CDK + Python | 사용자 |

## 3. 아키텍처

```
사용자 ──HTTPS──▶ CloudFront (기본 *.cloudfront.net 인증서, redirect-to-https)
                    │  정적 경로: CachingOptimized
                    │  /api/*: CachingDisabled + AllViewerExceptHostHeader
                    ▼ HTTP:80 + 커스텀 헤더 X-Origin-Verify
                  ALB (internet-facing, public subnet ×2 AZ)
                    │  SG 인바운드: com.amazonaws.global.cloudfront.origin-facing
                    │  (관리형 prefix list) 만 허용
                    │  리스너 규칙: X-Origin-Verify 불일치 → 403 고정 응답
                    ▼
                  ECS Fargate 서비스 (private subnet ×2 AZ, ARM64)
                    │  FastAPI 컨테이너 1개: SPA 정적 + /api + 수집 스케줄러
                    ├──▶ DynamoDB TrendTable
                    ├──▶ YouTube Data API v3 (기존 NAT Gateway 경유)
                    └──▶ Bedrock ap-northeast-2 (NAT 경유, Bearer 인증)
```

### 3.1 결정과 근거

1. **prefix list SG**: ALB SG 인바운드를 AWS 관리형 prefix list `com.amazonaws.global.cloudfront.origin-facing`으로 제한한다. 이 prefix list는 모든 CloudFront 배포(타 고객 포함)의 origin-facing IP를 포함하므로, CloudFront가 오리진 요청에 붙이는 비밀 커스텀 헤더 `X-Origin-Verify`를 ALB 리스너 규칙이 검증하는 2중 방어를 추가한다. 헤더 값은 CDK 배포 시 생성해 CloudFront 오리진 설정과 ALB 규칙에 주입한다.
2. **CloudFront → ALB 구간은 HTTP:80**: 커스텀 도메인과 ACM 인증서가 없으므로 오리진 구간은 HTTP다(CloudFront는 유효한 인증서가 없는 HTTPS 오리진을 거부한다). 사용자 구간은 항상 HTTPS이고, 오리진 구간은 prefix list + 비밀 헤더로 보호한다. 커스텀 도메인 도입 시 HTTPS 오리진으로 전환할 수 있는 구조를 유지한다.
3. **단일 오리진**: CloudFront의 오리진은 ALB 하나다. Fargate의 FastAPI가 React 빌드 산출물(정적)과 API를 모두 서빙한다. 프론트의 API base는 같은 오리진(`/api`)이므로 하드코딩이 필요 없다 — 선행 프로젝트의 "재배포 시 API URL 수동 갱신" 문제가 구조적으로 사라진다.
4. **Fargate**: ARM64/Graviton(빌드 호스트가 aarch64라 네이티브 빌드, 비용 절감), 0.5 vCPU / 1 GB, desired_count 1(기본). 조건부 쓰기 덕에 2 이상으로 늘려도 수집이 중복되지 않는다. 헬스체크 `GET /healthz`, 배포 서킷 브레이커 + 자동 롤백. 이미지는 CDK `DockerImageAsset`으로 빌드해 ECR에 푸시한다.
5. **오케스트레이션(접근 A — 단일 서비스 모놀리스)**: 컨테이너 내부 APScheduler가 매시 정각(UTC)에 수집한다. LLM 리포트는 온디맨드 생성 + DynamoDB 캐시. 대안(EventBridge 분리 수집, 리포트 사전 생성)은 이 데이터 규모(시간당 API 9회)에서 관리 비용이 실익을 넘어 기각했다. 수집 로직이 커지면 분리 경로가 열려 있다.

### 3.2 네트워크 / VPC 모드

`.env`의 `VPC_MODE`로 두 모드를 지원한다.

| 모드 | 동작 | 용도 |
|---|---|---|
| `existing` (기본) | `VPC_NAME`(기본 `cc-on-bedrock-vpc`)으로 `Vpc.from_lookup`. ALB는 기존 public subnet ×2, Fargate는 기존 private subnet ×2에 배치, 기존 NAT Gateway 재사용 | 이 계정의 현재 배포 |
| `new` | 2 AZ VPC(public + private) + NAT Gateway 1개 + DynamoDB Gateway Endpoint 신규 생성 | 이 레포를 사용하는 다른 사용자 |

실측 확인(2026-08-04): `cc-on-bedrock-vpc` = vpc-0dfa5610180dfa628, 10.100.0.0/16, public ×2 / private ×2 / isolated ×2, 가용 NAT Gateway 2개.

DynamoDB Gateway Endpoint는 `new` 모드에서는 생성하고, `existing` 모드에서는 공유 인프라(라우트 테이블) 변경을 피하기 위해 기본 비활성으로 두되 옵트인 플래그(`CREATE_DDB_ENDPOINT=true`)를 제공한다.

### 3.3 시크릿 처리

선행 프로젝트는 시크릿을 Lambda 환경변수로 주입해 CloudFormation 템플릿에 평문이 남는 약점이 문서화되어 있었다. 이 프로젝트는 다음으로 개선한다.

1. 개발자는 `.env`에 `YT_API_KEY`(필수), `AWS_BEARER_TOKEN_BEDROCK`(선택)를 기입한다. `.env`는 `.gitignore` 대상이며, 배포 스크립트가 시작 시 `git ls-files --error-unmatch .env`로 추적 여부를 검사해 추적 중이면 중단한다(선행 프로젝트에서 .env가 최초 커밋에 포함됐던 사고의 재발 방지).
2. 배포 스크립트(`scripts/deploy.sh`)가 `.env` 값을 AWS Secrets Manager 시크릿(`youtube-trends/app`)에 push한다. 값은 출력하지 않는다.
3. ECS 태스크 정의는 `secrets` 필드로 시크릿 ARN만 참조한다. 값은 템플릿·콘솔·cdk.out 어디에도 나타나지 않고 컨테이너 기동 시 주입된다.
4. `VPC_MODE` 등 비밀이 아닌 설정도 `.env`에서 읽되 이는 일반 환경변수로 전달한다.

## 4. 데이터 모델 (DynamoDB)

단일 테이블 `TrendTable`, on-demand 과금, TTL 속성 `expireAt`, PITR 비활성(캡스톤 규모).

| 아이템 유형 | PK | SK | 주요 속성 | TTL |
|---|---|---|---|---|
| 스냅샷 | `SNAP#ALL` 또는 `SNAP#CAT#{categoryId}` | `TS#{YYYY-MM-DDTHH}` (UTC 시 단위) | `capturedAt`(ISO), `items`(카드 배열), `degraded`(폴백 여부) | 30일 |
| 영상 시계열 | `VID#{videoId}` | `TS#{YYYY-MM-DDTHH}` | `rank`(전체 Top30 기준, 미진입 시 null), `views`, `likes`, `categoryId`, `title` | 30일 |
| LLM 리포트 캐시 | `REPORT#{kind}#{scope}` (kind: brief-now, brief-daily, trend) | `TS#{YYYY-MM-DDTHH}` | `text`, `model`, `generatedAt` | 2일 |

카드 스키마(저장): `rank, videoId, title, channel, views, likes, category, categoryId, thumbnail, publishedAt` — 관측값만 저장한다. 파생 필드(`delta, prevRank, baseline, viewsPerHour`)는 응답 시 계산하며 저장하지 않는다("스냅샷은 관측, 변동은 두 관측 사이의 값").

접근 패턴 → 쿼리 대응:

- 최신 목록: `Query PK=SNAP#{scope}, ScanIndexForward=False, Limit=1`
- T-24h 비교 기준: `Query PK=SNAP#{scope}, SK=TS#{T-24h}` 정확 일치, 없으면 ±2시간 폴백(과거 우선)
- 영상 시계열: `Query PK=VID#{id}, SK BETWEEN` — GSI 불필요
- 카테고리 점유율/진입이탈: `SNAP#ALL` 최근 N개(기본 48시간)를 Query 후 서버에서 집계

파생 필드의 기준 스냅샷 선택 규칙: 순위 변동 배지와 조회 속도는 1→2→3→4시간 전 스냅샷을 순서대로 폴백 조회해 첫 유효 스냅샷을 기준으로 계산한다. 기준 스냅샷의 나이가 0.75시간 미만이면 건너뛴다(짧은 구간의 시간당 환산이 값을 수 배로 확대하는 왜곡 방지 — 선행 프로젝트 실측 차용). 조회 속도는 `(현재 views - 기준 views) / 실제 경과 시간`으로 계산하며 1시간 간격을 가정하지 않는다.

null과 0의 의미 구분을 계약으로 유지한다: `baseline:null`=비교 스냅샷 없음, `prevRank:null`=이전 목록에 없던 영상(NEW), `viewsPerHour:null`=계산 불가, `0`=실제 0. 파생 계산 시 이전 값 검증은 정수형 검사로 하고 `Number(null)==0`류 함정(암묵 형변환)을 피한다.

## 5. 수집 파이프라인

컨테이너 내 APScheduler, 매시 정각(UTC) 실행.

1. `videos.list(chart=mostPopular, regionCode=KR, maxResults=30, part=snippet,statistics)` — 전체 Top 30
2. 고정 8개 카테고리 × `videoCategoryId` 지정 Top 10 — 음악(10), 게임(20), 엔터테인먼트(24), 뉴스/정치(25), 스포츠(17), 영화/애니메이션(1), 과학기술(28), 코미디(23)
3. 쿼터: 시간당 9 유닛, 일 216 유닛 (일일 쿼터 10,000의 2.2%)
4. 카테고리명은 기동 시 `videoCategories.list(regionCode=KR, hl=ko)` 1회 호출로 캐시(실패 시 다음 수집에서 재시도, 그동안 내장 기본명 사용)
5. 스냅샷 아이템은 **조건부 쓰기**(`attribute_not_exists(pk)`)로 저장 — 다중 태스크가 같은 시각에 수집해도 첫 쓰기만 성공(멱등)
6. 영상 시계열 아이템은 BatchWrite — 전체 Top30 + 카테고리 전용 영상 포함 시간당 최대 약 110건
7. **부분 실패 허용**: 특정 scope 호출 실패는 그 scope만 건너뛰고 나머지는 저장한다. 실패는 ERROR 로그로 남긴다.
8. **카테고리 폴백**: 특정 카테고리가 `mostPopular` 미지원 오류를 반환하면 전체 Top30에서 해당 카테고리 영상을 추려 대체하고 스냅샷에 `degraded: true`를 표시한다. 구현 초기에 8개 카테고리 각각의 실지원 여부를 라이브로 확인해 목록을 확정한다.
9. 빈 목록(0건)은 스냅샷으로 저장하지 않는다(전원 NEW 오탐 방지).

## 6. API 계약

FastAPI. 모든 응답 JSON. 오류는 `{error: string(한국어)}` + 상태 코드. 상류(YouTube/Bedrock) 오류 원문은 로그에만 남기고 클라이언트에 흘리지 않는다.

| 메서드/경로 | 기능 | 성공 응답 |
|---|---|---|
| `GET /api/trending?scope=all\|{catId}` | 최신 목록 + 파생 필드 | 카드 배열(전체 30 / 분야 10), 각 카드에 `delta, prevRank, baseline, viewsPerHour` 포함 |
| `GET /api/categories` | 고정 분야 목록 | `[{id, name}]` |
| `GET /api/videos/{videoId}/history?hours=168` | 영상 시계열 | `{videoId, points: [{ts, rank, views}]}` |
| `GET /api/trends/categories?hours=48` | 카테고리 점유율·진입/이탈 집계 | `{hours, series: [...]}` |
| `POST /api/brief` body `{scope, mode: "now"\|"daily"}` | LLM 브리핑 | `{brief, baseline?, cached}` |
| `POST /api/trends/report` body `{scope}` | LLM 추이 분석 리포트 | `{report, cached}` |
| `GET /healthz` | ALB 헬스체크(프로세스 생존만, DynamoDB 미접근) | `200 "ok"` |
| `GET /*` | React SPA 정적 서빙, 미매칭 경로는 index.html 폴백 | HTML/JS/CSS |

상태 코드 계약:

- `503` — LLM 키 미설정. `{error, enabled:false}`. 프론트는 브리핑/리포트 버튼을 잠근다. 배포는 성공하고 해당 기능만 비활성(graceful degradation).
- `409` — 비교 기준 스냅샷 부재(daily 브리핑, 배포 초기의 정상 상태). `{error, baseline:null}`.
- `502` — 상류 오류. `{error, code}` (code는 HTTP 상태 숫자만).
- `400` — 잘못된 파라미터(scope 미존재 등).

## 7. LLM 통합

1. **엔드포인트**: `https://bedrock-runtime.ap-northeast-2.amazonaws.com/model/global.anthropic.claude-sonnet-4-6/converse` — 서울 리전 엔드포인트 + global inference profile ID. 요구사항 그대로다.
2. **인증**: `Authorization: Bearer {AWS_BEARER_TOKEN_BEDROCK}`. IAM/SigV4를 쓰지 않는다. 근거: 이 계정의 조직 SCP(p-zmsqwix6)가 ap-northeast-2의 `bedrock:InvokeModel`을 거부함이 선행 프로젝트에서 실측됐고, 조직 밖에서 발급한 Bearer 키는 SCP 범위 밖이라 동작한다. 태스크 역할에 Bedrock IAM 정책을 부여하지 않는다.
3. **캐시 우선**: 같은 시간 버킷 + 같은 scope + 같은 kind의 결과는 DynamoDB 캐시에서 반환(`cached:true`). 무인증 공개 라우트의 LLM 토큰 비용을 시간당 scope·kind별 1회로 상한한다.
4. **프롬프트 입력은 서버 데이터만**: 클라이언트가 보낸 본문을 프롬프트에 넣지 않고, 서버가 DynamoDB에서 직접 읽은 스냅샷/집계만 사용한다 — 프롬프트 주입 표면을 제거한다. 그 위에 방어적 세탁을 유지한다: 항목 수 상한 50, 필드 길이 상한 120자, 공백 정규화(개행 주입 방지), rank 정수 검증.
5. **타임아웃**: Bedrock 호출 25초(컨테이너에는 Lambda식 하드 타임아웃이 없으므로 클라이언트 대기 상한으로 기능). 타임아웃 시 502.
6. **maxTokens**: 브리핑 1200, 추이 리포트 1500에서 시작해 실측(stopReason 관찰)으로 조정한다. `stopReason=max_tokens`면 잘린 텍스트에 안내문("⚠ 토큰 한도에 도달해 내용이 잘렸습니다")을 붙여 200으로 반환한다.
7. **추이 리포트 입력**: 원시 스냅샷이 아니라 서버가 사전 집계한 요약(신규 진입/이탈 목록, 순위 급변 상위, 카테고리 분포 변화, 조회 속도 상위)만 전달해 입력 토큰을 구조적으로 상한한다.

## 8. 프론트엔드

React 18 + Vite + TypeScript. 탭 3개.

1. **전체 Top 30** — 카드 그리드. 카드: 썸네일, 순위, 제목, 채널, 조회수/좋아요, 카테고리 배지, 순위 변동 배지(↑n/↓n/NEW — `baseline:null`이면 배지 생략), 조회 속도(`+391.4만/시` 형태, 부호는 ASCII `+/-`). 카드 클릭 시 YouTube 새 탭(noopener).
2. **분야별 Top 10** — 카테고리 탭 8개, 같은 카드 컴포넌트 재사용. `degraded` 스냅샷이면 "전체 목록에서 추린 결과" 안내 표시.
3. **추이 분석** — (a) 영상 선택 시계열 차트(Recharts): 순위 차트는 Y축 반전(1위가 위), 조회수 차트는 선형/로그 토글. (b) 카테고리 점유율 스택 영역 차트 + 진입/이탈 카운트. (c) LLM 패널: 현재 브리핑 / 24시간 비교 / 추이 리포트 버튼 3개, 503이면 버튼 잠금, 409는 오류가 아닌 안내로 표시.

공통: 다크/라이트 테마(시스템 추종 + 토글, 첫 페인트 전 확정으로 FOUC 방지), 외부 데이터는 React 기본 이스케이프로 XSS 방지(`dangerouslySetInnerHTML` 금지), API 오류 시 서버의 한국어 `error` 문구 + 재시도 버튼, 로딩 스켈레톤. API base는 같은 오리진 상대 경로 `/api`.

## 9. 에러 처리·운영

- 수집 실패는 웹 서빙에 영향을 주지 않는다(백그라운드 격리). 스냅샷이 없으면 조회 API는 파생 필드를 null로 내리고 200을 유지한다.
- 모든 외부 호출(YouTube, Bedrock, DynamoDB)에 명시적 타임아웃을 둔다.
- 구조화 로깅(JSON stdout → awslogs → CloudWatch Logs, 보존 2주). 정상 흐름은 INFO, 실패만 ERROR — 로그 레벨 기반 알람의 오발을 막는다.
- SIGTERM 수신 시 신규 요청 거부 없이 진행 중 요청을 drain 후 종료한다. ALB deregistration delay(기본 30초로 단축)와 정렬한다.
- CloudWatch 알람 2개(선택 배포 플래그): ALB 5xx 비율, 매시 스냅샷 부재(스냅샷 수집 성공 시 커스텀 메트릭 1 발행, 2시간 무발행 알람).

## 10. 테스트 전략

신규 프로젝트이므로 정상적인 자동화 테스트를 갖춘다(선행 프로젝트의 "테스트 금지" 제약은 그 저장소의 scaffold 사고에 기인한 것으로 이 프로젝트와 무관하다).

- **pytest 단위 테스트**: 파생 필드 계산(delta/viewsPerHour — null vs 0 구분 케이스 포함), 프롬프트 조립·세탁, DynamoDB 키 생성/파싱, 카테고리 폴백 분기. 외부 의존(YouTube, Bedrock, DynamoDB)은 fake/stub으로 대체한다.
- **FastAPI TestClient 통합 테스트**: 라우트별 상태 코드 계약(200/400/409/502/503), 응답 스키마.
- **frontend**: `tsc --noEmit` + Vite 빌드 성공을 게이트로 한다. 컴포넌트 단위 테스트는 초기 범위에서 제외한다(YAGNI).
- **배포 후 스모크**(`scripts/smoke.sh`): 라이브 라우트 curl — `/healthz` 200, `/api/trending` 200 + 배열, `/api/categories` 200, 존재하지 않는 API 경로 404 대조군.
- CI는 초기 범위 제외. 로컬 `pytest && tsc && vite build`가 게이트다.

## 11. 프로젝트 구조

```
youtube-trends/
├── infra/                     # CDK Python 앱
│   ├── app.py                 # 엔트리: .env 로드 → 스택 인스턴스화
│   └── stacks/
│       ├── network.py         # VPC_MODE 분기 (existing lookup / new 생성)
│       └── service.py         # ECR, ECS, ALB, CloudFront, DynamoDB, Secrets 참조
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 앱, 라우터 등록, 스케줄러 기동, SIGTERM 처리
│   │   ├── api/               # trending, videos, trends, brief 라우터
│   │   ├── collector/         # YouTube 호출, 스냅샷 적재
│   │   ├── llm/               # Bedrock Converse 클라이언트, 프롬프트 빌더
│   │   ├── store/             # DynamoDB 접근 계층 (키 규칙 단일 정의)
│   │   └── derive.py          # delta/viewsPerHour 파생 계산
│   ├── tests/
│   └── Dockerfile             # 멀티스테이지: frontend 빌드 → backend 이미지
├── frontend/                  # React + Vite + TS
├── scripts/
│   ├── deploy.sh              # .env 검사 → Secrets push → cdk deploy → 스모크
│   └── smoke.sh
├── .env.example               # YT_API_KEY, AWS_BEARER_TOKEN_BEDROCK, VPC_MODE, VPC_NAME
├── .gitignore                 # .env 최상단
└── docs/superpowers/specs/    # 이 문서
```

## 12. 범위 제외 (YAGNI)

- 사용자 인증/로그인 — 공개 사이트
- 커스텀 도메인/ACM — CloudFront 기본 도메인 사용
- CI/CD 파이프라인 — 로컬 게이트 + 수동 배포
- 다중 리전, 오토스케일링 정책 — desired_count 수동 조정
- 컴포넌트 단위 프론트 테스트, E2E 테스트
- 리포트 사전 생성(접근 C) — 온디맨드 + 캐시로 충분

## 13. 리스크와 완화

| 리스크 | 완화 |
|---|---|
| 카테고리별 mostPopular 미지원 가능성 | 구현 초기 라이브 확인으로 8개 목록 확정, 미지원 시 전체 목록 파생 폴백(`degraded`) |
| prefix list SG는 타 고객 CloudFront도 허용 | X-Origin-Verify 비밀 헤더 검증(ALB 리스너 규칙)으로 2중 방어 |
| 무인증 공개 라우트의 LLM 비용 증폭 | 시간 버킷 캐시로 시간당 scope·kind별 1회 상한 + 서버 데이터만 프롬프트 투입 |
| Bearer 키의 조직 SCP 제약 | 조직 밖 발급 키 전제를 README에 명시(선행 프로젝트 실측) |
| 다중 태스크 중복 수집 | 스냅샷 조건부 쓰기(멱등) |
| CloudFront→ALB HTTP 구간 | prefix list + 비밀 헤더로 보호, 커스텀 도메인 도입 시 HTTPS 전환 경로 유지 |
| .env 커밋 사고(선행 프로젝트에서 실제 발생) | .gitignore + 배포 스크립트의 추적 여부 사전 검사(추적 시 배포 중단) |
