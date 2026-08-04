# YouTube Trends Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** YouTube KR 트렌드(전체 Top 30, 분야별 Top 10, 추이 분석, LLM 브리핑)를 CloudFront → prefix SG → ALB → ECS Fargate로 서빙하는 웹 서비스를 구축한다.

**Architecture:** 단일 Fargate 컨테이너(FastAPI)가 React SPA 정적 파일과 `/api`를 모두 서빙하고, 컨테이너 내 스케줄러가 매시 YouTube 스냅샷을 DynamoDB에 적재한다. LLM(Sonnet 4.6)은 서울 리전 Bedrock 엔드포인트를 global inference ID + Bearer 토큰으로 호출하고 결과를 시간 버킷 단위로 캐시한다.

**Tech Stack:** Python 3.12, FastAPI, APScheduler, boto3, httpx / React 18 + Vite + TypeScript + Recharts / AWS CDK(Python), DynamoDB, ECS Fargate(ARM64), ALB, CloudFront, Secrets Manager

**Spec:** `docs/superpowers/specs/2026-08-04-youtube-trends-design.md` — 각 태스크의 요구사항은 이 스펙을 우선한다.

## Global Constraints

- 리전은 `ap-northeast-2`. LLM 모델 ID는 `global.anthropic.claude-sonnet-4-6`, 엔드포인트는 `https://bedrock-runtime.ap-northeast-2.amazonaws.com/model/global.anthropic.claude-sonnet-4-6/converse`.
- Bedrock 인증은 `Authorization: Bearer {AWS_BEARER_TOKEN_BEDROCK}` 단일 방식. SigV4·boto3 bedrock-runtime 클라이언트·태스크 역할 Bedrock IAM 정책을 쓰지 않는다(조직 SCP p-zmsqwix6가 서울 리전 `bedrock:InvokeModel`을 거부 — 조직 밖 발급 키 전제).
- 시크릿(YT_API_KEY, AWS_BEARER_TOKEN_BEDROCK)은 `.env`로만 공급한다. 값을 로그·문서·커밋·테스트 코드에 절대 쓰지 않는다. `.env`는 `.gitignore` 대상이며 배포 스크립트가 git 추적 여부를 검사해 추적 중이면 중단한다.
- 상류(YouTube/Bedrock) 오류 응답 원문을 클라이언트에 전달하지 않는다. 클라이언트에는 한국어 고정 문구 + 상태 코드 숫자만.
- 파생 필드 계약: `baseline:null`=비교 스냅샷 없음, `prevRank:null`=NEW, `viewsPerHour:null`=계산 불가, `0`=실제 0. 빈(0건) 목록은 스냅샷으로 저장하지 않는다.
- 외부 호출 타임아웃: YouTube 10초, Bedrock 25초. DynamoDB는 boto3 기본값.
- 스냅샷 시각 키는 UTC 시 단위 버킷(`YYYY-MM-DDTHH`). KST 변환을 서버에서 하지 않는다(표시는 프론트 몫).
- TDD: 모든 백엔드 태스크는 실패하는 테스트를 먼저 작성하고 실패를 확인한 뒤 구현한다.
- 커밋 메시지는 conventional commits(`feat:`, `test:`, `chore:`, `docs:`).
- Python 3.12, Node.js 22. 백엔드 의존성은 `backend/requirements.txt`, 개발 의존성은 `backend/requirements-dev.txt`에 고정한다.

## File Structure

```
youtube-trends/
├── infra/
│   ├── app.py                      # CDK 엔트리 (.env 로드 → 스택 2개)
│   ├── requirements.txt
│   └── stacks/
│       ├── __init__.py
│       ├── network.py              # VPC_MODE=existing|new 분기
│       └── service.py              # DynamoDB, ECS, ALB, CloudFront
├── backend/
│   ├── requirements.txt            # fastapi, uvicorn, boto3, httpx, apscheduler
│   ├── requirements-dev.txt        # pytest, moto[dynamodb]
│   ├── Dockerfile                  # 멀티스테이지 (frontend build → runtime)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py               # Settings (env 읽기)
│   │   ├── categories.py           # 고정 8개 카테고리 정의
│   │   ├── derive.py               # delta/viewsPerHour 파생 계산 (순수 함수)
│   │   ├── aggregate.py            # 카테고리 점유율/진입이탈 집계 (순수 함수)
│   │   ├── store/
│   │   │   ├── __init__.py
│   │   │   ├── keys.py             # PK/SK/버킷/TTL 규칙 (순수 함수, 단일 정의)
│   │   │   └── table.py            # TrendStore (DynamoDB 접근 계층)
│   │   ├── collector/
│   │   │   ├── __init__.py
│   │   │   ├── youtube.py          # YouTubeClient (httpx)
│   │   │   └── run.py              # collect_all (수집 오케스트레이션)
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── bedrock.py          # BedrockClient (Bearer converse)
│   │   │   └── prompts.py          # 프롬프트 빌더 + 세탁
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py             # 의존성 주입 (store/clients 싱글턴)
│   │   │   ├── trending.py         # GET /api/trending, /api/categories
│   │   │   ├── videos.py           # GET /api/videos/{id}/history
│   │   │   ├── trends.py           # GET /api/trends/categories
│   │   │   └── brief.py            # POST /api/brief, /api/trends/report
│   │   └── main.py                 # create_app, lifespan(스케줄러), SPA 정적 서빙
│   └── tests/                      # pytest (파일명은 대상 모듈과 1:1)
├── frontend/
│   ├── package.json  vite.config.ts  tsconfig.json  index.html
│   └── src/
│       ├── main.tsx  App.tsx  theme.ts  api.ts  types.ts
│       ├── components/  (Card.tsx, CardGrid.tsx, Badge.tsx, BriefPanel.tsx)
│       └── tabs/        (TopAll.tsx, ByCategory.tsx, Trends.tsx)
├── scripts/
│   ├── deploy.sh                   # .env 검사 → Secrets push → cdk deploy → smoke
│   └── smoke.sh
├── .env.example
└── .gitignore                      # 커밋 완료 (.env 최상단)
```

**태스크 의존 그래프:** T1 → T2 → T3 → {T4, T5} → T6 → T7 → {T8 → T9} → T10 → T11 → T12 → T13 → T14 → T15. T4(derive)와 T5(collector)는 T3(store) 이후 순서 무관.

---

### Task 1: 백엔드 스캐폴딩 + /healthz

**Files:**
- Create: `backend/requirements.txt`, `backend/requirements-dev.txt`, `backend/app/__init__.py`, `backend/app/config.py`, `backend/app/main.py`, `backend/tests/test_healthz.py`, `backend/pytest.ini`

**Interfaces:**
- Produces: `app.config.Settings` (필드: `table_name: str`, `yt_api_key: str`, `bedrock_token: str`, `aws_region: str = "ap-northeast-2"`, `collect_enabled: bool = True`, 클래스메서드 `from_env()`), `app.main.create_app(settings, store=None, yt=None, llm=None) -> FastAPI` — 이후 모든 태스크가 이 팩토리에 의존성을 주입한다. `GET /healthz` → `200 "ok"`(text/plain, DynamoDB 미접근).

- [ ] **Step 1: 의존성 파일과 pytest 설정 작성**

`backend/requirements.txt`:
```
fastapi==0.115.*
uvicorn[standard]==0.30.*
boto3==1.34.*
httpx==0.27.*
apscheduler==3.10.*
```

`backend/requirements-dev.txt`:
```
-r requirements.txt
pytest==8.*
moto[dynamodb]==5.*
```

`backend/pytest.ini`:
```ini
[pytest]
testpaths = tests
```

설치: `cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`

- [ ] **Step 2: 실패하는 테스트 작성**

`backend/tests/test_healthz.py`:
```python
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app


def make_settings(**over):
    base = dict(table_name="t", yt_api_key="x", bedrock_token="", collect_enabled=False)
    base.update(over)
    return Settings(**base)


def test_healthz_returns_ok_without_any_backend():
    app = create_app(make_settings())
    client = TestClient(app)
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.text == "ok"
```

- [ ] **Step 3: 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_healthz.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 4: 최소 구현**

`backend/app/__init__.py`: 빈 파일.

`backend/app/config.py`:
```python
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    table_name: str
    yt_api_key: str
    bedrock_token: str = ""
    aws_region: str = "ap-northeast-2"
    collect_enabled: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            table_name=os.environ["TABLE_NAME"],
            yt_api_key=os.environ.get("YT_API_KEY", ""),
            bedrock_token=os.environ.get("AWS_BEARER_TOKEN_BEDROCK", ""),
            aws_region=os.environ.get("AWS_REGION", "ap-northeast-2"),
            collect_enabled=os.environ.get("COLLECT_ENABLED", "true").lower() == "true",
        )
```

`backend/app/main.py`:
```python
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from app.config import Settings


def create_app(settings: Settings, store=None, yt=None, llm=None) -> FastAPI:
    app = FastAPI(title="youtube-trends")
    app.state.settings = settings
    app.state.store = store
    app.state.yt = yt
    app.state.llm = llm

    @app.get("/healthz", response_class=PlainTextResponse)
    def healthz() -> str:
        # ALB 헬스체크: 프로세스 생존만 확인한다. DynamoDB 장애가 태스크 교체 폭풍을
        # 일으키지 않도록 어떤 외부 의존에도 접근하지 않는다.
        return "ok"

    return app
```

- [ ] **Step 5: 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/test_healthz.py -v`
Expected: PASS (1 passed)

- [ ] **Step 6: 커밋**

```bash
git add backend/
git commit -m "feat: backend scaffolding with /healthz and Settings"
```

---

### Task 2: DynamoDB 키 규칙 (store/keys.py)

**Files:**
- Create: `backend/app/store/__init__.py`, `backend/app/store/keys.py`, `backend/tests/test_keys.py`

**Interfaces:**
- Produces (이후 모든 store/collector/api 태스크가 사용):
  - `hour_bucket(dt: datetime) -> str` — UTC 기준 `"2026-08-04T09"` 형식
  - `snap_pk(scope: str) -> str` — `scope="all"` → `"SNAP#ALL"`, `scope="10"` → `"SNAP#CAT#10"`
  - `vid_pk(video_id: str) -> str` — `"VID#{video_id}"`
  - `report_pk(kind: str, scope: str) -> str` — `"REPORT#{kind}#{scope}"`
  - `ts_sk(bucket: str) -> str` — `"TS#{bucket}"`
  - `ttl_epoch(now: datetime, days: int) -> int`
  - 상수 `RECENT_OFFSETS = [1, 2, 3, 4]`, `DAILY_OFFSETS = [24, 25, 26]`, `MIN_AGE_HOURS = 0.75`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_keys.py`:
```python
from datetime import datetime, timezone, timedelta
from app.store import keys


UTC_T = datetime(2026, 8, 4, 9, 30, 12, tzinfo=timezone.utc)


def test_hour_bucket_truncates_to_utc_hour():
    assert keys.hour_bucket(UTC_T) == "2026-08-04T09"


def test_hour_bucket_converts_non_utc_to_utc():
    kst = UTC_T.astimezone(timezone(timedelta(hours=9)))
    assert keys.hour_bucket(kst) == "2026-08-04T09"


def test_pk_builders():
    assert keys.snap_pk("all") == "SNAP#ALL"
    assert keys.snap_pk("10") == "SNAP#CAT#10"
    assert keys.vid_pk("abc123") == "VID#abc123"
    assert keys.report_pk("brief-now", "all") == "REPORT#brief-now#all"
    assert keys.ts_sk("2026-08-04T09") == "TS#2026-08-04T09"


def test_ttl_epoch_is_days_after_now():
    got = keys.ttl_epoch(UTC_T, days=30)
    assert got == int(UTC_T.timestamp()) + 30 * 86400


def test_shared_constants():
    assert keys.RECENT_OFFSETS == [1, 2, 3, 4]
    assert keys.DAILY_OFFSETS == [24, 25, 26]
    assert keys.MIN_AGE_HOURS == 0.75
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_keys.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.store'`

- [ ] **Step 3: 최소 구현**

`backend/app/store/__init__.py`: 빈 파일.

`backend/app/store/keys.py`:
```python
"""DynamoDB 키 규칙의 단일 정의.

스냅샷 시각 키는 UTC 시 단위 버킷이다. 수집 cron(minute=0)과 버킷 경계가
정렬되므로 "그 시각의 스냅샷"을 계산된 키 하나로 조회할 수 있다.
"""
from datetime import datetime, timezone

# 파생 필드 기준 스냅샷 폴백 오프셋(시간). 배지/속도는 1~4시간 전, 일간 비교는
# 24~26시간 전(과거로만 — 미래 방향 폴백은 "어제와 비교"의 의미를 깨뜨린다).
RECENT_OFFSETS = [1, 2, 3, 4]
DAILY_OFFSETS = [24, 25, 26]
# 기준 스냅샷 최소 연령. 너무 어린 스냅샷과 비교하면 시간당 환산이 수 배로
# 확대된다(선행 프로젝트 실측 0.11h → 9배 왜곡).
MIN_AGE_HOURS = 0.75


def hour_bucket(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H")


def snap_pk(scope: str) -> str:
    return "SNAP#ALL" if scope == "all" else f"SNAP#CAT#{scope}"


def vid_pk(video_id: str) -> str:
    return f"VID#{video_id}"


def report_pk(kind: str, scope: str) -> str:
    return f"REPORT#{kind}#{scope}"


def ts_sk(bucket: str) -> str:
    return f"TS#{bucket}"


def ttl_epoch(now: datetime, days: int) -> int:
    return int(now.timestamp()) + days * 86400
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/test_keys.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/store/ backend/tests/test_keys.py
git commit -m "feat: DynamoDB key rules with shared offset constants"
```

