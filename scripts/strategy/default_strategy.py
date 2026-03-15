"""默认策略实现。
基于均线、动量和偏离度等启发式规则的 3x3 看法生成。
"""

from typing import Dict
import pandas as pd


def generate_matrix(close_series: pd.Series, long_fund_trend: float = 0.0) -> Dict[str, str]:
    """生成 3x3 看法矩阵。"""
    return {
        "short": _short_horizon_opinion(close_series),
        "mid": _mid_horizon_opinion(close_series),
        "long": _long_horizon_opinion(close_series, long_fund_trend=long_fund_trend),
    }


def _short_horizon_opinion(close_series: pd.Series) -> str:
    """短期看法：结合 10 日动量和偏离度。"""
    current = float(close_series.iloc[-1])
    rolling_mean = float(close_series.tail(10).mean())
    momentum_10 = _safe_pct_change(close_series, periods=10)
    deviation = (current / rolling_mean - 1.0) if rolling_mean != 0 else 0.0

    score = 0.65 * momentum_10 + 0.35 * deviation
    return _map_score_to_opinion(score, buy_threshold=0.02, sell_threshold=-0.02)


def _mid_horizon_opinion(close_series: pd.Series) -> str:
    """中期看法：结合 30 日趋势、支撑和压力区。"""
    window = close_series.tail(30)
    ma10 = float(window.tail(10).mean())
    ma30 = float(window.mean())
    trend = (ma10 / ma30 - 1.0) if ma30 != 0 else 0.0

    latest = float(window.iloc[-1])
    support = float(window.min())
    resistance = float(window.max())
    band = resistance - support
    position = ((latest - support) / band) if band > 0 else 0.5
    zone_bias = 0.5 - position

    score = 0.7 * trend + 0.3 * zone_bias
    return _map_score_to_opinion(score, buy_threshold=0.015, sell_threshold=-0.015)


def _long_horizon_opinion(close_series: pd.Series, long_fund_trend: float) -> str:
    """长期看法：结合 120 日均线结构和基本面趋势输入。"""
    window = close_series.tail(120)
    latest = float(window.iloc[-1])
    ma30 = float(window.tail(30).mean())
    ma120 = float(window.mean())

    ma_structure = 0.0
    if ma120 != 0:
        ma_structure = (latest / ma120 - 1.0) * 0.5 + (ma30 / ma120 - 1.0) * 0.5

    score = 0.7 * ma_structure + 0.3 * long_fund_trend
    return _map_score_to_opinion(score, buy_threshold=0.01, sell_threshold=-0.01)


def _safe_pct_change(series: pd.Series, periods: int) -> float:
    """返回最后一个涨跌幅。"""
    if len(series) <= periods:
        return 0.0
    value = series.pct_change(periods=periods).iloc[-1]
    if pd.isna(value):
        return 0.0
    return float(value)


def _map_score_to_opinion(score: float, buy_threshold: float, sell_threshold: float) -> str:
    """映射分值为看法。"""
    if score >= buy_threshold:
        return "BUY"
    if score <= sell_threshold:
        return "SELL"
    return "HOLD"
