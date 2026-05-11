"""KDJ 策略。"""

from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd


KDJ_WINDOW = 9
KDJ_SHORT_WINDOW = 10
KDJ_MID_WINDOW = 18
KDJ_LONG_WINDOW = 27


def generate_matrix(close_series: pd.Series, **kwargs) -> Dict[str, str]:
    """返回 KDJ 3x3 看法矩阵。"""
    series = _prepare_close_series(close_series)
    return {
        "short": _kdj_opinion(series.tail(KDJ_SHORT_WINDOW), window=KDJ_WINDOW),
        "mid": _kdj_opinion(series.tail(KDJ_MID_WINDOW), window=KDJ_WINDOW),
        "long": _kdj_opinion(series.tail(KDJ_LONG_WINDOW), window=KDJ_WINDOW),
    }


def generate_signal(close_series: pd.Series) -> str:
    """返回 KDJ 单周期信号。"""
    return _kdj_opinion(close_series, window=KDJ_WINDOW)


def _prepare_close_series(close_series: pd.Series) -> pd.Series:
    if close_series is None:
        return pd.Series(dtype=float)

    series = pd.Series(close_series, dtype="float64").dropna()
    if series.empty:
        return pd.Series(dtype=float)
    return series.reset_index(drop=True)


def _calculate_kdj_series(close_series: pd.Series, window: int) -> Tuple[pd.Series, pd.Series, pd.Series]:
    lowest_low = close_series.rolling(window=window, min_periods=window).min()
    highest_high = close_series.rolling(window=window, min_periods=window).max()
    spread = (highest_high - lowest_low).replace(0, pd.NA)
    rsv = ((close_series - lowest_low) / spread) * 100
    rsv = rsv.fillna(50.0).clip(lower=0.0, upper=100.0)

    k_values = []
    d_values = []
    k_previous = 50.0
    d_previous = 50.0
    for value in rsv:
        k_current = (2.0 / 3.0) * k_previous + (1.0 / 3.0) * float(value)
        d_current = (2.0 / 3.0) * d_previous + (1.0 / 3.0) * k_current
        k_values.append(k_current)
        d_values.append(d_current)
        k_previous = k_current
        d_previous = d_current

    k_series = pd.Series(k_values, index=close_series.index, dtype="float64")
    d_series = pd.Series(d_values, index=close_series.index, dtype="float64")
    j_series = 3.0 * k_series - 2.0 * d_series
    return k_series, d_series, j_series


def _kdj_opinion(close_series: pd.Series, window: int = KDJ_WINDOW) -> str:
    series = _prepare_close_series(close_series)
    if len(series) < window + 1:
        return "HOLD"

    k_series, d_series, j_series = _calculate_kdj_series(series, window=window)
    if len(k_series) < 2:
        return "HOLD"

    previous_k = float(k_series.iloc[-2])
    previous_d = float(d_series.iloc[-2])
    current_k = float(k_series.iloc[-1])
    current_d = float(d_series.iloc[-1])
    current_j = float(j_series.iloc[-1])

    if current_j <= 20.0:
        return "BUY"
    if current_j >= 80.0:
        return "SELL"
    if previous_k <= previous_d and current_k > current_d:
        return "BUY"
    if previous_k >= previous_d and current_k < current_d:
        return "SELL"
    if current_k > current_d and current_j < 50.0:
        return "BUY"
    if current_k < current_d and current_j > 50.0:
        return "SELL"
    return "HOLD"
