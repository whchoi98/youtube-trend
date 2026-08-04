#!/usr/bin/env bash
# 파일 변경(Write|Edit) 후 문서 동기화 필요 여부를 감지한다.
# PostToolUse 훅 — 파일 경로는 인자($1) 또는 stdin JSON(tool_input.file_path)으로 받는다.
# 경고만 출력하고 작업을 막지는 않는다.

FILE_PATH="${1:-}"
if [ -z "$FILE_PATH" ] && [ ! -t 0 ]; then
    FILE_PATH=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)
fi
[ -z "$FILE_PATH" ] && exit 0

# 절대 경로를 프로젝트 루트 기준 상대 경로로 정규화한다
ROOT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
FILE_PATH="${FILE_PATH#"$ROOT_DIR"/}"

# 이 프로젝트의 소스 루트
SOURCE_ROOTS="backend/app frontend/src infra scripts"

# 1) 소스 루트 하위 파일 변경 시, 상위 경로 어디에도 CLAUDE.md가 없으면 모듈 문서 생성을 권고한다
#    (프로젝트 루트의 CLAUDE.md는 제외하고 디렉토리 트리를 거슬러 올라가며 확인한다)
for SRC_ROOT in $SOURCE_ROOTS; do
    if [[ "$FILE_PATH" == ${SRC_ROOT}/* ]]; then
        DIR=$(dirname "$FILE_PATH")
        FOUND_CLAUDE=false
        CHECK_DIR="$DIR"
        while [ "$CHECK_DIR" != "." ] && [ "$CHECK_DIR" != "/" ]; do
            if [ -f "$ROOT_DIR/$CHECK_DIR/CLAUDE.md" ]; then
                FOUND_CLAUDE=true
                break
            fi
            CHECK_DIR=$(dirname "$CHECK_DIR")
        done
        if ! $FOUND_CLAUDE; then
            echo "[doc-sync] $DIR 경로(상위 포함)에 CLAUDE.md가 없다. 모듈 문서 생성을 검토할 것."
        fi
        break
    fi
done

# 2) 소스 또는 아키텍처 문서 변경 시 ADR이 하나도 없으면 기록을 권고한다
IS_SOURCE=false
for SRC_ROOT in $SOURCE_ROOTS; do
    [[ "$FILE_PATH" == ${SRC_ROOT}/* ]] && IS_SOURCE=true && break
done
if $IS_SOURCE || [[ "$FILE_PATH" == docs/architecture.md ]]; then
    ADR_COUNT=$(find "$ROOT_DIR/docs/decisions" -name 'ADR-*.md' -not -name '.template.md' 2>/dev/null | wc -l)
    if [ "$ADR_COUNT" -eq 0 ]; then
        echo "[doc-sync] ADR이 없다. 주요 아키텍처 결정을 docs/decisions/에 기록할 것."
    fi
fi

# 3) IaC 파일(infra/* 또는 backend/Dockerfile) 변경 시 런북이 없으면 작성을 권고한다
if [[ "$FILE_PATH" == infra/* ]] || [[ "$FILE_PATH" == backend/Dockerfile ]]; then
    RUNBOOK_COUNT=$(find "$ROOT_DIR/docs/runbooks" -name '*.md' -not -name '.template.md' 2>/dev/null | wc -l)
    if [ "$RUNBOOK_COUNT" -eq 0 ]; then
        echo "[doc-sync] 런북이 없다. 배포/복구 절차를 docs/runbooks/에 작성할 것."
    fi
fi

exit 0
