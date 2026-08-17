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
TAGS_TTL_DAYS = 2


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
            "bucket": keys.bucket_from_sk(item["sk"]),
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

    def baseline_snapshot(self, scope, now, offsets, min_age_hours=0.0,
                          exclude_bucket=None):
        """오프셋(시간) 순서대로 폴백 조회. 절대 예외를 던지지 않는다 —
        기준 스냅샷 부재는 정상 상태(배지 없는 응답)이지 오류가 아니다.

        exclude_bucket: 최신 스냅샷 자신의 버킷. 수집이 한 사이클 빠지면
        오프셋 버킷이 최신 스냅샷과 겹쳐 자기 자신과 비교하게 되는데, 그러면
        "비교 불가(null)"가 실측 0으로 위장된다 — 반드시 건너뛴다."""
        try:
            for off in offsets:
                bucket = keys.hour_bucket(now - timedelta(hours=off))
                if exclude_bucket is not None and bucket == exclude_bucket:
                    continue
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

    def snapshots_sampled(self, scope, since, until, step_hours):
        """step_hours 간격 버킷을 GetItem으로 샘플 조회 (시간 오름차순).

        스냅샷은 버킷당 ~11KB라 96h를 넘는 범위는 Query 1MB 한도에 걸린다.
        범위 전체를 페이지네이션으로 다 읽는 대신, 앵커부터 과거 방향 step
        간격의 버킷만 점조회한다 — 읽기량이 hours와 무관하게 상수(≤96버킷
        + 앵커 탐색 ≤step-1회)로 유지된다. 수집 공백으로 비는 버킷은
        건너뛴다.

        앵커: until의 floor 버킷이 비어 있으면(정각~수집 완료 사이 요청,
        해당 시각 수집 실패·misfire) 1시간씩 최대 step-1회 후퇴해 가장
        새로운 실존 버킷을 앵커로 쓴다 — 그대로 step 점프하면 더 새로운
        실존 버킷을 건너뛰어 최신 포인트가 최대 step시간 후퇴해 보인다."""
        def _get(dt):
            res = self.table.get_item(
                Key={"pk": keys.snap_pk(scope),
                     "sk": keys.ts_sk(keys.hour_bucket(dt))})
            return res.get("Item")

        anchor = until.astimezone(timezone.utc).replace(
            minute=0, second=0, microsecond=0)
        dt, item = anchor, _get(anchor)
        for back in range(1, step_hours):
            probe = anchor - timedelta(hours=back)
            if item is not None or probe < since:
                break
            dt, item = probe, _get(probe)

        out = []
        while dt >= since:
            if item:
                out.append(self._to_snapshot(item))
            dt -= timedelta(hours=step_hours)
            item = _get(dt) if dt >= since else None
        out.reverse()
        return out

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

    def put_chart_points(self, chart, bucket, now, points):
        """차트 곡별 시계열 포인트 — 한 달(720h) 추이 조회를 스냅샷 범위
        조회(버킷당 ~14KB) 대신 곡 단위 소형 아이템 Query로 가능하게 한다."""
        with self.table.batch_writer() as bw:
            for p in points:
                bw.put_item(Item={
                    "pk": keys.chart_vid_pk(chart, p["videoId"]),
                    "sk": keys.ts_sk(bucket),
                    "rank": p.get("rank"), "views": p["views"],
                    "expireAt": keys.ttl_epoch(now, SNAPSHOT_TTL_DAYS),
                })

    def chart_video_history(self, chart, video_id, since, until):
        res = self.table.query(
            KeyConditionExpression=Key("pk").eq(keys.chart_vid_pk(chart, video_id))
            & Key("sk").between(keys.ts_sk(keys.hour_bucket(since)),
                                keys.ts_sk(keys.hour_bucket(until))),
        )
        return [{"ts": keys.bucket_from_sk(i["sk"]),
                 "rank": _int(i.get("rank"), default=None) if i.get("rank") is not None else None,
                 "views": _int(i.get("views"))} for i in res["Items"]]

    def video_history(self, video_id, since, until):
        res = self.table.query(
            KeyConditionExpression=Key("pk").eq(keys.vid_pk(video_id))
            & Key("sk").between(keys.ts_sk(keys.hour_bucket(since)),
                                keys.ts_sk(keys.hour_bucket(until))),
        )
        return [{"ts": keys.bucket_from_sk(i["sk"]),
                 "rank": _int(i.get("rank"), default=None) if i.get("rank") is not None else None,
                 "views": _int(i.get("views"))} for i in res["Items"]]

    # -- AI 태깅 ----------------------------------------------------------
    def get_tags(self, bucket):
        res = self.table.get_item(
            Key={"pk": keys.tags_pk(), "sk": keys.ts_sk(bucket)})
        item = res.get("Item")
        return json.loads(item["tags"]) if item else None

    def put_tags(self, bucket, tags, now) -> bool:
        """같은 버킷 선착 1회만 저장(멱등). LLM 출력은 비결정적이라 나중 쓰기가
        먼저 것을 덮으면 폴링 중인 클라이언트가 보는 태그가 뒤바뀐다."""
        try:
            self.table.put_item(
                Item={
                    "pk": keys.tags_pk(), "sk": keys.ts_sk(bucket),
                    "tags": json.dumps(tags, ensure_ascii=False),
                    "expireAt": keys.ttl_epoch(now, TAGS_TTL_DAYS),
                },
                ConditionExpression="attribute_not_exists(pk)",
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False  # 다른 태스크가 먼저 썼다 — 정상 흐름
            raise

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
