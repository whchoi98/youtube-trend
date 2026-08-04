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


def test_bool_views_render_as_zero():
    _, user = prompts.build_brief([card(views=True)])
    assert "조회 0" in user
