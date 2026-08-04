#!/usr/bin/env bash
# Notification 이벤트를 웹훅으로 전달한다.
# CLAUDE_NOTIFY_WEBHOOK 환경변수가 없으면 아무것도 하지 않는다 (선택 기능).
# 웹훅 URL과 페이로드 외의 시크릿은 다루지 않는다.

WEBHOOK_URL="${CLAUDE_NOTIFY_WEBHOOK:-}"
[ -z "$WEBHOOK_URL" ] && exit 0

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || true

EVENT="${1:-notification}"
MESSAGE="${2:-}"

# 인자가 없으면 stdin JSON에서 message를 읽는다
if [ -z "$MESSAGE" ] && [ ! -t 0 ]; then
    MESSAGE=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))" 2>/dev/null)
fi
[ -z "$MESSAGE" ] && MESSAGE="Claude Code event"

# JSON 이스케이프를 위해 python으로 페이로드를 생성한다
PAYLOAD=$(python3 - "$EVENT" "$MESSAGE" <<'EOF'
import datetime
import json
import os
import subprocess
import sys

event, message = sys.argv[1], sys.argv[2]
try:
    branch = subprocess.run(
        ["git", "branch", "--show-current"], capture_output=True, text=True
    ).stdout.strip() or "unknown"
except Exception:
    branch = "unknown"
print(json.dumps({
    "text": f"[{event}] {message}",
    "project": os.path.basename(os.getcwd()),
    "branch": branch,
    "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
}))
EOF
)

# 논블로킹 전송 (실패해도 세션에 영향 없음)
curl -s -m 5 -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" > /dev/null 2>&1 &

exit 0
