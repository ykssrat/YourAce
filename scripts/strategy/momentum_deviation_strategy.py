"""动量偏离策略实现。
基于均线、动量和偏离度等启发式规则的 3x3 看法生成。
"""

from typing import Dict
import pandas as pd

MACD_FAST_PERIOD = 12
MACD_SLOW_PERIOD = 26
MACD_SIGNAL_PERIOD = 9
MACD_SHORT_WINDOW = 60
MACD_MID_WINDOW = 120
MACD_LONG_WINDOW = 240


def generate_matrix(close_series: pd.Series, long_fund_trend: float = 0.0) -> Dict[str, str]:
    """生成 3x3 看法矩阵。"""
    return {
        "short": _short_horizon_opinion(close_series),
        "mid": _mid_horizon_opinion(close_series),
        "long": _long_horizon_opinion(close_series, long_fund_trend=long_fund_trend),
    }


def generate_macd_matrix(close_series: pd.Series, **kwargs) -> Dict[str, str]:
    """生成标准分钟线 MACD 的 3x3 看法矩阵。

    这里使用分钟级收盘价序列计算 EMA12、EMA26 和 DEA9，
    并以最近一根分钟线是否形成金叉/死叉作为交易信号。
    """
    minute_series = _prepare_minute_close_series(close_series)
    return {
        "short": _macd_horizon_opinion(minute_series.tail(MACD_SHORT_WINDOW)),
        "mid": _macd_horizon_opinion(minute_series.tail(MACD_MID_WINDOW)),
        "long": _macd_horizon_opinion(minute_series.tail(MACD_LONG_WINDOW)),
    }


def generate_macd_signal(close_series: pd.Series) -> str:
    """生成标准分钟线 MACD 单信号。"""
    return _macd_horizon_opinion(close_series)


def _short_horizon_opinion(close_series: pd.Series) -> str:
    """短期看法：结合 10 日动量和偏离度。"""
    current = float(close_series.iloc[-1])
    rolling_mean = float(close_series.tail(10).mean())
    momentum_10 = _safe_pct_change(close_series, periods=10)
    deviation = (current / rolling_mean - 1.0) if rolling_mean != 0 else 0.0

    signal_value = 0.65 * momentum_10 + 0.35 * deviation
    return _map_signal_value_to_opinion(signal_value, buy_threshold=0.02, sell_threshold=-0.02)


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

    signal_value = 0.7 * trend + 0.3 * zone_bias
    return _map_signal_value_to_opinion(signal_value, buy_threshold=0.015, sell_threshold=-0.015)


def _long_horizon_opinion(close_series: pd.Series, long_fund_trend: float) -> str:
    """长期看法：结合 120 日均线结构和基本面趋势输入。"""
    window = close_series.tail(120)
    latest = float(window.iloc[-1])
    ma30 = float(window.tail(30).mean())
    ma120 = float(window.mean())

    ma_structure = 0.0
    if ma120 != 0:
        ma_structure = (latest / ma120 - 1.0) * 0.5 + (ma30 / ma120 - 1.0) * 0.5

    signal_value = 0.7 * ma_structure + 0.3 * long_fund_trend
    return _map_signal_value_to_opinion(signal_value, buy_threshold=0.01, sell_threshold=-0.01)


def _safe_pct_change(series: pd.Series, periods: int) -> float:
    """返回最后一个涨跌幅。"""
    if len(series) <= periods:
        return 0.0
    value = series.pct_change(periods=periods).iloc[-1]
    if pd.isna(value):
        return 0.0
    return float(value)


def _map_signal_value_to_opinion(signal_value: float, buy_threshold: float, sell_threshold: float) -> str:
    """映射策略信号值为看法。"""
    if signal_value >= buy_threshold:
        return "BUY"
    if signal_value <= sell_threshold:
        return "SELL"
    return "HOLD"


def _prepare_minute_close_series(close_series: pd.Series) -> pd.Series:
    """清洗分钟线收盘价序列。"""
    if close_series is None:
        return pd.Series(dtype=float)

    series = pd.Series(close_series, dtype="float64").dropna()
    if series.empty:
        return pd.Series(dtype=float)
    return series.reset_index(drop=True)


def _calculate_macd_components(
    close_series: pd.Series,
    fast_period: int = MACD_FAST_PERIOD,
    slow_period: int = MACD_SLOW_PERIOD,
    signal_period: int = MACD_SIGNAL_PERIOD,
) -> Dict[str, pd.Series]:
    """计算 MACD 的 DIF、DEA 和柱体值。"""
    ema_fast = close_series.ewm(span=fast_period, adjust=False).mean()
    ema_slow = close_series.ewm(span=slow_period, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal_period, adjust=False).mean()
    macd_histogram = (dif - dea) * 2.0
    return {
        "dif": dif,
        "dea": dea,
        "histogram": macd_histogram,
    }


def _macd_horizon_opinion(
    close_series: pd.Series,
    fast_period: int = MACD_FAST_PERIOD,
    slow_period: int = MACD_SLOW_PERIOD,
    signal_period: int = MACD_SIGNAL_PERIOD,
) -> str:
    """根据标准 MACD 金叉/死叉生成单个周期信号。"""
    series = _prepare_minute_close_series(close_series)
    min_required = max(fast_period, slow_period, signal_period) + 1
    if len(series) < min_required:
        return "HOLD"

    components = _calculate_macd_components(series, fast_period=fast_period, slow_period=slow_period, signal_period=signal_period)
    dif = components["dif"]
    dea = components["dea"]
    histogram = components["histogram"]

    previous_dif = float(dif.iloc[-2])
    previous_dea = float(dea.iloc[-2])
    current_dif = float(dif.iloc[-1])
    current_dea = float(dea.iloc[-1])

    if previous_dif <= previous_dea and current_dif > current_dea:
        return "BUY"
    if previous_dif >= previous_dea and current_dif < current_dea:
        return "SELL"

    current_histogram = float(histogram.iloc[-1])
    if current_dif > current_dea and current_histogram > 0:
        return "BUY"
    if current_dif < current_dea and current_histogram < 0:
        return "SELL"

    return "HOLD"
