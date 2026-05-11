"""BOLL 策略。"""

from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd


BOLL_WINDOW = 20
BOLL_SHORT_WINDOW = 21
BOLL_MID_WINDOW = 60
BOLL_LONG_WINDOW = 120
BOLL_STD_MULTIPLIER = 2.0


def generate_matrix(close_series: pd.Series, **kwargs) -> Dict[str, str]:
    """返回 BOLL 3x3 看法矩阵。"""
    series = _prepare_close_series(close_series)
    return {
        "short": _boll_opinion(series.tail(BOLL_SHORT_WINDOW), window=BOLL_WINDOW),
        "mid": _boll_opinion(series.tail(BOLL_MID_WINDOW), window=BOLL_WINDOW),
        "long": _boll_opinion(series.tail(BOLL_LONG_WINDOW), window=BOLL_WINDOW),
    }


def generate_signal(close_series: pd.Series) -> str:
    """返回 BOLL 单周期信号。"""
    return _boll_opinion(close_series, window=BOLL_WINDOW)


def _prepare_close_series(close_series: pd.Series) -> pd.Series:
    if close_series is None:
        return pd.Series(dtype=float)

    series = pd.Series(close_series, dtype="float64").dropna()
    if series.empty:
        return pd.Series(dtype=float)
    return series.reset_index(drop=True)


def _calculate_boll_series(close_series: pd.Series, window: int) -> Tuple[pd.Series, pd.Series, pd.Series]:
    middle = close_series.rolling(window=window, min_periods=window).mean()
    deviation = close_series.rolling(window=window, min_periods=window).std(ddof=0).fillna(0.0)
    upper = middle + BOLL_STD_MULTIPLIER * deviation
    lower = middle - BOLL_STD_MULTIPLIER * deviation
    return middle, upper, lower


def _boll_opinion(close_series: pd.Series, window: int = BOLL_WINDOW) -> str:
    series = _prepare_close_series(close_series)
    if len(series) < window + 1:
        return "HOLD"

    middle, upper, lower = _calculate_boll_series(series, window=window)
    if len(middle) < 2:
        return "HOLD"

    previous_close = float(series.iloc[-2])
    current_close = float(series.iloc[-1])
    previous_middle = float(middle.iloc[-2])
    current_middle = float(middle.iloc[-1])
    previous_upper = float(upper.iloc[-2])
    current_upper = float(upper.iloc[-1])
    previous_lower = float(lower.iloc[-2])
    current_lower = float(lower.iloc[-1])

    if current_close <= current_lower:
        return "BUY"
    if current_close >= current_upper:
        return "SELL"
    if previous_close <= previous_middle and current_close > current_middle:
        return "BUY"
    if previous_close >= previous_middle and current_close < current_middle:
        return "SELL"
    if previous_close < previous_lower and current_close > current_lower:
        return "BUY"
    if previous_close > previous_upper and current_close < current_upper:
        return "SELL"
    return "HOLD"
