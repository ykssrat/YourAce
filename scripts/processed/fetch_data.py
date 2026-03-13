"""数据获取模块入口。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, Optional

import akshare as ak
import pandas as pd
import yaml


@dataclass
class StorageConfig:
    """数据存储配置。"""

    raw_data_dir: Path
    file_format: str


def load_storage_config(config_path: Path) -> StorageConfig:
    """读取数据配置文件。"""
    with config_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    storage = cfg.get("storage", {})
    raw_data_dir = Path(storage.get("raw_data_dir", "datas/raw"))
    file_format = str(storage.get("format", "parquet")).lower()
    return StorageConfig(raw_data_dir=raw_data_dir, file_format=file_format)


def _call_first_available(candidates: Iterable[str]) -> pd.DataFrame:
    """按候选函数名顺序调用 akshare 接口。"""
    last_error: Optional[Exception] = None
    for fn_name in candidates:
        fn: Optional[Callable[[], pd.DataFrame]] = getattr(ak, fn_name, None)
        if fn is None:
            continue
        try:
            df = fn()
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    if last_error is not None:
        raise RuntimeError(f"akshare 接口调用失败: {last_error}") from last_error
    raise RuntimeError("未找到可用的 akshare 接口，请检查 akshare 版本")


def _read_existing(path: Path) -> pd.DataFrame:
    """读取已有缓存文件。"""
    if not path.exists():
        return pd.DataFrame()
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _write_dataframe(df: pd.DataFrame, path: Path, preferred_format: str) -> Path:
    """写入数据，优先 parquet，失败时回退到 csv。"""
    path.parent.mkdir(parents=True, exist_ok=True)

    if preferred_format == "parquet":
        try:
            parquet_path = path.with_suffix(".parquet")
            df.to_parquet(parquet_path, index=False)
            return parquet_path
        except Exception:  # noqa: BLE001
            csv_path = path.with_suffix(".csv")
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            return csv_path

    csv_path = path.with_suffix(".csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    return csv_path


def _merge_incremental(old_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    """执行幂等增量合并，避免重复记录。"""
    if old_df.empty:
        return new_df.drop_duplicates().reset_index(drop=True)
    merged = pd.concat([old_df, new_df], ignore_index=True)
    return merged.drop_duplicates().reset_index(drop=True)


def _fetch_sources() -> Dict[str, pd.DataFrame]:
    """拉取股票、ETF、开放式基金数据源。"""
    return {
        "stock_list": _call_first_available(["stock_zh_a_spot_em", "stock_zh_a_spot"]),
        "etf_list": _call_first_available(["fund_etf_spot_em", "fund_etf_spot_sina"]),
        "open_fund_nav": _call_first_available(["fund_open_fund_daily_em", "fund_open_fund_info_em"]),
    }


def fetch_all_assets(config_path: str = "configs/data_config.yaml") -> Dict[str, str]:
    """拉取股票、ETF、开放式基金基础数据并写入缓存。"""
    config = load_storage_config(Path(config_path))
    written_files: Dict[str, str] = {}

    for name, new_df in _fetch_sources().items():
        base_path = config.raw_data_dir / name

        old_df = pd.DataFrame()
        if (base_path.with_suffix(".parquet")).exists():
            old_df = _read_existing(base_path.with_suffix(".parquet"))
        elif (base_path.with_suffix(".csv")).exists():
            old_df = _read_existing(base_path.with_suffix(".csv"))

        merged = _merge_incremental(old_df=old_df, new_df=new_df)
        written_path = _write_dataframe(merged, base_path, config.file_format)
        written_files[name] = str(written_path)

    return written_files


if __name__ == "__main__":
    result = fetch_all_assets()
    for source, file_path in result.items():
        print(f"{source}: {file_path}")
