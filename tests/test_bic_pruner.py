"""BIC 剪枝模块单元测试。"""

import numpy as np
import pandas as pd
import pytest

from scripts.features.bic_pruner import bic_prune_features


def test_bic_prune_selects_signal_feature() -> None:
    """应保留与目标强相关的特征。"""
    rng = np.random.default_rng(7)
    x1 = pd.Series(rng.normal(size=300), name="x1")
    x2 = pd.Series(rng.normal(size=300), name="x2")
    noise = rng.normal(scale=0.1, size=300)

    y = 2.5 * x1 + noise
    features = pd.DataFrame({"x1": x1, "x2": x2})

    result = bic_prune_features(features, pd.Series(y, name="target"))
    assert "x1" in result.selected_features


def test_bic_prune_with_missing_feature_raises() -> None:
    """候选特征不存在时应抛出异常。"""
    x = pd.DataFrame({"x1": [1.0, 2.0, 3.0]})
    y = pd.Series([1.0, 2.0, 3.0])

    with pytest.raises(ValueError):
        bic_prune_features(x, y, candidate_features=["x1", "x_missing"])


def test_bic_prune_with_empty_data_raises() -> None:
    """空输入应抛出异常。"""
    with pytest.raises(ValueError):
        bic_prune_features(pd.DataFrame(), pd.Series(dtype=float))
