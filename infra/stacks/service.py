import os
import secrets as pysecrets

from aws_cdk import (
    CfnOutput, Duration, RemovalPolicy, Stack,
    aws_cloudfront as cf, aws_cloudfront_origins as origins,
    aws_dynamodb as ddb, aws_ec2 as ec2, aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2, aws_logs as logs,
    aws_secretsmanager as sm,
)
from constructs import Construct

from stacks.network import resolve_vpc


class YoutubeTrendsStack(Stack):
    def __init__(self, scope: Construct, cid: str, *, vpc_mode: str,
                 vpc_name: str, secret_name: str, **kw):
        super().__init__(scope, cid, **kw)
        vpc = resolve_vpc(self, vpc_mode, vpc_name)

        table = ddb.Table(
            self, "TrendTable",
            partition_key=ddb.Attribute(name="pk", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="sk", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="expireAt",
            removal_policy=RemovalPolicy.DESTROY,  # 캡스톤 규모 — 정리 편의 우선
        )

        # deploy.sh가 미리 만들어 둔 시크릿을 이름으로 참조한다(값은 템플릿에 없음)
        app_secret = sm.Secret.from_secret_name_v2(self, "AppSecret", secret_name)

        cluster = ecs.Cluster(self, "Cluster", vpc=vpc)
        task = ecs.FargateTaskDefinition(
            self, "Task", cpu=512, memory_limit_mib=1024,
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.ARM64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX))
        container = task.add_container(
            "app",
            image=ecs.ContainerImage.from_asset(
                directory="..", file="backend/Dockerfile",
                platform=None),  # 빌드 호스트가 aarch64 — 네이티브 빌드
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="app",
                log_retention=logs.RetentionDays.TWO_WEEKS),
            environment={"TABLE_NAME": table.table_name, "COLLECT_ENABLED": "true"},
            secrets={
                "YT_API_KEY": ecs.Secret.from_secrets_manager(app_secret, "YT_API_KEY"),
                "AWS_BEARER_TOKEN_BEDROCK": ecs.Secret.from_secrets_manager(
                    app_secret, "AWS_BEARER_TOKEN_BEDROCK"),
            },
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL",
                         "python3 -c \"import urllib.request;urllib.request.urlopen('http://localhost:8000/healthz')\""],
                interval=Duration.seconds(30)))
        container.add_port_mappings(ecs.PortMapping(container_port=8000))
        table.grant_read_write_data(task.task_role)
        # 의도: Bedrock IAM 정책은 부여하지 않는다(Bearer 인증 — Global Constraints).

        service = ecs.FargateService(
            self, "Service", cluster=cluster, task_definition=task,
            desired_count=1,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            min_healthy_percent=100, max_healthy_percent=200)

        # ALB: prefix list SG — CloudFront origin-facing 대역만 인바운드 허용
        alb_sg = ec2.SecurityGroup(self, "AlbSg", vpc=vpc, allow_all_outbound=True)
        # com.amazonaws.global.cloudfront.origin-facing — ap-northeast-2 리전 ID.
        # aws ec2 describe-managed-prefix-lists로 2026-08-04에 실제 조회하여 검증됨.
        cf_prefix = ec2.Peer.prefix_list("pl-22a6434b")
        alb_sg.add_ingress_rule(cf_prefix, ec2.Port.tcp(80),
                                "CloudFront origin-facing only")
        alb = elbv2.ApplicationLoadBalancer(
            self, "Alb", vpc=vpc, internet_facing=True, security_group=alb_sg,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC))

        # 비밀 헤더: prefix list는 타 고객 CloudFront도 포함하므로 2중 방어
        # .env의 ORIGIN_VERIFY_TOKEN이 있으면 고정(재배포마다 CloudFront·ALB 동시 갱신 방지),
        # 없으면 매 synth마다 새로 생성(무해하나 배포 시 갱신됨).
        origin_verify = os.environ.get("ORIGIN_VERIFY_TOKEN") or pysecrets.token_urlsafe(24)
        listener = alb.add_listener("Http", port=80, open=False,
                                    default_action=elbv2.ListenerAction.fixed_response(
                                        403, content_type="text/plain", message_body="forbidden"))
        listener.add_targets(
            "App", port=8000, protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[service],
            conditions=[elbv2.ListenerCondition.http_header("X-Origin-Verify", [origin_verify])],
            priority=1,
            health_check=elbv2.HealthCheck(path="/healthz", healthy_http_codes="200"),
            deregistration_delay=Duration.seconds(30))

        dist = cf.Distribution(
            self, "Dist",
            default_behavior=cf.BehaviorOptions(
                origin=origins.HttpOrigin(
                    alb.load_balancer_dns_name,
                    protocol_policy=cf.OriginProtocolPolicy.HTTP_ONLY,
                    custom_headers={"X-Origin-Verify": origin_verify}),
                viewer_protocol_policy=cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cf.CachePolicy.CACHING_OPTIMIZED),
            additional_behaviors={
                "/api/*": cf.BehaviorOptions(
                    origin=origins.HttpOrigin(
                        alb.load_balancer_dns_name,
                        protocol_policy=cf.OriginProtocolPolicy.HTTP_ONLY,
                        custom_headers={"X-Origin-Verify": origin_verify}),
                    viewer_protocol_policy=cf.ViewerProtocolPolicy.HTTPS_ONLY,
                    allowed_methods=cf.AllowedMethods.ALLOW_ALL,
                    cache_policy=cf.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cf.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER)})

        CfnOutput(self, "SiteUrl", value=f"https://{dist.distribution_domain_name}")
        CfnOutput(self, "AlbDns", value=alb.load_balancer_dns_name)
        CfnOutput(self, "TableName", value=table.table_name)
        CfnOutput(self, "ServiceName", value=service.service_name)
