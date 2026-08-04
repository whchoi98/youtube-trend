"""CDK 엔트리. 저장소 루트의 .env를 읽어 VPC 모드 등 비밀 아닌 설정을 얻는다.
시크릿 값은 여기서 다루지 않는다 — scripts/deploy.sh가 Secrets Manager에 넣고
스택은 ARN 참조만 한다."""
import os

import aws_cdk as cdk
from dotenv import load_dotenv

from stacks.service import YoutubeTrendsStack

load_dotenv(dotenv_path="../.env", override=True)  # 파일이 셸을 이긴다(선행 프로젝트 규칙 계승)

app = cdk.App()
YoutubeTrendsStack(
    app, "YoutubeTrendsStack",
    vpc_mode=os.environ.get("VPC_MODE", "existing"),
    vpc_name=os.environ.get("VPC_NAME", "cc-on-bedrock-vpc"),
    secret_name=os.environ.get("APP_SECRET_NAME", "youtube-trends/app"),
    env=cdk.Environment(account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
                        region="ap-northeast-2"),
)
app.synth()