---

### Task 3: TrendStore (store/table.py)

**Files:**
- Create: `backend/app/store/table.py`, `backend/tests/test_table.py`, `backend/tests/conftest.py`

**Interfaces:**
- Consumes: `app.store.keys` 전부 (Task 2)
- Produces (collector/api 태스크가 사용):
  - `TrendStore(table)` — boto3 `Table` 리소스를 주입받는다
  - `put_snapshot(scope, captured_at: datetime, items: list[dict], degraded: bool = False) -> bool` — 조건부 쓰기, 이미 있으면 `False`
  - `latest_snapshot(scope) -> dict | None` — `{"capturedAt": str, "items": list, "degraded": bool}`
  - `baseline_snapshot(scope, now: datetime, offsets: list[int], min_age_hours: float = 0.0) -> dict | None` — 오프셋 순서대로 폴백, 나이 미달 건너뜀, 절대 예외를 던지지 않음
  - `put_video_points(bucket: str, now: datetime, points: list[dict]) -> None` — point: `{"videoId","rank","views","likes","categoryId","title"}`
  - `video_history(video_id, since: datetime, until: datetime) -> list[dict]` — `[{"ts","rank","views"}]` 오름차순
  - `snapshots_range(scope, since: datetime, until: datetime) -> list[dict]` — `[{"bucket","capturedAt","items"}]` 오름차순
  - `get_report(kind, scope, bucket) -> dict | None` / `put_report(kind, scope, bucket, text, model, now) -> None`

- [ ] **Step 1: moto 픽스처 작성**

`backend/tests/conftest.py`:
```python
import boto3
import pytest
from moto import mock_aws


@pytest.fixture()
def table():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="ap-northeast-2")
        t = ddb.create_table(
            TableName="TrendTable",
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield t
```

- [ ] **Step 2: 실패하는 테스트 작성**

`backend/tests/test_table.py`:
```python
from datetime import datetime, timedelta, timezone
from app.store.table import TrendStore

NOW = datetime(2026, 8, 4, 9, 0, tzinfo=timezone.utc)
CARD = {"rank": 1, "videoId": "v1", "title": "t", "channel": "c", "views": 100,
        "likes": 5, "category": "음악", "categoryId": "10",
        "thumbnail": "https://i.ytimg.com/vi/v1/hqdefault.jpg", "publishedAt": "2026-08-01T00:00:00Z"}


def test_put_snapshot_is_conditional(table):
    s = TrendStore(table)
    assert s.put_snapshot("all", NOW, [CARD]) is True
    assert s.put_snapshot("all", NOW, [CARD]) is False  # 같은 시각 키 중복 쓰기 거부


def test_latest_snapshot_returns_most_recent(table):
    s = TrendStore(table)
    s.put_snapshot("all", NOW - timedelta(hours=2), [dict(CARD, views=50)])
    s.put_snapshot("all", NOW, [CARD])
    got = s.latest_snapshot("all")
    assert got["items"][0]["views"] == 100
    assert s.latest_snapshot("10") is None


def test_baseline_snapshot_falls_back_and_respects_min_age(table):
    s = TrendStore(table)
    # 1시간 전 없음, 3시간 전 존재 → 오프셋 [1,2,3,4]가 3에서 발견
    s.put_snapshot("all", NOW - timedelta(hours=3), [CARD])
    got = s.baseline_snapshot("all", NOW, [1, 2, 3, 4])
    assert got is not None
    # min_age: 방금(0.2h 전 capturedAt) 스냅샷은 건너뛴다
    s2 = TrendStore(table)
    s2.put_snapshot("10", NOW - timedelta(minutes=12), [CARD])
    assert s2.baseline_snapshot("10", NOW, [1], min_age_hours=0.75) is None


def test_video_history_orders_ascending(table):
    s = TrendStore(table)
    for h, views in [(3, 10), (2, 20), (1, 30)]:
        ts = NOW - timedelta(hours=h)
        s.put_video_points(ts.strftime("%Y-%m-%dT%H"), ts,
                           [{"videoId": "v1", "rank": 1, "views": views,
                             "likes": 0, "categoryId": "10", "title": "t"}])
    pts = s.video_history("v1", NOW - timedelta(hours=4), NOW)
    assert [p["views"] for p in pts] == [10, 20, 30]


def test_report_roundtrip(table):
    s = TrendStore(table)
    assert s.get_report("brief-now", "all", "2026-08-04T09") is None
    s.put_report("brief-now", "all", "2026-08-04T09", "요약", "sonnet-4.6", NOW)
    got = s.get_report("brief-now", "all", "2026-08-04T09")
    assert got["text"] == "요약"
```

- [ ] **Step 3: 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_table.py -v`
Expected: FAIL — `ModuleNotFoundError` (table.py 부재)

- [ ] **Step 4: 구현**

`backend/app/store/table.py`:
```python
"""DynamoDB 접근 계층. 키 규칙은 keys.py에서만 가져온다.

숫자는 DynamoDB가 Decimal로 돌려주므로 조회 경로에서 int로 정규화한다
(JSON 직렬화와 파생 계산의 정수 검증이 Decimal에 걸려 넘어지지 않도록).
"""
import json
import logging
from datetime import datetime, timedelta, timezone

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.store import keys

log = logging.getLogger(__name__)

SNAPSHOT_TTL_DAYS = 30
REPORT_TTL_DAYS = 2


