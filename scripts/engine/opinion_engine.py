"""动态共识看法 (Dynamic Consensus Opinion) 引擎框架。
作为调度器，将请求分发给具体的策略实现。
"""

from __future__ import annotations
import importlib
from typing import Dict, List
import pandas as pd

VALID_HORIZONS = ["short", "mid", "long"]
VALID_OPINIONS = ["BUY", "HOLD", "SELL"]


def generate_opinion_matrix(
    close_series: pd.Series,
    strategy_name: str = "default",
    long_fund_trend: float = 0.0,
) -> Dict[str, str]:
    """
    通用引擎接口：根据策略名称调度具体算法。
    
    Args:
        close_series: 行情序列
        strategy_name: 策略标识，对应 scripts/strategy/ 下的文件名（如 "default", "livermore"）
        long_fund_trend: 基本面趋势输入（由外部传入）
        
    Returns:
        3x3 看法矩阵
    """
    _validate_close_series(close_series)

    # 动态加载策略模块
    try:
        # 兼容性处理：如果传入的是中文显示名，映射回文件名
        strategy_id = _map_strategy_label_to_id(strategy_name)
        module_path = f"scripts.strategy.{strategy_id}_strategy"
        
        # 尝试加载模块
        module = importlib.import_module(module_path)
        
        if not hasattr(module, "generate_matrix"):
            raise AttributeError(f"策略模块 {module_path} 缺失 generate_matrix 函数")
            
        return module.generate_matrix(close_series, long_fund_trend=long_fund_trend)
        
    except (ImportError, AttributeError) as e:
        # 如果策略未找到或加载失败，且不是默认策略，则抛出异常或回退
        if strategy_name != "default":
            raise ValueError(f"策略 '{strategy_name}' 加载失败: {str(e)}")
            
        # 兜底：如果默认策略加载也失败（不应该发生），手动定义一个简单逻辑
        return {h: "HOLD" for h in VALID_HORIZONS}


def _map_strategy_label_to_id(label: str) -> str:
    """内部映射：将 UI 标签或 ID 统一为策略文件后缀。"""
    mapping = {
        "默认": "default",
        "default": "default",
        "livermore": "livermore",
        "利弗莫尔策略": "livermore",
    }
    return mapping.get(label, label)


def _validate_close_series(close_series: pd.Series) -> None:
    """校验价格序列输入。"""
    if close_series.empty:
        raise ValueError("close_series 不能为空")
    if close_series.isna().all():
        raise ValueError("close_series 不能全为空值")
    if len(close_series) < 30:
        raise ValueError("close_series 长度至少为 30")
