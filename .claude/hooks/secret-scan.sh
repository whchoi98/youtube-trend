#!/usr/bin/env bash
# git commit 전에 스테이징된 파일에서 시크릿을 탐지한다 (PreToolUse: Bash).
# 시크릿 발견 시 exit 2로 명령을 차단한다. 시크릿 값 자체는 절대 출력하지 않는다.
# 선행 프로젝트에서 .env가 최초 커밋에 포함됐던 사고의 재발을 방지한다.

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || true

# stdin JSON에서 실행하려는 Bash 명령을 읽는다. git commit 계열일 때만 검사한다
# (stdin이 없으면 수동 실행으로 간주하고 전체 검사를 수행한다)
CMD=""
if [ ! -t 0 ]; then
    CMD=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)
    case "$CMD" in
        *"git commit"*) ;;
        *) exit 0 ;;
    esac
fi

# .env 자체가 스테이징되어 있으면 즉시 차단한다
if git diff --cached --name-only 2>/dev/null | grep -qx '\.env'; then
    echo "[secret-scan] 차단: .env가 스테이징되어 있다. git rm --cached .env 후 키를 회전할 것." >&2
    exit 2
fi

SECRETS_FOUND=0

# 탐지 패턴 (이 프로젝트에서 실제 사용하는 키 형식을 우선한다)
PATTERNS=(
    'AIza[0-9A-Za-z_-]{35}'                       # Google API Key (YT_API_KEY)
    'ABSK[A-Za-z0-9+/=_-]{16,}'                   # Bedrock API Key (Bearer)
    'bedrock-api-key-[A-Za-z0-9+/=_-]{16,}'       # Bedrock API Key (prefixed)
    '(AKIA|ASIA)[0-9A-Z]{16}'                     # AWS Access Key ID (장기/임시)
    'aws_secret_access_key\s*[=:]\s*[A-Za-z0-9/+=]{40}'  # AWS Secret Key
    'sk-ant-[A-Za-z0-9-]{90,}'                    # Anthropic API Key
    'ghp_[A-Za-z0-9]{36}'                         # GitHub PAT
    'github_pat_[A-Za-z0-9_]{82}'                 # GitHub Fine-grained PAT
    'ya29\.[A-Za-z0-9_-]{50,}'                    # Google OAuth Token
    'password\s*[:=]\s*["\x27][^"\x27]{8,}'       # 하드코딩된 비밀번호
    'secret\s*[:=]\s*["\x27][^"\x27]{8,}'         # 하드코딩된 시크릿
    'api[_-]?key\s*[:=]\s*["\x27][^"\x27]{8,}'    # 하드코딩된 API 키
)

# 검사 제외 대상 (예시 파일, lock 파일, 빌드 산출물)
SKIP_PATTERNS=(
    '.env.example'
    '*secret-scan.sh'
    '*package-lock.json'
    '*yarn.lock'
    '*pnpm-lock.yaml'
    '*poetry.lock'
    '*uv.lock'
    'node_modules/*'
    '*/node_modules/*'
    'cdk.out/*'
    '*/cdk.out/*'
)

STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null)
[ -z "$STAGED_FILES" ] && exit 0

for file in $STAGED_FILES; do
    skip=false
    for pattern in "${SKIP_PATTERNS[@]}"; do
        [[ "$file" == $pattern ]] && skip=true && break
    done
    $skip && continue
    [ ! -f "$file" ] && continue

    for regex in "${PATTERNS[@]}"; do
        if grep -qP "$regex" "$file" 2>/dev/null; then
            echo "[secret-scan] 시크릿 의심 항목 발견: $file (패턴: ${regex:0:30}...)" >&2
            SECRETS_FOUND=1
        fi
    done
done

if [ "$SECRETS_FOUND" -eq 1 ]; then
    {
        echo ""
        echo "[secret-scan] 차단: 스테이징된 파일에서 시크릿 의심 항목이 발견됐다."
        echo "[secret-scan] 위 파일을 확인해 시크릿을 제거한 뒤 다시 커밋할 것."
        echo "[secret-scan] 시크릿은 .env로만 공급하고, 저장소에는 .env.example만 둔다."
    } >&2
    exit 2
fi

exit 0