def _int(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


class TrendStore:
    def __init__(self, table):
        self.table = table

    # -- 스냅샷 ---------------------------------------------------------
    def put_snapshot(self, scope, captured_at, items, degraded=False) -> bool:
        if not items:  # 빈 목록은 저장하지 않는다(전원 NEW 오탐 방지)
            return False
        bucket = keys.hour_bucket(captured_at)
        try:
            self.table.put_item(
                Item={
                    "pk": keys.snap_pk(scope),
                    "sk": keys.ts_sk(bucket),
                    "capturedAt": captured_at.astimezone(timezone.utc).isoformat(),
                    "items": json.dumps(items, ensure_ascii=False),
                    "degraded": degraded,
                    "expireAt": keys.ttl_epoch(captured_at, SNAPSHOT_TTL_DAYS),
                },
                ConditionExpression="attribute_not_exists(pk)",
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False  # 다른 태스크가 먼저 썼다 — 정상 흐름
            raise

    def _to_snapshot(self, item):
        return {
            "bucket": item["sk"].removeprefix("TS#"),
            "capturedAt": item["capturedAt"],
            "items": json.loads(item["items"]),
            "degraded": bool(item.get("degraded", False)),
        }

    def latest_snapshot(self, scope):
        res = self.table.query(
            KeyConditionExpression=Key("pk").eq(keys.snap_pk(scope)),
            ScanIndexForward=False, Limit=1,
        )
        return self._to_snapshot(res["Items"][0]) if res["Items"] else None

    def baseline_snapshot(self, scope, now, offsets, min_age_hours=0.0):
        """오프셋(시간) 순서대로 폴백 조회. 절대 예외를 던지지 않는다 —
        기준 스냅샷 부재는 정상 상태(배지 없는 응답)이지 오류가 아니다."""
        try:
            for off in offsets:
                bucket = keys.hour_bucket(now - timedelta(hours=off))
                res = self.table.get_item(
                    Key={"pk": keys.snap_pk(scope), "sk": keys.ts_sk(bucket)})
                item = res.get("Item")
                if not item:
                    continue
                snap = self._to_snapshot(item)
                try:
                    captured = datetime.fromisoformat(snap["capturedAt"])
                    age_h = (now - captured).total_seconds() / 3600
                except ValueError:
                    continue
                if not (age_h >= min_age_hours):  # NaN 방어 형태 유지
                    continue
                return snap
        except Exception:
            log.exception("baseline_snapshot failed scope=%s", scope)
        return None

    def snapshots_range(self, scope, since, until):
        res = self.table.query(
            KeyConditionExpression=Key("pk").eq(keys.snap_pk(scope))
            & Key("sk").between(keys.ts_sk(keys.hour_bucket(since)),
                                keys.ts_sk(keys.hour_bucket(until))),
        )
        return [self._to_snapshot(i) for i in res["Items"]]

    # -- 영상 시계열 -----------------------------------------------------
    def put_video_points(self, bucket, now, points):
        with self.table.batch_writer() as bw:
            for p in points:
                bw.put_item(Item={
                    "pk": keys.vid_pk(p["videoId"]), "sk": keys.ts_sk(bucket),
                    "rank": p.get("rank"), "views": p["views"], "likes": p.get("likes", 0),
                    "categoryId": p.get("categoryId", ""), "title": p.get("title", ""),
                    "expireAt": keys.ttl_epoch(now, SNAPSHOT_TTL_DAYS),
                })

    def video_history(self, video_id, since, until):
        res = self.table.query(
            KeyConditionExpression=Key("pk").eq(keys.vid_pk(video_id))
            & Key("sk").between(keys.ts_sk(keys.hour_bucket(since)),
                                keys.ts_sk(keys.hour_bucket(until))),
        )
        return [{"ts": i["sk"].removeprefix("TS#"),
                 "rank": _int(i.get("rank"), default=None) if i.get("rank") is not None else None,
                 "views": _int(i.get("views"))} for i in res["Items"]]

    # -- LLM 리포트 캐시 --------------------------------------------------
    def get_report(self, kind, scope, bucket):
        res = self.table.get_item(
            Key={"pk": keys.report_pk(kind, scope), "sk": keys.ts_sk(bucket)})
        item = res.get("Item")
        return {"text": item["text"], "model": item["model"],
                "generatedAt": item["generatedAt"]} if item else None

    def put_report(self, kind, scope, bucket, text, model, now):
        self.table.put_item(Item={
            "pk": keys.report_pk(kind, scope), "sk": keys.ts_sk(bucket),
            "text": text, "model": model,
            "generatedAt": now.astimezone(timezone.utc).isoformat(),
            "expireAt": keys.ttl_epoch(now, REPORT_TTL_DAYS),
        })
```

- [ ] **Step 5: 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/test_table.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: 커밋**

```bash
git add backend/app/store/table.py backend/tests/test_table.py backend/tests/conftest.py
git commit -m "feat: TrendStore with conditional snapshot writes and fallback queries"
```

---

### Task 4: 파생 필드 계산 (derive.py)

**Files:**
- Create: `backend/app/derive.py`, `backend/tests/test_derive.py`

**Interfaces:**
- Consumes: 없음 (순수 함수 — store를 모른다)
- Produces: `with_derived(cards: list[dict], baseline: dict | None, now: datetime) -> list[dict]` — 각 카드에 `baseline`(ISO str|None), `prevRank`(int|None), `delta`(int|None), `viewsPerHour`(int|None)를 추가한 **새 리스트** 반환(입력 불변). Task 7의 `/api/trending`이 사용.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_derive.py`:
```python
from datetime import datetime, timedelta, timezone
from app.derive import with_derived

NOW = datetime(2026, 8, 4, 9, 0, tzinfo=timezone.utc)


def card(video_id, rank, views):
    return {"rank": rank, "videoId": video_id, "views": views}


def baseline_of(hours_ago, items):
    return {"capturedAt": (NOW - timedelta(hours=hours_ago)).isoformat(), "items": items}


def test_no_baseline_yields_all_null_not_new():
    out = with_derived([card("a", 1, 100)], None, NOW)
    assert out[0]["baseline"] is None
    assert out[0]["prevRank"] is None
    assert out[0]["delta"] is None
    assert out[0]["viewsPerHour"] is None


def test_rank_delta_positive_means_rising():
    base = baseline_of(2, [card("a", 5, 100)])
    out = with_derived([card("a", 2, 400)], base, NOW)
    assert out[0]["prevRank"] == 5
    assert out[0]["delta"] == 3          # prevRank - rank
    assert out[0]["viewsPerHour"] == 150  # (400-100)/2h


def test_new_entry_has_null_prev_but_baseline_set():
    base = baseline_of(2, [card("other", 1, 10)])
    out = with_derived([card("a", 3, 100)], base, NOW)
    assert out[0]["baseline"] is not None
    assert out[0]["prevRank"] is None    # NEW 판정 근거
    assert out[0]["viewsPerHour"] is None


def test_zero_views_growth_is_zero_not_null():
    base = baseline_of(2, [card("a", 1, 100)])
    out = with_derived([card("a", 1, 100)], base, NOW)
    assert out[0]["viewsPerHour"] == 0   # 실제 0과 null 구분


def test_non_numeric_prev_views_yields_null():
    base = baseline_of(2, [{"rank": 1, "videoId": "a", "views": None}])
    out = with_derived([card("a", 1, 100)], base, NOW)
    assert out[0]["viewsPerHour"] is None  # Number(null)==0류 함정 방지


def test_unparseable_captured_at_treated_as_no_baseline():
    out = with_derived([card("a", 1, 100)], {"capturedAt": "garbage", "items": []}, NOW)
    assert out[0]["baseline"] is None


def test_input_cards_not_mutated():
    c = card("a", 1, 100)
    with_derived([c], None, NOW)
    assert "delta" not in c
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_derive.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.derive'`

- [ ] **Step 3: 구현**

`backend/app/derive.py`:
```python
"""스냅샷 대비 파생 필드 계산. 순수 함수 — I/O 없음.

계약: baseline=None → 4필드 전부 None("비교 불가"). prevRank=None +
baseline!=None → 신규 진입(NEW). viewsPerHour는 실제 경과 시간으로
나눈다(1시간 간격 가정 금지 — 수집 간격은 폴백 때문에 1~4시간으로 흔들린다).
"""
from datetime import datetime


def with_derived(cards, baseline, now):
    captured = None
    prev_by_id = {}
    if baseline:
        try:
            captured = datetime.fromisoformat(baseline["capturedAt"])
        except (ValueError, KeyError, TypeError):
            captured = None
        if captured is not None:
            prev_by_id = {c.get("videoId"): c for c in baseline.get("items", [])}

    out = []
    for c in cards:
        d = dict(c)
        if captured is None:
            d.update(baseline=None, prevRank=None, delta=None, viewsPerHour=None)
            out.append(d)
            continue
        d["baseline"] = captured.isoformat()
        prev = prev_by_id.get(c.get("videoId"))
        if prev is None:
            d.update(prevRank=None, delta=None, viewsPerHour=None)
            out.append(d)
            continue
        prev_rank = prev.get("rank")
        d["prevRank"] = prev_rank if isinstance(prev_rank, int) else None
        d["delta"] = (d["prevRank"] - c["rank"]) if d["prevRank"] is not None else None
        prev_views = prev.get("views")
        hours = (now - captured).total_seconds() / 3600
        if isinstance(prev_views, int) and isinstance(c.get("views"), int) and hours > 0:
            d["viewsPerHour"] = round((c["views"] - prev_views) / hours)
        else:
            d["viewsPerHour"] = None
        out.append(d)
    return out
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/test_derive.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/derive.py backend/tests/test_derive.py
git commit -m "feat: derived rank/velocity fields with null-vs-zero contract"
```

---

### Task 5: YouTube 수집 (categories.py, collector/)

**Files:**
- Create: `backend/app/categories.py`, `backend/app/collector/__init__.py`, `backend/app/collector/youtube.py`, `backend/app/collector/run.py`, `backend/tests/test_youtube.py`, `backend/tests/test_collect.py`

**Interfaces:**
- Consumes: `TrendStore.put_snapshot / put_video_points` (Task 3), `keys.hour_bucket` (Task 2)
- Produces:
  - `app.categories.CATEGORIES: list[tuple[str, str]]` — `[("10","음악"),("20","게임"),("24","엔터테인먼트"),("25","뉴스/정치"),("17","스포츠"),("1","영화/애니메이션"),("28","과학기술"),("23","코미디")]`
  - `YouTubeClient(api_key, client: httpx.Client)` — `most_popular(category_id: str | None, max_results: int) -> list[dict]`(카드 dict 반환), `UpstreamError(status: int)` 예외
  - `collect_all(store, yt, now) -> dict` — `{"written": int, "skipped": list[str], "degraded": list[str]}` (Task 6 스케줄러가 호출)

- [ ] **Step 1: 실패하는 테스트 작성 — YouTubeClient**

`backend/tests/test_youtube.py`:
```python
import httpx
import pytest
from app.collector.youtube import YouTubeClient, UpstreamError


def yt_payload():
    return {"items": [{
        "id": "v1",
        "snippet": {"title": "제목", "channelTitle": "채널", "categoryId": "10",
                    "publishedAt": "2026-08-01T00:00:00Z",
                    "thumbnails": {"high": {"url": "https://i.ytimg.com/x.jpg"}}},
        "statistics": {"viewCount": "1234", "likeCount": "56"},
    }]}


def make_client(handler):
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return YouTubeClient(api_key="k", client=http, category_names={"10": "음악"})


def test_most_popular_maps_cards_and_coerces_numbers():
    def handler(req):
        assert req.url.params["chart"] == "mostPopular"
        assert req.url.params["regionCode"] == "KR"
        return httpx.Response(200, json=yt_payload())
    cards = make_client(handler).most_popular(None, 30)
    c = cards[0]
    assert c["rank"] == 1 and c["videoId"] == "v1"
    assert c["views"] == 1234 and c["likes"] == 56   # 문자열 → int
    assert c["category"] == "음악" and c["categoryId"] == "10"


def test_missing_like_count_becomes_zero():
    payload = yt_payload()
    del payload["items"][0]["statistics"]["likeCount"]  # 비공개 좋아요
    cards = make_client(lambda r: httpx.Response(200, json=payload)).most_popular(None, 30)
    assert cards[0]["likes"] == 0


def test_category_param_passed_through():
    def handler(req):
        assert req.url.params["videoCategoryId"] == "20"
        return httpx.Response(200, json=yt_payload())
    make_client(handler).most_popular("20", 10)


def test_upstream_error_raises_with_status_only():
    def handler(req):
        return httpx.Response(403, json={"error": {"message": "secret-internal"}})
    with pytest.raises(UpstreamError) as ei:
        make_client(handler).most_popular(None, 30)
    assert ei.value.status == 403
    assert "secret-internal" not in str(ei.value)  # 상류 본문 비노출
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_youtube.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현 — categories.py, youtube.py**

`backend/app/categories.py`:
```python
"""고정 8개 분야. id는 YouTube videoCategoryId. 한글명은 기동 시
videoCategories.list(hl=ko)로 갱신을 시도하고 실패하면 이 기본값을 쓴다.
mostPopular 미지원 카테고리는 collect_all이 전체 목록 파생으로 폴백한다."""
CATEGORIES: list[tuple[str, str]] = [
    ("10", "음악"), ("20", "게임"), ("24", "엔터테인먼트"), ("25", "뉴스/정치"),
    ("17", "스포츠"), ("1", "영화/애니메이션"), ("28", "과학기술"), ("23", "코미디"),
]
CATEGORY_NAMES = dict(CATEGORIES)
```

`backend/app/collector/__init__.py`: 빈 파일.

`backend/app/collector/youtube.py`:
```python
"""YouTube Data API v3 클라이언트. httpx.Client를 주입받는다(테스트는 MockTransport).

상류 오류 본문(GCP 프로젝트 번호·콘솔 URL 포함 가능)은 로그에만 남기고
예외에는 상태 코드만 싣는다.
"""
import logging

import httpx

from app.categories import CATEGORY_NAMES

log = logging.getLogger(__name__)
BASE = "https://www.googleapis.com/youtube/v3"
TIMEOUT = 10.0


class UpstreamError(Exception):
    def __init__(self, status: int):
        super().__init__(f"youtube upstream status={status}")
        self.status = status


class YouTubeClient:
    def __init__(self, api_key, client=None, category_names=None):
        self.api_key = api_key
        self.client = client or httpx.Client(timeout=TIMEOUT)
        self.category_names = dict(category_names or CATEGORY_NAMES)

    def load_category_names(self):
        """기동 시 1회 호출. 실패해도 기본명으로 동작한다."""
        try:
            res = self.client.get(f"{BASE}/videoCategories", params={
                "part": "snippet", "regionCode": "KR", "hl": "ko", "key": self.api_key})
            if res.status_code == 200:
                for it in res.json().get("items", []):
                    self.category_names[it["id"]] = it["snippet"]["title"]
        except httpx.HTTPError:
            log.warning("videoCategories load failed; using defaults")

    def most_popular(self, category_id, max_results):
        params = {"part": "snippet,statistics", "chart": "mostPopular",
                  "regionCode": "KR", "maxResults": str(max_results), "key": self.api_key}
        if category_id:
            params["videoCategoryId"] = category_id
        try:
            res = self.client.get(f"{BASE}/videos", params=params)
        except httpx.HTTPError as e:
            log.error("youtube request failed: %s", type(e).__name__)
            raise UpstreamError(502) from e
        if res.status_code != 200:
            log.error("youtube status=%s body=%s", res.status_code, res.text[:500])
            raise UpstreamError(res.status_code)
        cards = []
        for i, it in enumerate(res.json().get("items", []), start=1):
            sn, st = it.get("snippet", {}), it.get("statistics", {})
            cat_id = sn.get("categoryId", "")
            cards.append({
                "rank": i, "videoId": it.get("id", ""),
                "title": sn.get("title", ""), "channel": sn.get("channelTitle", ""),
                "views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)),
                "category": self.category_names.get(cat_id, "기타"), "categoryId": cat_id,
                "thumbnail": sn.get("thumbnails", {}).get("high", {}).get("url", ""),
                "publishedAt": sn.get("publishedAt", ""),
            })
        return cards
```

- [ ] **Step 4: youtube 테스트 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/test_youtube.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: 실패하는 테스트 작성 — collect_all**

`backend/tests/test_collect.py`:
```python
from datetime import datetime, timezone
from app.collector.run import collect_all
from app.collector.youtube import UpstreamError
from app.store.table import TrendStore

NOW = datetime(2026, 8, 4, 9, 0, tzinfo=timezone.utc)


def card(video_id, rank, cat="10"):
    return {"rank": rank, "videoId": video_id, "title": "t", "channel": "c",
            "views": 10, "likes": 1, "category": "음악", "categoryId": cat,
            "thumbnail": "", "publishedAt": ""}


class FakeYT:
    def __init__(self, fail_categories=()):
        self.fail = set(fail_categories)

    def most_popular(self, category_id, max_results):
        if category_id in self.fail:
            raise UpstreamError(404)
        if category_id is None:
            return [card("a", 1, "10"), card("b", 2, "20")]
        return [card(f"{category_id}-1", 1, category_id)]


def test_collect_writes_all_and_categories(table):
    store = TrendStore(table)
    result = collect_all(store, FakeYT(), NOW)
    assert result["written"] >= 9  # 전체 1 + 카테고리 8
    assert store.latest_snapshot("all") is not None
    assert store.latest_snapshot("10") is not None


def test_failed_category_falls_back_to_derived_from_all(table):
    store = TrendStore(table)
    result = collect_all(store, FakeYT(fail_categories={"20"}), NOW)
    snap = store.latest_snapshot("20")
    assert snap["degraded"] is True           # 전체 목록 파생 폴백
    assert snap["items"][0]["videoId"] == "b"
    assert "20" in result["degraded"]


def test_video_points_written_for_all_scope(table):
    store = TrendStore(table)
    collect_all(store, FakeYT(), NOW)
    pts = store.video_history("a", NOW.replace(hour=0), NOW)
    assert len(pts) == 1 and pts[0]["rank"] == 1
```

- [ ] **Step 6: 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_collect.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.collector.run'`

- [ ] **Step 7: 구현 — collector/run.py**

`backend/app/collector/run.py`:
```python
"""수집 오케스트레이션. 부분 실패 허용 — scope 하나의 실패가 나머지를 막지 않는다."""
import logging

from app.categories import CATEGORIES
from app.collector.youtube import UpstreamError
from app.store import keys

log = logging.getLogger(__name__)


def collect_all(store, yt, now):
    written, skipped, degraded = 0, [], []
    bucket = keys.hour_bucket(now)

    # 1) 전체 Top 30 — 실패하면 이번 사이클 전체를 접는다(파생 폴백의 원천이므로)
    try:
        all_cards = yt.most_popular(None, 30)
    except UpstreamError as e:
        log.error("collect: ALL scope failed status=%s", e.status)
        return {"written": 0, "skipped": ["all"], "degraded": []}
    if store.put_snapshot("all", now, all_cards):
        written += 1
    store.put_video_points(bucket, now, [
        {"videoId": c["videoId"], "rank": c["rank"], "views": c["views"],
         "likes": c["likes"], "categoryId": c["categoryId"], "title": c["title"]}
        for c in all_cards])

    # 2) 카테고리별 Top 10 — 미지원/실패 카테고리는 전체 목록 파생으로 폴백
    for cat_id, _name in CATEGORIES:
        try:
            cards = yt.most_popular(cat_id, 10)
            is_degraded = False
        except UpstreamError as e:
            log.warning("collect: category %s failed status=%s; deriving", cat_id, e.status)
            cards = [dict(c, rank=i) for i, c in enumerate(
                (c for c in all_cards if c["categoryId"] == cat_id), start=1)][:10]
            is_degraded = True
        if not cards:
            skipped.append(cat_id)
            continue
        if store.put_snapshot(cat_id, now, cards, degraded=is_degraded):
            written += 1
        if is_degraded:
            degraded.append(cat_id)

    log.info("collect done bucket=%s written=%s skipped=%s degraded=%s",
             bucket, written, skipped, degraded)
    return {"written": written, "skipped": skipped, "degraded": degraded}
```

- [ ] **Step 8: 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/ -v`
Expected: PASS (전체 — healthz/keys/table/derive/youtube/collect)

- [ ] **Step 9: 커밋**

```bash
git add backend/app/categories.py backend/app/collector/ backend/tests/test_youtube.py backend/tests/test_collect.py
git commit -m "feat: YouTube collector with category fallback and partial-failure isolation"
```

---

### Task 6: 스케줄러 + 앱 조립 (main.py 확장, api/deps.py)

**Files:**
- Create: `backend/app/api/__init__.py`, `backend/app/api/deps.py`, `backend/tests/test_app_wiring.py`
- Modify: `backend/app/main.py` (Task 1에서 생성한 파일 — `create_app`에 lifespan/스케줄러 추가)

**Interfaces:**
- Consumes: `Settings`(T1), `TrendStore`(T3), `YouTubeClient`(T5), `collect_all`(T5)
- Produces:
  - `create_app(settings, store=None, yt=None, llm=None)` — 주입 인자가 None이면 실물 생성(운영), 주입되면 그대로 사용(테스트). `settings.collect_enabled=True`일 때만 APScheduler가 매시 정각(UTC) `collect_all` 실행.
  - `app.api.deps.get_store(request) -> TrendStore`, `get_settings(request)`, `get_yt(request)`, `get_llm(request)` — 라우터 태스크(T7, T9)가 사용하는 FastAPI 의존성.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_app_wiring.py`:
```python
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app


def test_scheduler_not_started_when_collect_disabled():
    settings = Settings(table_name="t", yt_api_key="x", collect_enabled=False)
    app = create_app(settings, store=object(), yt=object())
    with TestClient(app):  # lifespan 실행
        assert app.state.scheduler is None


def test_scheduler_started_when_enabled():
    settings = Settings(table_name="t", yt_api_key="x", collect_enabled=True)
    app = create_app(settings, store=object(), yt=object())
    with TestClient(app):
        assert app.state.scheduler is not None
        jobs = app.state.scheduler.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == "hourly-collect"
    assert app.state.scheduler.running is False  # 종료 시 정리
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_app_wiring.py -v`
Expected: FAIL — `AttributeError: 'State' object has no attribute 'scheduler'`

- [ ] **Step 3: 구현**

`backend/app/api/__init__.py`: 빈 파일.

`backend/app/api/deps.py`:
```python
from fastapi import Request


def get_settings(request: Request):
    return request.app.state.settings


def get_store(request: Request):
    return request.app.state.store


def get_yt(request: Request):
    return request.app.state.yt


def get_llm(request: Request):
    return request.app.state.llm
```

`backend/app/main.py` 전체 교체:
```python
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from app.config import Settings

logging.basicConfig(level=logging.INFO, format='{"lvl":"%(levelname)s","msg":"%(message)s","logger":"%(name)s"}')
log = logging.getLogger(__name__)


def _build_real_dependencies(settings):
    """운영 경로에서만 import — 테스트는 주입으로 우회한다."""
    import boto3
    from app.collector.youtube import YouTubeClient
    from app.store.table import TrendStore

    table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(settings.table_name)
    yt = YouTubeClient(settings.yt_api_key)
    yt.load_category_names()
    return TrendStore(table), yt


def create_app(settings: Settings, store=None, yt=None, llm=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app.state.store is None or app.state.yt is None:
            app.state.store, app.state.yt = _build_real_dependencies(settings)
        app.state.scheduler = None
        if settings.collect_enabled:
            from apscheduler.schedulers.background import BackgroundScheduler
            from app.collector.run import collect_all

            sched = BackgroundScheduler(timezone="UTC")
            sched.add_job(
                lambda: collect_all(app.state.store, app.state.yt,
                                    datetime.now(timezone.utc)),
                trigger="cron", minute=0, id="hourly-collect",
                misfire_grace_time=300, coalesce=True,
            )
            sched.start()
            app.state.scheduler = sched
        yield
        if app.state.scheduler is not None:
            # SIGTERM → uvicorn graceful shutdown → lifespan 종료.
            # wait=False: 수집 중이어도 drain을 막지 않는다(다음 시각에 재수집됨).
            app.state.scheduler.shutdown(wait=False)

    app = FastAPI(title="youtube-trends", lifespan=lifespan)
    app.state.settings = settings
    app.state.store = store
    app.state.yt = yt
    app.state.llm = llm

    @app.get("/healthz", response_class=PlainTextResponse)
    def healthz() -> str:
        return "ok"

    return app
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/ -v`
Expected: PASS (전체 — 기존 healthz 테스트 포함 회귀 없음)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/main.py backend/app/api/ backend/tests/test_app_wiring.py
git commit -m "feat: app assembly with hourly collect scheduler and DI seams"
```

---

### Task 7: 조회 API (trending/videos/trends 라우터 + aggregate.py)

**Files:**
- Create: `backend/app/api/trending.py`, `backend/app/api/videos.py`, `backend/app/api/trends.py`, `backend/app/aggregate.py`, `backend/tests/test_api_read.py`, `backend/tests/test_aggregate.py`
- Modify: `backend/app/main.py` (라우터 3개 include)

**Interfaces:**
- Consumes: `TrendStore`(T3), `with_derived`(T4), `keys.RECENT_OFFSETS/MIN_AGE_HOURS`(T2), `CATEGORIES`(T5), `deps`(T6)
- Produces (프론트 T10~11과 스모크 T15가 의존하는 HTTP 계약):
  - `GET /api/trending?scope=all|{catId}` → 200 카드 배열(파생 필드 포함) / 400 잘못된 scope / 200 `[]` 스냅샷 부재 시
  - `GET /api/categories` → 200 `[{"id","name"}]`
  - `GET /api/videos/{videoId}/history?hours=168` → 200 `{"videoId","points":[{"ts","rank","views"}]}`
  - `GET /api/trends/categories?hours=48` → 200 `{"hours","series":[{"ts","shares":{catId:count},"entered":int,"exited":int}]}`
  - `app.aggregate.category_series(snapshots: list[dict]) -> list[dict]` — 순수 함수

- [ ] **Step 1: 실패하는 테스트 작성 — aggregate**

`backend/tests/test_aggregate.py`:
```python
from app.aggregate import category_series


def snap(bucket, ids_cats):
    return {"bucket": bucket, "capturedAt": bucket + ":00:00+00:00",
            "items": [{"videoId": v, "categoryId": c, "rank": i + 1, "views": 1}
                      for i, (v, c) in enumerate(ids_cats)]}


def test_shares_counted_per_bucket():
    out = category_series([snap("2026-08-04T08", [("a", "10"), ("b", "10"), ("c", "20")])])
    assert out[0]["shares"] == {"10": 2, "20": 1}
    assert out[0]["entered"] == 0 and out[0]["exited"] == 0  # 첫 스냅샷은 기준 없음


def test_entered_exited_between_buckets():
    s1 = snap("2026-08-04T08", [("a", "10"), ("b", "20")])
    s2 = snap("2026-08-04T09", [("a", "10"), ("c", "20")])  # b 이탈, c 진입
    out = category_series([s1, s2])
    assert out[1]["entered"] == 1 and out[1]["exited"] == 1
```

- [ ] **Step 2: 실패하는 테스트 작성 — 읽기 API**

`backend/tests/test_api_read.py`:
```python
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from app.store.table import TrendStore

NOW = datetime.now(timezone.utc)


def card(video_id, rank, views=100):
    return {"rank": rank, "videoId": video_id, "title": "t", "channel": "c",
            "views": views, "likes": 1, "category": "음악", "categoryId": "10",
            "thumbnail": "", "publishedAt": ""}


def make_client(table):
    settings = Settings(table_name="t", yt_api_key="x", collect_enabled=False)
    app = create_app(settings, store=TrendStore(table), yt=object())
    return TestClient(app), TrendStore(table)


def test_trending_empty_when_no_snapshot(table):
    client, _ = make_client(table)
    res = client.get("/api/trending")
    assert res.status_code == 200 and res.json() == []


def test_trending_includes_derived_fields(table):
    client, store = make_client(table)
    store.put_snapshot("all", NOW - timedelta(hours=2), [card("a", 5, views=50)])
    store.put_snapshot("all", NOW, [card("a", 2, views=350)])
    body = client.get("/api/trending?scope=all").json()
    assert body[0]["delta"] == 3
    assert body[0]["viewsPerHour"] == 150


def test_trending_rejects_unknown_scope(table):
    client, _ = make_client(table)
    assert client.get("/api/trending?scope=999").status_code == 400


def test_categories_lists_fixed_eight(table):
    client, _ = make_client(table)
    body = client.get("/api/categories").json()
    assert len(body) == 8 and body[0] == {"id": "10", "name": "음악"}


def test_video_history_endpoint(table):
    client, store = make_client(table)
    ts = NOW - timedelta(hours=1)
    store.put_video_points(ts.strftime("%Y-%m-%dT%H"), ts,
                           [{"videoId": "a", "rank": 3, "views": 42,
                             "likes": 0, "categoryId": "10", "title": "t"}])
    body = client.get("/api/videos/a/history?hours=24").json()
    assert body["videoId"] == "a" and body["points"][0]["views"] == 42


def test_trends_categories_endpoint(table):
    client, store = make_client(table)
    store.put_snapshot("all", NOW - timedelta(hours=1), [card("a", 1)])
    store.put_snapshot("all", NOW, [card("b", 1)])
    body = client.get("/api/trends/categories?hours=48").json()
    assert body["hours"] == 48 and len(body["series"]) == 2
    assert body["series"][1]["entered"] == 1
```

- [ ] **Step 3: 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_aggregate.py tests/test_api_read.py -v`
Expected: FAIL — `ModuleNotFoundError` 2건

- [ ] **Step 4: 구현**

`backend/app/aggregate.py`:
```python
"""스냅샷 목록 → 카테고리 점유율/진입이탈 시계열. 순수 함수."""


def category_series(snapshots):
    out, prev_ids = [], None
    for s in snapshots:
        ids = {c.get("videoId") for c in s["items"]}
        shares = {}
        for c in s["items"]:
            cid = c.get("categoryId", "")
            shares[cid] = shares.get(cid, 0) + 1
        entered = len(ids - prev_ids) if prev_ids is not None else 0
        exited = len(prev_ids - ids) if prev_ids is not None else 0
        out.append({"ts": s["bucket"], "shares": shares,
                    "entered": entered, "exited": exited})
        prev_ids = ids
    return out
```

`backend/app/api/trending.py`:
```python
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_store
from app.categories import CATEGORIES, CATEGORY_NAMES
from app.derive import with_derived
from app.store import keys

router = APIRouter(prefix="/api")
VALID_SCOPES = {"all"} | {cid for cid, _ in CATEGORIES}


@router.get("/trending")
def trending(scope: str = "all", store=Depends(get_store)):
    if scope not in VALID_SCOPES:
        raise HTTPException(400, detail={"error": "지원하지 않는 분야입니다"})
    snap = store.latest_snapshot(scope)
    if snap is None:
        return []
    now = datetime.now(timezone.utc)
    baseline = store.baseline_snapshot(scope, now, keys.RECENT_OFFSETS,
                                       min_age_hours=keys.MIN_AGE_HOURS)
    return with_derived(snap["items"], baseline, now)


@router.get("/categories")
def categories():
    return [{"id": cid, "name": CATEGORY_NAMES[cid]} for cid, _ in CATEGORIES]
```

`backend/app/api/videos.py`:
```python
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_store

router = APIRouter(prefix="/api")


@router.get("/videos/{video_id}/history")
def video_history(video_id: str, hours: int = Query(default=168, ge=1, le=720),
                  store=Depends(get_store)):
    until = datetime.now(timezone.utc)
    since = until - timedelta(hours=hours)
    return {"videoId": video_id, "points": store.video_history(video_id, since, until)}
```

`backend/app/api/trends.py`:
```python
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from app.aggregate import category_series
from app.api.deps import get_store

router = APIRouter(prefix="/api")


@router.get("/trends/categories")
def trends_categories(hours: int = Query(default=48, ge=2, le=720),
                      store=Depends(get_store)):
    until = datetime.now(timezone.utc)
    snaps = store.snapshots_range("all", until - timedelta(hours=hours), until)
    return {"hours": hours, "series": category_series(snaps)}
```

`backend/app/main.py`의 `create_app` 마지막(healthz 아래)에 추가:
```python
    from app.api import trending as trending_api, videos as videos_api, trends as trends_api
    app.include_router(trending_api.router)
    app.include_router(videos_api.router)
    app.include_router(trends_api.router)
```

- [ ] **Step 5: 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/ -v`
Expected: PASS (전체)

- [ ] **Step 6: 커밋**

```bash
git add backend/app/api/ backend/app/aggregate.py backend/app/main.py backend/tests/test_api_read.py backend/tests/test_aggregate.py
git commit -m "feat: read APIs for trending, video history, and category trends"
```

---

### Task 8: LLM 클라이언트 + 프롬프트 (llm/)

**Files:**
- Create: `backend/app/llm/__init__.py`, `backend/app/llm/bedrock.py`, `backend/app/llm/prompts.py`, `backend/tests/test_bedrock.py`, `backend/tests/test_prompts.py`

**Interfaces:**
- Consumes: 없음 (독립 모듈 — httpx 주입)
- Produces (T9가 사용):
  - `BedrockClient(token: str, client: httpx.Client | None)` — `converse(system: str, user: str, max_tokens: int) -> tuple[str, str]`(text, stop_reason). 토큰 빈 문자열이면 `LlmDisabled` 예외. 상류 오류는 `LlmUpstreamError(status)`.
  - `MODEL_ID = "global.anthropic.claude-sonnet-4-6"`, `ENDPOINT`(Global Constraints의 URL), `TIMEOUT = 25.0`
  - `prompts.clean_text(s, max_len=120) -> str`, `prompts.build_brief(cards) -> tuple[str, str]`(system, user), `prompts.build_daily(cards, baseline) -> tuple[str, str]`, `prompts.build_trend_report(series, movers) -> tuple[str, str]`, `MAX_ITEMS = 50`
  - `TRUNCATION_NOTICE = "\n\n⚠ 토큰 한도에 도달해 내용이 잘렸습니다."`

- [ ] **Step 1: 실패하는 테스트 작성 — BedrockClient**

`backend/tests/test_bedrock.py`:
```python
import httpx
import pytest
from app.llm.bedrock import BedrockClient, LlmDisabled, LlmUpstreamError, ENDPOINT


def ok_payload(text="분석", stop="end_turn"):
    return {"output": {"message": {"content": [{"text": text}]}}, "stopReason": stop}


def make(handler, token="tok"):
    return BedrockClient(token, client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_disabled_when_no_token():
    with pytest.raises(LlmDisabled):
        make(lambda r: httpx.Response(200), token="").converse("s", "u", 100)


def test_converse_sends_bearer_and_parses_text():
    def handler(req):
        assert str(req.url) == ENDPOINT
        assert req.headers["authorization"] == "Bearer tok"
        return httpx.Response(200, json=ok_payload())
    text, stop = make(handler).converse("시스템", "사용자", 100)
    assert text == "분석" and stop == "end_turn"


def test_upstream_error_hides_body():
    def handler(req):
        return httpx.Response(403, json={"message": "account-id-12345 denied"})
    with pytest.raises(LlmUpstreamError) as ei:
        make(handler).converse("s", "u", 100)
    assert ei.value.status == 403
    assert "account-id" not in str(ei.value)


def test_timeout_maps_to_upstream_error():
    def handler(req):
        raise httpx.ReadTimeout("slow")
    with pytest.raises(LlmUpstreamError) as ei:
        make(handler).converse("s", "u", 100)
    assert ei.value.status == 504
```

- [ ] **Step 2: 실패하는 테스트 작성 — prompts**

`backend/tests/test_prompts.py`:
```python
from app.llm import prompts


def card(**over):
    base = {"rank": 1, "videoId": "v", "title": "제목", "channel": "채널",
            "views": 1234567, "likes": 1, "category": "음악", "categoryId": "10"}
    base.update(over)
    return base


def test_clean_text_collapses_newlines_and_truncates():
    s = prompts.clean_text("줄1\n줄2\t줄3" + "가" * 300)
    assert "\n" not in s and "\t" not in s
    assert len(s) <= 120


def test_build_brief_caps_items():
    system, user = prompts.build_brief([card(rank=i) for i in range(1, 100)])
    assert user.count("위:") <= prompts.MAX_ITEMS


def test_rank_must_be_int_or_question_mark():
    _, user = prompts.build_brief([card(rank="<주입시도>")])
    assert "<주입시도>" not in user and "?위:" in user


def test_build_daily_includes_entered_exited_sections():
    prev = {"capturedAt": "2026-08-03T09:00:00+00:00",
            "items": [card(videoId="old", title="이탈영상")]}
    _, user = prompts.build_daily([card(videoId="new", title="진입영상")], prev)
    assert "진입영상" in user and "이탈영상" in user


def test_build_trend_report_serializes_series():
    series = [{"ts": "2026-08-04T08", "shares": {"10": 3}, "entered": 0, "exited": 0}]
    movers = [card(title="급상승왕")]
    _, user = prompts.build_trend_report(series, movers)
    assert "2026-08-04T08" in user and "급상승왕" in user
```

- [ ] **Step 3: 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_bedrock.py tests/test_prompts.py -v`
Expected: FAIL — `ModuleNotFoundError` 2건

- [ ] **Step 4: 구현**

`backend/app/llm/__init__.py`: 빈 파일.

`backend/app/llm/bedrock.py`:
```python
"""Bedrock Converse REST 직접 호출. Bearer 인증 전용(SigV4/boto3 금지 —
조직 SCP가 서울 리전 InvokeModel을 거부하므로 조직 밖 발급 키가 전제).
"""
import logging

import httpx

log = logging.getLogger(__name__)

MODEL_ID = "global.anthropic.claude-sonnet-4-6"
ENDPOINT = f"https://bedrock-runtime.ap-northeast-2.amazonaws.com/model/{MODEL_ID}/converse"
TIMEOUT = 25.0


class LlmDisabled(Exception):
    """토큰 미설정 — 503 graceful degradation 신호."""


class LlmUpstreamError(Exception):
    def __init__(self, status: int):
        super().__init__(f"bedrock upstream status={status}")
        self.status = status


class BedrockClient:
    def __init__(self, token: str, client: httpx.Client | None = None):
        self.token = token
        self.client = client or httpx.Client(timeout=TIMEOUT)

    def converse(self, system: str, user: str, max_tokens: int):
        if not self.token:
            raise LlmDisabled()
        body = {
            "system": [{"text": system}],
            "messages": [{"role": "user", "content": [{"text": user}]}],
            "inferenceConfig": {"maxTokens": max_tokens},
        }
        try:
            res = self.client.post(ENDPOINT, json=body, headers={
                "authorization": f"Bearer {self.token}",
                "content-type": "application/json"})
        except httpx.HTTPError as e:
            log.error("bedrock request failed: %s", type(e).__name__)
            raise LlmUpstreamError(504) from e
        if res.status_code != 200:
            # 오류 본문에 계정 ID·모델 ARN이 올 수 있다 — 로그에만 남긴다.
            log.error("bedrock status=%s body=%s", res.status_code, res.text[:500])
            raise LlmUpstreamError(res.status_code)
        data = res.json()
        try:
            text = data["output"]["message"]["content"][0]["text"]
        except (KeyError, IndexError, TypeError):
            log.error("bedrock unexpected shape keys=%s", list(data.keys()))
            raise LlmUpstreamError(502)
        return text, data.get("stopReason", "")
```

`backend/app/llm/prompts.py`:
```python
"""프롬프트 빌더. 입력은 서버가 DynamoDB에서 읽은 데이터지만, 제목·채널명은
YouTube를 거친 외부 문자열이므로 세탁을 유지한다(개행 주입으로 목록 구조
위조 방지, 길이 상한으로 토큰 증폭 방지).
"""
MAX_ITEMS = 50
MAX_LIST = 8
TRUNCATION_NOTICE = "\n\n⚠ 토큰 한도에 도달해 내용이 잘렸습니다."

SYSTEM = (
    "당신은 YouTube 한국 트렌드 분석가다. 주어진 자료에 없는 사실을 만들지 마라. "
    "한국어로, 소제목 있는 간결한 문단으로 답하라."
)


def clean_text(s, max_len=120):
    if not isinstance(s, str):
        return ""
    return " ".join(s.split())[:max_len]


def _pos(v):
    return str(v) if isinstance(v, int) and not isinstance(v, bool) else "?"


def _line(c):
    return (f"{_pos(c.get('rank'))}위: {clean_text(c.get('title'))} — "
            f"{clean_text(c.get('channel'))} ({clean_text(c.get('category'), 30)}, "
            f"조회 {c.get('views') if isinstance(c.get('views'), int) else 0:,})")


def build_brief(cards):
    lines = [_line(c) for c in cards[:MAX_ITEMS]]
    user = "다음은 현재 YouTube 한국 급상승 목록이다.\n" + "\n".join(lines) + \
           "\n\n오늘의 트렌드 흐름을 3개 소제목으로 브리핑하라."
    return SYSTEM, user


def build_daily(cards, baseline):
    cur_ids = {c.get("videoId") for c in cards}
    prev_items = baseline.get("items", [])
    prev_ids = {c.get("videoId") for c in prev_items}
    entered = [c for c in cards if c.get("videoId") not in prev_ids][:MAX_LIST]
    exited = [c for c in prev_items if c.get("videoId") not in cur_ids][:MAX_LIST]
    user = (
        f"기준 시각: {clean_text(baseline.get('capturedAt'), 40)}\n"
        "== 새로 진입 ==\n" + "\n".join(_line(c) for c in entered) +
        "\n== 이탈 ==\n" + "\n".join(_line(c) for c in exited) +
        "\n== 현재 상위 ==\n" + "\n".join(_line(c) for c in cards[:10]) +
        "\n\n어제와 비교해 무엇이 달라졌는지 브리핑하라."
    )
    return SYSTEM, user


def build_trend_report(series, movers):
    share_lines = [
        f"{s['ts']}: 점유 {s['shares']} 진입 {s['entered']} 이탈 {s['exited']}"
        for s in series[-24:]  # 최근 24버킷으로 입력 상한
    ]
    user = (
        "== 시간대별 카테고리 점유/진입이탈 ==\n" + "\n".join(share_lines) +
        "\n== 조회 속도 상위 ==\n" + "\n".join(_line(c) for c in movers[:MAX_LIST]) +
        "\n\n최근 트렌드의 추이(상승세 분야, 순위 교체 양상)를 분석하라."
    )
    return SYSTEM, user
```

- [ ] **Step 5: 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/test_bedrock.py tests/test_prompts.py -v`
Expected: PASS (9 passed)

- [ ] **Step 6: 커밋**

```bash
git add backend/app/llm/ backend/tests/test_bedrock.py backend/tests/test_prompts.py
git commit -m "feat: Bedrock bearer client and sanitized prompt builders"
```

---

### Task 9: LLM API 라우터 (api/brief.py)

**Files:**
- Create: `backend/app/api/brief.py`, `backend/tests/test_api_brief.py`
- Modify: `backend/app/main.py` (brief 라우터 include + 운영 경로에서 `BedrockClient` 생성)

**Interfaces:**
- Consumes: `BedrockClient/LlmDisabled/LlmUpstreamError`(T8), `prompts`(T8), `TrendStore.get_report/put_report/latest_snapshot/baseline_snapshot`(T3), `keys.DAILY_OFFSETS`(T2), `with_derived`(T4)
- Produces (프론트 T11, 스모크 T15가 의존):
  - `POST /api/brief` body `{"scope":"all","mode":"now"|"daily"}` → 200 `{"brief","baseline"?,"cached"}` / 400 / 409(daily 기준 부재, `{"error","baseline":null}`) / 502 `{"error","code"}` / 503 `{"error","enabled":false}`
  - `POST /api/trends/report` body `{"scope":"all"}` → 200 `{"report","cached"}` / 400 / 502 / 503
  - maxTokens: brief-now 1200, brief-daily 600, trend 1500 (실측 후 조정 — stopReason 로그로 판단)

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_api_brief.py`:
```python
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from app.config import Settings
from app.llm.bedrock import LlmDisabled, LlmUpstreamError
from app.main import create_app
from app.store.table import TrendStore

NOW = datetime.now(timezone.utc)


def card(video_id="a", rank=1):
    return {"rank": rank, "videoId": video_id, "title": "t", "channel": "c",
            "views": 10, "likes": 1, "category": "음악", "categoryId": "10",
            "thumbnail": "", "publishedAt": ""}


class FakeLlm:
    def __init__(self, disabled=False, fail=False, stop="end_turn"):
        self.disabled, self.fail, self.stop = disabled, fail, stop
        self.calls = 0

    def converse(self, system, user, max_tokens):
        if self.disabled:
            raise LlmDisabled()
        if self.fail:
            raise LlmUpstreamError(500)
        self.calls += 1
        return "브리핑 텍스트", self.stop


def make_client(table, llm):
    settings = Settings(table_name="t", yt_api_key="x", collect_enabled=False)
    store = TrendStore(table)
    app = create_app(settings, store=store, yt=object(), llm=llm)
    return TestClient(app), store


def test_brief_503_when_llm_disabled(table):
    client, store = make_client(table, FakeLlm(disabled=True))
    store.put_snapshot("all", NOW, [card()])
    res = client.post("/api/brief", json={"scope": "all", "mode": "now"})
    assert res.status_code == 503 and res.json()["enabled"] is False


def test_brief_now_generates_then_caches(table):
    llm = FakeLlm()
    client, store = make_client(table, llm)
    store.put_snapshot("all", NOW, [card()])
    r1 = client.post("/api/brief", json={"scope": "all", "mode": "now"})
    r2 = client.post("/api/brief", json={"scope": "all", "mode": "now"})
    assert r1.json()["cached"] is False and r2.json()["cached"] is True
    assert llm.calls == 1  # 캐시로 토큰 소비 시간당 1회 상한


def test_brief_daily_409_without_baseline(table):
    client, store = make_client(table, FakeLlm())
    store.put_snapshot("all", NOW, [card()])
    res = client.post("/api/brief", json={"scope": "all", "mode": "daily"})
    assert res.status_code == 409 and res.json()["baseline"] is None


def test_brief_daily_uses_24h_snapshot(table):
    client, store = make_client(table, FakeLlm())
    store.put_snapshot("all", NOW - timedelta(hours=24), [card("old")])
    store.put_snapshot("all", NOW, [card("new")])
    res = client.post("/api/brief", json={"scope": "all", "mode": "daily"})
    assert res.status_code == 200 and res.json()["baseline"] is not None


def test_truncated_response_appends_notice_still_200(table):
    client, store = make_client(table, FakeLlm(stop="max_tokens"))
    store.put_snapshot("all", NOW, [card()])
    body = client.post("/api/brief", json={"scope": "all", "mode": "now"}).json()
    assert "잘렸습니다" in body["brief"]


def test_upstream_failure_returns_502_with_code_only(table):
    client, store = make_client(table, FakeLlm(fail=True))
    store.put_snapshot("all", NOW, [card()])
    res = client.post("/api/brief", json={"scope": "all", "mode": "now"})
    assert res.status_code == 502 and res.json()["code"] == 500


def test_trend_report_endpoint(table):
    client, store = make_client(table, FakeLlm())
    store.put_snapshot("all", NOW - timedelta(hours=1), [card("a")])
    store.put_snapshot("all", NOW, [card("b")])
    res = client.post("/api/trends/report", json={"scope": "all"})
    assert res.status_code == 200 and res.json()["report"] == "브리핑 텍스트"
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_api_brief.py -v`
Expected: FAIL — 404 (라우터 미등록)

- [ ] **Step 3: 구현**

`backend/app/api/brief.py`:
```python
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.aggregate import category_series
from app.api.deps import get_llm, get_store
from app.api.trending import VALID_SCOPES
from app.llm import prompts
from app.llm.bedrock import MODEL_ID, LlmDisabled, LlmUpstreamError
from app.store import keys

router = APIRouter(prefix="/api")

MAX_TOKENS = {"brief-now": 1200, "brief-daily": 600, "trend": 1500}
ERR = {"upstream": "분석 생성에 실패했습니다", "disabled": "브리핑 기능이 설정되지 않았습니다",
       "no_baseline": "비교할 어제 데이터가 아직 없습니다", "no_snapshot": "표시할 목록이 아직 없습니다"}


class BriefReq(BaseModel):
    scope: str = "all"
    mode: str = "now"


class ReportReq(BaseModel):
    scope: str = "all"


def _cached_or_generate(store, llm, kind, scope, now, build):
    """캐시 우선 생성. build() -> (system, user) 또는 오류 응답(JSONResponse)."""
    bucket = keys.hour_bucket(now)
    hit = store.get_report(kind, scope, bucket)
    if hit:
        return {"text": hit["text"], "cached": True}
    built = build()
    if isinstance(built, JSONResponse):
        return built
    system, user = built
    try:
        text, stop = llm.converse(system, user, MAX_TOKENS[kind])
    except LlmDisabled:
        return JSONResponse({"error": ERR["disabled"], "enabled": False}, status_code=503)
    except LlmUpstreamError as e:
        return JSONResponse({"error": ERR["upstream"], "code": e.status}, status_code=502)
    if stop == "max_tokens":
        text += prompts.TRUNCATION_NOTICE
    store.put_report(kind, scope, bucket, text, MODEL_ID, now)
    return {"text": text, "cached": False}


@router.post("/brief")
def brief(req: BriefReq, store=Depends(get_store), llm=Depends(get_llm)):
    if req.scope not in VALID_SCOPES or req.mode not in ("now", "daily"):
        return JSONResponse({"error": "잘못된 요청입니다"}, status_code=400)
    now = datetime.now(timezone.utc)
    snap = store.latest_snapshot(req.scope)
    if snap is None:
        return JSONResponse({"error": ERR["no_snapshot"]}, status_code=409)

    baseline = None
    if req.mode == "daily":
        baseline = store.baseline_snapshot(req.scope, now, keys.DAILY_OFFSETS)
        if baseline is None:
            return JSONResponse({"error": ERR["no_baseline"], "baseline": None},
                                status_code=409)

    kind = f"brief-{req.mode}"
    build = (lambda: prompts.build_daily(snap["items"], baseline)) if req.mode == "daily" \
        else (lambda: prompts.build_brief(snap["items"]))
    out = _cached_or_generate(store, llm, kind, req.scope, now, build)
    if isinstance(out, JSONResponse):
        return out
    body = {"brief": out["text"], "cached": out["cached"]}
    if baseline:
        body["baseline"] = baseline["capturedAt"]
    return body


@router.post("/trends/report")
def trend_report(req: ReportReq, store=Depends(get_store), llm=Depends(get_llm)):
    if req.scope not in VALID_SCOPES:
        return JSONResponse({"error": "잘못된 요청입니다"}, status_code=400)
    now = datetime.now(timezone.utc)

    def build():
        snaps = store.snapshots_range(req.scope, now - timedelta(hours=48), now)
        if not snaps:
            return JSONResponse({"error": ERR["no_snapshot"]}, status_code=409)
        series = category_series(snaps)
        movers = sorted(snaps[-1]["items"], key=lambda c: c.get("views", 0),
                        reverse=True)
        return prompts.build_trend_report(series, movers)

    out = _cached_or_generate(store, llm, "trend", req.scope, now, build)
    if isinstance(out, JSONResponse):
        return out
    return {"report": out["text"], "cached": out["cached"]}
```

`backend/app/main.py` 수정 2곳:
1. 라우터 include 줄에 `from app.api import brief as brief_api` + `app.include_router(brief_api.router)` 추가.
2. `_build_real_dependencies`가 `(store, yt, llm)` 3-튜플을 반환하도록 변경:
```python
    from app.llm.bedrock import BedrockClient
    llm = BedrockClient(settings.bedrock_token)
    return TrendStore(table), yt, llm
```
lifespan에서 `if app.state.llm is None: ...` 형태로 store/yt/llm 각각 None일 때만 채운다.

- [ ] **Step 4: 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/ -v`
Expected: PASS (전체)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/api/brief.py backend/app/main.py backend/tests/test_api_brief.py
git commit -m "feat: LLM brief and trend report APIs with hourly cache"
```

---

### Task 10: 프론트엔드 스캐폴딩 + 전체 Top 30 탭

프론트 태스크의 게이트는 스펙대로 `tsc --noEmit` + `vite build` 성공이다(컴포넌트 단위 테스트는 범위 제외). 개발 중 확인은 `npm run dev` + 백엔드 로컬 실행으로 한다.

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/theme.ts`, `frontend/src/types.ts`, `frontend/src/api.ts`, `frontend/src/components/Card.tsx`, `frontend/src/components/CardGrid.tsx`, `frontend/src/components/Badge.tsx`, `frontend/src/tabs/TopAll.tsx`

**Interfaces:**
- Consumes: T7의 HTTP 계약 (`/api/trending`, `/api/categories`)
- Produces: `src/types.ts`의 `Card` 타입(백엔드 카드 13필드와 1:1), `src/api.ts`의 `fetchJson<T>(path)` / `postJson<T>(path, body)` — T11이 재사용. `ApiError extends Error { status: number; body: { error?: string } }`.

- [ ] **Step 1: Vite 프로젝트 생성**

```bash
cd frontend && npm create vite@latest . -- --template react-ts
npm install && npm install recharts
```

`vite.config.ts`에 개발 프록시 추가(로컬에서 백엔드 8000 포트로):
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
```

- [ ] **Step 2: 타입과 API 클라이언트 작성**

`frontend/src/types.ts`:
```ts
export interface Card {
  rank: number; videoId: string; title: string; channel: string;
  views: number; likes: number; category: string; categoryId: string;
  thumbnail: string; publishedAt: string;
  baseline: string | null; prevRank: number | null;
  delta: number | null; viewsPerHour: number | null;
}
export interface Category { id: string; name: string }
export interface HistoryPoint { ts: string; rank: number | null; views: number }
export interface TrendBucket { ts: string; shares: Record<string, number>; entered: number; exited: number }
```

`frontend/src/api.ts`:
```ts
export class ApiError extends Error {
  constructor(public status: number, public body: { error?: string; enabled?: boolean }) {
    super(body.error ?? `HTTP ${status}`)
  }
}

async function handle<T>(res: Response): Promise<T> {
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new ApiError(res.status, body ?? {})
  return body as T
}

export const fetchJson = <T,>(path: string) => fetch(path).then(r => handle<T>(r))
export const postJson = <T,>(path: string, body: unknown) =>
  fetch(path, { method: 'POST', headers: { 'content-type': 'application/json' },
                body: JSON.stringify(body) }).then(r => handle<T>(r))
```

- [ ] **Step 3: 테마·카드·그리드·Top30 탭 구현**

`frontend/src/theme.ts` — `data-theme` 토글 + `prefers-color-scheme` 초기값 + localStorage(`yt-theme`) 저장. `index.html`의 `<head>` 인라인 스크립트로 첫 페인트 전 테마 확정(FOUC 방지):
```html
<script>
  try {
    var t = localStorage.getItem('yt-theme') ||
      (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.dataset.theme = t;
  } catch (e) { document.documentElement.dataset.theme = 'light'; }
</script>
```

`frontend/src/components/Badge.tsx` — 순위 변동 배지. 계약: `baseline===null` → 렌더 안 함, `prevRank===null` → `NEW`, `delta>0` → `↑n`, `delta<0` → `↓n`, `delta===0` → `-`. 색과 함께 문자를 항상 병기(색맹 대응):
```tsx
import type { Card } from '../types'

export function DeltaBadge({ c }: { c: Card }) {
  if (c.baseline === null) return null
  if (c.prevRank === null) return <span className="badge new">NEW</span>
  if (c.delta === null || c.delta === 0) return <span className="badge same">-</span>
  return c.delta > 0
    ? <span className="badge up">{'↑'}{c.delta}</span>
    : <span className="badge down">{'↓'}{-c.delta}</span>
}

export function velocityText(v: number | null): string | null {
  if (v === null) return null
  const abs = Math.abs(v)
  const num = abs >= 10000 ? `${(abs / 10000).toFixed(1)}만` : `${abs}`
  return `${v > 0 ? '+' : v < 0 ? '-' : ''}${num}/시`  // ASCII 부호(글리프 커버리지)
}
```

`frontend/src/components/Card.tsx` — 썸네일(로드 실패 시 대체 배경), 순위, 제목, 채널, 조회수/좋아요 축약, 카테고리 배지, `DeltaBadge`, `velocityText`(`role="img"` + `aria-label` 부여). 카드 전체가 YouTube 새 탭 링크(`rel="noopener noreferrer"`). 외부 문자열은 JSX 텍스트 노드로만 렌더(dangerouslySetInnerHTML 금지).

`frontend/src/tabs/TopAll.tsx` — `fetchJson<Card[]>('/api/trending?scope=all')`, 로딩 스켈레톤 8장, 실패 시 `ApiError.body.error` 한국어 문구 + 재시도 버튼, 상단에 합산 조회수·채널 수·최다 카테고리 3타일.

`frontend/src/App.tsx` — 탭 3개(전체/분야별/추이 분석) 라우팅은 useState로(라우터 라이브러리 불필요 — YAGNI), 헤더에 새로고침·테마 토글.

- [ ] **Step 4: 게이트 통과 확인**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: 타입 오류 0, `dist/` 생성 성공

- [ ] **Step 5: 로컬 연동 확인 (수동)**

터미널 1: `cd backend && TABLE_NAME=dummy COLLECT_ENABLED=false .venv/bin/uvicorn app.main:app --factory` 는 팩토리 시그니처가 다르므로 로컬 실행 헬퍼를 쓴다 — `backend/app/main.py` 말미에 추가:
```python
def dev_app():
    """로컬 개발용: uvicorn app.main:dev_app --factory --port 8000"""
    return create_app(Settings.from_env())
```
터미널 2: `cd frontend && npm run dev` → http://localhost:5173 에서 목록/오류 표시 확인 (DynamoDB 없으면 빈 목록 정상).

- [ ] **Step 6: 커밋**

```bash
git add frontend/
git commit -m "feat: React SPA scaffolding with Top-30 tab and delta badges"
```

---

### Task 11: 분야별 Top 10 탭 + 추이 분석 탭

**Files:**
- Create: `frontend/src/tabs/ByCategory.tsx`, `frontend/src/tabs/Trends.tsx`, `frontend/src/components/BriefPanel.tsx`
- Modify: `frontend/src/App.tsx` (탭 연결)

**Interfaces:**
- Consumes: `fetchJson/postJson/ApiError`(T10), `Card/Category/HistoryPoint/TrendBucket`(T10), T7·T9 HTTP 계약

- [ ] **Step 1: 분야별 탭**

`frontend/src/tabs/ByCategory.tsx` — `fetchJson<Category[]>('/api/categories')`로 탭 칩 8개 생성, 선택 시 `fetchJson<Card[]>('/api/trending?scope=' + id)`. `CardGrid` 재사용. 응답 카드에 `degraded` 표시가 필요하므로 백엔드 `/api/trending`이 스냅샷의 `degraded`를 헤더가 아닌 별도 필드로 줄 수 없다(배열 계약) — **카드가 아닌 스냅샷 속성이므로 이 탭에서는 표시 생략**(YAGNI: 스펙의 "안내 표시"는 카테고리 폴백이 실측으로 확인된 뒤 응답 계약 확장과 함께 재검토. Self-review 노트 참조).

- [ ] **Step 2: 추이 분석 탭**

`frontend/src/tabs/Trends.tsx`:
- 영상 선택: 현재 Top30을 `<select>`로 제공 → `fetchJson<{videoId: string, points: HistoryPoint[]}>('/api/videos/' + id + '/history?hours=168')`
- Recharts `LineChart` 2개: 순위(YAxis `reversed domain={[1,30]}`), 조회수(`scale` 토글 linear/log)
- 카테고리 점유율: `fetchJson<{series: TrendBucket[]}>('/api/trends/categories?hours=48')` → 스택 `AreaChart` + 진입/이탈 `BarChart`
- X축 라벨은 UTC 버킷 문자열을 `new Date(ts + ':00:00Z')`로 파싱해 KST로 표시

`frontend/src/components/BriefPanel.tsx` — 버튼 3개(오늘의 브리핑 / 어제와 비교 / 추이 리포트):
```tsx
const onBrief = async (mode: 'now' | 'daily') => {
  setBusy(true)
  try {
    const r = await postJson<{ brief: string; baseline?: string; cached: boolean }>(
      '/api/brief', { scope: 'all', mode })
    setText(headingFor(mode, r.baseline) + '\n\n' + r.brief)
  } catch (e) {
    if (e instanceof ApiError && e.status === 503) setDisabled(true)      // 키 미설정: 버튼 잠금
    else if (e instanceof ApiError && e.status === 409) setText(e.body.error ?? '아직 데이터가 없습니다')
    else setText(e instanceof ApiError ? (e.body.error ?? '요청 실패') : '요청 실패')
  } finally { setBusy(false) }
}
```
응답 텍스트는 `white-space: pre-wrap` 평문으로만 렌더.

- [ ] **Step 3: 게이트 통과 확인**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: 성공

- [ ] **Step 4: 커밋**

```bash
git add frontend/
git commit -m "feat: category and trends tabs with charts and LLM panel"
```

---

### Task 12: Dockerfile + 로컬 컨테이너 검증

**Files:**
- Create: `backend/Dockerfile`, `backend/.dockerignore`
- Modify: `backend/app/main.py` (SPA 정적 서빙 추가)

**Interfaces:**
- Consumes: T10~11의 `frontend/` 빌드, T6의 `create_app`
- Produces: 단일 이미지 — `docker run -p 8000:8000` 으로 기동, `/` → SPA, `/api/*` → API, `/healthz` → ok. T13 CDK가 이 Dockerfile을 빌드한다. 컨텍스트는 **저장소 루트**(frontend를 복사해야 하므로): `docker build -f backend/Dockerfile .`

- [ ] **Step 1: SPA 정적 서빙 추가**

`backend/app/main.py`의 `create_app` 말미(라우터 include 뒤)에 추가:
```python
    import os
    static_dir = os.environ.get("STATIC_DIR", "/srv/static")
    if os.path.isdir(static_dir):
        from fastapi.staticfiles import StaticFiles
        from starlette.responses import FileResponse

        app.mount("/assets", StaticFiles(directory=f"{static_dir}/assets"), name="assets")

        @app.get("/{path:path}")
        def spa(path: str):
            # /api·/healthz는 위에서 먼저 매칭된다. 나머지는 SPA 폴백.
            full = os.path.join(static_dir, path)
            if path and os.path.isfile(full):
                return FileResponse(full)
            return FileResponse(os.path.join(static_dir, "index.html"))
```

- [ ] **Step 2: Dockerfile 작성**

`backend/Dockerfile`:
```dockerfile
# 스테이지 1: 프론트 빌드
FROM node:22-slim AS fe
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 스테이지 2: 런타임 (ARM64 — CDK가 platform 지정)
FROM python:3.12-slim
WORKDIR /srv
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=fe /fe/dist ./static
ENV STATIC_DIR=/srv/static
EXPOSE 8000
# --factory: create_app 팩토리 사용. dev_app은 Settings.from_env()를 읽는다.
CMD ["uvicorn", "app.main:dev_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

`backend/.dockerignore`: `.venv`, `tests`, `__pycache__` (루트 컨텍스트용으로 저장소 루트에도 `.dockerignore` 생성: `node_modules`, `frontend/dist`, `.git`, `cdk.out`, `.venv`)

- [ ] **Step 3: 로컬 빌드·기동 검증**

```bash
docker build -f backend/Dockerfile -t youtube-trends:local .
docker run --rm -p 8000:8000 -e TABLE_NAME=dummy -e COLLECT_ENABLED=false youtube-trends:local &
sleep 3
curl -s localhost:8000/healthz            # 기대: ok
curl -s localhost:8000/ | head -c 100     # 기대: <!doctype html ...
curl -s localhost:8000/api/categories | head -c 80  # 기대: [{"id":"10","name":"음악"} ...
kill %1
```

주의: `TABLE_NAME=dummy` 환경에서 `/api/trending`은 DynamoDB 접근 오류가 난다 — 이 검증 범위는 정적 서빙·헬스체크·무DB 라우트까지다.

- [ ] **Step 4: 커밋**

```bash
git add backend/Dockerfile backend/.dockerignore .dockerignore backend/app/main.py
git commit -m "feat: multi-stage Docker image serving SPA and API"
```

---

### Task 13: CDK 인프라 (infra/)

**Files:**
- Create: `infra/requirements.txt`, `infra/app.py`, `infra/cdk.json`, `infra/stacks/__init__.py`, `infra/stacks/network.py`, `infra/stacks/service.py`

**Interfaces:**
- Consumes: `backend/Dockerfile`(T12, 루트 컨텍스트 빌드)
- Produces: 스택 `YoutubeTrendsStack` — CfnOutput `SiteUrl`(CloudFront), `AlbDns`, `TableName`, `ServiceName`. 환경변수 계약: 컨테이너에 `TABLE_NAME`(일반), `YT_API_KEY`·`AWS_BEARER_TOKEN_BEDROCK`(Secrets Manager 참조), `COLLECT_ENABLED=true`.

- [ ] **Step 1: CDK 앱 스캐폴딩**

`infra/requirements.txt`:
```
aws-cdk-lib==2.*
constructs>=10.0.0
python-dotenv==1.*
```

`infra/cdk.json`:
```json
{ "app": "python3 app.py" }
```

`infra/app.py`:
```python
"""CDK 엔트리. 저장소 루트의 .env를 읽어 VPC 모드 등 비밀 아닌 설정을 얻는다.
시크릿 값은 여기서 다루지 않는다 — scripts/deploy.sh가 Secrets Manager에 넣고
스택은 ARN 참조만 한다."""
import os

import aws_cdk as cdk
from dotenv import load_dotenv

from stacks.service import YoutubeTrendsStack

load_dotenv(dotenv_path="../.env", override=True)  # 파일이 셸을 이긴다(선행 프로젝트 규칙 계승)

app = cdk.App()
YoutubeTrendsStack(
    app, "YoutubeTrendsStack",
    vpc_mode=os.environ.get("VPC_MODE", "existing"),
    vpc_name=os.environ.get("VPC_NAME", "cc-on-bedrock-vpc"),
    secret_name=os.environ.get("APP_SECRET_NAME", "youtube-trends/app"),
    env=cdk.Environment(account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
                        region="ap-northeast-2"),
)
app.synth()
```

- [ ] **Step 2: 네트워크 분기 구현**

`infra/stacks/network.py`:
```python
from aws_cdk import aws_ec2 as ec2


def resolve_vpc(scope, vpc_mode: str, vpc_name: str) -> ec2.IVpc:
    """existing: 이름 태그로 조회(계정의 cc-on-bedrock-vpc — public×2/private×2,
    기존 NAT 재사용). new: 이 레포를 쓰는 다른 사용자용 — 2AZ + NAT 1 + DDB 엔드포인트."""
    if vpc_mode == "existing":
        return ec2.Vpc.from_lookup(scope, "Vpc", tags={"Name": vpc_name})
    vpc = ec2.Vpc(
        scope, "Vpc", max_azs=2, nat_gateways=1,
        subnet_configuration=[
            ec2.SubnetConfiguration(name="public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24),
            ec2.SubnetConfiguration(name="private", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, cidr_mask=20),
        ])
    vpc.add_gateway_endpoint("DdbEndpoint", service=ec2.GatewayVpcEndpointAwsService.DYNAMODB)
    return vpc
```

- [ ] **Step 3: 서비스 스택 구현**

`infra/stacks/service.py`:
```python
import secrets as pysecrets

from aws_cdk import (
    CfnOutput, Duration, RemovalPolicy, Stack,
    aws_cloudfront as cf, aws_cloudfront_origins as origins,
    aws_dynamodb as ddb, aws_ec2 as ec2, aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2, aws_logs as logs,
    aws_secretsmanager as sm,
)
from constructs import Construct

from stacks.network import resolve_vpc


class YoutubeTrendsStack(Stack):
    def __init__(self, scope: Construct, cid: str, *, vpc_mode: str,
                 vpc_name: str, secret_name: str, **kw):
        super().__init__(scope, cid, **kw)
        vpc = resolve_vpc(self, vpc_mode, vpc_name)

        table = ddb.Table(
            self, "TrendTable",
            partition_key=ddb.Attribute(name="pk", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="sk", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="expireAt",
            removal_policy=RemovalPolicy.DESTROY,  # 캡스톤 규모 — 정리 편의 우선
        )

        # deploy.sh가 미리 만들어 둔 시크릿을 이름으로 참조한다(값은 템플릿에 없음)
        app_secret = sm.Secret.from_secret_name_v2(self, "AppSecret", secret_name)

        cluster = ecs.Cluster(self, "Cluster", vpc=vpc)
        task = ecs.FargateTaskDefinition(
            self, "Task", cpu=512, memory_limit_mib=1024,
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.ARM64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX))
        container = task.add_container(
            "app",
            image=ecs.ContainerImage.from_asset(
                directory="..", file="backend/Dockerfile",
                platform=None),  # 빌드 호스트가 aarch64 — 네이티브 빌드
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="app",
                log_retention=logs.RetentionDays.TWO_WEEKS),
            environment={"TABLE_NAME": table.table_name, "COLLECT_ENABLED": "true"},
            secrets={
                "YT_API_KEY": ecs.Secret.from_secrets_manager(app_secret, "YT_API_KEY"),
                "AWS_BEARER_TOKEN_BEDROCK": ecs.Secret.from_secrets_manager(
                    app_secret, "AWS_BEARER_TOKEN_BEDROCK"),
            },
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL",
                         "python3 -c \"import urllib.request;urllib.request.urlopen('http://localhost:8000/healthz')\""],
                interval=Duration.seconds(30)))
        container.add_port_mappings(ecs.PortMapping(container_port=8000))
        table.grant_read_write_data(task.task_role)
        # 의도: Bedrock IAM 정책은 부여하지 않는다(Bearer 인증 — Global Constraints).

        service = ecs.FargateService(
            self, "Service", cluster=cluster, task_definition=task,
            desired_count=1,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            min_healthy_percent=100, max_healthy_percent=200)

        # ALB: prefix list SG — CloudFront origin-facing 대역만 인바운드 허용
        alb_sg = ec2.SecurityGroup(self, "AlbSg", vpc=vpc, allow_all_outbound=True)
        cf_prefix = ec2.Peer.prefix_list("pl-22a6434b")  # com.amazonaws.global.cloudfront.origin-facing
        alb_sg.add_ingress_rule(cf_prefix, ec2.Port.tcp(80),
                                "CloudFront origin-facing only")
        alb = elbv2.ApplicationLoadBalancer(
            self, "Alb", vpc=vpc, internet_facing=True, security_group=alb_sg,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC))

        # 비밀 헤더: prefix list는 타 고객 CloudFront도 포함하므로 2중 방어
        origin_verify = pysecrets.token_urlsafe(24)
        listener = alb.add_listener("Http", port=80, open=False,
                                    default_action=elbv2.ListenerAction.fixed_response(
                                        403, content_type="text/plain", message_body="forbidden"))
        listener.add_targets(
            "App", port=8000, protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[service],
            conditions=[elbv2.ListenerCondition.http_header("X-Origin-Verify", [origin_verify])],
            priority=1,
            health_check=elbv2.HealthCheck(path="/healthz", healthy_http_codes="200"),
            deregistration_delay=Duration.seconds(30))

        dist = cf.Distribution(
            self, "Dist",
            default_behavior=cf.BehaviorOptions(
                origin=origins.HttpOrigin(
                    alb.load_balancer_dns_name,
                    protocol_policy=cf.OriginProtocolPolicy.HTTP_ONLY,
                    custom_headers={"X-Origin-Verify": origin_verify}),
                viewer_protocol_policy=cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cf.CachePolicy.CACHING_OPTIMIZED),
            additional_behaviors={
                "/api/*": cf.BehaviorOptions(
                    origin=origins.HttpOrigin(
                        alb.load_balancer_dns_name,
                        protocol_policy=cf.OriginProtocolPolicy.HTTP_ONLY,
                        custom_headers={"X-Origin-Verify": origin_verify}),
                    viewer_protocol_policy=cf.ViewerProtocolPolicy.HTTPS_ONLY,
                    allowed_methods=cf.AllowedMethods.ALLOW_ALL,
                    cache_policy=cf.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cf.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER)})

        CfnOutput(self, "SiteUrl", value=f"https://{dist.distribution_domain_name}")
        CfnOutput(self, "AlbDns", value=alb.load_balancer_dns_name)
        CfnOutput(self, "TableName", value=table.table_name)
        CfnOutput(self, "ServiceName", value=service.service_name)
