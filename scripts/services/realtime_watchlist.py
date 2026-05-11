"""自选池实时信号服务。

这一层负责账号隔离、自选池维护、行情抓取、分钟线信号计算和通知合成。
当 Redis 不可用时，自动回退到内存后端，保证本地联调和测试可运行。
"""

from __future__ import annotations

import copy
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, time
from functools import lru_cache
from hashlib import pbkdf2_hmac
from pathlib import Path
from secrets import token_hex
from typing import Any, Dict, Iterable, List, Optional, Sequence

import akshare as ak
import numpy as np
import pandas as pd
import urllib.request
import urllib.error

from scripts.utils.asset_loader import detect_asset_type, get_asset_name, load_assets

# ---- 东方财富免费行情 API ----

_EM_SPOT_URL = "http://push2.eastmoney.com/api/qt/clist/get"
_EM_MINUTE_URL = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
_EM_SPOT_FIELDS = "f2,f3,f4,f5,f6,f7,f8,f12,f14"
_EM_SPOT_PARAMS = "pn=1&pz=5000&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
_EM_REQUEST_TIMEOUT = 8


def _em_stock_code(code: str) -> str:
    """将 6 位代码转为东方财富 secid 格式（0=上海, 1=深圳）。"""
    c = _normalize_code(code)
    if c.startswith(("6", "9")):
        return f"1.{c}"
    return f"0.{c}"


def _fetch_spot_from_eastmoney() -> pd.DataFrame:
    """从东方财富拉取全 A 股实时行情快照。"""
    url = f"{_EM_SPOT_URL}?{_EM_SPOT_PARAMS}&fields={_EM_SPOT_FIELDS}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=_EM_REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return pd.DataFrame()

    rows = (data or {}).get("data", {}).get("diff", [])
    if not rows:
        return pd.DataFrame()

    records = []
    for r in rows:
        code = str(r.get("f12", ""))
        name = str(r.get("f14", ""))
        if not code:
            continue
        records.append({
            "code": _normalize_code(code),
            "name": name,
            "latest_price": _safe_float(r.get("f2")),
            "pct_change": _safe_float(r.get("f3")),
            "volume": _safe_float(r.get("f5")),
            "amount": _safe_float(r.get("f6")),
            "turnover": _safe_float(r.get("f8")),
        })
    return pd.DataFrame(records)


