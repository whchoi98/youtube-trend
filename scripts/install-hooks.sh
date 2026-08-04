#!/usr/bin/env bash
# git commit-msg 훅을 설치한다 (커밋 메시지에서 Co-Authored-By 줄 제거).
# 마커 기반 멱등 — 이미 설치되어 있으면 아무것도 하지 않는다.
# 사용법: bash scripts/install-hooks.sh
set -euo pipefail
cd "$(dirname "$0")/.."

MARKER="# youtube-trends:commit-msg-hook v1"

# worktree에서도 올바른 훅 경로를 얻는다
HOOKS_DIR=$(git rev-parse --git-path hooks 2>/dev/null) || {
    echo "ERROR: git 저장소가 아니다"; exit 1;
}
mkdir -p "$HOOKS_DIR"
HOOK_FILE="$HOOKS_DIR/commit-msg"

if [ -f "$HOOK_FILE" ] && grep -qF "$MARKER" "$HOOK_FILE"; then
    echo "OK: commit-msg 훅이 이미 설치되어 있다 (마커 확인 — 건너뜀)"
    exit 0
fi

# 마커 없는 기존 훅은 덮어쓰기 전에 백업한다
if [ -f "$HOOK_FILE" ]; then
    cp "$HOOK_FILE" "$HOOK_FILE.bak"
    echo "주의: 기존 commit-msg 훅을 $HOOK_FILE.bak 으로 백업했다"
fi

cat > "$HOOK_FILE" <<HOOK
#!/usr/bin/env bash
$MARKER
# 커밋 메시지에서 Co-Authored-By 줄을 제거한다 (AI 공동 저자 표기 방지)
sed -i '/^[Cc]o-[Aa]uthored-[Bb]y:/d' "\$1"
# 끝의 연속 빈 줄을 정리한다
sed -i -e :a -e '/^\n*\$/{\$d;N;ba' -e '}' "\$1"
HOOK
chmod +x "$HOOK_FILE"

echo "OK: commit-msg 훅 설치 완료 ($HOOK_FILE)"
