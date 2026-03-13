"""特征工程与参数空间定义。"""

from __future__ import annotations

from typing import Dict, Iterable, List

import pandas as pd


def build_parameter_space() -> Dict[str, List[float]]:
    """定义待搜索参数空间。"""
    return {
        "ma_window": [5, 10, 20, 30, 60],
        "ema_window": [5, 12, 26, 60],
        "rsi_window": [6, 14, 21],
        "rsi_threshold": [20, 30, 70, 80],
        "momentum_window": [5, 10, 20],
    }


def sma(series: pd.Series, window: int) -> pd.Series:
    """简单移动平均。"""
    _validate_window(window)
    return series.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    """指数移动平均。"""
    _validate_window(window)
    return series.ewm(span=window, adjust=False, min_periods=window).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """相对强弱指标 RSI。"""
    _validate_window(window)

    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def momentum(series: pd.Series, window: int = 10) -> pd.Series:
    """动量因子（相对过去 window 周期涨跌幅）。"""
    _validate_window(window)
    return series.pct_change(periods=window)


def compute_feature_frame(
    close_series: pd.Series,
    ma_windows: Iterable[int] = (5, 10, 20),
    rsi_window: int = 14,
    momentum_window: int = 10,
) -> pd.DataFrame:
    """基于收盘价生成常用因子表。"""
    result = pd.DataFrame({"close": close_series})

    for w in ma_windows:
        result[f"sma_{w}"] = sma(close_series, w)
        result[f"ema_{w}"] = ema(close_series, w)

    result[f"rsi_{rsi_window}"] = rsi(close_series, window=rsi_window)
    result[f"momentum_{momentum_window}"] = momentum(close_series, window=momentum_window)
    return result


def _validate_window(window: int) -> None:
    """校验时间窗口参数合法性。"""
    if window <= 0:
        raise ValueError("window 必须为正整数")
