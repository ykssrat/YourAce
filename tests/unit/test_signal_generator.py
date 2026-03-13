"""三维时间窗信号生成器单元测试。"""

import numpy as np
import pandas as pd
import pytest

from scripts.strategy.signal_generator import generate_multi_horizon_signal


def test_generate_multi_horizon_signal_returns_expected_keys() -> None:
    """输出应包含短中长期三个维度。"""
    close = pd.Series(np.linspace(10, 20, 130))
    result = generate_multi_horizon_signal(close, long_fund_trend=0.02)

    assert set(result.keys()) == {"short", "mid", "long"}


def test_generate_multi_horizon_signal_labels_are_valid() -> None:
    """输出标签应在允许集合中。"""
    close = pd.Series(np.linspace(20, 10, 130))
    result = generate_multi_horizon_signal(close, long_fund_trend=-0.01)

    for label in result.values():
        assert label in {"BUY", "HOLD", "SELL"}


def test_generate_multi_horizon_signal_with_short_series_raises() -> None:
    """样本过短时应抛出异常。"""
    close = pd.Series([10.0, 10.2, 10.1])
    with pytest.raises(ValueError):
        generate_multi_horizon_signal(close)
