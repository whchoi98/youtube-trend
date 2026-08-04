#!/bin/bash
# 하네스 검증 테스트 러너 — Claude Code 훅/구조/시크릿 패턴을 검증한다.
# backend/tests(pytest 66개)와는 무관하다. 백엔드 테스트는 cd backend && .venv/bin/pytest tests/ -q 로 실행한다.
# 사용법: bash tests/run-all.sh [test-file-pattern]
# 예시:   bash tests/run-all.sh           # 전체 실행
#         bash tests/run-all.sh hooks     # 훅 테스트만
#         bash tests/run-all.sh secret    # 시크릿 패턴 테스트만

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

TOTAL=0
PASSED=0
FAILED=0
SKIPPED=0
FAILURES=()

export TEST_RUNNER_ACTIVE=1

pass() {
    TOTAL=$((TOTAL + 1))
    PASSED=$((PASSED + 1))
    echo -e "  ${GREEN}✓${NC} $1"
}

fail() {
    TOTAL=$((TOTAL + 1))
    FAILED=$((FAILED + 1))
    FAILURES+=("$1: $2")
    echo -e "  ${RED}✗${NC} $1"
    echo -e "    ${RED}→ $2${NC}"
}

skip() {
    TOTAL=$((TOTAL + 1))
    SKIPPED=$((SKIPPED + 1))
    echo -e "  ${YELLOW}○${NC} $1 (건너뜀: $2)"
}

assert_eq() {
    local desc="$1" expected="$2" actual="$3"
    [ "$expected" = "$actual" ] && pass "$desc" || fail "$desc" "기대값 '$expected', 실제값 '$actual'"
}

assert_contains() {
    local desc="$1" haystack="$2" needle="$3"
    echo "$haystack" | grep -qF "$needle" && pass "$desc" || fail "$desc" "출력에 '$needle' 없음"
}

assert_file_exists() {
    local desc="$1" filepath="$2"
    [ -f "$filepath" ] && pass "$desc" || fail "$desc" "파일 없음: $filepath"
}

assert_dir_exists() {
    local desc="$1" dirpath="$2"
    [ -d "$dirpath" ] && pass "$desc" || fail "$desc" "디렉토리 없음: $dirpath"
}

assert_file_executable() {
    local desc="$1" filepath="$2"
    [ -x "$filepath" ] && pass "$desc" || fail "$desc" "실행권한 없음: $filepath"
}

assert_json_valid() {
    local desc="$1" filepath="$2"
    python3 -m json.tool "$filepath" > /dev/null 2>&1 && pass "$desc" || fail "$desc" "JSON 형식 오류: $filepath"
}

assert_bash_syntax() {
    local desc="$1" filepath="$2"
    bash -n "$filepath" 2>/dev/null && pass "$desc" || fail "$desc" "bash 문법 오류: $filepath"
}

assert_grep_match() {
    local desc="$1" pattern="$2" input="$3"
    echo "$input" | grep -qP "$pattern" 2>/dev/null && pass "$desc" || fail "$desc" "패턴 '$pattern' 미탐지 (탐지되어야 한다)"
}

assert_grep_no_match() {
    local desc="$1" pattern="$2" input="$3"
    echo "$input" | grep -qP "$pattern" 2>/dev/null && fail "$desc" "패턴 '$pattern' 오탐 (탐지되면 안 된다)" || pass "$desc"
}

export -f pass fail skip assert_eq assert_contains assert_file_exists assert_dir_exists
export -f assert_file_executable assert_json_valid assert_bash_syntax
export -f assert_grep_match assert_grep_no_match

FILTER="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${CYAN}=== YouTube Trends 하네스 테스트 스위트 ===${NC}"
echo ""

TEST_FILES=$(find "$SCRIPT_DIR" -name "test-*.sh" -not -name "run-all.sh" | sort)

for test_file in $TEST_FILES; do
    test_name=$(basename "$test_file" .sh)
    if [ -n "$FILTER" ] && ! echo "$test_name" | grep -q "$FILTER"; then
        continue
    fi
    echo -e "${CYAN}▸ $test_name${NC}"
    source "$test_file"
    echo ""
done

echo -e "${CYAN}=== 결과 ===${NC}"
echo -e "  전체:    $TOTAL"
echo -e "  ${GREEN}통과:    $PASSED${NC}"
[ "$FAILED" -gt 0 ] && echo -e "  ${RED}실패:    $FAILED${NC}" || echo -e "  실패:    0"
[ "$SKIPPED" -gt 0 ] && echo -e "  ${YELLOW}건너뜀:  $SKIPPED${NC}" || echo -e "  건너뜀:  0"

if [ "$FAILED" -gt 0 ]; then
    echo ""
    echo -e "${RED}=== 실패 목록 ===${NC}"
    for f in "${FAILURES[@]}"; do
        echo -e "  ${RED}✗${NC} $f"
    done
    exit 1
else
    echo ""
    echo -e "${GREEN}전체 테스트 통과.${NC}"
fi
