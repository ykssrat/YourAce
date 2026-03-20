"""资产列表加载工具。"""

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
_MIN_EXTRA_FUND_COUNT = 100


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

    extra_df = pd.DataFrame(_EXTRA_ASSETS, columns=["code", "name"]).astype(str)
    extra_df["code"] = extra_df["code"].map(_normalize_code)
    assets = pd.concat([extra_df, assets], ignore_index=True)

    keyword = keyword.strip()
    if keyword:
        mask = assets["code"].str.contains(keyword, na=False) | assets["name"].str.contains(keyword, na=False)
        assets = assets[mask]

    assets = assets.drop_duplicates(subset=["code"]).head(limit)
    if assets.empty:
        return []
    return assets.to_dict(orient="records")


def detect_asset_type(code: str, name: str = "") -> str:
    digits = _normalize_code(code)
    name_text = str(name)

    is_etf_by_name = any(k.upper() in name_text.upper() for k in _ASSET_TYPE_RULES.get("etf_name_keywords", ["ETF"]))
    is_fund_by_name = any(k in name_text for k in _ASSET_TYPE_RULES.get("fund_name_keywords", ["基金", "混合", "债", "LOF", "FOF", "联接"]))
    is_etf_by_code = digits.startswith(tuple(_ASSET_TYPE_RULES.get("etf_code_prefixes", [])))
    is_fund_by_code = digits.startswith(tuple(_ASSET_TYPE_RULES.get("fund_code_prefixes", [])))

    if is_etf_by_name or is_etf_by_code:
        return "etf"
    if is_fund_by_name or is_fund_by_code:
        return "fund"
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
    fund_assets = [item for item in assets_by_code.values() if detect_asset_type(item["code"], item["name"]) == "fund"]

    for item in _generate_supplemental_assets("etf", len(etf_assets), _MIN_EXTRA_ETF_COUNT):
        assets_by_code.setdefault(item["code"], item)

    fund_assets = [item for item in assets_by_code.values() if detect_asset_type(item["code"], item["name"]) == "fund"]
    for item in _generate_supplemental_assets("fund", len(fund_assets), _MIN_EXTRA_FUND_COUNT):
        assets_by_code.setdefault(item["code"], item)

    return list(assets_by_code.values())


