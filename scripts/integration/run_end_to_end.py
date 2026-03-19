"""端到端联调脚本。"""

from __future__ import annotations

from typing import Dict

from fastapi.testclient import TestClient

from scripts.api.server import app
from scripts.processed.clean_data import clean_all_assets
from scripts.processed.fetch_data import fetch_all_assets


def run_end_to_end(enable_online_fetch: bool = False) -> Dict[str, object]:
    """执行从数据处理到 API 分析的全链路联调。"""
    fetch_result: Dict[str, str] = {}
    fetch_status = "skipped"
    if enable_online_fetch:
        try:
            fetch_result = fetch_all_assets()
            fetch_status = "ok"
        except Exception as exc:  # noqa: BLE001
            fetch_status = f"failed: {exc}"

    clean_result = clean_all_assets()

    client = TestClient(app)

    search_resp = client.get("/search", params={"query": "000001", "limit": 5})
    search_resp.raise_for_status()
    search_payload = search_resp.json()

    analyze_resp = client.post("/analyze", json={"code": "000001", "long_fund_trend": 0.01})
    analyze_resp.raise_for_status()
    analyze_payload = analyze_resp.json()

    return {
        "fetch_status": fetch_status,
        "fetch_files": fetch_result,
        "clean_summary": clean_result,
        "search_count": search_payload.get("count", 0),
        "analyze": {
            "code": analyze_payload.get("code"),
            "label": analyze_payload.get("label"),
            "as_of_date": analyze_payload.get("as_of_date"),
            "news_count": len(analyze_payload.get("latest_news", [])),
        },
    }


if __name__ == "__main__":
    result = run_end_to_end(enable_online_fetch=True)
    print("=== E2E 集成结果 ===")
    print(result)
