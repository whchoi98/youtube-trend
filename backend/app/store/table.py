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
