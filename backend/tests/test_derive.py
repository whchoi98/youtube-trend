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


def test_bool_prev_values_rejected():
    base = baseline_of(2, [{"rank": True, "videoId": "a", "views": False}])
    out = with_derived([card("a", 1, 100)], base, NOW)
    assert out[0]["prevRank"] is None
    assert out[0]["viewsPerHour"] is None


def test_non_positive_elapsed_hours_yields_null():
    base = {"capturedAt": NOW.isoformat(), "items": [card("a", 1, 50)]}
    out = with_derived([card("a", 1, 100)], base, NOW)
    assert out[0]["viewsPerHour"] is None  # hours == 0
