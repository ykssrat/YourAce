"""YourAce 后端 API 服务。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from collections import deque
from typing import Dict, List

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from scripts.features.bic_pruner import bic_prune_features
from scripts.features.calc_features import compute_feature_frame
from scripts.engine.opinion_engine import generate_opinion_matrix, VALID_OPINIONS
from scripts.utils.asset_loader import load_assets, get_asset_name
from scripts.utils.news_fetcher import fetch_latest_news
import json

_CONFIG_PATH = Path("configs/asset_config.json")
with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
    _ASSET_CONFIG = json.load(f)



app = FastAPI(title="YourAce API", version="0.1.6")
_SCREEN_EVENT_LOG_PATH = Path("datas/logs/screen_events.jsonl")

# 合法枚举值，用于请求校验
_VALID_HORIZONS = {"short", "mid", "long"}
_VALID_SCORE_OPERATORS = {"gte", "lte"}
_VALID_OPINIONS = {"BUY", "HOLD", "SELL", ""}
_VALID_ASSET_TYPES = {"stock", "etf", "fund"}

# 兼容前端“不限”筛选
_VALID_HORIZONS_WITH_ALL = _VALID_HORIZONS | {""}
_VALID_ASSET_TYPES_WITH_ALL = _VALID_ASSET_TYPES | {""}


class AnalyzeRequest(BaseModel):
    """分析请求体。"""

    code: str = Field(..., min_length=1, max_length=20)
    strategy: str = Field(default="momentum_deviation")
    long_fund_trend: float = Field(default=0.0, ge=-1.0, le=1.0)
    include_news: bool = Field(default=True)


class ScreenRequest(BaseModel):
    """选股请求体。"""

    asset_type: str = Field(default="")
    horizon: str = Field(default="")
    strategy: str = Field(default="momentum_deviation")
    opinion: str = Field(default="")
    round_size: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class DiagnoseRequest(BaseModel):
    """诊股请求体。"""

    code: str = Field(..., min_length=1, max_length=20)
    strategy: str = Field(default="momentum_deviation")
    include_news: bool = Field(default=True)


class ScreenActionLogRequest(BaseModel):
    asset_type: str = Field(default="")
    horizon: str = Field(default="")
    opinion: str = Field(default="")
    strategy: str = Field(default="momentum_deviation")
    round_size: int = Field(default=0, ge=0, le=500)
    offset: int = Field(default=0, ge=0)
    result_count: int = Field(default=0, ge=0)
    total_available: int = Field(default=0, ge=0)
    scanned_count: int = Field(default=0, ge=0)
    signal_miss_count: int = Field(default=0, ge=0)


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

    matrix = generate_opinion_matrix(
        close_series=close_series,
        strategy_name=payload.strategy,
        long_fund_trend=payload.long_fund_trend,
    )

    selected_features = _run_bic_pruning(close_series)
    latest_news = fetch_latest_news(code, limit=3) if payload.include_news else []
    asset_name = get_asset_name(code)
    
    # 总体标签取中位看法或统一简化
    overall_label = matrix["mid"]

    return {
        "code": code,
        "name": asset_name,
        "as_of_date": datetime.now().strftime("%Y-%m-%d"),
        "label": overall_label,
        "horizon_signals": matrix,
        "matrix": matrix,
        "selected_features": selected_features,
        "news_enabled": payload.include_news,
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


@app.post("/screen")
def screen_assets(payload: ScreenRequest) -> Dict[str, object]:
    """批量筛选资产，返回当前分页内符合条件的标的。"""
    if payload.horizon not in _VALID_HORIZONS_WITH_ALL:
        raise HTTPException(status_code=400, detail=f"horizon 非法，合法值: {_VALID_HORIZONS_WITH_ALL}")
    if payload.opinion not in _VALID_OPINIONS:
        raise HTTPException(status_code=400, detail=f"opinion 非法，合法值: {_VALID_OPINIONS}")
    if payload.asset_type not in _VALID_ASSET_TYPES_WITH_ALL:
        raise HTTPException(status_code=400, detail=f"asset_type 非法，合法值: {_VALID_ASSET_TYPES_WITH_ALL}")

    strategy_name = payload.strategy

    all_assets = load_assets(keyword="", limit=10000)
    if payload.asset_type:
        all_assets = [
            asset
            for asset in all_assets
            if _match_asset_type(str(asset.get("code", "")), payload.asset_type, str(asset.get("name", "")))
        ]
    all_assets = _rebalance_assets_for_screen(all_assets)
    total = len(all_assets)

    start = payload.offset
    end = start + payload.round_size
    batch = all_assets[start:end]

    items: List[Dict[str, object]] = []
    signal_miss_count = 0

    for asset in batch:
        code = str(asset["code"])
        name = str(asset.get("name", ""))

        close_series = _load_close_series(code)
        matrix = generate_opinion_matrix(close_series, strategy_name=strategy_name)

        # 看法过滤
        if payload.opinion:
            if payload.horizon:
                matched = matrix[payload.horizon] == payload.opinion
            else:
                matched = any(v == payload.opinion for v in matrix.values())
            
            if not matched:
                signal_miss_count += 1
                continue

        items.append({
            "code": code,
            "name": name,
            "label": matrix["mid"],
            "horizon_signals": matrix,
            "matrix": matrix,
        })

    return {
        "items": items,
        "scanned_count": len(batch),
        "offset": start,
        "has_more": end < total,
        "total_available": total,
        "signal_miss_count": signal_miss_count,
    }


@app.post("/screen/log")
def log_screen_action(payload: ScreenActionLogRequest) -> Dict[str, object]:
    """记录一次选股行为，供远程服务端留存分析。"""
    event = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "asset_type": payload.asset_type,
        "horizon": payload.horizon,
        "opinion": payload.opinion,
        "strategy": payload.strategy,
        "round_size": payload.round_size,
        "offset": payload.offset,
        "result_count": payload.result_count,
        "total_available": payload.total_available,
        "scanned_count": payload.scanned_count,
        "signal_miss_count": payload.signal_miss_count,
    }
    _append_screen_log(event)
    return {"status": "ok"}


@app.post("/diagnose")
def diagnose_asset(payload: DiagnoseRequest) -> Dict[str, object]:
    """诊断指定标的，返回含 3x3 看法矩阵的详细分析结果。"""
    code = payload.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="code 不能为空")

    close_series = _load_close_series(code)
    if close_series.empty:
        raise HTTPException(status_code=404, detail=f"未找到标的 {code} 的行情数据")

    matrix = generate_opinion_matrix(close_series, strategy_name=payload.strategy)

    selected_features = _run_bic_pruning(close_series)
    latest_news = fetch_latest_news(code, limit=3) if payload.include_news else []
    asset_name = get_asset_name(code)

    return {
        "code": code,
        "name": asset_name,
        "as_of_date": datetime.now().strftime("%Y-%m-%d"),
        "label": matrix["mid"],
        "horizon_signals": matrix,
        "matrix": matrix,
        "selected_features": selected_features,
        "news_enabled": payload.include_news,
        "latest_news": latest_news,
    }


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


def _match_asset_type(code: str, asset_type: str, name: str = "") -> bool:
    """根据代码前缀粗分产品类型。"""
    digits = "".join(ch for ch in str(code) if ch.isdigit())
    if len(digits) < 6:
        return False

    name_text = str(name)
    rules = _ASSET_CONFIG.get("asset_type_rules", {})
    
    is_etf_by_name = any(k in name_text.upper() for k in rules.get("etf_name_keywords", ["ETF"]))
    is_fund_by_name = any(k in name_text for k in rules.get("fund_name_keywords", ["基金", "混合", "债", "LOF", "FOF", "联接"]))
    
    is_etf_by_code = digits.startswith(tuple(rules.get("etf_code_prefixes", [])))
    is_fund_by_code = digits.startswith(tuple(rules.get("fund_code_prefixes", [])))
    
    is_etf = is_etf_by_name or is_etf_by_code
    is_fund = is_fund_by_name or is_fund_by_code

    if asset_type == "stock":
        stock_prefixes = tuple(rules.get("stock_code_prefixes", []))
        return (not is_etf) and (not is_fund) and (digits.startswith(stock_prefixes) if stock_prefixes else True)
    if asset_type == "etf":
        return is_etf
    if asset_type == "fund":
        return is_fund and (not is_etf)
    return True


def _rebalance_assets_for_screen(assets: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """通过轻量聚类对候选重排，提升前缀与行业关键词分布均匀性。"""
    if len(assets) <= 16:
        return assets

    labels = _cluster_assets(assets)
    buckets: Dict[int, deque] = {}
    for asset, label in zip(assets, labels):
        buckets.setdefault(int(label), deque()).append(asset)

    # 轮询抽样：避免单一簇连续出现
    cluster_order = sorted(buckets.keys(), key=lambda k: len(buckets[k]), reverse=True)
    result: List[Dict[str, str]] = []
    while any(buckets[k] for k in cluster_order):
        for k in cluster_order:
            if buckets[k]:
                result.append(buckets[k].popleft())
    return result


def _cluster_assets(assets: List[Dict[str, str]]) -> np.ndarray:
    """基于代码前缀+名称关键词进行轻量 KMeans 聚类。"""
    feats = np.array([_asset_feature_vector(a) for a in assets], dtype=float)
    n = len(feats)
    if n == 0:
        return np.array([], dtype=int)

    # 按样本数自适应簇数，避免过拟合
    k = min(12, max(4, n // 120), n)
    if k == n:
        return np.arange(n, dtype=int)

    # 标准化
    mean = feats.mean(axis=0, keepdims=True)
    std = feats.std(axis=0, keepdims=True)
    std[std == 0] = 1.0
    x = (feats - mean) / std

    init_idx = np.linspace(0, n - 1, num=k, dtype=int)
    centers = x[init_idx].copy()
    labels = np.zeros(n, dtype=int)

    for _ in range(15):
        d2 = ((x[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        new_labels = d2.argmin(axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels

        for ci in range(k):
            members = x[labels == ci]
            if len(members) == 0:
                # 空簇重置到当前最离散点
                farthest = d2.min(axis=1).argmax()
                centers[ci] = x[farthest]
            else:
                centers[ci] = members.mean(axis=0)

    return labels


def _asset_feature_vector(asset: Dict[str, str]) -> List[float]:
    """构造聚类特征：代码前缀、行业关键词、代码区段。"""
    code = str(asset.get("code", ""))
    name = str(asset.get("name", ""))
    digits = "".join(ch for ch in code if ch.isdigit()).zfill(6)

    prefix_map = {"0": 0.0, "3": 1.0, "6": 2.0, "5": 3.0, "1": 4.0, "9": 5.0}
    prefix_feature = prefix_map.get(digits[:1], 6.0)
    board_feature = float(int(digits[:3])) / 999.0
    industry_feature = float(_infer_industry_group(name))
    hash_feature = float(sum(ord(ch) for ch in name) % 97) / 97.0

    return [prefix_feature, industry_feature, board_feature, hash_feature]


def _infer_industry_group(name: str) -> int:
    """基于名称关键词推断行业组（无行业字段时的近似做法）。"""
    text = str(name)
    industry_groups = _ASSET_CONFIG.get("industry_groups", [])
    
    for group in industry_groups:
        if any(word in text for word in group.get("keywords", [])):
            return group.get("id", 10)
    return 10


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


def _append_screen_log(event: Dict[str, object]) -> None:
    _SCREEN_EVENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _SCREEN_EVENT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