```

주의(구현 시 확인): `pl-22a6434b`는 CloudFront origin-facing 관리형 prefix list의 리전별 ID다 — 배포 전 `aws ec2 describe-managed-prefix-lists --region ap-northeast-2 --filters Name=prefix-list-name,Values=com.amazonaws.global.cloudfront.origin-facing`으로 실제 ID를 확인해 교체한다. 비밀 헤더 값이 synth마다 바뀌면 CloudFront·ALB가 동시 갱신되므로 무해하나, 안정성을 원하면 `.env`의 `ORIGIN_VERIFY_TOKEN`으로 고정할 수 있게 `os.environ.get("ORIGIN_VERIFY_TOKEN") or pysecrets.token_urlsafe(24)`로 구현한다.

- [ ] **Step 4: synth 게이트**

```bash
cd infra && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -c "import app"  # import 오류 즉시 검출
VPC_MODE=new npx cdk synth --quiet   # new 모드는 lookup 없이 synth 가능
```
Expected: 템플릿 생성 성공. `existing` 모드 synth는 AWS 자격 증명이 필요(from_lookup)하므로 T15 배포 단계에서 확인한다.

- [ ] **Step 5: 커밋**

```bash
git add infra/
git commit -m "feat: CDK stack with prefix-list SG, origin-verify header, and VPC modes"
```

---

### Task 14: 배포 스크립트 + .env.example + README

**Files:**
- Create: `scripts/deploy.sh`, `scripts/smoke.sh`, `.env.example`, `README.md`

**Interfaces:**
- Consumes: T13 스택 출력(`SiteUrl`), 시크릿 이름 `youtube-trends/app`
- Produces: `./scripts/deploy.sh`(전체 배포 원커맨드), `./scripts/smoke.sh <SiteUrl>`(T15가 사용)

- [ ] **Step 1: .env.example 작성**

```bash
# YouTube Data API v3 키 (필수) — https://console.cloud.google.com
YT_API_KEY=

