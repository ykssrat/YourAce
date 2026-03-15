"""回测引擎实现。"""

from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd


def run_backtest(
    price_frame: pd.DataFrame,
    *,
    code_col: str = "code",
    date_col: str = "date",
    close_col: str = "close",
    position_col: str = "position",
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252,
) -> Dict[str, object]:
    """执行回测并返回总体与按代码拆分的绩效指标。"""
    _validate_price_frame(
        price_frame=price_frame,
        code_col=code_col,
        date_col=date_col,
        close_col=close_col,
    )

    frame = price_frame.copy()
    frame[date_col] = pd.to_datetime(frame[date_col], errors="coerce")
    frame = frame.dropna(subset=[date_col, close_col, code_col])
    frame = frame.sort_values(by=[code_col, date_col]).reset_index(drop=True)
    frame["asset_return"] = frame.groupby(code_col)[close_col].pct_change().fillna(0.0)

    if position_col in frame.columns:
        shifted_position = frame.groupby(code_col)[position_col].shift(1).fillna(0.0)
        frame["strategy_return"] = frame["asset_return"] * shifted_position
    else:
        frame["strategy_return"] = frame["asset_return"]

    by_code: Dict[str, Dict[str, float]] = {}
    for code, group in frame.groupby(code_col):
        by_code[str(code)] = calculate_metrics(
            returns=group["strategy_return"],
            risk_free_rate=risk_free_rate,
            periods_per_year=periods_per_year,
        )

    overall_metrics = calculate_metrics(
        returns=frame["strategy_return"],
        risk_free_rate=risk_free_rate,
        periods_per_year=periods_per_year,
    )

    recent_trade_date = frame[date_col].max()
    as_of_date = recent_trade_date.strftime("%Y-%m-%d") if pd.notna(recent_trade_date) else None

    return {
        "as_of_date": as_of_date,
        "metrics": overall_metrics,
        "by_code": by_code,
    }


def calculate_metrics(
    returns: pd.Series,
    *,
    risk_free_rate: float,
    periods_per_year: int,
) -> Dict[str, float]:
    """计算年化收益率、夏普比率、胜率。"""
    if returns.empty:
        return {
            "annual_return": 0.0,
            "sharpe": 0.0,
            "win_rate": 0.0,
        }

    ret = returns.astype(float).replace([np.inf, -np.inf], np.nan).dropna()
    if ret.empty:
        return {
            "annual_return": 0.0,
            "sharpe": 0.0,
            "win_rate": 0.0,
        }

    cumulative = (1.0 + ret).prod()
    periods = len(ret)
    annual_return = cumulative ** (periods_per_year / periods) - 1.0

    daily_rf = risk_free_rate / periods_per_year
    excess = ret - daily_rf
    std = excess.std(ddof=1)
    if std == 0 or np.isnan(std):
        sharpe = 0.0
    else:
        sharpe = np.sqrt(periods_per_year) * excess.mean() / std

    win_rate = float((ret > 0).sum() / periods)
    return {
        "annual_return": round(float(annual_return), 6),
        "sharpe": round(float(sharpe), 6),
        "win_rate": round(win_rate, 6),
    }


def compare_backtest_results(
    before: Dict[str, object],
    after: Dict[str, object],
) -> Dict[str, float]:
    """比较剪枝前后的核心指标变化。"""
    before_metrics = before.get("metrics", {})
    after_metrics = after.get("metrics", {})
    return {
        "annual_return_delta": round(float(after_metrics.get("annual_return", 0.0) - before_metrics.get("annual_return", 0.0)), 6),
        "sharpe_delta": round(float(after_metrics.get("sharpe", 0.0) - before_metrics.get("sharpe", 0.0)), 6),
        "win_rate_delta": round(float(after_metrics.get("win_rate", 0.0) - before_metrics.get("win_rate", 0.0)), 6),
    }


def _validate_price_frame(
    price_frame: pd.DataFrame,
    code_col: str,
    date_col: str,
    close_col: str,
) -> None:
    """校验回测输入数据完整性。"""
    if price_frame.empty:
        raise ValueError("price_frame 不能为空")

    required = {code_col, date_col, close_col}
    missing = required - set(price_frame.columns)
    if missing:
        raise ValueError(f"缺少必需字段: {sorted(missing)}")
