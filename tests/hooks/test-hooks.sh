#!/bin/bash
# .claude/hooks/*.sh 검증 — 존재·실행권한·문법·settings.json 등록·런타임 동작.
# run-all.sh가 source로 실행한다 (단독 실행 불가).

# --- 존재·실행권한·문법 (훅 4종) ---
HOOKS=(session-context secret-scan check-doc-sync notify)
for hook in "${HOOKS[@]}"; do
    assert_file_exists "$hook.sh 존재" ".claude/hooks/$hook.sh"
    assert_file_executable "$hook.sh 실행권한" ".claude/hooks/$hook.sh"
    assert_bash_syntax "$hook.sh bash 문법" ".claude/hooks/$hook.sh"
done

# --- settings.json 등록 검증 ---
assert_file_exists "settings.json 존재" ".claude/settings.json"
assert_json_valid "settings.json JSON 유효" ".claude/settings.json"

SETTINGS=$(cat .claude/settings.json)
assert_contains "SessionStart 훅 등록" "$SETTINGS" "session-context.sh"
assert_contains "PreToolUse 훅 등록 (secret-scan)" "$SETTINGS" "secret-scan.sh"
assert_contains "PostToolUse 훅 등록 (check-doc-sync)" "$SETTINGS" "check-doc-sync.sh"
assert_contains "PostToolUse matcher는 Write|Edit" "$SETTINGS" "Write|Edit"
assert_contains "Notification 훅 등록 (notify)" "$SETTINGS" "notify.sh"
assert_contains ".env 직접 읽기 deny 등록" "$SETTINGS" "Read(./.env)"

# --- 동작 검증: session-context ---
if [ -x .claude/hooks/session-context.sh ]; then
    OUTPUT=$(CLAUDE_PROJECT_DIR="$PROJECT_ROOT" bash .claude/hooks/session-context.sh 2>&1 || true)
    assert_contains "session-context: 프로젝트 헤더 출력" "$OUTPUT" "YouTube Trends"
    assert_contains "session-context: 핵심 명령 안내 포함" "$OUTPUT" "pytest"
else
    skip "session-context 동작 검증" "훅 파일 없음"
fi

# --- 동작 검증: check-doc-sync ---
if [ -x .claude/hooks/check-doc-sync.sh ]; then
    # 경로 없음 → 출력 없음, exit 0
    OUTPUT=$(echo '{}' | CLAUDE_PROJECT_DIR="$PROJECT_ROOT" bash .claude/hooks/check-doc-sync.sh "" 2>&1 || true)
    assert_eq "check-doc-sync: 빈 경로는 출력 없음" "" "$OUTPUT"
    # 소스 루트 밖 파일(README.md) → 출력 없음
    OUTPUT=$(echo '{"tool_input":{"file_path":"README.md"}}' | CLAUDE_PROJECT_DIR="$PROJECT_ROOT" bash .claude/hooks/check-doc-sync.sh 2>&1 || true)
    assert_eq "check-doc-sync: 소스 밖 파일은 출력 없음" "" "$OUTPUT"
else
    skip "check-doc-sync 동작 검증" "훅 파일 없음"
fi

# --- 동작 검증: notify ---
if [ -x .claude/hooks/notify.sh ]; then
    OUTPUT=$(CLAUDE_NOTIFY_WEBHOOK="" bash .claude/hooks/notify.sh "test" "msg" 2>&1 || true)
    assert_eq "notify: 웹훅 미설정 시 침묵" "" "$OUTPUT"
else
    skip "notify 동작 검증" "훅 파일 없음"
fi

# --- 동작 검증: secret-scan (임시 git 저장소에서 end-to-end) ---
if [ -x .claude/hooks/secret-scan.sh ]; then
    # git commit이 아닌 명령은 검사 없이 통과한다
    RC=0
    echo '{"tool_input":{"command":"ls -la"}}' \
        | CLAUDE_PROJECT_DIR="$PROJECT_ROOT" bash .claude/hooks/secret-scan.sh >/dev/null 2>&1 || RC=$?
    assert_eq "secret-scan: 비커밋 명령은 통과(exit 0)" "0" "$RC"

    TMP_REPO=$(mktemp -d "${TMPDIR:-/tmp}/yt-secret-scan-test.XXXXXX")
    git -C "$TMP_REPO" init -q

    # 진양성: 가짜 AWS Access Key ID (런타임 조립 — 저장소에 완성형 토큰을 남기지 않는다)
    FAKE_P1="AKIA"
    FAKE_P2="IOSFODNN7EXAMPLE"
    printf 'aws_key = %s%s\n' "$FAKE_P1" "$FAKE_P2" > "$TMP_REPO/config.py"
    git -C "$TMP_REPO" add config.py
    RC=0
    echo '{"tool_input":{"command":"git commit -m test"}}' \
        | CLAUDE_PROJECT_DIR="$TMP_REPO" bash "$PROJECT_ROOT/.claude/hooks/secret-scan.sh" >/dev/null 2>&1 || RC=$?
    assert_eq "secret-scan: 스테이징된 가짜 키를 차단(exit 2)" "2" "$RC"

    # .env 스테이징 자체를 차단한다
    git -C "$TMP_REPO" rm -q --cached config.py
    rm -f "$TMP_REPO/config.py"
    echo "YT_API_KEY=dummy" > "$TMP_REPO/.env"
    git -C "$TMP_REPO" add -f .env
    RC=0
    echo '{"tool_input":{"command":"git commit -m test"}}' \
        | CLAUDE_PROJECT_DIR="$TMP_REPO" bash "$PROJECT_ROOT/.claude/hooks/secret-scan.sh" >/dev/null 2>&1 || RC=$?
    assert_eq "secret-scan: .env 스테이징을 차단(exit 2)" "2" "$RC"

    # 위양성 아님: 무해한 파일은 통과한다
    git -C "$TMP_REPO" rm -q --cached .env
    rm -f "$TMP_REPO/.env"
    echo "print('hello')" > "$TMP_REPO/main.py"
    git -C "$TMP_REPO" add main.py
    RC=0
    echo '{"tool_input":{"command":"git commit -m test"}}' \
        | CLAUDE_PROJECT_DIR="$TMP_REPO" bash "$PROJECT_ROOT/.claude/hooks/secret-scan.sh" >/dev/null 2>&1 || RC=$?
    assert_eq "secret-scan: 무해한 파일은 통과(exit 0)" "0" "$RC"

    rm -rf "$TMP_REPO"
else
    skip "secret-scan 동작 검증" "훅 파일 없음"
fi
