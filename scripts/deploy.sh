#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# 1) .env 존재·비추적 검사 (값은 출력하지 않는다)
[ -f .env ] || { echo "ERROR: .env가 없습니다. .env.example을 복사해 작성하세요"; exit 1; }
if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  echo "ERROR: .env가 git에 추적되고 있습니다. git rm --cached .env 후 키를 회전하세요"; exit 1
fi
set -a; source .env; set +a
[ -n "${YT_API_KEY:-}" ] || { echo "ERROR: YT_API_KEY가 비어 있습니다"; exit 1; }

# 2) 시크릿 push (create 실패 시 update — 값은 임시 파일로만 전달한다.
#    aws CLI 인자로 직접 넘기면 ps/proc/*/cmdline으로 노출되므로 file:// 참조를 쓴다)
SECRET_NAME="${APP_SECRET_NAME:-youtube-trends/app}"
TMP_SECRET=$(mktemp)
chmod 600 "$TMP_SECRET"
trap 'rm -f "$TMP_SECRET"' EXIT
python3 - > "$TMP_SECRET" <<'EOF'
import json, os
print(json.dumps({"YT_API_KEY": os.environ.get("YT_API_KEY",""),
                  "AWS_BEARER_TOKEN_BEDROCK": os.environ.get("AWS_BEARER_TOKEN_BEDROCK","")}))
EOF
aws secretsmanager create-secret --region ap-northeast-2 --name "$SECRET_NAME" \
  --secret-string "file://$TMP_SECRET" >/dev/null 2>&1 || \
aws secretsmanager put-secret-value --region ap-northeast-2 --secret-id "$SECRET_NAME" \
  --secret-string "file://$TMP_SECRET" >/dev/null || \
  { echo "ERROR: 시크릿 push 실패"; exit 1; }
echo "OK: 시크릿 push 완료 ($SECRET_NAME)"

# 3) 검증 게이트
(cd backend && .venv/bin/pytest -q)
(cd frontend && npx tsc --noEmit && npm run build >/dev/null)

# 4) 배포 (시스템 cdk는 버전 불일치 — npx aws-cdk@2로 고정 실행)
(cd infra && npx aws-cdk@2 deploy YoutubeTrendsStack --require-approval never)

# 5) 스모크
SITE=$(aws cloudformation describe-stacks --region ap-northeast-2 \
  --stack-name YoutubeTrendsStack \
  --query "Stacks[0].Outputs[?OutputKey=='SiteUrl'].OutputValue" --output text)
./scripts/smoke.sh "$SITE"
