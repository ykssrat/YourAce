"""三维时间窗信号生成器。"""

from typing import Dict


def generate_multi_horizon_signal() -> Dict[str, str]:
    """输出短中长期离散建议。"""
    return {
        "short": "HOLD",
        "mid": "HOLD",
        "long": "HOLD",
    }
