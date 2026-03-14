"""生成本地股票池缓存（stock_list）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Optional

import akshare as ak
import pandas as pd

# 允许脚本直接运行时导入仓库内模块。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.processed.fetch_data import load_storage_config


def build_stock_list(config_path: str = "configs/data_config.yaml") -> str:
    """拉取 A 股股票列表并写入 datas/raw/stock_list。"""
    config = load_storage_config(Path(config_path))
    raw_dir = config.raw_data_dir
    raw_dir.mkdir(parents=True, exist_ok=True)

    df = _fetch_stock_universe()
    normalized = _normalize_stock_table(df)

    base_path = raw_dir / "stock_list"
    if config.file_format == "parquet":
        try:
            target = base_path.with_suffix(".parquet")
            normalized.to_parquet(target, index=False)
            return str(target)
        except Exception:  # noqa: BLE001
            target = base_path.with_suffix(".csv")
            normalized.to_csv(target, index=False, encoding="utf-8-sig")
            return str(target)

    target = base_path.with_suffix(".csv")
    normalized.to_csv(target, index=False, encoding="utf-8-sig")
    return str(target)


def _fetch_stock_universe() -> pd.DataFrame:
    """按候选接口顺序拉取股票列表。"""
    candidates = [
        "stock_info_a_code_name",  # 更偏静态的代码清单接口，稳定性更高
        "stock_zh_a_spot_em",
        "stock_zh_a_spot",
    ]
    last_error: Optional[Exception] = None

    for name in candidates:
        fn: Optional[Callable[[], pd.DataFrame]] = getattr(ak, name, None)
        if fn is None:
            continue
        try:
            df = fn()
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    if last_error is not None:
        raise RuntimeError(f"拉取股票列表失败: {last_error}") from last_error
    raise RuntimeError("未找到可用股票列表接口，请检查 akshare 版本")


def _normalize_stock_table(df: pd.DataFrame) -> pd.DataFrame:
    """统一列名为 code/name，便于后续筛选使用。"""
    code_col = _find_column(df, ["代码", "code", "symbol", "证券代码", "A股代码"])
    name_col = _find_column(df, ["名称", "name", "简称", "证券简称", "A股简称"])
    if code_col is None or name_col is None:
        raise RuntimeError("股票列表字段不完整，缺少代码或名称列")

    result = (
        df[[code_col, name_col]]
        .rename(columns={code_col: "code", name_col: "name"})
        .dropna()
        .astype(str)
    )
    result["code"] = result["code"].map(_normalize_code)
    result["name"] = result["name"].str.strip()
    result = result[result["code"] != ""]
    result = result.drop_duplicates(subset=["code"]).reset_index(drop=True)
    if result.empty:
        raise RuntimeError("标准化后股票列表为空")
    return result


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """从候选字段中匹配实际列名。"""
    lower_map = {str(col).lower(): str(col) for col in df.columns}
    for name in candidates:
        col = lower_map.get(name.lower())
        if col is not None:
            return col
    return None


def _normalize_code(code: str) -> str:
    """统一证券代码格式，保留前导零。"""
    value = str(code).strip()
    if value.endswith(".0"):
        value = value[:-2]
    digits = "".join(ch for ch in value if ch.isdigit())
    if digits and len(digits) <= 6:
        return digits.zfill(6)
    return value


if __name__ == "__main__":
    output = build_stock_list()
    print(f"stock_list written: {output}")
