# Backend Module (FastAPI)

## Role

YouTube 급상승 데이터의 수집·저장·파생·집계·홈 조합·AI 태깅·LLM 브리핑을 담당하는 FastAPI 앱이다.

- `app/api/` — 라우터 계층 (trending, trends, videos, brief, home) + 의존성 (deps.py)
- `app/collector/` — YouTube Data API 수집 (youtube.py) 및 수집 실행 루프 (run.py)
- `app/llm/` — Bedrock 호출 (bedrock.py, Bearer 인증 전용) 및 프롬프트 (prompts.py — 브리핑/리포트/태깅)
- `app/store/` — DynamoDB 접근 (table.py) 및 키 규칙 단일 정의 (keys.py)
- `app/derive.py` — 스냅샷 간 파생 지표 계산
- `app/aggregate.py` — 카테고리 점유율 등 집계
- `app/home.py` — 홈 행 구성·인사이트 칩·퀴즈 추천 (순수 함수, I/O 없음)
- `app/tagging.py` — 수집 후 AI 태깅 파이프라인. 최신 ALL 스냅샷 버킷 단위로 멱등하며, LLM 미설정·실패 시 조용히 스킵한다(태그는 부가 정보)

## Key Files

- `app/main.py` — `create_app(settings, store=None, yt=None, llm=None)`: DI 주입 시임. 실제 구현은 기본값으로 생성되고, 테스트는 fake/moto 구현을 인자로 주입한다.
- `app/store/keys.py` — pk/sk 포맷의 유일한 정의처.
- `app/config.py` — Settings (.env 기반).
- `conftest.py`, `tests/conftest.py` — pytest 픽스처.

## Rules

- 테스트 규율: pytest + moto(DynamoDB 모킹)다. 실행은 `cd backend && .venv/bin/pytest tests/ -q`, 131개 전부 green을 유지한다. 외부 네트워크(YouTube/Bedrock 실호출)에 의존하는 테스트를 추가하지 않는다.
- 의존성 주입은 `create_app` 시임을 통해서만 한다. 모듈 전역을 몽키패치하는 테스트를 새로 만들지 않는다.
- 스냅샷 키 규칙은 `app/store/keys.py` 단일 정의다. 라우터·수집기·테스트 어디서도 pk/sk 문자열을 직접 조립하지 않는다. 키 포맷 변경 시 `tests/test_keys.py`부터 갱신한다.
- 오류 계약: 모든 오류 응답은 `{"error": "<한국어 메시지>"}` + 4xx/5xx다. FastAPI 기본 detail 포맷을 노출하지 않는다.
- 파생 필드는 null(계산 불가) vs 0(실측 0)을 구분한다.
- Bedrock은 Bearer 토큰 인증 전용이다. `AWS_BEARER_TOKEN_BEDROCK` 부재 시 LLM 엔드포인트만 503으로 응답하고 나머지 기능은 정상 동작해야 한다.
