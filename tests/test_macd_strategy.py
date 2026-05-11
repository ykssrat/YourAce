"""MACD 策略单元测试。"""

import pandas as pd

from scripts.engine.opinion_engine import generate_opinion_matrix
from scripts.strategy.momentum_deviation_strategy import generate_macd_matrix, generate_macd_signal


def test_generate_macd_signal_detects_golden_cross_on_minute_series() -> None:
    """标准分钟线在最后一根形成金叉时应返回 BUY。"""
    close_series = pd.Series([100.0] * 30 + [120.0])

    assert generate_macd_signal(close_series) == "BUY"


def test_generate_macd_signal_detects_dead_cross_on_minute_series() -> None:
    """标准分钟线在最后一根形成死叉时应返回 SELL。"""
    close_series = pd.Series([100.0] * 30 + [80.0])

    assert generate_macd_signal(close_series) == "SELL"


def test_generate_macd_matrix_returns_expected_three_horizons() -> None:
    """MACD 矩阵应返回 short/mid/long 三个维度。"""
    close_series = pd.Series([100.0] * 240 + [120.0])

    assert generate_macd_matrix(close_series) == {
        "short": "BUY",
        "mid": "BUY",
        "long": "BUY",
    }


def test_opinion_engine_supports_macd_strategy_alias() -> None:
    """引擎应支持 macd 策略名并调用分钟线 MACD 实现。"""
    close_series = pd.Series([100.0] * 240 + [120.0])

    result = generate_opinion_matrix(close_series, strategy_name="MACD")

    assert result == {
        "short": "BUY",
        "mid": "BUY",
        "long": "BUY",
    }
