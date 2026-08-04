import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    table_name: str
    yt_api_key: str
    bedrock_token: str = ""
    aws_region: str = "ap-northeast-2"
    collect_enabled: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            table_name=os.environ["TABLE_NAME"],
            yt_api_key=os.environ.get("YT_API_KEY", ""),
            bedrock_token=os.environ.get("AWS_BEARER_TOKEN_BEDROCK", ""),
            aws_region=os.environ.get("AWS_REGION", "ap-northeast-2"),
            collect_enabled=os.environ.get("COLLECT_ENABLED", "true").lower() == "true",
        )
