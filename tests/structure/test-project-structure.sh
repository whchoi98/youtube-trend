#!/bin/bash
# 프로젝트 구조 검증 — 이 저장소의 실제 파일 기준.
# run-all.sh가 source로 실행한다 (단독 실행 불가).

# --- CLAUDE.md 4개 (루트 + 모듈 3개) ---
assert_file_exists "루트 CLAUDE.md" "CLAUDE.md"
assert_file_exists "backend/CLAUDE.md" "backend/CLAUDE.md"
assert_file_exists "frontend/CLAUDE.md" "frontend/CLAUDE.md"
assert_file_exists "infra/CLAUDE.md" "infra/CLAUDE.md"

# --- .claude 구성 ---
assert_file_exists ".claude/settings.json" ".claude/settings.json"
assert_json_valid ".claude/settings.json JSON 유효" ".claude/settings.json"
assert_dir_exists ".claude/hooks 디렉토리" ".claude/hooks"
assert_dir_exists ".claude/skills 디렉토리" ".claude/skills"

# --- backend (FastAPI + pytest) ---
assert_dir_exists "backend/app" "backend/app"
assert_dir_exists "backend/tests" "backend/tests"
assert_file_exists "backend/pytest.ini" "backend/pytest.ini"
assert_file_exists "backend/requirements.txt" "backend/requirements.txt"
assert_file_exists "backend/requirements-dev.txt" "backend/requirements-dev.txt"
assert_file_exists "backend/Dockerfile" "backend/Dockerfile"

# --- frontend (React + Vite + TS) ---
assert_file_exists "frontend/package.json" "frontend/package.json"
assert_file_exists "frontend/package-lock.json (npm ci 전제)" "frontend/package-lock.json"
assert_file_exists "frontend/vite.config.ts" "frontend/vite.config.ts"
assert_file_exists "frontend/tsconfig.json" "frontend/tsconfig.json"
assert_dir_exists "frontend/src" "frontend/src"

# --- infra (CDK Python) ---
assert_file_exists "infra/app.py" "infra/app.py"
assert_file_exists "infra/cdk.json" "infra/cdk.json"
assert_dir_exists "infra/stacks" "infra/stacks"

# --- scripts: 존재·실행권한·문법 ---
for script in setup.sh install-hooks.sh deploy.sh smoke.sh; do
    assert_file_exists "scripts/$script 존재" "scripts/$script"
    assert_file_executable "scripts/$script 실행권한" "scripts/$script"
    assert_bash_syntax "scripts/$script bash 문법" "scripts/$script"
done
assert_file_executable "tests/run-all.sh 실행권한" "tests/run-all.sh"

# --- 시크릿 위생 ---
assert_file_exists ".env.example" ".env.example"
GITIGNORE=$(cat .gitignore 2>/dev/null || echo "")
assert_contains ".gitignore에 .env 등록" "$GITIGNORE" ".env"
if git ls-files --error-unmatch .env >/dev/null 2>&1; then
    fail ".env 비추적 확인" ".env가 git에 추적되고 있다 — git rm --cached .env 후 키를 회전할 것"
else
    pass ".env 비추적 확인"
fi

# --- 문서/설정 ---
assert_file_exists "docs/architecture.md" "docs/architecture.md"
assert_file_exists "README.md" "README.md"
assert_file_exists ".editorconfig" ".editorconfig"
assert_file_exists ".dockerignore (빌드 컨텍스트=저장소 루트)" ".dockerignore"
