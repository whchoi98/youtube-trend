from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app


def make_settings(**over):
    base = dict(table_name="t", yt_api_key="x", bedrock_token="", collect_enabled=False)
    base.update(over)
    return Settings(**base)


def test_healthz_returns_ok_without_any_backend():
    app = create_app(make_settings())
    client = TestClient(app)
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.text == "ok"
