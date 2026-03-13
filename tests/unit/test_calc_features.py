"""特征工程模块单元测试。"""

import pandas as pd

from scripts.features.calc_features import (
    build_parameter_space,
    compute_feature_frame,
    ema,
    momentum,
    rsi,
    sma,
)


def test_build_parameter_space_contains_required_keys() -> None:
    """参数空间应覆盖核心因子。"""
    space = build_parameter_space()
    assert "ma_window" in space
    assert "rsi_window" in space
    assert "momentum_window" in space


def test_sma_and_ema_outputs_length() -> None:
    """均线输出长度应与输入一致。"""
    series = pd.Series([1, 2, 3, 4, 5, 6])
    assert len(sma(series, 3)) == len(series)
    assert len(ema(series, 3)) == len(series)


def test_rsi_and_momentum_outputs_length() -> None:
    """RSI 与动量输出长度应与输入一致。"""
    series = pd.Series([10, 10.5, 10.2, 11, 11.5, 11.8, 12])
    assert len(rsi(series, 3)) == len(series)
    assert len(momentum(series, 2)) == len(series)


def test_compute_feature_frame_contains_columns() -> None:
    """特征表应包含核心列。"""
    close = pd.Series([1, 2, 3, 4, 5, 6, 7, 8], name="close")
    df = compute_feature_frame(close, ma_windows=(3, 5), rsi_window=3, momentum_window=2)

    assert "close" in df.columns
    assert "sma_3" in df.columns
    assert "ema_5" in df.columns
    assert "rsi_3" in df.columns
    assert "momentum_2" in df.columns
