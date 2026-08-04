# Infra Module (CDK Python)

## Role

AWS CDK Python으로 전체 인프라를 정의한다. CloudFormation 스택은 `YoutubeTrendsStack` 하나이며 코드가 2모듈로 분리되어 있다.

- `app.py` — CDK 엔트리. 저장소 루트 `.env`에서 비밀 아닌 설정(VPC_MODE 등)만 읽는다.
- `stacks/network.py` — `resolve_vpc`: VPC 2모드 처리. `existing`은 이름 태그로 기존 VPC lookup, `new`는 2AZ + NAT 1 + DynamoDB 게이트웨이 엔드포인트 신규 생성.
- `stacks/service.py` — `YoutubeTrendsStack`: DynamoDB 테이블(pk/sk, TTL `expireAt`), ECS Fargate ARM64, ALB, CloudFront, 시크릿 참조.

## Rules

- synth/deploy는 반드시 `npx aws-cdk@2`를 쓴다 (`cd infra && npx aws-cdk@2 synth`). 시스템 설치 cdk는 버전 비호환이다.
- ALB 접근 경계는 이중이다: CloudFront origin-facing prefix list SG(`pl-22a6434b`)로 네트워크 계층을 좁히고, CloudFront가 붙이는 `X-Origin-Verify` 비밀 헤더를 ALB 리스너 규칙에서 검증한다. 어느 한쪽도 제거하지 않는다.
- 시크릿은 Secrets Manager 이름 참조만 한다 (`sm.Secret.from_secret_name_v2`, 기본 이름 `youtube-trends/app`). 시크릿 값은 `scripts/deploy.sh`가 미리 push 하며, CDK 코드·템플릿·출력 어디에도 값이 나타나면 안 된다.
- VPC 모드 기본값은 `existing`(`VPC_NAME` lookup)이다. lookup은 계정 컨텍스트가 필요하므로 synth 실패 시 `CDK_DEFAULT_ACCOUNT`/리전(ap-northeast-2) 컨텍스트부터 확인한다.
