"""基于 BIC 的参数剪枝算法。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

import pandas as pd
import statsmodels.api as sm


@dataclass
class BICPruneResult:
    """BIC 剪枝输出结果。"""

    selected_features: List[str]
    best_bic: float
    history: List[Dict[str, float | str]]


def bic_prune_features(
    feature_frame: pd.DataFrame,
    target_series: pd.Series,
    candidate_features: Sequence[str] | None = None,
) -> BICPruneResult:
    """基于前向搜索执行 BIC 剪枝。

    规则：仅当新增特征使 BIC 下降时保留，否则剔除。
    """
    if feature_frame.empty:
        raise ValueError("feature_frame 不能为空")
    if target_series.empty:
        raise ValueError("target_series 不能为空")

    if candidate_features is None:
        candidate_features = list(feature_frame.columns)

    _validate_feature_names(feature_frame, candidate_features)

    dataset = feature_frame.loc[:, list(candidate_features)].copy()
    dataset["target"] = target_series
    dataset = dataset.dropna(axis=0, how="any")
    if dataset.empty:
        raise ValueError("特征与目标对齐后无有效样本")

    y = dataset["target"]

    selected: List[str] = []
    remaining = list(candidate_features)
    history: List[Dict[str, float | str]] = []

    current_bic = _fit_bic(y=y, x_df=pd.DataFrame(index=y.index))

    while remaining:
        best_feature = ""
        best_bic = current_bic

        for feature in remaining:
            trial = selected + [feature]
            trial_bic = _fit_bic(y=y, x_df=dataset[trial])
            if trial_bic < best_bic:
                best_bic = trial_bic
                best_feature = feature

        if not best_feature:
            break

        selected.append(best_feature)
        remaining.remove(best_feature)
        history.append(
            {
                "feature": best_feature,
                "bic_before": float(current_bic),
                "bic_after": float(best_bic),
            }
        )
        current_bic = best_bic

    return BICPruneResult(
        selected_features=selected,
        best_bic=float(current_bic),
        history=history,
    )


def _fit_bic(y: pd.Series, x_df: pd.DataFrame) -> float:
    """拟合 OLS 并返回 BIC。"""
    x = sm.add_constant(x_df, has_constant="add")
    model = sm.OLS(y, x)
    result = model.fit()
    return float(result.bic)


def _validate_feature_names(
    feature_frame: pd.DataFrame,
    candidate_features: Sequence[str],
) -> None:
    """校验候选特征是否都存在。"""
    missing = [name for name in candidate_features if name not in feature_frame.columns]
    if missing:
        raise ValueError(f"候选特征不存在: {missing}")
