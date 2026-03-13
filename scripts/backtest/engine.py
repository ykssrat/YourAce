"""回测引擎骨架。"""

from typing import Dict


def run_backtest() -> Dict[str, float]:
    """返回回测核心指标占位值。"""
    return {
        "annual_return": 0.0,
        "sharpe": 0.0,
        "win_rate": 0.0,
    }
