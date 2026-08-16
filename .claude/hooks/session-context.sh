#!/usr/bin/env bash
# 세션 시작 시 프로젝트 컨텍스트를 출력한다 (SessionStart).
# 시크릿 값은 절대 출력하지 않는다 — 키의 존재 여부만 알린다.

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || true

echo "=== YouTube Trends 프로젝트 컨텍스트 ==="
echo "제품: YouTube KR 급상승 전체 Top30 + 분야별 Top10(8개 카테고리) + 추이 분석 + LLM 브리핑/추이 리포트"
echo "스택: Python 3.12 FastAPI(backend) / React 18+Vite+TS(frontend) / CDK Python(infra) / ECS Fargate ARM64 + ALB + CloudFront / DynamoDB 단일 테이블 / Bedrock(Bearer 인증)"
echo "라이브: https://d2y73ug3aaah05.cloudfront.net (계정 종속 — 재배포 시 변동)"
echo ""
echo "핵심 명령:"
echo "  백엔드 테스트: cd backend && .venv/bin/pytest tests/ -q   (129개)"
echo "  프론트 게이트: cd frontend && npx tsc --noEmit && npm run build"
echo "  CDK synth:     cd infra && npx aws-cdk@2 synth   (시스템 cdk 버전 비호환 — 반드시 npx aws-cdk@2)"
echo "  배포:          ./scripts/deploy.sh"
echo "  스모크:        ./scripts/smoke.sh <SiteUrl>"
echo ""

# git 상태
BRANCH=$(git branch --show-current 2>/dev/null)
[ -n "$BRANCH" ] && echo "브랜치: $BRANCH"
LAST_COMMIT=$(git log -1 --format="%h %s (%cr)" 2>/dev/null)
[ -n "$LAST_COMMIT" ] && echo "최근 커밋: $LAST_COMMIT"
CHANGES=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
if [ "$CHANGES" -gt 0 ]; then
    echo "미커밋 변경: ${CHANGES}개 파일"
fi

# .env 상태 (키 존재 여부만 — 값은 출력하지 않는다)
if [ -f .env ]; then
    ENV_STATUS=""
    for KEY in YT_API_KEY AWS_BEARER_TOKEN_BEDROCK ORIGIN_VERIFY_TOKEN VPC_MODE VPC_NAME APP_SECRET_NAME; do
        if grep -qE "^${KEY}=." .env 2>/dev/null; then
            ENV_STATUS="$ENV_STATUS $KEY=설정됨"
        else
            ENV_STATUS="$ENV_STATUS $KEY=없음"
        fi
    done
    echo ".env: 존재함 —$ENV_STATUS"
    echo "      (YT_API_KEY 필수, AWS_BEARER_TOKEN_BEDROCK 없으면 LLM 기능만 503)"
    if git ls-files --error-unmatch .env >/dev/null 2>&1; then
        echo "경고: .env가 git에 추적되고 있다. 즉시 git rm --cached .env 후 키를 회전할 것."
    fi
else
    echo ".env: 없음 — .env.example을 복사해 작성할 것 (YT_API_KEY 필수)"
fi

echo "========================================"
exit 0
