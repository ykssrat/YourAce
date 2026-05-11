"""RSI、KDJ、BOLL 策略单元测试。"""

from __future__ import annotations

import pandas as pd

from scripts.engine.opinion_engine import generate_opinion_matrix
from scripts.strategy.boll_strategy import generate_matrix as generate_boll_matrix, generate_signal as generate_boll_signal
from scripts.strategy.kdj_strategy import generate_matrix as generate_kdj_matrix, generate_signal as generate_kdj_signal
from scripts.strategy.rsi_strategy import generate_matrix as generate_rsi_matrix, generate_signal as generate_rsi_signal


def test_rsi_strategy_supports_buy_and_sell() -> None:
    """RSI 策略在超卖和超买场景下应给出买卖信号。"""
    buy_series = pd.Series([120.0 - float(index) for index in range(60)])
    sell_series = pd.Series([60.0 + float(index) for index in range(60)])

    assert generate_rsi_signal(buy_series) == "BUY"
    assert generate_rsi_signal(sell_series) == "SELL"
    assert generate_rsi_matrix(buy_series) == {"short": "BUY", "mid": "BUY", "long": "BUY"}
    assert generate_opinion_matrix(buy_series, strategy_name="RSI") == {"short": "BUY", "mid": "BUY", "long": "BUY"}


def test_kdj_strategy_supports_buy_and_sell() -> None:
    """KDJ 策略在低位和高位时应给出买卖信号。"""
    buy_series = pd.Series([120.0 - float(index) for index in range(60)])
    sell_series = pd.Series([60.0 + float(index) for index in range(60)])

    assert generate_kdj_signal(buy_series) == "BUY"
    assert generate_kdj_signal(sell_series) == "SELL"
    assert generate_kdj_matrix(buy_series) == {"short": "BUY", "mid": "BUY", "long": "BUY"}
    assert generate_opinion_matrix(buy_series, strategy_name="KDJ") == {"short": "BUY", "mid": "BUY", "long": "BUY"}


def test_boll_strategy_supports_buy_and_sell() -> None:
    """BOLL 策略在跌破下轨和突破上轨时应给出买卖信号。"""
    buy_series = pd.Series([100.0] * 40 + [80.0])
    sell_series = pd.Series([100.0] * 40 + [120.0])

    assert generate_boll_signal(buy_series) == "BUY"
    assert generate_boll_signal(sell_series) == "SELL"
    assert generate_boll_matrix(buy_series) == {"short": "BUY", "mid": "BUY", "long": "BUY"}
    assert generate_opinion_matrix(buy_series, strategy_name="BOLL") == {"short": "BUY", "mid": "BUY", "long": "BUY"}
