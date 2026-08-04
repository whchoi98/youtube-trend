#!/bin/bash
# secret-scan.sh 탐지 패턴의 진양성(TP)/위양성(FP) 검증.
# run-all.sh가 source로 실행한다 (단독 실행 불가).
# 주의: 완성형 토큰은 런타임에 조립한다 — 저장소 파일에 완성형을 남기면
# 이 프로젝트의 secret-scan 훅과 GitHub Push Protection이 커밋을 차단한다.

if ! echo probe | grep -qP 'probe' 2>/dev/null; then
    skip "시크릿 패턴 테스트 전체" "grep -P(PCRE) 미지원 환경"
    return 0
fi

# --- 훅 파일에서 패턴 목록을 추출한다 (훅이 진실의 원천) ---
SECRET_HOOK=".claude/hooks/secret-scan.sh"
HOOK_PATTERNS=()
if [ -f "$SECRET_HOOK" ]; then
    mapfile -t HOOK_PATTERNS < <(sed -n '/^PATTERNS=(/,/^)/p' "$SECRET_HOOK" | grep -oP "^\s*'\K[^']+" || true)
fi
if [ "${#HOOK_PATTERNS[@]}" -ge 3 ]; then
    pass "secret-scan.sh에서 패턴 ${#HOOK_PATTERNS[@]}개 추출"
else
    fail "secret-scan.sh에서 패턴 추출" "패턴 ${#HOOK_PATTERNS[@]}개 — 훅 없음 또는 형식 변경 (기본 패턴으로 대체 검사)"
    HOOK_PATTERNS=(
        'AIza[0-9A-Za-z_-]{35}'
        'ABSK[A-Za-z0-9+/=_-]{16,}'
        '(AKIA|ASIA)[0-9A-Z]{16}'
    )
fi

# 프로젝트 핵심 키 형식이 훅에 정의되어 있는지 확인한다
HOOK_CONTENT=$(cat "$SECRET_HOOK" 2>/dev/null || echo "")
assert_contains "훅에 Google API Key(AIza) 패턴 정의" "$HOOK_CONTENT" "AIza"
assert_contains "훅에 Bedrock Key(ABSK) 패턴 정의" "$HOOK_CONTENT" "ABSK"
assert_contains "훅에 AWS Access Key(AKIA) 패턴 정의" "$HOOK_CONTENT" "AKIA"

secret_matches_any() {
    local text="$1" p
    for p in "${HOOK_PATTERNS[@]}"; do
        if echo "$text" | grep -qP "$p" 2>/dev/null; then
            return 0
        fi
    done
    return 1
}

# --- 진양성: 반드시 탐지해야 한다 (가짜 값 — 런타임 조립) ---
TP_G1="AIza"; TP_G2="SyFAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKE0"
assert_grep_match "TP: Google API Key (YT_API_KEY 형식)" 'AIza[0-9A-Za-z_-]{35}' "YT_API_KEY=${TP_G1}${TP_G2}"

TP_B1="ABSK"; TP_B2="FakeBedrockKeyFakeBedrockKey0000"
assert_grep_match "TP: Bedrock Bearer Key" 'ABSK[A-Za-z0-9+/=_-]{16,}' "AWS_BEARER_TOKEN_BEDROCK=${TP_B1}${TP_B2}"

TP_A1="AKIA"; TP_A2="IOSFODNN7EXAMPLE"
assert_grep_match "TP: AWS Access Key ID (장기)" '(AKIA|ASIA)[0-9A-Z]{16}' "aws_key = ${TP_A1}${TP_A2}"
assert_grep_match "TP: AWS Access Key ID (임시)" '(AKIA|ASIA)[0-9A-Z]{16}' "aws_key = ASIA${TP_A2}"

TP_S1="wJalrXUtnFEMI/K7MDENG"; TP_S2="/bPxRfiCYEXAMPLEKEY"
assert_grep_match "TP: AWS Secret Access Key" 'aws_secret_access_key\s*[=:]\s*[A-Za-z0-9/+=]{40}' "aws_secret_access_key = ${TP_S1}${TP_S2}"

assert_grep_match "TP: 하드코딩된 비밀번호" 'password\s*[:=]\s*["\x27][^"\x27]{8,}' 'password = "fake-password-value"'

# --- 위양성: 탐지하면 안 된다 ---
assert_grep_no_match "FP: .env.example 빈 값 (YT_API_KEY=)" 'AIza[0-9A-Za-z_-]{35}' "YT_API_KEY="
assert_grep_no_match "FP: 문서 속 AIza 접두사 언급" 'AIza[0-9A-Za-z_-]{35}' "Google API 키는 AIza로 시작하는 39자 문자열이다"
assert_grep_no_match "FP: 문서 속 ABSK 접두사 언급" 'ABSK[A-Za-z0-9+/=_-]{16,}' "Bedrock Bearer 토큰은 ABSK 접두사로 시작한다"
assert_grep_no_match "FP: 문서 속 AKIA 접두사 언급" '(AKIA|ASIA)[0-9A-Z]{16}' "Access Key ID는 AKIA 또는 ASIA로 시작한다"
assert_grep_no_match "FP: 빈 비밀번호" 'password\s*[:=]\s*["\x27][^"\x27]{8,}' 'password = ""'
assert_grep_no_match "FP: 일반 base64 문자열" '(AKIA|ASIA)[0-9A-Z]{16}' "dGhpcyBpcyBhIHRlc3Q="

# --- 픽스처: 진양성 샘플은 전부 최소 1개 패턴에 걸려야 한다 ---
# 형식: <설명>|<조각1>|<조각2> — 조각을 이어붙여 완성형 토큰을 만든다
TP_FIXTURE="tests/fixtures/secret-samples.txt"
if [ -f "$TP_FIXTURE" ]; then
    while IFS= read -r line; do
        case "$line" in ''|'#'*) continue ;; esac
        DESC=$(echo "$line" | cut -d'|' -f1)
        ASSEMBLED=$(echo "$line" | cut -d'|' -f2- | tr -d '|')
        if secret_matches_any "$ASSEMBLED"; then
            pass "픽스처 TP: $DESC 탐지"
        else
            fail "픽스처 TP: $DESC 탐지" "어떤 패턴에도 걸리지 않았다"
        fi
    done < "$TP_FIXTURE"
else
    fail "픽스처 존재: secret-samples.txt" "파일 없음: $TP_FIXTURE"
fi

# --- 픽스처: 위양성 샘플은 어떤 패턴에도 걸리면 안 된다 ---
FP_FIXTURE="tests/fixtures/false-positives.txt"
if [ -f "$FP_FIXTURE" ]; then
    FP_HITS=0
    while IFS= read -r line; do
        case "$line" in ''|'#'*) continue ;; esac
        if secret_matches_any "$line"; then
            fail "픽스처 FP: 오탐 없음" "오탐 발생 줄: $line"
            FP_HITS=1
        fi
    done < "$FP_FIXTURE"
    [ "$FP_HITS" -eq 0 ] && pass "픽스처 FP: 전체 위양성 샘플 미탐지"
else
    fail "픽스처 존재: false-positives.txt" "파일 없음: $FP_FIXTURE"
fi
