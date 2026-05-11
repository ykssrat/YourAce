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
    strategy_name: str = "momentum_deviation",
    long_fund_trend: float = 0.0,
) -> Dict[str, str]:
    """
    通用引擎接口：根据策略名称调度具体算法。
    
    Args:
        close_series: 行情序列
        strategy_name: 策略标识，对应 scripts/strategy/ 下的文件名（如 "momentum_deviation", "livermore"）
        long_fund_trend: 基本面趋势输入（由外部传入）
        
    Returns:
        3x3 看法矩阵
    """
    _validate_close_series(close_series)

    # 动态加载策略模块
    try:
        # 兼容性处理：如果传入的是中文显示名，映射回文件名
        strategy_id = _map_strategy_label_to_id(strategy_name)

        if strategy_id == "macd":
            module = importlib.import_module("scripts.strategy.momentum_deviation_strategy")
            if not hasattr(module, "generate_macd_matrix"):
                raise AttributeError("策略模块 scripts.strategy.momentum_deviation_strategy 缺失 generate_macd_matrix 函数")
            return module.generate_macd_matrix(close_series, long_fund_trend=long_fund_trend)

        module_path = f"scripts.strategy.{strategy_id}_strategy"
        
        # 尝试加载模块
        module = importlib.import_module(module_path)
        
        if not hasattr(module, "generate_matrix"):
            raise AttributeError(f"策略模块 {module_path} 缺失 generate_matrix 函数")
            
        return module.generate_matrix(close_series, long_fund_trend=long_fund_trend)
        
    except (ImportError, AttributeError) as e:
        # 如果策略未找到或加载失败，且不是默认策略，则抛出异常或回退
        if strategy_name != "momentum_deviation":
            raise ValueError(f"策略 '{strategy_name}' 加载失败: {str(e)}")
            
        # 兜底：如果默认策略加载也失败（不应该发生），手动定义一个简单逻辑
        return {h: "HOLD" for h in VALID_HORIZONS}


def _map_strategy_label_to_id(label: str) -> str:
    """内部映射：将 UI 标签或 ID 统一为策略文件后缀。"""
    mapping = {
        "动量偏离策略": "momentum_deviation",
        "momentum_deviation": "momentum_deviation",
        "RSI": "rsi",
        "rsi": "rsi",
        "RSI策略": "rsi",
        "KDJ": "kdj",
        "kdj": "kdj",
        "KDJ策略": "kdj",
        "macd": "macd",
        "MACD": "macd",
        "MACD策略": "macd",
        "分钟线MACD": "macd",
        "分钟线macd": "macd",
        "BOLL": "boll",
        "boll": "boll",
        "BOLL策略": "boll",
        "布林": "boll",
        "布林带策略": "boll",
        "livermore": "livermore",
        "利弗莫尔策略": "livermore",
    }
    return mapping.get(label, label)


def generate_consensus_matrix(
    close_series: pd.Series,
    long_fund_trend: float = 0.0,
) -> Dict[str, Dict[str, object]]:
    """融合动量偏离、RSI、KDJ、BOLL、MACD 五大策略，生成统一共识矩阵。

    每个窗口期返回：
    - buy: 看多策略数
    - sell: 看空策略数
    - hold: 静默策略数
    - total: 总策略数
    - consensus: 多数意见 (BUY/HOLD/SELL)
    - signals: 各策略的具体信号
    """
    strategies = {
        "动量偏离": "momentum_deviation",
        "RSI": "rsi",
        "KDJ": "kdj",
        "BOLL": "boll",
        "MACD": "macd",
    }

    horizon_votes: Dict[str, Dict[str, int]] = {"short": {"BUY": 0, "SELL": 0, "HOLD": 0},
                                                  "mid": {"BUY": 0, "SELL": 0, "HOLD": 0},
                                                  "long": {"BUY": 0, "SELL": 0, "HOLD": 0}}
    horizon_signals: Dict[str, Dict[str, str]] = {"short": {}, "mid": {}, "long": {}}

    for label, strategy_id in strategies.items():
        try:
            matrix = generate_opinion_matrix(close_series, strategy_name=strategy_id, long_fund_trend=long_fund_trend)
            for horizon in VALID_HORIZONS:
                opinion = matrix.get(horizon, "HOLD")
                horizon_votes[horizon][opinion] += 1
                horizon_signals[horizon][label] = opinion
        except Exception:
            for horizon in VALID_HORIZONS:
                horizon_signals[horizon][label] = "N/A"

    result: Dict[str, Dict[str, object]] = {}
    for horizon in VALID_HORIZONS:
        votes = horizon_votes[horizon]
        total = sum(votes.values())
        if votes["BUY"] > votes["SELL"] and votes["BUY"] > votes["HOLD"]:
            consensus = "BUY"
        elif votes["SELL"] > votes["BUY"] and votes["SELL"] > votes["HOLD"]:
            consensus = "SELL"
        else:
            consensus = "HOLD"
        result[horizon] = {
            "buy": votes["BUY"],
            "sell": votes["SELL"],
            "hold": votes["HOLD"],
            "total": total,
            "consensus": consensus,
            "signals": horizon_signals[horizon],
        }

    return result


_HORIZON_DAYS: Dict[str, str] = {
    "short": "5日",
    "mid": "20日",
    "long": "60日",
}


def get_horizon_label(horizon: str) -> str:
    """返回窗口期对应的交易日标签。"""
    return _HORIZON_DAYS.get(horizon, horizon)


def _validate_close_series(close_series: pd.Series) -> None:
    """校验价格序列输入。"""
    if close_series.empty:
        raise ValueError("close_series 不能为空")
    if close_series.isna().all():
        raise ValueError("close_series 不能全为空值")
    if len(close_series) < 30:
        raise ValueError("close_series 长度至少为 30")