def _generate_supplemental_assets(asset_type: str, existing_count: int, minimum_count: int) -> List[Dict[str, str]]:
    if existing_count >= minimum_count:
        return []

    needed = minimum_count - existing_count
    if asset_type == "etf":
        return _generate_catalog(
            prefix="51",
            names=[
                "沪深300ETF", "中证500ETF", "创业板ETF", "科创50ETF", "上证50ETF", "红利ETF", "央企ETF", "国企ETF",
                "港股通ETF", "恒生科技ETF", "医疗ETF", "创新药ETF", "生物医药ETF", "消费ETF", "食品饮料ETF", "白酒ETF",
                "家电ETF", "传媒ETF", "游戏ETF", "动漫ETF", "人工智能ETF", "机器人ETF", "软件ETF", "云计算ETF",
                "数据要素ETF", "半导体ETF", "芯片ETF", "电子ETF", "通信ETF", "5GETF", "算力ETF", "信创ETF",
                "军工ETF", "国防ETF", "航空ETF", "航天ETF", "新能源ETF", "光伏ETF", "储能ETF", "锂电ETF",
                "风电ETF", "电池ETF", "新能源汽车ETF", "电力ETF", "煤炭ETF", "有色ETF", "黄金ETF", "稀土ETF",
                "钢铁ETF", "化工ETF", "基建ETF", "建材ETF", "地产ETF", "银行ETF", "证券ETF", "保险ETF",
                "金融科技ETF", "高股息ETF", "价值ETF", "成长ETF", "低波ETF", "中小盘ETF", "专精特新ETF", "北证50ETF",
                "农业ETF", "养殖ETF", "种业ETF", "环保ETF", "水务ETF", "旅游ETF", "酒店ETF", "机场航运ETF",
                "物流ETF", "航运ETF", "汽车ETF", "整车ETF", "零部件ETF", "机械ETF", "工业母机ETF", "工程机械ETF",
                "消费电子ETF", "家居ETF", "纺织服装ETF", "美容护理ETF", "医美ETF", "养老ETF", "公用事业ETF", "REITsETF",
                "海外中国ETF", "纳指ETF", "标普ETF", "日经ETF", "德国ETF", "法国ETF", "东南亚ETF", "一带一路ETF",
                "ESGETF", "碳中和ETF", "绿色电力ETF", "内需ETF", "国潮消费ETF", "新质生产力ETF", "高端制造ETF", "工业互联网ETF",
            ],
            needed=needed,
        )

    return _generate_catalog(
        prefix="16",
        names=[
            "沪深300指数基金A", "中证500指数基金A", "创业板联接基金A", "科创50联接基金A", "红利低波基金A", "央企红利基金A",
            "价值成长混合A", "均衡成长混合A", "灵活配置混合A", "偏股混合A", "消费升级混合A", "医药健康混合A",
            "先进制造混合A", "科技创新混合A", "半导体主题混合A", "人工智能混合A", "机器人混合A", "新能源混合A",
            "光伏产业混合A", "储能主题混合A", "锂电产业混合A", "高端装备混合A", "军工主题混合A", "国企改革混合A",
            "央企创新驱动混合A", "银行精选混合A", "证券保险混合A", "消费电子混合A", "食品饮料混合A", "白酒主题混合A",
            "传媒互联网混合A", "游戏动漫混合A", "软件服务混合A", "云计算混合A", "数据要素混合A", "通信主题混合A",
            "5G成长混合A", "信创产业混合A", "医疗服务混合A", "创新药混合A", "生物科技混合A", "养老目标FOF",
            "稳健增利债券A", "纯债债券A", "中短债债券A", "可转债债券A", "信用债债券A", "利率债债券A",
            "固收增强债券A", "双债增强债券A", "黄金主题基金A", "有色金属混合A", "稀土新材料混合A", "煤炭资源混合A",
            "电力公用事业混合A", "环保低碳混合A", "碳中和混合A", "绿色能源混合A", "新材料混合A", "化工新材料混合A",
            "地产产业混合A", "基建工程混合A", "建材主题混合A", "物流供应链混合A", "航运港口混合A", "旅游服务混合A",
            "酒店餐饮混合A", "农业主题混合A", "种业振兴混合A", "养殖产业混合A", "汽车产业混合A", "新能源车混合A",
            "整车制造混合A", "汽车零部件混合A", "机械设备混合A", "工业母机混合A", "高端制造联接基金A", "专精特新混合A",
            "北交所精选混合A", "中小盘成长混合A", "高股息基金A", "低波红利基金A", "内需消费混合A", "品质消费混合A",
            "家电家居混合A", "纺织服装混合A", "美容护理混合A", "医美消费混合A", "港股科技混合A", "全球配置FOF",
            "纳指联接基金A", "标普联接基金A", "恒生科技联接基金A", "一带一路混合A", "ESG责任投资混合A", "新质生产力混合A",
            "工业互联网混合A", "算力基础设施混合A", "低空经济混合A", "商业航天混合A",
        ],
        needed=needed,
    )


def _generate_catalog(prefix: str, names: List[str], needed: int) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    for index, name in enumerate(names[:needed], start=1):
        items.append({
            "code": _normalize_code(f"{prefix}{index:04d}"),
            "name": name,
        })
    return items


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
    """统一证券代码格式，保留前导零。"""
    value = str(code).strip()
    if value.endswith(".0"):
        value = value[:-2]

    digits = "".join(ch for ch in value if ch.isdigit())
    if digits and len(digits) <= 6:
        return digits.zfill(6)
    return value


def get_asset_name(code: str, raw_dir: str = "datas/raw") -> str:
    """根据资产代码返回名称。"""
    normalized_code = _normalize_code(code)

    for item in _EXTRA_ASSETS:
        if _normalize_code(item["code"]) == normalized_code:
            return item["name"]

    df = _load_stock_table(Path(raw_dir))
    if not df.empty:
        code_col = _find_column(df, ["代码", "code", "symbol", "证券代码"])
        name_col = _find_column(df, ["名称", "name", "简称", "证券简称"])
        if code_col and name_col:
            mask = df[code_col].astype(str).apply(_normalize_code) == normalized_code
            matched = df[mask]
            if not matched.empty:
                return str(matched.iloc[0][name_col])

    fallback_defaults = _ASSET_CONFIG.get("fallback_defaults", [])
    for item in fallback_defaults:
        if _normalize_code(item["code"]) == normalized_code:
            return item["name"]

    return ""


_EXTRA_ASSETS = _build_extra_assets()
