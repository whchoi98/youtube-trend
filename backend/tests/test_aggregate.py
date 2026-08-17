from app.aggregate import category_series


def snap(bucket, ids_cats):
    return {"bucket": bucket, "capturedAt": bucket + ":00:00+00:00",
            "items": [{"videoId": v, "categoryId": c, "rank": i + 1, "views": 1}
                      for i, (v, c) in enumerate(ids_cats)]}


def test_shares_counted_per_bucket():
    out = category_series([snap("2026-08-04T08", [("a", "10"), ("b", "10"), ("c", "20")])])
    assert out[0]["shares"] == {"10": 2, "20": 1}
    # 첫 스냅샷은 비교 기준이 없다 — 실측 0이 아니라 null(계산 불가)
    assert out[0]["entered"] is None and out[0]["exited"] is None


def test_entered_exited_between_buckets():
    s1 = snap("2026-08-04T08", [("a", "10"), ("b", "20")])
    s2 = snap("2026-08-04T09", [("a", "10"), ("c", "20")])  # b 이탈, c 진입
    out = category_series([s1, s2])
    assert out[1]["entered"] == 1 and out[1]["exited"] == 1
