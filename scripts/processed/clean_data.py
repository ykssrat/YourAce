"""数据清洗模块入口。"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import yaml


def _load_raw_dir(config_path: Path) -> Path:
    """读取原始数据目录配置。"""
    with config_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    raw_dir = cfg.get("storage", {}).get("raw_data_dir", "datas/raw")
    return Path(raw_dir)


def _read_table(file_path: Path) -> pd.DataFrame:
    """根据扩展名读取表格文件。"""
    if file_path.suffix == ".parquet":
        return pd.read_parquet(file_path)
    return pd.read_csv(file_path)


def _write_table(df: pd.DataFrame, file_path: Path) -> None:
    """按原格式回写清洗后的数据。"""
    if file_path.suffix == ".parquet":
        df.to_parquet(file_path, index=False)
        return
    df.to_csv(file_path, index=False, encoding="utf-8-sig")


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """统一列名风格为小写下划线。"""
    renamed = {
        col: str(col).strip().lower().replace(" ", "_")
        for col in df.columns
    }
    return df.rename(columns=renamed)


def _find_date_column(df: pd.DataFrame) -> Optional[str]:
    """尝试识别时间列。"""
    candidates = ["date", "trade_date", "日期", "净值日期", "时间"]
    for col in df.columns:
        if str(col).lower() in {c.lower() for c in candidates}:
            return col
    return None


def clean_all_assets(config_path: str = "configs/data_config.yaml") -> Dict[str, int]:
    """统一时间序列并清洗重复记录。"""
    raw_dir = _load_raw_dir(Path(config_path))
    if not raw_dir.exists():
        return {}

    cleaned_rows: Dict[str, int] = {}
    for file_path in raw_dir.glob("*"):
        if file_path.suffix not in {".parquet", ".csv"}:
            continue

        df = _read_table(file_path)
        if df.empty:
            cleaned_rows[file_path.name] = 0
            continue

        df = _normalize_columns(df)
        date_col = _find_date_column(df)
        if date_col is not None:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df = df.dropna(subset=[date_col]).sort_values(by=date_col)

        df = df.drop_duplicates().reset_index(drop=True)
        _write_table(df, file_path)
        cleaned_rows[file_path.name] = len(df)

    return cleaned_rows


if __name__ == "__main__":
    result = clean_all_assets()
    for file_name, rows in result.items():
        print(f"{file_name}: {rows}")
