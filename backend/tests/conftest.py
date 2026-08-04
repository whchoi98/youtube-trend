import boto3
import pytest
from moto import mock_aws


@pytest.fixture()
def table():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="ap-northeast-2")
        t = ddb.create_table(
            TableName="TrendTable",
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield t