# Bedrock API 키 (선택 — 없으면 LLM 기능만 503 비활성)
# 주의: 조직 SCP가 서울 리전 InvokeModel을 거부하는 계정에서는
# 조직 밖에서 발급한 키가 필요하다 (Bearer 인증은 SCP 범위 밖).
AWS_BEARER_TOKEN_BEDROCK=

# VPC 모드: existing(기본, VPC_NAME 조회) | new(신규 생성 — 이 레포를 처음 쓰는 계정용)
VPC_MODE=existing
VPC_NAME=cc-on-bedrock-vpc

# Secrets Manager 시크릿 이름 (deploy.sh가 생성/갱신)
APP_SECRET_NAME=youtube-trends/app
```

- [ ] **Step 2: deploy.sh 작성**

`scripts/deploy.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# 1) .env 존재·비추적 검사 (값은 출력하지 않는다)
[ -f .env ] || { echo "ERROR: .env가 없습니다. .env.example을 복사해 작성하세요"; exit 1; }
if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  echo "ERROR: .env가 git에 추적되고 있습니다. git rm --cached .env 후 키를 회전하세요"; exit 1
fi
set -a; source .env; set +a
[ -n "${YT_API_KEY:-}" ] || { echo "ERROR: YT_API_KEY가 비어 있습니다"; exit 1; }

