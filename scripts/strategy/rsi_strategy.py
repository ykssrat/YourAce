"""RSI 策略。"""

from __future__ import annotations

from typing import Dict

import pandas as pd


RSI_WINDOW = 14
RSI_SHORT_WINDOW = 15
RSI_MID_WINDOW = 21
RSI_LONG_WINDOW = 30
RSI_BUY_THRESHOLD = 30.0
RSI_SELL_THRESHOLD = 70.0


def generate_matrix(close_series: pd.Series, **kwargs) -> Dict[str, str]:
    """返回 RSI 3x3 看法矩阵。"""
    series = _prepare_close_series(close_series)
    return {
        "short": _rsi_opinion(series.tail(RSI_SHORT_WINDOW), window=RSI_WINDOW),
        "mid": _rsi_opinion(series.tail(RSI_MID_WINDOW), window=RSI_WINDOW),
        "long": _rsi_opinion(series.tail(RSI_LONG_WINDOW), window=RSI_WINDOW),
    }


def generate_signal(close_series: pd.Series) -> str:
    """返回 RSI 单周期信号。"""
    return _rsi_opinion(close_series, window=RSI_WINDOW)


def _prepare_close_series(close_series: pd.Series) -> pd.Series:
    if close_series is None:
        return pd.Series(dtype=float)

    series = pd.Series(close_series, dtype="float64").dropna()
    if series.empty:
        return pd.Series(dtype=float)
    return series.reset_index(drop=True)


def _calculate_rsi_series(close_series: pd.Series, window: int) -> pd.Series:
    delta = close_series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()

    rsi = pd.Series(index=close_series.index, dtype="float64")
    neutral_mask = (avg_gain == 0) & (avg_loss == 0)
    buy_mask = (avg_gain > 0) & (avg_loss == 0)
    sell_mask = (avg_gain == 0) & (avg_loss > 0)
    ratio_mask = ~(neutral_mask | buy_mask | sell_mask)

    if ratio_mask.any():
        rs = avg_gain[ratio_mask] / avg_loss[ratio_mask].replace(0, pd.NA)
        rsi.loc[ratio_mask] = 100 - (100 / (1 + rs))
    rsi.loc[buy_mask] = 100.0
    rsi.loc[sell_mask] = 0.0
    rsi.loc[neutral_mask] = 50.0
    return rsi


def _rsi_opinion(close_series: pd.Series, window: int = RSI_WINDOW) -> str:
    series = _prepare_close_series(close_series)
    if len(series) < window + 1:
        return "HOLD"

    rsi_series = _calculate_rsi_series(series, window=window).dropna()
    if len(rsi_series) == 0:
        return "HOLD"

    current_rsi = float(rsi_series.iloc[-1])
    previous_rsi = float(rsi_series.iloc[-2]) if len(rsi_series) >= 2 else current_rsi

    if current_rsi <= RSI_BUY_THRESHOLD:
        return "BUY"
    if current_rsi >= RSI_SELL_THRESHOLD:
        return "SELL"
    if current_rsi < 45.0 and current_rsi >= previous_rsi:
        return "BUY"
    if current_rsi > 55.0 and current_rsi <= previous_rsi:
        return "SELL"
    return "HOLD"
