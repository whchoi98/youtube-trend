from aws_cdk import aws_ec2 as ec2


def resolve_vpc(scope, vpc_mode: str, vpc_name: str) -> ec2.IVpc:
    """existing: 이름 태그로 조회(계정의 cc-on-bedrock-vpc — public×2/private×2,
    기존 NAT 재사용). new: 이 레포를 쓰는 다른 사용자용 — 2AZ + NAT 1 + DDB 엔드포인트."""
    if vpc_mode == "existing":
        return ec2.Vpc.from_lookup(scope, "Vpc", tags={"Name": vpc_name})
    vpc = ec2.Vpc(
        scope, "Vpc", max_azs=2, nat_gateways=1,
        subnet_configuration=[
            ec2.SubnetConfiguration(name="public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24),
            ec2.SubnetConfiguration(name="private", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, cidr_mask=20),
        ])
    vpc.add_gateway_endpoint("DdbEndpoint", service=ec2.GatewayVpcEndpointAwsService.DYNAMODB)
    return vpc
