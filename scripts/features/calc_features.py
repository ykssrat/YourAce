"""特征工程与参数空间定义。"""

from typing import Dict, List


def build_parameter_space() -> Dict[str, List[float]]:
    """定义待搜索参数空间。"""
    return {
        "ma_window": [5, 10, 20, 30, 60],
        "rsi_threshold": [20, 30, 70, 80],
    }