def _fetch_minute_from_eastmoney(code: str) -> pd.DataFrame:
    """从东方财富拉取个股 1 分钟 K 线（最近约 240 根）。"""
    secid = _em_stock_code(code)
    url = (
        f"{_EM_MINUTE_URL}?secid={secid}"
        f"&fields1=f1,f2,f3,f4,f5,f6"
        f"&fields2=f51,f52,f53,f54,f55,f56,f57"
        f"&klt=1&fqt=1&end=20500101&lmt=240"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=_EM_REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return pd.DataFrame()

    klines = (data or {}).get("data", {}).get("klines", [])
    if not klines:
        return pd.DataFrame()

    records = []
    for line in klines:
        parts = str(line).split(",")
        if len(parts) < 7:
            continue
        records.append({
            "time": pd.Timestamp(parts[0]),
            "close": _safe_float(parts[3]),
            "volume": _safe_float(parts[6]),
        })
    return _normalize_minute_frame(pd.DataFrame(records))

try:  # pragma: no cover - 运行环境可能没有安装 redis
    import redis
except Exception:  # noqa: BLE001
    redis = None


_DEFAULT_CONFIG_PATH = Path("configs/realtime_watchlist_config.json")
_DEFAULT_RECOMMENDED_ETF_CODES = ["510300", "159915", "510500", "588000", "512480", "512000", "512010", "512660"]
_ACTION_LABELS = {
    "BUY": "买入",
    "SELL": "卖出",
    "HOLD": "静默",
}
# A 股交易时段：上午 9:30–11:30，下午 13:00–15:00（周一至周五）
_TRADING_AM_START = time(9, 30)
_TRADING_AM_END = time(11, 30)
_TRADING_PM_START = time(13, 0)
_TRADING_PM_END = time(15, 0)


def _is_a_share_trading_time(now: Optional[datetime] = None) -> bool:
    """判断当前是否处于 A 股连续竞价时段。"""
    t = (now or datetime.now())
    if t.weekday() >= 5:
        return False
    clock = t.time()
    return (_TRADING_AM_START <= clock <= _TRADING_AM_END) or (_TRADING_PM_START <= clock <= _TRADING_PM_END)


@dataclass(frozen=True)
class RuntimeConfig:
    """实时看盘配置。"""

    redis_url: str = "redis://127.0.0.1:6379/0"
    quote_cache_seconds: int = 30
    minute_cache_seconds: int = 30
    notification_dedup_seconds: int = 60
    stream_interval_seconds: int = 20
    stream_duration_seconds: int = 300
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    p2_window_minutes: int = 10
    p2_threshold: float = 0.02


@dataclass(frozen=True)
class SignalCandidate:
    """单条信号候选。"""

    signal_id: str
    action: str
    title: str
    reason: str


class _JsonStoreBackend:
    """JSON 存储后端抽象。"""

    def get_value(self, key: str) -> Any:
        raise NotImplementedError

    def set_value(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def add_members(self, key: str, *members: str) -> None:
        raise NotImplementedError

    def remove_members(self, key: str, *members: str) -> None:
        raise NotImplementedError

    def read_members(self, key: str) -> List[str]:
        raise NotImplementedError

    def append_item(self, key: str, value: Any) -> None:
        raise NotImplementedError

    def read_items(self, key: str) -> List[Any]:
        raise NotImplementedError

    def clear_items(self, key: str) -> None:
        raise NotImplementedError


class _MemoryJsonStoreBackend(_JsonStoreBackend):
    """内存回退实现。"""

    def __init__(self) -> None:
        self._values: Dict[str, Any] = {}
        self._members: Dict[str, set[str]] = {}
        self._items: Dict[str, List[Any]] = {}
        self._expires: Dict[str, datetime] = {}
        self._lock = threading.RLock()

    def _is_expired(self, key: str) -> bool:
        expires_at = self._expires.get(key)
        if expires_at is None:
            return False
        if datetime.now() <= expires_at:
            return False
        self._values.pop(key, None)
        self._members.pop(key, None)
        self._items.pop(key, None)
        self._expires.pop(key, None)
        return True

    def get_value(self, key: str) -> Any:
        with self._lock:
            self._is_expired(key)
            value = self._values.get(key)
            return copy.deepcopy(value)

    def set_value(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        with self._lock:
            self._values[key] = copy.deepcopy(value)
            if ttl_seconds is not None:
                self._expires[key] = datetime.now() + timedelta(seconds=ttl_seconds)
            elif key in self._expires:
                self._expires.pop(key, None)

    def delete(self, key: str) -> None:
        with self._lock:
            self._values.pop(key, None)
            self._members.pop(key, None)
            self._items.pop(key, None)
            self._expires.pop(key, None)

    def add_members(self, key: str, *members: str) -> None:
        with self._lock:
            bucket = self._members.setdefault(key, set())
            for member in members:
                bucket.add(str(member))

    def remove_members(self, key: str, *members: str) -> None:
        with self._lock:
            bucket = self._members.setdefault(key, set())
            for member in members:
                bucket.discard(str(member))

    def read_members(self, key: str) -> List[str]:
        with self._lock:
            self._is_expired(key)
            return sorted(self._members.get(key, set()))

    def append_item(self, key: str, value: Any) -> None:
        with self._lock:
            bucket = self._items.setdefault(key, [])
            bucket.append(copy.deepcopy(value))

    def read_items(self, key: str) -> List[Any]:
        with self._lock:
            self._is_expired(key)
            return copy.deepcopy(self._items.get(key, []))

    def clear_items(self, key: str) -> None:
        with self._lock:
            self._items.pop(key, None)


class _RedisJsonStoreBackend(_JsonStoreBackend):
    """Redis 存储实现。"""

    def __init__(self, client: Any) -> None:
        self._client = client

    def get_value(self, key: str) -> Any:
        raw = self._client.get(key)
        if raw in (None, ""):
            return None
        try:
            return json.loads(raw)
        except Exception:  # noqa: BLE001
            return raw

    def set_value(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        payload = json.dumps(value, ensure_ascii=False)
        if ttl_seconds is None:
            self._client.set(key, payload)
        else:
            self._client.set(key, payload, ex=ttl_seconds)

    def delete(self, key: str) -> None:
        self._client.delete(key)

    def add_members(self, key: str, *members: str) -> None:
        if members:
            self._client.sadd(key, *[str(member) for member in members])

    def remove_members(self, key: str, *members: str) -> None:
        if members:
            self._client.srem(key, *[str(member) for member in members])

    def read_members(self, key: str) -> List[str]:
        return sorted(str(item) for item in self._client.smembers(key))

    def append_item(self, key: str, value: Any) -> None:
        self._client.rpush(key, json.dumps(value, ensure_ascii=False))

    def read_items(self, key: str) -> List[Any]:
        raw_items = self._client.lrange(key, 0, -1)
        result: List[Any] = []
        for raw in raw_items:
            try:
                result.append(json.loads(raw))
            except Exception:  # noqa: BLE001
                result.append(raw)
        return result

    def clear_items(self, key: str) -> None:
        self._client.delete(key)


def _load_runtime_config(config_path: Path = _DEFAULT_CONFIG_PATH) -> RuntimeConfig:
    """读取实时看盘配置，缺省时使用内置值。"""
    defaults = RuntimeConfig()
    if not config_path.exists():
        return defaults

    try:
        with config_path.open("r", encoding="utf-8") as f:
            raw = json.load(f) or {}
    except Exception:  # noqa: BLE001
        return defaults

    def _int(name: str, fallback: int) -> int:
        value = raw.get(name, fallback)
        try:
            return int(value)
        except Exception:  # noqa: BLE001
            return fallback

    def _float(name: str, fallback: float) -> float:
        value = raw.get(name, fallback)
        try:
            return float(value)
        except Exception:  # noqa: BLE001
            return fallback

    return RuntimeConfig(
        redis_url=str(raw.get("redis_url", defaults.redis_url)),
        quote_cache_seconds=_int("quote_cache_seconds", defaults.quote_cache_seconds),
        minute_cache_seconds=_int("minute_cache_seconds", defaults.minute_cache_seconds),
        notification_dedup_seconds=_int("notification_dedup_seconds", defaults.notification_dedup_seconds),
        stream_interval_seconds=_int("stream_interval_seconds", defaults.stream_interval_seconds),
        stream_duration_seconds=_int("stream_duration_seconds", defaults.stream_duration_seconds),
        macd_fast=_int("macd_fast", defaults.macd_fast),
        macd_slow=_int("macd_slow", defaults.macd_slow),
        macd_signal=_int("macd_signal", defaults.macd_signal),
        p2_window_minutes=_int("p2_window_minutes", defaults.p2_window_minutes),
        p2_threshold=_float("p2_threshold", defaults.p2_threshold),
    )


def _build_backend(config: RuntimeConfig) -> _JsonStoreBackend:
    """优先使用 Redis，失败则回退到内存。"""
    if redis is not None:
        try:
            client = redis.Redis.from_url(config.redis_url, decode_responses=True)
            client.ping()
            return _RedisJsonStoreBackend(client)
        except Exception:  # noqa: BLE001
            pass
    return _MemoryJsonStoreBackend()


def _normalize_code(code: str) -> str:
    digits = "".join(ch for ch in str(code) if ch.isdigit())
    return digits.zfill(6) if digits else ""


def _now_label(current_time: Optional[datetime] = None) -> datetime:
    return current_time or datetime.now()


def _format_clock_label(current_time: datetime) -> str:
    return current_time.strftime("%H:%M").lstrip("0") or "0:00"


def _action_to_label(action: str) -> str:
    return _ACTION_LABELS.get(action, action)


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return fallback
        result = float(value)
        if np.isnan(result):
            return fallback
        return result
    except Exception:  # noqa: BLE001
        return fallback


def _first_existing(row: Dict[str, Any], names: Sequence[str], fallback: Any = None) -> Any:
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return fallback


def _normalize_spot_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["code", "name", "latest_price", "pct_change", "volume", "amount", "turnover"])

    code_col = _find_column(df, ["代码", "code", "symbol"])
    name_col = _find_column(df, ["名称", "name", "简称"])
    latest_price_col = _find_column(df, ["最新价", "收盘", "close", "price"])
    pct_change_col = _find_column(df, ["涨跌幅", "pct_change", "change_pct"])
    volume_col = _find_column(df, ["成交量", "volume"])
    amount_col = _find_column(df, ["成交额", "amount"])
    turnover_col = _find_column(df, ["换手率", "turnover"])

    normalized = pd.DataFrame()
    normalized["code"] = df[code_col].astype(str).map(_normalize_code) if code_col else ""
    normalized["name"] = df[name_col].astype(str) if name_col else ""
    normalized["latest_price"] = pd.to_numeric(df[latest_price_col], errors="coerce") if latest_price_col else np.nan
    normalized["pct_change"] = pd.to_numeric(df[pct_change_col], errors="coerce") / 100.0 if pct_change_col else np.nan
    normalized["volume"] = pd.to_numeric(df[volume_col], errors="coerce") if volume_col else np.nan
    normalized["amount"] = pd.to_numeric(df[amount_col], errors="coerce") if amount_col else np.nan
    normalized["turnover"] = pd.to_numeric(df[turnover_col], errors="coerce") if turnover_col else np.nan
    normalized = normalized.dropna(subset=["code"]).drop_duplicates(subset=["code"])
    return normalized.reset_index(drop=True)


def _normalize_minute_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["time", "close", "volume"])

    time_col = _find_column(df, ["时间", "日期", "datetime", "date", "time"])
    close_col = _find_column(df, ["收盘", "收盘价", "close", "最新价"])
    volume_col = _find_column(df, ["成交量", "volume"])

    normalized = pd.DataFrame()
    if time_col:
        normalized["time"] = pd.to_datetime(df[time_col], errors="coerce")
    else:
        normalized["time"] = pd.NaT
    normalized["close"] = pd.to_numeric(df[close_col], errors="coerce") if close_col else np.nan
    normalized["volume"] = pd.to_numeric(df[volume_col], errors="coerce") if volume_col else np.nan
    normalized = normalized.dropna(subset=["close"]).reset_index(drop=True)
    if normalized["time"].notna().any():
        normalized = normalized.sort_values("time").reset_index(drop=True)
    return normalized


def _find_column(df: pd.DataFrame, candidates: Sequence[str]) -> Optional[str]:
    lower_map = {str(col).lower(): str(col) for col in df.columns}
    for candidate in candidates:
        matched = lower_map.get(candidate.lower())
        if matched is not None:
            return matched
    return None


def _generate_mock_minute_frame(code: str, points: int = 120) -> pd.DataFrame:
    seed = sum(ord(ch) for ch in code)
    rng = np.random.default_rng(seed)
    steps = rng.normal(loc=0.0008, scale=0.006, size=points)
    closes = 100 * np.cumprod(1 + steps)
    volumes = np.abs(rng.normal(loc=1200, scale=320, size=points)).round(0)
    base_time = datetime.now().replace(second=0, microsecond=0) - timedelta(minutes=points - 1)
    times = [base_time + timedelta(minutes=index) for index in range(points)]
    return pd.DataFrame({"time": times, "close": closes, "volume": volumes})


def _generate_mock_spot_frame(codes: Sequence[str]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for code in codes:
        seed = sum(ord(ch) for ch in code)
        rng = np.random.default_rng(seed)
        price = float(10 + (seed % 90) + rng.normal(0, 0.5))
        change_pct = float(np.clip(rng.normal(loc=0.008, scale=0.018), -0.08, 0.08))
        rows.append(
            {
                "code": code,
                "name": get_asset_name(code),
                "latest_price": price,
                "pct_change": change_pct,
                "volume": float(abs(rng.normal(loc=3_000_000, scale=500_000))),
                "amount": float(abs(rng.normal(loc=30_000_000, scale=8_000_000))),
                "turnover": float(abs(rng.normal(loc=1.2, scale=0.6))),
                "updated_at": now,
                "source": "mock",
            }
        )
    return pd.DataFrame(rows)


def _generate_mock_minute_history(code: str) -> pd.DataFrame:
    frame = _generate_mock_minute_frame(code)
    return frame


def _format_minute_time_label(value: Any) -> str:
    if isinstance(value, pd.Timestamp):
        return value.strftime("%H:%M")
    if isinstance(value, datetime):
        return value.strftime("%H:%M")

    text = str(value).strip()
    if not text:
        return ""
    if len(text) >= 5:
        return text[-5:]
    return text


def _macd_signal(close_series: pd.Series, fast: int, slow: int, signal: int) -> SignalCandidate:
    closes = pd.to_numeric(close_series, errors="coerce").dropna().astype(float)
    if len(closes) < max(fast, slow, signal) + 2:
        return SignalCandidate("P1", "HOLD", "MACD 数据不足", "分钟线数据不足，暂无 MACD 信号")

    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = dif - dea

    prev_hist = float(hist.iloc[-2])
    curr_hist = float(hist.iloc[-1])
    if prev_hist <= 0 < curr_hist:
        return SignalCandidate("P1", "BUY", "MACD 金叉买入", "分钟线 MACD 刚刚金叉")
    if prev_hist >= 0 > curr_hist:
        return SignalCandidate("P1", "SELL", "MACD 死叉卖出", "分钟线 MACD 刚刚死叉")
    return SignalCandidate("P1", "HOLD", "MACD 无交叉", "分钟线 MACD 当前没有新的金叉/死叉")


def _fast_move_signal(close_series: pd.Series, window_minutes: int, threshold: float) -> SignalCandidate:
    closes = pd.to_numeric(close_series, errors="coerce").dropna().astype(float)
    if len(closes) <= window_minutes:
        return SignalCandidate("P2", "HOLD", "P2 数据不足", "分钟线数据不足，暂无 P2 信号")

    base_price = float(closes.iloc[-(window_minutes + 1)])
    latest_price = float(closes.iloc[-1])
    if base_price == 0:
        return SignalCandidate("P2", "HOLD", "P2 无法计算", "P2 无法计算涨跌幅")

    move = latest_price / base_price - 1.0
    if move >= threshold:
        return SignalCandidate("P2", "SELL", "10分钟快速拉升卖出", f"10分钟累计涨幅达到 {move:.2%}")
    if move <= -threshold:
        return SignalCandidate("P2", "BUY", "10分钟快速下跌买入", f"10分钟累计跌幅达到 {move:.2%}")
    return SignalCandidate("P2", "HOLD", "P2 未触发", f"10分钟累计涨跌幅 {move:.2%} 未超过阈值")


def _time_rule_signal(current_time: datetime) -> SignalCandidate:
    current_clock = current_time.time()
    if current_clock < time(10, 0):
        return SignalCandidate("P3", "SELL", "10点前经验卖出", "10:00 之前按经验偏卖出")
    if current_clock > time(14, 30):
        return SignalCandidate("P3", "BUY", "14:30后经验买入", "14:30 之后按经验偏买入")
    return SignalCandidate("P3", "HOLD", "P3 未触发", "当前不在 P3 的经验区间")


def _sector_rule_signal(stock_pct_change: Optional[float], etf_pct_change: Optional[float]) -> SignalCandidate:
    if stock_pct_change is None or etf_pct_change is None:
        return SignalCandidate("P4", "HOLD", "P4 数据不足", "缺少个股或 ETF 的涨跌幅数据")

    if stock_pct_change > 0 and etf_pct_change > 0:
        return SignalCandidate("P4", "SELL", "板块普涨卖出", f"个股 {stock_pct_change:.2%} 且 ETF {etf_pct_change:.2%} 同涨")
    if stock_pct_change < 0 and etf_pct_change < 0:
        return SignalCandidate("P4", "BUY", "板块普跌买入", f"个股 {stock_pct_change:.2%} 且 ETF {etf_pct_change:.2%} 同跌")
    return SignalCandidate("P4", "HOLD", "P4 未触发", "个股和 ETF 未形成同涨或同跌")


def combine_signal_candidates(candidates: Sequence[SignalCandidate]) -> Dict[str, Any]:
    """按 P1>P2>P3>P4 合成最终动作。"""
    ordered_candidates = [candidate for candidate in candidates if candidate.action in {"BUY", "SELL", "HOLD"}]
    active_candidates = [candidate for candidate in ordered_candidates if candidate.action in {"BUY", "SELL"}]
    primary_candidate = active_candidates[0] if active_candidates else None
    buy_count = sum(candidate.action == "BUY" for candidate in active_candidates)
    sell_count = sum(candidate.action == "SELL" for candidate in active_candidates)

    if primary_candidate is None:
        final_action = "BUY" if buy_count >= 2 else "HOLD"
    elif primary_candidate.action == "SELL":
        final_action = "SELL"
    else:
        final_action = "BUY" if buy_count >= 2 else "HOLD"

    notify = final_action in {"BUY", "SELL"}
    if final_action == "BUY" and buy_count < 2:
        notify = False

    reason_tags = [candidate.signal_id for candidate in active_candidates]
    return {
        "primary_signal": primary_candidate.signal_id if primary_candidate else "",
        "primary_action": primary_candidate.action if primary_candidate else "HOLD",
        "final_action": final_action,
        "final_action_label": _action_to_label(final_action),
        "notify": notify,
        "buy_signal_count": buy_count,
        "sell_signal_count": sell_count,
        "reason_tags": reason_tags,
        "reason_text": "+".join(reason_tags),
        "signals": [asdict(candidate) for candidate in ordered_candidates],
    }


def evaluate_intraday_signals(
    close_series: pd.Series,
    stock_pct_change: Optional[float] = None,
    etf_pct_change: Optional[float] = None,
    current_time: Optional[datetime] = None,
    config: Optional[RuntimeConfig] = None,
) -> Dict[str, Any]:
    """根据分钟线、时间和板块涨跌幅计算 P1-P4。非交易时段统一返回休市。"""
    runtime_config = config or RuntimeConfig()
    now = _now_label(current_time)
    if not _is_a_share_trading_time(now):
        return {
            "timestamp": now.isoformat(timespec="seconds"),
            "clock": _format_clock_label(now),
            "signals": [],
            "decision": {
                "primary_signal": "",
                "primary_action": "HOLD",
                "final_action": "HOLD",
                "final_action_label": "休市",
                "notify": False,
                "buy_signal_count": 0,
                "sell_signal_count": 0,
                "reason_tags": [],
                "reason_text": "非交易时段",
                "signals": [],
            },
            "notification": "",
        }
    p1 = _macd_signal(close_series, runtime_config.macd_fast, runtime_config.macd_slow, runtime_config.macd_signal)
    p2 = _fast_move_signal(close_series, runtime_config.p2_window_minutes, runtime_config.p2_threshold)
    p3 = _time_rule_signal(now)
    p4 = _sector_rule_signal(stock_pct_change, etf_pct_change)
    decision = combine_signal_candidates([p1, p2, p3, p4])

    if decision["notify"]:
        message = f"{_format_clock_label(now)}-{decision['reason_text']}"
    else:
        message = ""

    return {
        "timestamp": now.isoformat(timespec="seconds"),
        "clock": _format_clock_label(now),
        "signals": decision["signals"],
        "decision": decision,
        "notification": message,
    }


# 登录态：未勾选「保持登录」时服务端会话较短；勾选后较长。旧数据无 token_expires_at 则不校验过期。
_SESSION_HOURS_WHEN_NOT_PERSISTED = 8
_SESSION_DAYS_WHEN_PERSISTED = 7


def _token_expiry_label(persist_session: bool) -> str:
    now = datetime.now()
    if persist_session:
        return (now + timedelta(days=_SESSION_DAYS_WHEN_PERSISTED)).isoformat(timespec="seconds")
    return (now + timedelta(hours=_SESSION_HOURS_WHEN_NOT_PERSISTED)).isoformat(timespec="seconds")


class WatchlistRuntime:
    """自选池运行时服务。"""

    def __init__(self, config: Optional[RuntimeConfig] = None, backend: Optional[_JsonStoreBackend] = None) -> None:
        self.config = config or _load_runtime_config()
        self.backend = backend or _build_backend(self.config)

    def register_user(self, username: str, password: str, *, persist_session: bool = False) -> Dict[str, Any]:
        username = username.strip()
        password = password.strip()
        if not username:
            raise ValueError("用户名不能为空")
        if not password:
            raise ValueError("密码不能为空")

        lookup_key = self._username_key(username)
        if self.backend.get_value(lookup_key):
            raise ValueError("用户名已存在")

        user_id = token_hex(16)
        token = token_hex(24)
        salt = token_hex(8)
        password_hash = self._hash_password(password, salt)
        record = {
            "user_id": user_id,
            "username": username,
            "password_hash": password_hash,
            "salt": salt,
            "token": token,
            "persist_session": bool(persist_session),
            "token_expires_at": _token_expiry_label(persist_session),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.backend.set_value(self._user_key(user_id), record)
        self.backend.set_value(lookup_key, user_id)
        self.backend.set_value(self._token_key(token), user_id)
        return self._public_user_record(record)

    def login_user(self, username: str, password: str, *, persist_session: bool = False) -> Dict[str, Any]:
        username = username.strip()
        password = password.strip()
        if not username:
            raise ValueError("用户名不能为空")
        if not password:
            raise ValueError("密码不能为空")

        user_id = self.backend.get_value(self._username_key(username))
        if not user_id:
            raise ValueError("用户名或密码错误")

        record = self.backend.get_value(self._user_key(str(user_id)))
        if not record:
            raise ValueError("用户不存在")
        if self._hash_password(password, str(record.get("salt", ""))) != record.get("password_hash"):
            raise ValueError("用户名或密码错误")

        old_token = str(record.get("token", "")).strip()
        if old_token:
            self.backend.delete(self._token_key(old_token))

        token = token_hex(24)
        record["token"] = token
        record["persist_session"] = bool(persist_session)
        record["token_expires_at"] = _token_expiry_label(persist_session)
        record["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self.backend.set_value(self._user_key(str(user_id)), record)
        self.backend.set_value(self._token_key(token), str(user_id))
        return self._public_user_record(record)

    def refresh_session(self, user_id: str, token: str) -> Dict[str, Any]:
        """在 token 仍有效时顺延过期时间（按用户上次选择的保持登录策略）。"""
        user_id = str(user_id).strip()
        token = str(token).strip()
        if not user_id or not token:
            raise ValueError("认证失败，请先登录")

        token_user_id = self.backend.get_value(self._token_key(token))
        if str(token_user_id or "") != user_id:
            raise ValueError("认证失败，请先登录")

        record = self.backend.get_value(self._user_key(user_id))
        if not record or str(record.get("token", "")) != token:
            raise ValueError("认证失败，请先登录")

        self._raise_if_token_expired(record)

        persist = bool(record.get("persist_session", False))
        record["token_expires_at"] = _token_expiry_label(persist)
        record["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self.backend.set_value(self._user_key(user_id), record)
        return self._public_user_record(record)

    def add_watchlist_item(
        self,
        user_id: str,
        token: str,
        code: str,
        stock_name: str = "",
        etf_code: str = "",
        etf_name: str = "",
        sector_name: str = "",
    ) -> Dict[str, Any]:
        self._require_auth(user_id, token)
        code = _normalize_code(code)
        if not code:
            raise ValueError("股票代码不能为空")

        stock_name = stock_name.strip() or get_asset_name(code) or code
        etf_code = _normalize_code(etf_code)
        etf_name = etf_name.strip() or (get_asset_name(etf_code) if etf_code else "")
        sector_name = sector_name.strip() or etf_name or stock_name

        item = {
            "code": code,
            "name": stock_name,
            "etf_code": etf_code,
            "etf_name": etf_name,
            "sector_name": sector_name,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.backend.set_value(self._watchlist_item_key(user_id, code), item)
        self.backend.add_members(self._watchlist_codes_key(user_id), code)
        self.backend.delete(self._dedup_marker_key(user_id, code))
        return {
            "user_id": user_id,
            "item": item,
            "recommendations": self.recommend_etfs(code, stock_name=stock_name),
        }

    def remove_watchlist_item(self, user_id: str, token: str, code: str) -> Dict[str, Any]:
        self._require_auth(user_id, token)
        code = _normalize_code(code)
        if not code:
            raise ValueError("股票代码不能为空")

        self.backend.delete(self._watchlist_item_key(user_id, code))
        self.backend.remove_members(self._watchlist_codes_key(user_id), code)
        self.backend.delete(self._dedup_marker_key(user_id, code))
        return {"user_id": user_id, "code": code, "removed": True}

    def list_watchlist(self, user_id: str, token: str) -> Dict[str, Any]:
        self._require_auth(user_id, token)
        items = self._read_watchlist_items(user_id)
        return {"user_id": user_id, "count": len(items), "items": items}

    def recommend_etfs(self, code: str, stock_name: str = "", limit: int = 5) -> List[Dict[str, Any]]:
        code = _normalize_code(code)
        if limit <= 0:
            raise ValueError("limit 必须大于 0")

        stock_name = stock_name.strip() or get_asset_name(code)
        universe = load_assets(keyword="", limit=10000)
        etfs = [asset for asset in universe if detect_asset_type(str(asset.get("code", "")), str(asset.get("name", ""))) == "etf"]
        if not etfs:
            return []

        tokens = self._collect_keywords(stock_name)
        scored: List[Dict[str, Any]] = []
        for asset in etfs:
            asset_name = str(asset.get("name", ""))
            score = 0
            matched_tokens: List[str] = []
            for token in tokens:
                if token and token in asset_name:
                    score += 2
                    matched_tokens.append(token)
            if score > 0:
                scored.append(
                    {
                        "code": str(asset.get("code", "")),
                        "name": asset_name,
                        "score": score,
                        "matched_keywords": matched_tokens,
                    }
                )

        if not scored:
            broad = [asset for asset in etfs if str(asset.get("code", "")) in _DEFAULT_RECOMMENDED_ETF_CODES]
            if not broad:
                broad = etfs[:limit]
            return [
                {
                    "code": str(asset.get("code", "")),
                    "name": str(asset.get("name", "")),
                    "score": 1,
                    "matched_keywords": [],
                }
                for asset in broad[:limit]
            ]

        scored.sort(key=lambda item: (-int(item["score"]), item["code"]))
        return scored[:limit]

    def get_watchlist_quotes(self, user_id: str, token: str) -> Dict[str, Any]:
        snapshot = self.refresh_watchlist(user_id, token, enqueue_notifications=False)
        return {"user_id": user_id, "count": len(snapshot["items"]), "items": [item["quote"] for item in snapshot["items"]]}

    def get_watchlist_signals(self, user_id: str, token: str) -> Dict[str, Any]:
        snapshot = self.refresh_watchlist(user_id, token, enqueue_notifications=False)
        return {"user_id": user_id, "count": len(snapshot["items"]), "items": [item["signals"] for item in snapshot["items"]]}

    def get_watchlist_summary(self, user_id: str, token: str) -> Dict[str, Any]:
        return self.refresh_watchlist(user_id, token, enqueue_notifications=True)

    def refresh_watchlist(self, user_id: str, token: str, enqueue_notifications: bool = True) -> Dict[str, Any]:
        self._require_auth(user_id, token)
        items = self._read_watchlist_items(user_id)
        if not items:
            return {"user_id": user_id, "count": 0, "items": [], "notifications": []}

        spot_map = self._load_spot_quotes_map()
        codes = [str(item.get("code", "")) for item in items]
        etf_codes = [str(item.get("etf_code", "")) for item in items if str(item.get("etf_code", ""))]
        minute_map = self._load_minute_history_map(codes + etf_codes)

        item_views: List[Dict[str, Any]] = []
        notifications: List[Dict[str, Any]] = []
        for item in items:
            view = self._build_watchlist_item_view(item, spot_map, minute_map)
            item_views.append(view)
            notification = view.get("notification")
            if enqueue_notifications and notification:
                dedup_key = self._dedup_marker_key(user_id, str(item.get("code", "")), str(notification.get("fingerprint", "")))
                if not self.backend.get_value(dedup_key):
                    self.backend.set_value(
                        dedup_key,
                        {"created_at": datetime.now().isoformat(timespec="seconds")},
                        ttl_seconds=self.config.notification_dedup_seconds,
                    )
                    self.backend.append_item(self._notification_queue_key(user_id), notification)
                    notifications.append(notification)

        return {"user_id": user_id, "count": len(item_views), "items": item_views, "notifications": notifications}

    def drain_notifications(self, user_id: str, token: str) -> Dict[str, Any]:
        self._require_auth(user_id, token)
        queue_key = self._notification_queue_key(user_id)
        items = self.backend.read_items(queue_key)
        self.backend.clear_items(queue_key)
        return {"user_id": user_id, "count": len(items), "items": items}

    def _read_watchlist_items(self, user_id: str) -> List[Dict[str, Any]]:
        codes = self.backend.read_members(self._watchlist_codes_key(user_id))
        items: List[Dict[str, Any]] = []
        for code in codes:
            item = self.backend.get_value(self._watchlist_item_key(user_id, code))
            if item:
                items.append(item)
        return sorted(items, key=lambda item: str(item.get("code", "")))

    def _build_watchlist_item_view(
        self,
        item: Dict[str, Any],
        spot_map: Dict[str, Dict[str, Any]],
        minute_map: Dict[str, pd.DataFrame],
    ) -> Dict[str, Any]:
        code = str(item.get("code", ""))
        etf_code = str(item.get("etf_code", ""))
        stock_name = str(item.get("name", "")) or get_asset_name(code) or code
        etf_name = str(item.get("etf_name", "")) or (get_asset_name(etf_code) if etf_code else "")
        sector_name = str(item.get("sector_name", "")) or etf_name or stock_name

        stock_quote = self._build_quote_view(code, stock_name, spot_map)
        etf_quote = self._build_quote_view(etf_code, etf_name, spot_map) if etf_code else None
        minute_frame = minute_map.get(code)
        has_real_minute = minute_frame is not None and not minute_frame.empty
        if not has_real_minute:
            minute_frame = pd.DataFrame(columns=["time", "close", "volume"])
        intraday_marker = self._build_intraday_marker_view(minute_frame)
        minute_volume = self._build_minute_volume_view(minute_frame)
        signal_summary = self._build_signal_summary(
            code=code,
            stock_name=stock_name,
            minute_frame=minute_frame,
            stock_quote=stock_quote,
            etf_quote=etf_quote,
        )

        notification = None
        if signal_summary["decision"]["notify"]:
            notification = {
                "code": code,
                "name": stock_name,
                "sector_name": sector_name,
                "etf_code": etf_code,
                "etf_name": etf_name,
                "action": signal_summary["decision"]["final_action"],
                "action_label": signal_summary["decision"]["final_action_label"],
                "timestamp": signal_summary["timestamp"],
                "clock": signal_summary["clock"],
                "reason_tags": signal_summary["decision"]["reason_tags"],
                "reason_text": signal_summary["decision"]["reason_text"],
                "message": f"{stock_name}（{code}）{signal_summary['decision']['final_action_label']}-{signal_summary['clock']}-{signal_summary['decision']['reason_text']}",
                "fingerprint": self._build_fingerprint(code, signal_summary),
            }

        return {
            "code": code,
            "name": stock_name,
            "sector_name": sector_name,
            "etf_code": etf_code,
            "etf_name": etf_name,
            "quote": stock_quote,
            "etf_quote": etf_quote,
            "intraday_high": intraday_marker["intraday_high"],
            "intraday_high_time": intraday_marker["intraday_high_time"],
            "intraday_low": intraday_marker["intraday_low"],
            "intraday_low_time": intraday_marker["intraday_low_time"],
            "minute_volume": minute_volume,
            "signals": signal_summary,
            "notification": notification,
        }

    def _build_quote_view(self, code: str, fallback_name: str, spot_map: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        code = _normalize_code(code)
        now = datetime.now().isoformat(timespec="seconds")
        row = spot_map.get(code)
        if row:
            latest_price = _safe_float(row.get("latest_price"))
            pct_change = _safe_float(row.get("pct_change"))
            name = str(row.get("name", "")) or fallback_name
            volume = _safe_float(row.get("volume"))
            amount = _safe_float(row.get("amount"))
            turnover = _safe_float(row.get("turnover"))
            source = str(row.get("source", "akshare_spot"))
        else:
            latest_price = 0.0
            pct_change = 0.0
            volume = 0.0
            amount = 0.0
            turnover = 0.0
            name = fallback_name
            source = "mock"

        return {
            "code": code,
            "name": name,
            "latest_price": latest_price,
            "pct_change": pct_change,
            "volume": volume,
            "amount": amount,
            "turnover": turnover,
            "updated_at": now,
            "source": source,
        }

    def _build_minute_volume_view(self, minute_frame: pd.DataFrame) -> List[Dict[str, Any]]:
        if minute_frame is None or minute_frame.empty:
            return []
        frame = minute_frame.tail(20).copy()
        result: List[Dict[str, Any]] = []
        for _, row in frame.iterrows():
            minute_time = row.get("time")
            if isinstance(minute_time, pd.Timestamp):
                time_label = minute_time.strftime("%H:%M")
            elif isinstance(minute_time, datetime):
                time_label = minute_time.strftime("%H:%M")
            else:
                time_label = str(minute_time)
            result.append({"time": time_label, "volume": int(_safe_float(row.get("volume"), 0.0))})
        return result

    def _build_intraday_marker_view(self, minute_frame: pd.DataFrame) -> Dict[str, Any]:
        default_view = {
            "intraday_high": 0.0,
            "intraday_high_time": "",
            "intraday_low": 0.0,
            "intraday_low_time": "",
        }
        if minute_frame is None or minute_frame.empty or "close" not in minute_frame.columns:
            return default_view

        frame = minute_frame.copy()
        frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
        frame = frame.dropna(subset=["close"])
        if frame.empty:
            return default_view

        high_idx = frame["close"].idxmax()
        low_idx = frame["close"].idxmin()
        high_row = frame.loc[high_idx]
        low_row = frame.loc[low_idx]

        return {
            "intraday_high": _safe_float(high_row.get("close")),
            "intraday_high_time": _format_minute_time_label(high_row.get("time")),
            "intraday_low": _safe_float(low_row.get("close")),
            "intraday_low_time": _format_minute_time_label(low_row.get("time")),
        }

    def _build_signal_summary(
        self,
        code: str,
        stock_name: str,
        minute_frame: pd.DataFrame,
        stock_quote: Dict[str, Any],
        etf_quote: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        close_series = minute_frame["close"] if minute_frame is not None and not minute_frame.empty else pd.Series(dtype=float)
        result = evaluate_intraday_signals(
            close_series=close_series,
            stock_pct_change=_safe_float(stock_quote.get("pct_change")) if stock_quote else None,
            etf_pct_change=_safe_float(etf_quote.get("pct_change")) if etf_quote else None,
            current_time=datetime.now(),
            config=self.config,
        )
        result["stock_name"] = stock_name
        result["code"] = code
        return result

    def _build_fingerprint(self, code: str, signal_summary: Dict[str, Any]) -> str:
        action = str(signal_summary.get("decision", {}).get("final_action", "HOLD"))
        reason = str(signal_summary.get("decision", {}).get("reason_text", ""))
        clock = str(signal_summary.get("clock", ""))
        return f"{_normalize_code(code)}:{action}:{reason}:{clock}"

    def _load_spot_quotes_map(self) -> Dict[str, Dict[str, Any]]:
        """拉取全市场行情快照。非交易时段仅使用缓存，不再请求 akshare 避免无效请求。"""
        cache_key = self._cache_spot_key()
        cached = self.backend.get_value(cache_key)
        if isinstance(cached, dict) and cached.get("items"):
            return {str(item.get("code", "")): item for item in cached["items"] if str(item.get("code", ""))}

        if not _is_a_share_trading_time():
            return {}

        try:
            spot_frame = _normalize_spot_frame(_fetch_spot_from_eastmoney())
        except Exception:  # noqa: BLE001
            spot_frame = pd.DataFrame()

        if spot_frame.empty:
            self.backend.set_value(cache_key, {"saved_at": datetime.now().isoformat(timespec="seconds"), "items": []}, ttl_seconds=self.config.quote_cache_seconds)
            return {}

        items: List[Dict[str, Any]] = []
        now = datetime.now().isoformat(timespec="seconds")
        for _, row in spot_frame.iterrows():
            items.append(
                {
                    "code": str(row.get("code", "")),
                    "name": str(row.get("name", "")),
                    "latest_price": _safe_float(row.get("latest_price")),
                    "pct_change": _safe_float(row.get("pct_change")),
                    "volume": _safe_float(row.get("volume")),
                    "amount": _safe_float(row.get("amount")),
                    "turnover": _safe_float(row.get("turnover")),
                    "updated_at": now,
                    "source": "akshare_spot",
                }
            )

        self.backend.set_value(cache_key, {"saved_at": now, "items": items}, ttl_seconds=self.config.quote_cache_seconds)
        return {str(item.get("code", "")): item for item in items if str(item.get("code", ""))}

    def _load_minute_history_map(self, codes: Sequence[str]) -> Dict[str, pd.DataFrame]:
        """拉取分钟线历史。非交易时段仅用缓存，失败不生成假数据。"""
        normalized_codes = [code for code in {_normalize_code(code) for code in codes} if code]
        if not normalized_codes:
            return {}

        result: Dict[str, pd.DataFrame] = {}
        missing_codes: List[str] = []
        for code in normalized_codes:
            cache_key = self._minute_cache_key(code)
            cached = self.backend.get_value(cache_key)
            if isinstance(cached, dict) and cached.get("items"):
                result[code] = _normalize_minute_frame(pd.DataFrame(cached["items"]))
            else:
                missing_codes.append(code)

        if not missing_codes:
            return result

        if not _is_a_share_trading_time():
            return result

        def _fetch(code: str) -> tuple[str, pd.DataFrame]:
            try:
                frame = _fetch_minute_from_eastmoney(code)
                if frame.empty:
                    frame = pd.DataFrame(columns=["time", "close", "volume"])
            except Exception:  # noqa: BLE001
                frame = pd.DataFrame(columns=["time", "close", "volume"])
            return code, frame

        max_workers = min(8, len(missing_codes)) or 1
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(_fetch, code): code for code in missing_codes}
            for future in as_completed(future_map):
                code, frame = future.result()
                result[code] = frame
                cache_items = frame.tail(500).to_dict(orient="records")
                self.backend.set_value(
                    self._minute_cache_key(code),
                    {"saved_at": datetime.now().isoformat(timespec="seconds"), "items": cache_items},
                    ttl_seconds=self.config.minute_cache_seconds,
                )

        return result

    def _require_auth(self, user_id: str, token: str) -> None:
        user_id = str(user_id).strip()
        token = str(token).strip()
        if not user_id:
            raise ValueError("user_id 不能为空")
        if not token:
            raise ValueError("token 不能为空")

        token_user_id = self.backend.get_value(self._token_key(token))
        if str(token_user_id or "") != user_id:
            raise ValueError("认证失败，请先登录")

        record = self.backend.get_value(self._user_key(user_id))
        if not record or str(record.get("token", "")) != token:
            raise ValueError("认证失败，请先登录")

        self._raise_if_token_expired(record)

    def _raise_if_token_expired(self, record: Dict[str, Any]) -> None:
        exp_raw = record.get("token_expires_at")
        if not exp_raw:
            return
        try:
            expires_at = datetime.fromisoformat(str(exp_raw))
        except ValueError:
            return
        if datetime.now() > expires_at:
            raise ValueError("登录状态已过期，请重新登录")

    def _hash_password(self, password: str, salt: str) -> str:
        return pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()

    def _public_user_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "user_id": record.get("user_id", ""),
            "username": record.get("username", ""),
            "token": record.get("token", ""),
            "created_at": record.get("created_at", ""),
            "updated_at": record.get("updated_at", ""),
            "token_expires_at": record.get("token_expires_at", ""),
            "persist_session": bool(record.get("persist_session", False)),
        }

    def _collect_keywords(self, stock_name: str) -> List[str]:
        text = str(stock_name)
        keywords: List[str] = []
        for group in self._industry_groups():
            group_keywords = [str(keyword) for keyword in group.get("keywords", []) if str(keyword)]
            if any(keyword in text for keyword in group_keywords):
                keywords.extend(group_keywords)

        if not keywords:
            keywords.extend(["半导体", "芯片", "电子", "通信", "医药", "银行", "新能源", "白酒", "军工", "基建"])
        unique_keywords: List[str] = []
        for keyword in keywords:
            if keyword not in unique_keywords:
                unique_keywords.append(keyword)
        return unique_keywords

    def _industry_groups(self) -> List[Dict[str, Any]]:
        config_path = Path("configs/asset_config.json")
        if not config_path.exists():
            return []
        try:
            with config_path.open("r", encoding="utf-8") as f:
                raw = json.load(f) or {}
        except Exception:  # noqa: BLE001
            return []
        groups = raw.get("industry_groups", [])
        return groups if isinstance(groups, list) else []

    def _user_key(self, user_id: str) -> str:
        return f"user:{user_id}:profile"

    def _username_key(self, username: str) -> str:
        return f"auth:username:{username.lower()}"

    def _token_key(self, token: str) -> str:
        return f"auth:token:{token}"

    def _watchlist_codes_key(self, user_id: str) -> str:
        return f"user:{user_id}:watchlist:codes"

    def _watchlist_item_key(self, user_id: str, code: str) -> str:
        return f"user:{user_id}:watchlist:item:{_normalize_code(code)}"

    def _notification_queue_key(self, user_id: str) -> str:
        return f"user:{user_id}:notifications"

    def _dedup_marker_key(self, user_id: str, code: str, fingerprint: str = "") -> str:
        normalized_code = _normalize_code(code)
        if fingerprint:
            return f"user:{user_id}:notify_dedup:{normalized_code}:{fingerprint}"
        return f"user:{user_id}:notify_dedup:{normalized_code}"

    def _cache_spot_key(self) -> str:
        return "market:spot:cache"

    def _minute_cache_key(self, code: str) -> str:
        return f"market:minute:{_normalize_code(code)}"


@lru_cache(maxsize=1)
def get_watchlist_runtime() -> WatchlistRuntime:
    """获取单例服务实例。"""
    return WatchlistRuntime()