# 2) 시크릿 push (create 실패 시 update — 값 비출력)
SECRET_NAME="${APP_SECRET_NAME:-youtube-trends/app}"
PAYLOAD=$(python3 - <<'EOF'
import json, os
print(json.dumps({"YT_API_KEY": os.environ.get("YT_API_KEY",""),
                  "AWS_BEARER_TOKEN_BEDROCK": os.environ.get("AWS_BEARER_TOKEN_BEDROCK","")}))
EOF
)
aws secretsmanager create-secret --region ap-northeast-2 --name "$SECRET_NAME" \
  --secret-string "$PAYLOAD" >/dev/null 2>&1 || \
aws secretsmanager put-secret-value --region ap-northeast-2 --secret-id "$SECRET_NAME" \
  --secret-string "$PAYLOAD" >/dev/null
echo "OK: 시크릿 push 완료 ($SECRET_NAME)"

# 3) 검증 게이트
(cd backend && .venv/bin/pytest -q)
(cd frontend && npx tsc --noEmit && npm run build >/dev/null)

# 4) 배포
(cd infra && npx cdk deploy YoutubeTrendsStack --require-approval never)

# 5) 스모크
SITE=$(aws cloudformation describe-stacks --region ap-northeast-2 \
  --stack-name YoutubeTrendsStack \
  --query "Stacks[0].Outputs[?OutputKey=='SiteUrl'].OutputValue" --output text)
