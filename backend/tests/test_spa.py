from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app


def make_app_with_static(tmp_path, monkeypatch):
    static = tmp_path / "static"
    static.mkdir()
    (static / "assets").mkdir()  # Required for app.mount("/assets", ...)
    (static / "index.html").write_text("<html>spa</html>")
    (static / "app.js").write_text("console.log(1)")
    (tmp_path / "secret.txt").write_text("top-secret")
    monkeypatch.setenv("STATIC_DIR", str(static))
    settings = Settings(table_name="t", yt_api_key="x", collect_enabled=False)
    return create_app(settings, store=object(), yt=object(), llm=object())


def test_spa_serves_real_file_and_fallback(tmp_path, monkeypatch):
    client = TestClient(make_app_with_static(tmp_path, monkeypatch))
    assert client.get("/app.js").text == "console.log(1)"
    assert "spa" in client.get("/no-such-route").text


def test_spa_blocks_path_traversal(tmp_path, monkeypatch):
    client = TestClient(make_app_with_static(tmp_path, monkeypatch))
    res = client.get("/%2e%2e/secret.txt")
    assert "top-secret" not in res.text
    assert "spa" in res.text  # 폴백으로 처리


def test_unknown_api_path_returns_404_not_spa(tmp_path, monkeypatch):
    client = TestClient(make_app_with_static(tmp_path, monkeypatch))
    res = client.get("/api/nonexistent")
    assert res.status_code == 404
    assert res.json() == {"error": "찾을 수 없습니다"}


def test_registered_api_routes_still_match_before_catchall(tmp_path, monkeypatch):
    client = TestClient(make_app_with_static(tmp_path, monkeypatch))
    assert client.get("/api/categories").status_code == 200  # 등록 라우트는 catch-all 이전에 매칭


def test_index_fallback_sets_no_cache(tmp_path, monkeypatch):
    client = TestClient(make_app_with_static(tmp_path, monkeypatch))
    res = client.get("/no-such-route")
    assert res.headers["cache-control"] == "no-cache"
    assert client.get("/app.js").headers.get("cache-control") != "no-cache"
