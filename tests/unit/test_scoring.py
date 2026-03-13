"""评分系统与分类器单元测试。"""

import pytest

from scripts.strategy.scoring import aggregate_signal_score, classify_score


def test_classify_score_boundaries() -> None:
    """分段边界应符合设计区间。"""
    assert classify_score(80) == "STRONG_BUY"
    assert classify_score(60) == "BUY"
    assert classify_score(40) == "HOLD"
    assert classify_score(20) == "SELL"
    assert classify_score(0) == "STRONG_SELL"


def test_aggregate_signal_score_all_buy() -> None:
    """全 BUY 时分值应接近 100。"""
    result = aggregate_signal_score({"short": "BUY", "mid": "BUY", "long": "BUY"})
    assert result.score == 100.0
    assert result.label == "STRONG_BUY"


def test_aggregate_signal_score_all_sell() -> None:
    """全 SELL 时分值应接近 0。"""
    result = aggregate_signal_score({"short": "SELL", "mid": "SELL", "long": "SELL"})
    assert result.score == 0.0
    assert result.label == "STRONG_SELL"


def test_aggregate_signal_score_invalid_signal_raises() -> None:
    """非法信号值应抛出异常。"""
    with pytest.raises(ValueError):
        aggregate_signal_score({"short": "UP", "mid": "BUY", "long": "SELL"})


def test_aggregate_signal_score_invalid_weight_raises() -> None:
    """权重和不为 1 时应抛出异常。"""
    with pytest.raises(ValueError):
        aggregate_signal_score(
            {"short": "BUY", "mid": "HOLD", "long": "SELL"},
            weights={"short": 0.5, "mid": 0.5, "long": 0.5},
        )
