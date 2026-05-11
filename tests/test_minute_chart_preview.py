"""分钟图闭路预览测试。"""

from __future__ import annotations

import os
import math
import sys
from datetime import datetime as real_datetime
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from scripts.api.server import app
from scripts.services import realtime_watchlist as rw


client = TestClient(app)


class _FixedDatetime(real_datetime):
    @classmethod
    def now(cls, tz=None):
        return real_datetime(2026, 5, 6, 11, 0, 0, tzinfo=tz)


def _install_runtime(monkeypatch) -> rw.WatchlistRuntime:
    runtime = rw.WatchlistRuntime(config=rw.RuntimeConfig(), backend=rw._MemoryJsonStoreBackend())
    monkeypatch.setattr("scripts.api.server.get_watchlist_runtime", lambda: runtime)
    return runtime


def _fake_spot_em() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"代码": "000001", "名称": "平安银行", "最新价": 10.72, "涨跌幅": 2.18, "成交量": 1680000, "成交额": 18000000, "换手率": 1.21},
            {"代码": "510300", "名称": "沪深300ETF", "最新价": 4.88, "涨跌幅": 1.02, "成交量": 880000, "成交额": 4300000, "换手率": 0.52},
        ]
    )


def _fake_hist_min_em(code: str) -> pd.DataFrame:
    """模拟东方财富分钟线返回。"""
    if code == "000001":
        closes = [10.00 + 0.01 * index for index in range(40)]
        volumes = [900 + int(220 * math.sin(index / 4.0)) + index * 42 for index in range(40)]
    else:
        closes = [5.00 + 0.005 * index for index in range(40)]
        volumes = [650 + int(120 * math.cos(index / 5.0)) + index * 18 for index in range(40)]

    times = pd.date_range("2026-05-06 10:21:00", periods=40, freq="1min")
    return pd.DataFrame({"time": times, "close": closes, "volume": volumes})


def render_minute_chart_preview(points: list[dict[str, object]], limit: int = 18) -> str:
    """把分钟量转换成可读的文本预览。"""
    window = points[-limit:]
    if not window:
        return "分钟图预览：暂无数据"

    volumes = [int(point.get("volume", 0) or 0) for point in window]
    max_volume = max(max(volumes), 1)

    lines = [
        f"分钟图预览（最近 {len(window)} 分钟）",
        f"最高量: {max_volume}  最新量: {volumes[-1]}",
        "说明: █ 越多代表分钟量越高，最后一行是最新分钟",
        "",
    ]

    for index, point in enumerate(window):
        volume = int(point.get("volume", 0) or 0)
        bar_count = max(1, round((volume / max_volume) * 8))
        bars = "█" * bar_count
        time_label = str(point.get("time", "--"))
        marker = "  ← 最新" if index == len(window) - 1 else ""
        lines.append(f"{time_label:>5} | {bars:<8} {volume:>5}{marker}")

    return "\n".join(lines)


def render_watchlist_card_preview(item: dict[str, object]) -> str:
    """把一张自选卡片渲染成可读的文本预览。"""
    quote = item.get("quote", {}) if isinstance(item.get("quote"), dict) else {}
    signals = item.get("signals", {}) if isinstance(item.get("signals"), dict) else {}
    decision = signals.get("decision", {}) if isinstance(signals.get("decision"), dict) else {}

    lines = [
        f"{item.get('name', '--')} ({item.get('code', '--')})",
        f"最新价 {format_preview_money(quote.get('latest_price'))}  涨跌幅 {format_preview_percent(quote.get('pct_change'))}",
        f"盘中高点 {format_preview_money(item.get('intraday_high'))} @ {item.get('intraday_high_time', '--')}",
        f"盘中低点 {format_preview_money(item.get('intraday_low'))} @ {item.get('intraday_low_time', '--')}",
        f"绑定 ETF {item.get('etf_name', '未绑定') or '未绑定'}  板块 {item.get('sector_name', '未命名') or '未命名'}",
        f"信号 {decision.get('final_action_label', '--')} · {decision.get('reason_text', '')}",
        "",
        render_minute_chart_preview(item.get("minute_volume", [])),
    ]

    return "\n".join(lines)


def format_preview_money(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "--"

    if number <= 0:
        return "--"
    return f"¥{number:.2f}"


def format_preview_percent(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "--"

    prefix = "+" if number >= 0 else ""
    return f"{prefix}{number * 100:.2f}%"


def test_minute_chart_preview_smoke(monkeypatch) -> None:
    """走真实接口链路并输出分钟图文本预览。"""
    runtime = _install_runtime(monkeypatch)
    monkeypatch.setattr(rw, "_fetch_spot_from_eastmoney", _fake_spot_em)
    monkeypatch.setattr(rw, "_fetch_minute_from_eastmoney", _fake_hist_min_em)
    monkeypatch.setattr(rw, "datetime", _FixedDatetime)

    register_response = client.post("/auth/register", json={"username": "preview_user", "password": "preview123"})
    assert register_response.status_code == 200
    auth_payload = register_response.json()

    add_response = client.post(
        "/watchlist/add",
        json={
            "user_id": auth_payload["user_id"],
            "token": auth_payload["token"],
            "code": "000001",
            "stock_name": "平安银行",
            "etf_code": "510300",
            "etf_name": "沪深300ETF",
            "sector_name": "金融板块",
        },
    )
    assert add_response.status_code == 200

    summary_response = client.get(
        "/watchlist/summary",
        params={"user_id": auth_payload["user_id"], "token": auth_payload["token"]},
    )
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()

    assert summary_payload["count"] == 1
    item = summary_payload["items"][0]
    preview = render_watchlist_card_preview(item)

    print(preview)

    assert "分钟图预览" in preview
    assert "盘中高点" in preview
    assert "盘中低点" in preview
    assert "← 最新" in preview
    assert "平安银行" in preview
    assert runtime is not None
