"""资产列表加载工具。"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd


def load_assets(
    keyword: str = "",
    limit: int = 20,
    raw_dir: str = "datas/raw",
) -> List[Dict[str, str]]:
    """返回待检索资产列表。"""
    if limit <= 0:
        raise ValueError("limit 必须为正整数")

    df = _load_stock_table(Path(raw_dir))
    if df.empty:
        return _fallback_assets(keyword=keyword, limit=limit)

    code_col = _find_column(df, ["代码", "code", "symbol", "证券代码"])
    name_col = _find_column(df, ["名称", "name", "简称", "证券简称"])
    if code_col is None or name_col is None:
        return _fallback_assets(keyword=keyword, limit=limit)

    assets = (
        df[[code_col, name_col]]
        .rename(columns={code_col: "code", name_col: "name"})
        .dropna()
        .astype(str)
    )
    assets["code"] = assets["code"].map(_normalize_code)

    keyword = keyword.strip()
    if keyword:
        mask = assets["code"].str.contains(keyword, na=False) | assets["name"].str.contains(keyword, na=False)
        assets = assets[mask]

    assets = assets.drop_duplicates(subset=["code"]).head(limit)
    if assets.empty:
        return []
    return assets.to_dict(orient="records")


def _load_stock_table(raw_dir: Path) -> pd.DataFrame:
    """读取股票列表缓存。"""
    parquet = raw_dir / "stock_list.parquet"
    csv = raw_dir / "stock_list.csv"

    if parquet.exists():
        return pd.read_parquet(parquet)
    if csv.exists():
        return pd.read_csv(csv, dtype=str)
    return pd.DataFrame()


def _find_column(df: pd.DataFrame, candidates: List[str]) -> str | None:
    """根据候选名称查找列。"""
    lower_map = {str(col).lower(): str(col) for col in df.columns}
    for name in candidates:
        col = lower_map.get(name.lower())
        if col is not None:
            return col
    return None


def _fallback_assets(keyword: str, limit: int) -> List[Dict[str, str]]:
    """无缓存时提供兜底资产列表。"""
    defaults = [
        {"code": "000001", "name": "平安银行"},
        {"code": "600519", "name": "贵州茅台"},
        {"code": "510300", "name": "沪深300ETF"},
        {"code": "159915", "name": "创业板ETF"},
    ]
    keyword = keyword.strip()
    if not keyword:
        return defaults[:limit]

    filtered = [
        item
        for item in defaults
        if keyword in item["code"] or keyword in item["name"]
    ]
    return filtered[:limit]


def _normalize_code(code: str) -> str:
    """统一证券代码格式，保留前导零。"""
    value = str(code).strip()
    if value.endswith(".0"):
        value = value[:-2]

    digits = "".join(ch for ch in value if ch.isdigit())
    if digits and len(digits) <= 6:
        return digits.zfill(6)
    return value
