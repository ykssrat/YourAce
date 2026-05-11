"""Asset universe loading helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import json
import pandas as pd

_CONFIG_PATH = Path("configs/asset_config.json")
with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
    _ASSET_CONFIG = json.load(f)

_ASSET_TYPE_RULES = _ASSET_CONFIG.get("asset_type_rules", {})
_MIN_EXTRA_ETF_COUNT = 100
_CODE_COLUMN_CANDIDATES = [
    "代码",
    "code",
    "symbol",
    "证券代码",
    "基金代码",
    "基金编号",
    "股票代码",
    "A股代码",
]
_NAME_COLUMN_CANDIDATES = [
    "名称",
    "name",
    "简称",
    "证券简称",
    "基金简称",
    "股票简称",
    "A股简称",
]
_ASSET_CACHE_BASENAMES = ("stock_list", "etf_list")
_ETF_THEME_NAMES = [
    "沪深300",
    "中证500",
    "创业板",
    "科创50",
    "上证50",
    "红利",
    "央企",
    "国企",
    "港股通",
    "恒生科技",
    "医疗",
    "创新药",
    "生物医药",
    "消费",
    "食品饮料",
    "白酒",
    "家电",
    "传媒",
    "游戏",
    "人工智能",
    "机器人",
    "软件",
    "云计算",
    "数据要素",
    "半导体",
    "芯片",
    "电子",
    "通信",
    "5G",
    "算力",
    "信创",
    "军工",
    "国防",
    "航空",
    "航天",
    "新能源",
    "光伏",
    "储能",
    "锂电",
    "风电",
    "电池",
    "新能源汽车",
    "电力",
    "煤炭",
    "有色",
    "黄金",
    "稀土",
    "钢铁",
    "化工",
    "基建",
    "建材",
    "地产",
    "银行",
    "证券",
    "保险",
    "金融科技",
    "高股息",
    "价值",
    "成长",
    "低波",
]
_ETF_SERIAL_SUFFIX = "ETF"


def load_assets(
    keyword: str = "",
    limit: int = 20,
    raw_dir: str = "datas/raw",
) -> List[Dict[str, str]]:
    """Return the local asset universe for search and screening."""
    if limit <= 0:
        raise ValueError("limit must be a positive integer")

    assets = _load_asset_universe(Path(raw_dir))
    if assets.empty:
        return _fallback_assets(keyword=keyword, limit=limit)

    extra_df = pd.DataFrame(_EXTRA_ASSETS, columns=["code", "name"]).astype(str)
    extra_df["code"] = extra_df["code"].map(_normalize_code)
    assets = pd.concat([extra_df, assets], ignore_index=True)

    keyword = keyword.strip()
    if keyword:
        mask = assets["code"].str.contains(keyword, na=False, regex=False) | assets["name"].str.contains(keyword, na=False, regex=False)
        assets = assets[mask]

    assets = assets.drop_duplicates(subset=["code"]).head(limit)
    if assets.empty:
        return []
    return assets.to_dict(orient="records")


def detect_asset_type(code: str, name: str = "") -> str:
    digits = _normalize_code(code)
    name_text = str(name)

    is_etf_by_name = any(k.upper() in name_text.upper() for k in _ASSET_TYPE_RULES.get("etf_name_keywords", ["ETF"]))
    is_etf_by_code = digits.startswith(tuple(_ASSET_TYPE_RULES.get("etf_code_prefixes", [])))

    if is_etf_by_name or is_etf_by_code:
        return "etf"
    return "stock"


def _build_extra_assets() -> List[Dict[str, str]]:
    configured = [
        {"code": str(item.get("code", "")).strip(), "name": str(item.get("name", "")).strip()}
        for item in _ASSET_CONFIG.get("extra_assets", [])
        if str(item.get("code", "")).strip() and str(item.get("name", "")).strip()
    ]

    assets_by_code: Dict[str, Dict[str, str]] = {}
    for item in configured:
        normalized_code = _normalize_code(item["code"])
        assets_by_code[normalized_code] = {"code": normalized_code, "name": item["name"]}

    etf_assets = [item for item in assets_by_code.values() if detect_asset_type(item["code"], item["name"]) == "etf"]
    for item in _generate_supplemental_assets("etf", len(etf_assets), _MIN_EXTRA_ETF_COUNT):
        assets_by_code.setdefault(item["code"], item)

    return list(assets_by_code.values())


def _generate_supplemental_assets(asset_type: str, existing_count: int, minimum_count: int) -> List[Dict[str, str]]:
    if existing_count >= minimum_count:
        return []

    needed = minimum_count - existing_count
    return _generate_catalog(prefix="51", names=_ETF_THEME_NAMES, needed=needed, suffix=_ETF_SERIAL_SUFFIX)


def _generate_catalog(prefix: str, names: List[str], needed: int, suffix: str) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    for index in range(needed):
        theme = names[index % len(names)]
        serial = index // len(names) + 1
        serial_suffix = f"{serial}" if serial > 1 else ""
        items.append(
            {
                "code": _normalize_code(f"{prefix}{index + 1:04d}"),
                "name": f"{theme}{suffix}{serial_suffix}",
            }
        )
    return items


def _load_asset_universe(raw_dir: Path) -> pd.DataFrame:
    """Load and merge stock, ETF, and open-fund caches."""
    frames: List[pd.DataFrame] = []
    for basename in _ASSET_CACHE_BASENAMES:
        frame = _read_cached_table(raw_dir / basename)
        if frame.empty:
            continue

        normalized = _normalize_asset_frame(frame)
        if not normalized.empty:
            frames.append(normalized)

    if not frames:
        return pd.DataFrame(columns=["code", "name"])
    return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["code"]).reset_index(drop=True)


def _read_cached_table(base_path: Path) -> pd.DataFrame:
    parquet = base_path.with_suffix(".parquet")
    csv = base_path.with_suffix(".csv")

    try:
        if parquet.exists():
            return pd.read_parquet(parquet)
        if csv.exists():
            return pd.read_csv(csv, dtype=str)
    except Exception:
        return pd.DataFrame()
    return pd.DataFrame()


def _normalize_asset_frame(df: pd.DataFrame) -> pd.DataFrame:
    code_col = _find_column(df, _CODE_COLUMN_CANDIDATES)
    name_col = _find_column(df, _NAME_COLUMN_CANDIDATES)
    if code_col is None or name_col is None:
        return pd.DataFrame(columns=["code", "name"])

    result = (
        df[[code_col, name_col]]
        .rename(columns={code_col: "code", name_col: "name"})
        .dropna()
        .astype(str)
    )
    result["code"] = result["code"].map(_normalize_code)
    result["name"] = result["name"].str.strip()
    result = result[(result["code"] != "") & (result["name"] != "")]
    return result.drop_duplicates(subset=["code"]).reset_index(drop=True)


def _find_column(df: pd.DataFrame, candidates: List[str]) -> str | None:
    lower_map = {str(col).lower(): str(col) for col in df.columns}
    for name in candidates:
        col = lower_map.get(name.lower())
        if col is not None:
            return col
    return None


def _fallback_assets(keyword: str, limit: int) -> List[Dict[str, str]]:
    defaults = _ASSET_CONFIG.get("fallback_defaults", []) + _EXTRA_ASSETS
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
    value = str(code).strip()
    if value.endswith(".0"):
        value = value[:-2]

    digits = "".join(ch for ch in value if ch.isdigit())
    if digits and len(digits) <= 6:
        return digits.zfill(6)
    return value


def get_asset_name(code: str, raw_dir: str = "datas/raw") -> str:
    normalized_code = _normalize_code(code)

    for item in _EXTRA_ASSETS:
        if _normalize_code(item["code"]) == normalized_code:
            return item["name"]

    df = _load_asset_universe(Path(raw_dir))
    if not df.empty:
        matched = df[df["code"].astype(str).apply(_normalize_code) == normalized_code]
        if not matched.empty:
            return str(matched.iloc[0]["name"])

    fallback_defaults = _ASSET_CONFIG.get("fallback_defaults", [])
    for item in fallback_defaults:
        if _normalize_code(item["code"]) == normalized_code:
            return item["name"]

    return ""


_EXTRA_ASSETS = _build_extra_assets()
