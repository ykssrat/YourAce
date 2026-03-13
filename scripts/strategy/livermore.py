"""Livermore 策略骨架。"""

from dataclasses import dataclass


@dataclass
class LivermoreConfig:
    """策略配置。"""

    max_positions: int = 5


def generate_signal() -> str:
    """返回策略信号。"""
    return "HOLD"
