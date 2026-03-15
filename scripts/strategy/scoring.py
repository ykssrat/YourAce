"""评分系统与分类器。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


VALID_SIGNALS = {"BUY", "HOLD", "SELL"}
SIGNAL_VALUE_MAP = {
    "BUY": 1.0,
    "HOLD": 0.0,
    "SELL": -1.0,
}


@dataclass
class ScoreResult:
    """评分结果对象。"""

    score: float
    label: str


def aggregate_signal_score(
    horizon_signals: Dict[str, str],
    weights: Dict[str, float] | None = None,
    horizon_strengths: Dict[str, float] | None = None,
) -> ScoreResult:
    """将三维离散信号映射为 0-100 分与离散标签。"""
    _validate_horizon_signals(horizon_signals)

    if weights is None:
        weights = {"short": 0.35, "mid": 0.35, "long": 0.30}

    _validate_weights(weights)

    weighted_sum = 0.0
    if horizon_strengths is None:
        for horizon, signal in horizon_signals.items():
            weighted_sum += weights[horizon] * SIGNAL_VALUE_MAP[signal]
    else:
        _validate_horizon_strengths(horizon_strengths)
        for horizon, signal in horizon_signals.items():
            # 强度方向必须与离散信号一致，避免出现 BUY + 负强度的矛盾输入。
            strength = max(-1.0, min(1.0, float(horizon_strengths[horizon])))
            if signal == "BUY":
                strength = max(0.0, strength)
            elif signal == "SELL":
                strength = min(0.0, strength)
            else:
                strength = 0.0
            weighted_sum += weights[horizon] * strength

    # 线性映射：[-1, 1] -> [0, 100]
    score = (weighted_sum + 1.0) * 50.0
    score = max(0.0, min(100.0, score))
    label = classify_score(score)
    return ScoreResult(score=round(score, 1), label=label)


def classify_score(score: float) -> str:
    """按分段区间输出离散建议。"""
    if score < 0 or score > 100:
        raise ValueError("score 必须在 [0, 100] 区间")

    if score >= 80:
        return "STRONG_BUY"
    if score >= 60:
        return "BUY"
    if score >= 40:
        return "HOLD"
    if score >= 20:
        return "SELL"
    return "STRONG_SELL"


def _validate_horizon_signals(horizon_signals: Dict[str, str]) -> None:
    """校验三维信号格式。"""
    required = {"short", "mid", "long"}
    if set(horizon_signals.keys()) != required:
        raise ValueError("horizon_signals 必须包含 short、mid、long")

    invalid = [s for s in horizon_signals.values() if s not in VALID_SIGNALS]
    if invalid:
        raise ValueError(f"存在非法信号值: {invalid}")


def _validate_weights(weights: Dict[str, float]) -> None:
    """校验权重配置。"""
    required = {"short", "mid", "long"}
    if set(weights.keys()) != required:
        raise ValueError("weights 必须包含 short、mid、long")

    total = sum(weights.values())
    if abs(total - 1.0) > 1e-9:
        raise ValueError("weights 总和必须为 1")

    if any(v < 0 for v in weights.values()):
        raise ValueError("weights 不能为负数")


def _validate_horizon_strengths(horizon_strengths: Dict[str, float]) -> None:
    """校验连续强度格式。"""
    required = {"short", "mid", "long"}
    if set(horizon_strengths.keys()) != required:
        raise ValueError("horizon_strengths 必须包含 short、mid、long")

    if any(not isinstance(v, (int, float)) for v in horizon_strengths.values()):
        raise ValueError("horizon_strengths 必须为数值")
