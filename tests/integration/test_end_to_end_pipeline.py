"""全链路集成测试。"""

from scripts.integration.run_end_to_end import run_end_to_end


def test_end_to_end_pipeline_runs() -> None:
    """从数据处理到分析接口应完整跑通。"""
    result = run_end_to_end()

    assert result["fetch_status"] in {"skipped", "ok"} or str(result["fetch_status"]).startswith("failed:")
    assert "fetch_files" in result
    assert "clean_summary" in result
    assert "analyze" in result

    analyze = result["analyze"]
    assert analyze["code"] == "000001"
    assert analyze["label"] in {"BUY", "HOLD", "SELL"}
    assert isinstance(analyze["news_count"], int)
