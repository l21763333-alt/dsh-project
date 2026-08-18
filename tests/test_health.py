"""健康检查接口测试。"""
from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_docs_available(client: TestClient) -> None:
    """Swagger 文档可访问（团队联调入口）。"""
    resp = client.get("/api/docs")
    assert resp.status_code == 200
