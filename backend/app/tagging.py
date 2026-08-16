"""수집 후 AI 태깅 파이프라인. 태그는 부가 정보다 — 어떤 실패도 홈 응답을
막지 않도록 조용히 스킵하고, 다음 수집 사이클에서 재시도된다.

저장 단위는 전체(ALL) 스냅샷의 시간 버킷이다. 같은 버킷에 태그가 이미 있으면
no-op(멱등)이라 수집 잡·기동 잡이 겹쳐 호출해도 LLM은 한 번만 탄다.
"""
import json
import logging

from app.llm import prompts
from app.llm.bedrock import LlmDisabled, LlmUpstreamError

log = logging.getLogger(__name__)

# 30개 영상 × 엔트리당 ~90토큰(태그 3종 + 한 줄 분석)에 여유를 둔 상한.
# 잘리면 JSON 파싱이 실패해 저장하지 않고 다음 사이클에 재시도한다.
TAGS_MAX_TOKENS = 4000
# comment(한 줄 AI 분석) 길이 상한 — LLM 자유 텍스트라 반드시 자른다
COMMENT_MAX = 80


def _norm_tags(raw, valid_ids):
    """LLM 출력에서 유효 항목만 걸러 정규화한다. 어휘 밖 값·모르는 videoId는 버린다."""
    out = {}
    if not isinstance(raw, dict):
        return out
    for vid, t in raw.items():
        if vid not in valid_ids or not isinstance(t, dict):
            continue
        raw_topics = t.get("topics")
        # 순서 보존 dedupe 후 상한 — 중복 topic이 두 번째 슬롯을 밀어내거나
        # 홈 주제 행에 같은 카드를 두 번 넣지 않도록
        topics = list(dict.fromkeys(
            x for x in raw_topics if x in prompts.TOPIC_VOCAB))[:2] \
            if isinstance(raw_topics, list) else []
        age = t.get("age") if t.get("age") in prompts.AGE_VOCAB else None
        vibe = t.get("vibe") if t.get("vibe") in prompts.VIBE_VOCAB else None
        # comment는 고정 어휘가 아닌 자유 텍스트 — 개행 제거 + 길이 상한 세탁
        raw_comment = t.get("comment")
        comment = prompts.clean_text(raw_comment, COMMENT_MAX) or None \
            if isinstance(raw_comment, str) else None
        if topics or age or vibe or comment:
            out[vid] = {"topics": topics, "age": age, "vibe": vibe,
                        "comment": comment}
    return out


def parse_tags(text, valid_ids):
    """모델 출력에서 첫 '{'~마지막 '}' 구간만 JSON으로 시도 — 코드 펜스·부연 내성."""
    if not isinstance(text, str):
        return {}
    try:
        raw = json.loads(text[text.index("{"):text.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
        return {}
    return _norm_tags(raw, valid_ids)


def ensure_tags(store, llm, now):
    """최신 ALL 스냅샷 버킷에 태그가 없으면 생성한다.

    반환: 태그 dict(기존 것 포함) 또는 None(스냅샷 없음·LLM 미설정·실패).
    """
    snap = store.latest_snapshot("all")
    if snap is None:
        return None
    existing = store.get_tags(snap["bucket"])
    if existing is not None:
        return existing
    system, user = prompts.build_tags(snap["items"])
    try:
        text, _stop = llm.converse(system, user, TAGS_MAX_TOKENS)
    except LlmDisabled:
        return None
    except LlmUpstreamError as e:
        log.warning("tagging: upstream failed status=%s", e.status)
        return None
    tags = parse_tags(text, {c.get("videoId") for c in snap["items"]})
    if not tags:
        log.warning("tagging: no valid tags parsed bucket=%s", snap["bucket"])
        return None
    if not store.put_tags(snap["bucket"], tags, now):
        # 동시 실행(롤링 배포 중 태스크 2개 등)에서 다른 쪽이 먼저 썼다 —
        # 선착 결과를 반환해 모든 소비자가 같은 태그를 본다
        winner = store.get_tags(snap["bucket"])
        return winner if winner is not None else tags
    log.info("tagging: stored %s tags bucket=%s", len(tags), snap["bucket"])
    return tags
