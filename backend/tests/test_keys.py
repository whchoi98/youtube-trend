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
    assert keys.chart_vid_pk("songs", "abc123") == "CVID#songs#abc123"
    assert keys.report_pk("brief-now", "all") == "REPORT#brief-now#all"
    assert keys.snap_pk("rgn-US") == "SNAP#RGN#US"
    assert keys.snap_pk("spot-aws") == "SNAP#SPOT#aws"
    assert keys.snap_pk("chart-ytmusic") == "SNAP#CHART#ytmusic"
    assert keys.tags_pk() == "TAGS#ALL"
    assert keys.ts_sk("2026-08-04T09") == "TS#2026-08-04T09"


def test_bucket_from_sk_roundtrip():
    assert keys.bucket_from_sk(keys.ts_sk("2026-08-04T09")) == "2026-08-04T09"


def test_ttl_epoch_is_days_after_now():
    got = keys.ttl_epoch(UTC_T, days=30)
    assert got == int(UTC_T.timestamp()) + 30 * 86400


def test_shared_constants():
    assert keys.RECENT_OFFSETS == [1, 2, 3, 4]
    assert keys.DAILY_OFFSETS == [24, 25, 26]
    assert keys.MIN_AGE_HOURS == 0.75