./scripts/smoke.sh "$SITE"
```

- [ ] **Step 3: smoke.sh 작성**

`scripts/smoke.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
SITE="${1:?usage: smoke.sh <site-url>}"
fail=0
check() { # check <이름> <기대상태코드> <경로> [메서드] [바디]
  local name="$1" want="$2" path="$3" method="${4:-GET}" body="${5:-}"
  local got
  got=$(curl -s -o /tmp/smoke-body -w "%{http_code}" -X "$method" \
    ${body:+-H content-type:application/json -d "$body"} "$SITE$path")
  if [ "$got" = "$want" ]; then echo "PASS $name ($got)"; else
    echo "FAIL $name: want $want got $got"; fail=1; fi
}
check "healthz"        200 "/healthz"
check "SPA index"      200 "/"
check "trending"       200 "/api/trending"
check "categories"     200 "/api/categories"
check "bad scope"      400 "/api/trending?scope=999"
check "404 대조군"     404 "/api/nonexistent"   # 게이트웨이가 아닌 앱 계층 판정 확인
check "brief (키 유무에 따라 200/503/409)" 200 "/api/brief" POST '{"scope":"all","mode":"now"}' || true
exit $fail
```
주의: brief 검사는 키 설정 여부·스냅샷 유무에 따라 200/503/409가 모두 정상이다 — 마지막 검사만은 상태 코드를 기록하되 실패로 치지 않는다(구현 시 `check` 호출 대신 코드 출력만 하도록 조정).

- [ ] **Step 4: README 작성**

`README.md` 필수 절: 개요(기능 4종), 아키텍처 다이어그램(Mermaid — CloudFront→prefix SG→ALB→Fargate→DynamoDB/YouTube/Bedrock), 사전 요건(Node 22, Python 3.12, Docker, CDK 부트스트랩된 계정), 설치·배포(`cp .env.example .env` → 키 기입 → `./scripts/deploy.sh`), VPC 모드 설명(existing/new), **두 키에 대한 주의**(SCP·Bearer 전제, 키 회전 절차), API 문서(6개 엔드포인트 + 상태 코드 계약), 로컬 개발(백엔드 uvicorn + 프론트 vite dev), 비용 개요(Fargate 상시 1태스크 + NAT는 기존 재사용).

- [ ] **Step 5: 실행권한·커밋**

```bash
chmod +x scripts/deploy.sh scripts/smoke.sh
git add scripts/ .env.example README.md
git commit -m "feat: deploy pipeline with secret push and smoke tests"
```

---

### Task 15: 실배포 + 라이브 검증

**Files:**
- Modify: 없음 (배포·검증·기록만. 발견된 결함은 해당 태스크 파일로 돌아가 수정)

**Interfaces:**
- Consumes: 전체. 사용자로부터 `.env` 값(YT_API_KEY 필수, Bedrock 키 선택)이 준비되어 있어야 한다.

- [ ] **Step 1: prefix list ID 실측 확인**

```bash
aws ec2 describe-managed-prefix-lists --region ap-northeast-2 \
  --filters Name=prefix-list-name,Values=com.amazonaws.global.cloudfront.origin-facing \
  --query "PrefixLists[0].PrefixListId" --output text
