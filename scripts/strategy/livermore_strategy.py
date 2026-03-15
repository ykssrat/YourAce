"""Livermore 策略。"""

from dataclasses import dataclass
from typing import Dict
import pandas as pd


@dataclass
class LivermoreConfig:
    """策略配置。"""

    max_positions: int = 5


def generate_signal() -> str:
    """返回策略信号。"""
    return "HOLD"


def generate_matrix(close_series: pd.Series, **kwargs) -> Dict[str, str]:
    """返回 Livermore 看法矩阵（目前为占位）。"""
    # 这里未来可以接入具体的利弗莫尔突破/关键点逻辑
    return {
        "short": "HOLD",
        "mid": "HOLD",
        "long": "HOLD",
    }
