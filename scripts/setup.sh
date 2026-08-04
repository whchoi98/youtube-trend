#!/usr/bin/env bash
# 신규 개발자 셋업 스크립트 — 저장소 클론 직후 1회 실행한다.
# 사용법: bash scripts/setup.sh
# 시크릿 값은 어떤 경우에도 출력하지 않는다 (존재 여부만 알린다).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== YouTube Trends 개발 환경 셋업 ==="

# 1) 사전 요건 확인
command -v git >/dev/null 2>&1 || { echo "ERROR: git이 필요하다"; exit 1; }

PYTHON_BIN=""
if command -v python3.12 >/dev/null 2>&1; then
    PYTHON_BIN="python3.12"
elif command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)'; then
    PYTHON_BIN="python3"
fi
[ -n "$PYTHON_BIN" ] || { echo "ERROR: Python 3.12가 필요하다 (backend 런타임 기준)"; exit 1; }
echo "OK: $($PYTHON_BIN --version)"

command -v node >/dev/null 2>&1 || { echo "ERROR: Node.js가 필요하다 (frontend: React 18 + Vite + TS)"; exit 1; }
echo "OK: node $(node --version)"

if command -v docker >/dev/null 2>&1; then
    echo "OK: $(docker --version)"
else
    echo "주의: docker가 없다 — 로컬 개발/테스트는 가능하지만 배포(./scripts/deploy.sh)에는 필요하다"
fi

# 2) backend 가상환경 + 의존성 (requirements-dev.txt가 requirements.txt를 포함한다)
if [ ! -d backend/.venv ]; then
    echo "생성: backend/.venv"
    "$PYTHON_BIN" -m venv backend/.venv
fi
backend/.venv/bin/pip install -q --upgrade pip
backend/.venv/bin/pip install -q -r backend/requirements-dev.txt
echo "OK: backend 의존성 설치 완료"

# 3) frontend 의존성 (lock 파일 기준 재현 설치)
(cd frontend && npm ci --silent)
echo "OK: frontend 의존성 설치 완료"

# 4) .env 준비 (값은 절대 출력하지 않는다 — 키 존재 여부만 비교한다)
if [ ! -f .env ]; then
    cp .env.example .env
    chmod 600 .env
    echo "생성: .env (.env.example 복사, 권한 600)"
    echo "  → .env를 열어 YT_API_KEY(필수) 등 값을 채울 것"
else
    chmod 600 .env
    # .env.example에 있는 키 중 .env에 없는 키만 이름으로 알린다
    MISSING_KEYS=$(comm -23 \
        <(grep -oE '^[A-Za-z_]+=' .env.example | sort -u) \
        <(grep -oE '^[A-Za-z_]+=' .env | sort -u) | tr -d '=' | tr '\n' ' ')
    if [ -n "${MISSING_KEYS// /}" ]; then
        echo "주의: .env에 없는 키 — $MISSING_KEYS(.env.example 참고)"
    fi
fi
if ! grep -qE '^YT_API_KEY=.+' .env; then
    echo "주의: YT_API_KEY가 비어 있다 — 수집이 동작하지 않는다 (필수)"
fi
if ! grep -qE '^AWS_BEARER_TOKEN_BEDROCK=.+' .env; then
    echo "참고: AWS_BEARER_TOKEN_BEDROCK이 비어 있다 — LLM 브리핑/리포트만 503으로 비활성"
fi

# 5) 백엔드 테스트 1회 (66개 통과 기준선 확인)
echo "실행: 백엔드 테스트"
(cd backend && .venv/bin/pytest tests/ -q)

# 6) Claude 훅 실행권한 + git commit-msg 훅 설치
if ls .claude/hooks/*.sh >/dev/null 2>&1; then
    chmod +x .claude/hooks/*.sh
    echo "OK: .claude/hooks/*.sh 실행권한 부여"
fi
bash scripts/install-hooks.sh

echo ""
echo "=== 셋업 완료 ==="
echo "다음 단계:"
echo "  1. .env에 YT_API_KEY 등 값을 채운다 (시크릿은 .env로만 공급한다)"
echo "  2. CLAUDE.md에서 프로젝트 규약을 읽는다"
echo "  3. 하네스 검증: bash tests/run-all.sh"
echo "  4. 배포: ./scripts/deploy.sh / 스모크: ./scripts/smoke.sh <SiteUrl>"
