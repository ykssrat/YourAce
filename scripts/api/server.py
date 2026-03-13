"""YourAce 后端 API 服务。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from scripts.features.bic_pruner import bic_prune_features
from scripts.features.calc_features import compute_feature_frame
from scripts.strategy.scoring import aggregate_signal_score
from scripts.strategy.signal_generator import generate_multi_horizon_signal
from scripts.utils.asset_loader import load_assets
from scripts.utils.news_fetcher import fetch_latest_news


app = FastAPI(title="YourAce API", version="0.1.0")


class AnalyzeRequest(BaseModel):
    """分析请求体。"""

    code: str = Field(..., min_length=1, max_length=20)
    long_fund_trend: float = Field(default=0.0, ge=-1.0, le=1.0)


@app.get("/search")
def search_assets(
    query: str = Query(default="", max_length=50),
    limit: int = Query(default=20, ge=1, le=200),
) -> Dict[str, object]:
    """股票/ETF 检索接口。"""
    assets = load_assets(keyword=query, limit=limit)
    return {"query": query, "count": len(assets), "items": assets}


@app.post("/analyze")
def analyze_asset(payload: AnalyzeRequest) -> Dict[str, object]:
    """触发本地分析并返回评分结果。"""
    code = payload.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="code 不能为空")

    close_series = _load_close_series(code)
    if close_series.empty:
        raise HTTPException(status_code=404, detail=f"未找到标的 {code} 的行情数据")

    horizon_signals = generate_multi_horizon_signal(
        close_series=close_series,
        long_fund_trend=payload.long_fund_trend,
    )
    score_result = aggregate_signal_score(horizon_signals)

    selected_features = _run_bic_pruning(close_series)
    latest_news = fetch_latest_news(code, limit=3)
    return {
        "code": code,
        "as_of_date": datetime.now().strftime("%Y-%m-%d"),
        "score": score_result.score,
        "label": score_result.label,
        "horizon_signals": horizon_signals,
        "selected_features": selected_features,
        "latest_news": latest_news,
    }


@app.get("/news")
def get_latest_news(
    code: str = Query(..., min_length=1, max_length=20),
    limit: int = Query(default=3, ge=1, le=10),
) -> Dict[str, object]:
    """返回指定标的最新资讯。"""
    items = fetch_latest_news(code=code, limit=limit)
    return {
        "code": code,
        "count": len(items),
        "items": items,
    }


@app.get("/health")
def health() -> Dict[str, str]:
    """健康检查。"""
    return {"status": "ok"}


def _run_bic_pruning(close_series: pd.Series) -> List[str]:
    """执行 BIC 特征剪枝，失败时返回空列表。"""
    feature_frame = compute_feature_frame(close_series)
    target = close_series.pct_change().shift(-1)

    features = feature_frame.drop(columns=["close"], errors="ignore")
    if features.empty:
        return []

    try:
        result = bic_prune_features(features, target)
        return result.selected_features
    except Exception:
        return []


def _load_close_series(code: str, raw_dir: str = "datas/raw") -> pd.Series:
    """优先读取本地缓存行情，缺失时生成可复现实验序列。"""
    directory = Path(raw_dir)
    candidates = [
        directory / f"kline_{code}.parquet",
        directory / f"kline_{code}.csv",
    ]

    for file_path in candidates:
        if not file_path.exists():
            continue

        if file_path.suffix == ".parquet":
            df = pd.read_parquet(file_path)
        else:
            df = pd.read_csv(file_path)

        close_col = _find_close_column(df)
        if close_col is None:
            continue

        series = pd.to_numeric(df[close_col], errors="coerce").dropna()
        if len(series) >= 30:
            return series.reset_index(drop=True)

    return _generate_mock_close_series(code)


def _find_close_column(df: pd.DataFrame) -> str | None:
    """查找收盘价字段名。"""
    candidates = ["close", "收盘", "收盘价"]
    lower_map = {str(col).lower(): str(col) for col in df.columns}
    for name in candidates:
        col = lower_map.get(name.lower())
        if col is not None:
            return col
    return None


def _generate_mock_close_series(code: str) -> pd.Series:
    """生成确定性模拟行情，保证离线可测。"""
    seed = sum(ord(ch) for ch in code)
    rng = np.random.default_rng(seed)
    steps = rng.normal(loc=0.0008, scale=0.012, size=180)
    prices = 100 * np.cumprod(1 + steps)
    return pd.Series(prices)