```
출력된 ID가 `infra/stacks/service.py`의 값과 다르면 교체 후 커밋.

- [ ] **Step 2: 배포 실행**

```bash
./scripts/deploy.sh
```
Expected: 시크릿 push → pytest 전체 통과 → tsc/vite 성공 → `cdk deploy` 성공(최초 약 10~15분, CloudFront 배포 포함) → 스모크 PASS. 실패 시 CloudFormation 이벤트를 확인하고, 원인 태스크로 돌아가 수정 후 재배포.

- [ ] **Step 3: 첫 스냅샷 수집 확인**

배포 직후에는 스냅샷이 없어 `/api/trending`이 `[]`를 반환한다(정상). 다음 정각 이후:
```bash
aws logs tail /aws/ecs/... --region ap-northeast-2 --since 1h | grep "collect done"
curl -s "$SITE/api/trending" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d), d[0]['title'][:30] if d else '')"
```
Expected: `collect done ... written=9` 로그, 목록 30건. 강제 즉시 수집이 필요하면 ECS Exec 대신 스케줄 대기를 원칙으로 한다(수집 로직은 이미 pytest로 검증됨).

- [ ] **Step 4: 파생 필드·LLM 라이브 확인**

수집 2회(2시간) 후: `/api/trending` 응답의 `delta/viewsPerHour`가 null이 아닌 항목 존재 확인. Bedrock 키가 설정돼 있으면:
```bash
curl -s -X POST "$SITE/api/brief" -H content-type:application/json \
  -d '{"scope":"all","mode":"now"}' | python3 -m json.tool | head -5
```
Expected: `brief` 텍스트 + `cached:false`, 재호출 시 `cached:true`. CloudWatch 로그에서 `stopReason` 확인 — `max_tokens`가 반복되면 해당 kind의 MAX_TOKENS 상향을 검토(T9 주석 참조).

- [ ] **Step 5: 최종 커밋·기록**

배포 출력(SiteUrl 등)과 실측치(스냅샷 크기, 브리핑 소요 시간)를 README 배포 절에 반영하고 커밋:
```bash
git add README.md && git commit -m "docs: record live deployment outputs and measurements"
```

---

## Self-Review

**1. Spec coverage:**
- 전체 Top30/분야별 Top10 → T5(수집)·T7(조회)·T10~11(UI) ✓
- 추이 4종: 시계열 차트 T11, 카테고리 점유율/진입이탈 T7(aggregate)+T11, LLM 리포트 T8~9+T11, 배지/속도 T4+T10 ✓
- CloudFront→prefix SG→ALB→Fargate, 비밀 헤더, VPC 2모드 → T13 ✓
- .env → Secrets Manager, 추적 검사 → T14 ✓ / Bearer·global ID·서울 엔드포인트 → T8(Global Constraints) ✓
- 헬스체크·SIGTERM·서킷브레이커 → T6(uvicorn graceful + scheduler shutdown)·T13(deregistration 30s) ✓
- 갭 1: 스펙 9절의 CloudWatch 알람 2개(선택 배포 플래그)는 태스크에 없다 — 스펙이 "선택"으로 규정했고 초기 배포 범위에서 제외한다. 후속 작업으로 남긴다.
- 갭 2(의도적 축소): 분야별 탭의 `degraded` 안내 표시는 T11 Step 1에 기록했듯 `/api/trending`의 배열 응답 계약과 충돌해 초기 범위에서 제외 — 카테고리 폴백이 실측되면 응답 계약 확장(`{items, degraded}` 래핑 또는 헤더)과 함께 재설계한다.

**2. Placeholder scan:** "TBD/TODO/적절히/나중에" 패턴 없음. 모든 코드 스텝에 실제 코드 포함 ✓. T13의 prefix list ID는 자리표시자가 아니라 실측 교체 절차(T15 Step 1)가 계획에 있다.

**3. Type consistency:**
- `create_app(settings, store, yt, llm)` — T1 정의, T6 확장, T7/T9/T12 사용 일치 ✓
- `TrendStore` 메서드명 — T3 정의 ↔ T5(`put_snapshot/put_video_points`)·T7(`latest_snapshot/baseline_snapshot/video_history/snapshots_range`)·T9(`get_report/put_report`) 일치 ✓
- `keys.RECENT_OFFSETS/DAILY_OFFSETS/MIN_AGE_HOURS` — T2 정의 ↔ T7/T9 사용 일치 ✓
- 카드 필드명(`videoId/viewsPerHour/prevRank/baseline/delta`) — 백엔드(T4~T9)와 프론트 `types.ts`(T10) 일치 ✓
- 수정 1건 반영: T9의 `_build_real_dependencies` 3-튜플 변경은 T6 코드의 2-튜플과 어긋난다 — T9 Step 3에 명시적 수정 지시로 기재했다(T6를 소급 수정하지 않고 T9에서 확장).

