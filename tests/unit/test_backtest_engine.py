"""回测引擎单元测试。"""

import pandas as pd
import pytest

from scripts.backtest.lightweight.engine import compare_backtest_results, run_backtest


def test_run_backtest_returns_core_metrics_and_as_of_date() -> None:
    """回测应返回三项核心指标及最新交易日。"""
    data = pd.DataFrame(
        {
            "code": ["000001"] * 5,
            "date": pd.date_range("2026-01-01", periods=5, freq="D"),
            "close": [10.0, 10.2, 10.1, 10.4, 10.5],
            "position": [1, 1, 1, 1, 1],
        }
    )

    result = run_backtest(data)
    assert result["as_of_date"] == "2026-01-05"
    assert set(result["metrics"].keys()) == {"annual_return", "sharpe", "win_rate"}


def test_run_backtest_splits_by_code() -> None:
    """结果应按代码拆分，便于定位标的表现。"""
    data = pd.DataFrame(
        {
            "code": ["000001", "000001", "000002", "000002"],
            "date": ["2026-01-01", "2026-01-02", "2026-01-01", "2026-01-02"],
            "close": [10.0, 10.5, 20.0, 19.8],
            "position": [1, 1, 1, 1],
        }
    )

    result = run_backtest(data)
    assert "000001" in result["by_code"]
    assert "000002" in result["by_code"]


def test_compare_backtest_results_outputs_delta() -> None:
    """应正确输出剪枝前后指标差异。"""
    before = {"metrics": {"annual_return": 0.1, "sharpe": 0.5, "win_rate": 0.4}}
    after = {"metrics": {"annual_return": 0.15, "sharpe": 0.8, "win_rate": 0.45}}

    diff = compare_backtest_results(before, after)
    assert diff["annual_return_delta"] == 0.05
    assert diff["sharpe_delta"] == 0.3
    assert diff["win_rate_delta"] == 0.05


def test_run_backtest_with_missing_columns_raises() -> None:
    """缺失必需字段时应抛出异常。"""
    bad = pd.DataFrame({"date": ["2026-01-01"], "close": [10.0]})
    with pytest.raises(ValueError):
        run_backtest(bad)
