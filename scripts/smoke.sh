#!/usr/bin/env bash
set -euo pipefail
SITE="${1:?usage: smoke.sh <site-url>}"
fail=0
check() { # check <이름> <기대상태코드> <경로> [메서드] [바디]
  local name="$1" want="$2" path="$3" method="${4:-GET}" body="${5:-}"
  local got
  got=$(curl -s -o /tmp/smoke-body -w "%{http_code}" -X "$method" \
    ${body:+-H content-type:application/json -d "$body"} "$SITE$path")
  if [ "$got" = "$want" ]; then echo "PASS $name ($got)"; else
    echo "FAIL $name: want $want got $got"; fail=1; fi
}
check "healthz"        200 "/healthz"
check "SPA index"      200 "/"
check "trending"       200 "/api/trending"
check "categories"     200 "/api/categories"
check "bad scope"      400 "/api/trending?scope=999"
check "404 대조군"     404 "/api/nonexistent"   # 게이트웨이가 아닌 앱 계층 판정 확인

# brief: 키 설정 여부·스냅샷 유무에 따라 200/503/409가 모두 정상이다.
# 상태 코드를 기록만 하고 실패로 치지 않는다(PASS/FAIL 판정에서 제외).
brief_status=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
  -H content-type:application/json -d '{"scope":"all","mode":"now"}' "$SITE/api/brief")
echo "INFO brief status=$brief_status (200/503/409 모두 정상)"

exit $fail
