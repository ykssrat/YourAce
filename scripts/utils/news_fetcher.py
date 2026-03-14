"""新闻抓取工具。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime
from typing import Callable, Dict, Iterable, List, Optional

import akshare as ak
import pandas as pd


def fetch_latest_news(code: str, limit: int = 3, timeout_seconds: float = 2.5) -> List[Dict[str, str]]:
    """抓取指定标的的最新新闻，失败时返回兜底数据。"""
    clean_code = code.strip()
    if not clean_code:
        raise ValueError("code 不能为空")
    if limit <= 0:
        raise ValueError("limit 必须为正整数")

    try:
        raw_df = _call_news_source(clean_code, timeout_seconds=timeout_seconds)
        normalized = _normalize_news_frame(raw_df)
        if normalized.empty:
            return _fallback_news(clean_code, limit)
        return normalized.head(limit).to_dict(orient="records")
    except Exception:
        return _fallback_news(clean_code, limit)


def _call_news_source(code: str, timeout_seconds: float) -> pd.DataFrame:
    """按候选接口顺序拉取新闻。"""
    sources: Iterable[Callable[[], pd.DataFrame]] = [
        lambda: ak.stock_news_em(symbol=code),
        lambda: ak.stock_news_main_cx(),
    ]

    last_error: Optional[Exception] = None
    for fn in sources:
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(fn)
                df = future.result(timeout=timeout_seconds)
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
        except TimeoutError as exc:
            last_error = RuntimeError("新闻接口超时")
            _ = exc
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    if last_error is not None:
        raise RuntimeError(f"新闻接口调用失败: {last_error}") from last_error
    raise RuntimeError("未获得可用新闻数据")


def _normalize_news_frame(df: pd.DataFrame) -> pd.DataFrame:
    """统一新闻字段。"""
    title_col = _find_col(df, ["新闻标题", "标题", "title"])
    source_col = _find_col(df, ["文章来源", "来源", "source"])
    time_col = _find_col(df, ["发布时间", "时间", "date"])
    url_col = _find_col(df, ["新闻链接", "链接", "url"])

    if title_col is None:
        return pd.DataFrame(columns=["title", "source", "time", "url"])

    normalized = pd.DataFrame()
    normalized["title"] = df[title_col].astype(str)
    normalized["source"] = df[source_col].astype(str) if source_col else "未知来源"

    if time_col:
        dt = pd.to_datetime(df[time_col], errors="coerce")
        normalized["time"] = dt.dt.strftime("%Y-%m-%d %H:%M").fillna("")
    else:
        normalized["time"] = ""

    normalized["url"] = df[url_col].astype(str) if url_col else ""
    normalized = normalized.dropna(subset=["title"]).drop_duplicates(subset=["title"])
    normalized = normalized[normalized["title"].str.len() > 0]
    return normalized.reset_index(drop=True)


def _find_col(df: pd.DataFrame, candidates: List[str]) -> str | None:
    """从 DataFrame 里查找字段名。"""
    lower_map = {str(col).lower(): str(col) for col in df.columns}
    for name in candidates:
        col = lower_map.get(name.lower())
        if col is not None:
            return col
    return None


def _fallback_news(code: str, limit: int) -> List[Dict[str, str]]:
    """无外部数据时的离线兜底新闻。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    items = [
        {
            "title": f"{code} 行情观察：短期波动加大，关注量价配合",
            "source": "YourAce 本地资讯",
            "time": now,
            "url": "",
        },
        {
            "title": f"{code} 行业跟踪：资金风格切换带来估值分化",
            "source": "YourAce 本地资讯",
            "time": now,
            "url": "",
        },
        {
            "title": f"{code} 风险提示：公告与财报窗口期临近",
            "source": "YourAce 本地资讯",
            "time": now,
            "url": "",
        },
    ]
    return items[:limit]
