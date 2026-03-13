"""后端 API 集成测试。"""

from fastapi.testclient import TestClient

from scripts.api.server import app


client = TestClient(app)


def test_search_endpoint_returns_items() -> None:
    """search 接口应返回检索列表。"""
    response = client.get("/search", params={"query": "平安", "limit": 10})
    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert isinstance(payload["items"], list)


def test_analyze_endpoint_returns_score_and_signals() -> None:
    """analyze 接口应返回分数、标签与三维信号。"""
    response = client.post("/analyze", json={"code": "000001", "long_fund_trend": 0.02})
    assert response.status_code == 200

    payload = response.json()
    assert "score" in payload
    assert "label" in payload
    assert set(payload["horizon_signals"].keys()) == {"short", "mid", "long"}


def test_health_endpoint_ok() -> None:
    """健康检查接口应返回 ok。"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
