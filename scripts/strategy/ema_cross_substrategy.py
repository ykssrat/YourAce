"""
均线交叉子策略实现。
基于快慢均线交叉生成多空信号，风格对齐 Lean EmaCrossAlphaModel。
"""

import pandas as pd
from typing import Dict


def ema_cross_signal(close_series: pd.Series, fast_period: int = 12, slow_period: int = 26) -> str:
    """
    均线交叉信号生成函数。
    :param close_series: 收盘价序列
    :param fast_period: 快线周期
    :param slow_period: 慢线周期
    :return: 'BUY'/'SELL'/'HOLD'
    """
    if len(close_series) < max(fast_period, slow_period) + 1:
        return "HOLD"
    fast_ema = close_series.ewm(span=fast_period, adjust=False).mean()
    slow_ema = close_series.ewm(span=slow_period, adjust=False).mean()
    # 判断交叉点
    if fast_ema.iloc[-2] <= slow_ema.iloc[-2] and fast_ema.iloc[-1] > slow_ema.iloc[-1]:
        return "BUY"
    elif fast_ema.iloc[-2] >= slow_ema.iloc[-2] and fast_ema.iloc[-1] < slow_ema.iloc[-1]:
        return "SELL"
    else:
        return "HOLD"


def generate_matrix(close_series: pd.Series) -> Dict[str, str]:
    """
    生成短期（10日）、中期（30日）、长期（120日）均线交叉看法矩阵。
    :param close_series: 收盘价序列
    :return: dict，包含 short/mid/long 三个周期的'BUY'/'SELL'/'HOLD'信号
    """
    return {
        "short": ema_cross_signal(close_series.tail(10), fast_period=3, slow_period=7),
        "mid": ema_cross_signal(close_series.tail(30), fast_period=7, slow_period=15),
        "long": ema_cross_signal(close_series.tail(120), fast_period=15, slow_period=30),
    }