# Security / 보안 구현 상세

[![English](https://img.shields.io/badge/Language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/Language-한국어-red)](#korean)

<a id="english"></a>
## English

### 1. Overview
Security spans three areas: secret supply (single `.env` source pushed to Secrets Manager, values never written anywhere else), origin protection (CloudFront prefix-list SG plus `X-Origin-Verify` shared header), and input/output hygiene (path-traversal guard, external-string laundering for prompts, upstream error bodies kept out of exceptions).

### 2. Components
| Component | Path | Purpose |
|---|---|---|
| Secret pipeline | `scripts/deploy.sh` | Verifies `.env` exists and is not git-tracked (rotate keys if it was); passes secret JSON via `file://` temp file with `chmod 600` and trap cleanup — never as CLI args visible in `ps`/`/proc/*/cmdline` |
| Origin defense | `infra/stacks/service.py` | ALB SG allows only prefix list `pl-22a6434b` (CloudFront origin-facing); listener defaults to fixed 403 and forwards only when `X-Origin-Verify` matches; secrets injected into ECS from Secrets Manager by name |
| Path traversal guard | `backend/app/main.py` | SPA catch-all resolves `realpath` and refuses to serve any file outside the static base (falls back to SPA index); unregistered `/api/*` stays 404 JSON |
| Prompt input laundering | `backend/app/llm/prompts.py` | `clean_text` collapses whitespace/newlines and caps length — YouTube-sourced titles/channel names cannot forge list structure or amplify tokens |
| Upstream error hygiene (Bedrock) | `backend/app/llm/bedrock.py` | Error bodies (may contain account ID / model ARN) are logged only; exceptions carry the status code alone |
| Upstream error hygiene (YouTube) | `backend/app/collector/youtube.py` | Error bodies (may contain GCP project number / console URL) are logged only; `UpstreamError` carries the status alone |
| Settings surface | `backend/app/config.py` | Frozen dataclass fed exclusively from environment variables (`YT_API_KEY`, `AWS_BEARER_TOKEN_BEDROCK`, `TABLE_NAME`) |

### 3. Key Decisions
- Secret values must never be written to any file or output; `scripts/deploy.sh` is the only push path (`youtube-trends/app` in Secrets Manager) and the CDK template holds a name reference only.
- Bedrock uses Bearer auth exclusively — no SigV4/IAM policy is granted, because the org SCP denies InvokeModel in this region and the key is issued outside the org.
- Two-layer origin defense: the prefix list also covers other customers' CloudFront distributions, so the `X-Origin-Verify` shared header is the second, mandatory check.
- The container runs as non-root user `app` (see `backend/Dockerfile`).
- Health check (`/healthz`) touches no external dependency, avoiding auth-error amplification during upstream incidents.

### 4. Code Pointers
- `scripts/deploy.sh` — `.env` checks and `file://` secret transfer
- `infra/stacks/service.py` — SG prefix list, 403 default action, header condition
- `backend/app/main.py` — `realpath`-based traversal guard in the SPA route
- `backend/app/llm/prompts.py` — `clean_text` and line-format laundering
- `backend/app/llm/bedrock.py`, `backend/app/collector/youtube.py` — log-only error bodies

### 5. Cross-references
- Related modules: `scripts/`, `infra/stacks/`, `backend/app/llm/`
- Related ADRs: none yet
- Related runbooks: none yet
- Related layers: [iac.md](iac.md), [infrastructure.md](infrastructure.md), [agent-llm.md](agent-llm.md)

<a id="korean"></a>
## 한국어

### 1. 개요
보안은 세 영역에 걸친다. 시크릿 공급(단일 `.env` → Secrets Manager push, 값은 다른 어디에도 기록 금지), 오리진 보호(CloudFront prefix list SG + `X-Origin-Verify` 공유 헤더), 입출력 위생(경로 traversal 가드, 프롬프트 외부 문자열 세탁, 상류 오류 본문의 예외 격리)이다.

### 2. 구성요소
| 구성요소 | 경로 | 목적 |
|---|---|---|
| 시크릿 파이프라인 | `scripts/deploy.sh` | `.env` 존재·git 비추적 검사(추적 시 키 회전 안내). 시크릿 JSON은 `chmod 600` + trap 정리되는 임시 파일의 `file://` 참조로만 전달한다 — CLI 인자는 `ps`/`/proc/*/cmdline`에 노출된다 |
| 오리진 방어 | `infra/stacks/service.py` | ALB SG는 prefix list `pl-22a6434b`(CloudFront origin-facing)만 허용. 리스너 기본 동작은 고정 403, `X-Origin-Verify` 일치 시에만 포워딩. 시크릿은 Secrets Manager 이름 참조로 ECS에 주입 |
| 경로 traversal 가드 | `backend/app/main.py` | SPA catch-all이 `realpath`로 해석해 정적 base 밖 파일은 존재해도 서빙하지 않는다(SPA index로 폴백). 미등록 `/api/*`는 404 JSON 유지 |
| 프롬프트 입력 세탁 | `backend/app/llm/prompts.py` | `clean_text`가 공백·개행을 접고 길이를 상한한다 — YouTube발 제목·채널명이 목록 구조를 위조하거나 토큰을 증폭할 수 없다 |
| 상류 오류 위생(Bedrock) | `backend/app/llm/bedrock.py` | 오류 본문(계정 ID·모델 ARN 포함 가능)은 로그에만 남기고 예외에는 상태 코드만 싣는다 |
| 상류 오류 위생(YouTube) | `backend/app/collector/youtube.py` | 오류 본문(GCP 프로젝트 번호·콘솔 URL 포함 가능)은 로그에만, `UpstreamError`에는 상태 코드만 |
| 설정 표면 | `backend/app/config.py` | 환경 변수만으로 채워지는 frozen dataclass(`YT_API_KEY`, `AWS_BEARER_TOKEN_BEDROCK`, `TABLE_NAME`) |

### 3. 주요 결정
- 시크릿 값은 어떤 파일·출력에도 기록하지 않는다. push 경로는 `scripts/deploy.sh` 하나뿐이고(Secrets Manager `youtube-trends/app`), CDK 템플릿은 이름 참조만 갖는다.
- Bedrock은 Bearer 인증 전용이다 — 조직 SCP가 이 리전의 InvokeModel을 거부하고 키가 조직 밖에서 발급되므로 SigV4/IAM 정책을 부여하지 않는다.
- 오리진 2중 방어: prefix list는 타 고객의 CloudFront도 포함하므로 `X-Origin-Verify` 공유 헤더가 필수적인 2차 검증이다.
- 컨테이너는 non-root 사용자 `app`으로 실행한다(`backend/Dockerfile` 참조).
- 헬스체크(`/healthz`)는 외부 의존에 접근하지 않아 상류 장애 시 인증 오류 증폭을 피한다.

### 4. 코드 포인터
- `scripts/deploy.sh` — `.env` 검사와 `file://` 시크릿 전달
- `infra/stacks/service.py` — SG prefix list, 기본 403, 헤더 조건
- `backend/app/main.py` — SPA 라우트의 `realpath` 기반 traversal 가드
- `backend/app/llm/prompts.py` — `clean_text`와 목록 형식 세탁
- `backend/app/llm/bedrock.py`, `backend/app/collector/youtube.py` — 오류 본문 로그 격리

### 5. 상호 참조
- 관련 모듈: `scripts/`, `infra/stacks/`, `backend/app/llm/`
- 관련 ADR: 아직 없음
- 관련 런북: 아직 없음
- 관련 레이어: [iac.md](iac.md), [infrastructure.md](infrastructure.md), [agent-llm.md](agent-llm.md)

Last updated: 2026-08-04
