"""自选池实时信号接口测试。"""

from __future__ import annotations

from datetime import datetime as real_datetime

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from scripts.api.server import app
from scripts.services import realtime_watchlist as rw


client = TestClient(app)


class _FixedDatetime(real_datetime):
    @classmethod
    def now(cls, tz=None):
        return real_datetime(2026, 4, 29, 11, 0, 0, tzinfo=tz)


def _install_runtime(monkeypatch) -> rw.WatchlistRuntime:
    runtime = rw.WatchlistRuntime(config=rw.RuntimeConfig(), backend=rw._MemoryJsonStoreBackend())
    monkeypatch.setattr("scripts.api.server.get_watchlist_runtime", lambda: runtime)
    return runtime


def _fake_spot_em() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"代码": "000001", "名称": "平安银行", "最新价": 10.0, "涨跌幅": -3.0, "成交量": 1000, "成交额": 10000, "换手率": 1.2},
            {"代码": "510300", "名称": "沪深300ETF", "最新价": 5.0, "涨跌幅": -1.0, "成交量": 2000, "成交额": 20000, "换手率": 0.5},
        ]
    )


def _fake_hist_min_em(symbol: str = "000001", **_: object) -> pd.DataFrame:
    if symbol == "000001":
        closes = np.linspace(100, 90, 40)
    else:
        closes = np.linspace(50, 49, 40)

    times = pd.date_range("2026-04-29 10:20:00", periods=40, freq="1min")
    volumes = np.arange(1, 41)
    return pd.DataFrame({"时间": times, "收盘": closes, "成交量": volumes})


def test_signal_combination_rules() -> None:
    """合买必须至少两个买入信号，卖出则由更高优先级信号直接触发。"""
    sell_result = rw.combine_signal_candidates(
        [
            rw.SignalCandidate("P1", "SELL", "P1 卖出", ""),
            rw.SignalCandidate("P2", "BUY", "P2 买入", ""),
            rw.SignalCandidate("P4", "BUY", "P4 买入", ""),
        ]
    )
    assert sell_result["final_action"] == "SELL"
    assert sell_result["notify"] is True
    assert sell_result["primary_signal"] == "P1"

    silent_result = rw.combine_signal_candidates(
        [
            rw.SignalCandidate("P1", "BUY", "P1 买入", ""),
            rw.SignalCandidate("P2", "HOLD", "", ""),
            rw.SignalCandidate("P3", "HOLD", "", ""),
            rw.SignalCandidate("P4", "HOLD", "", ""),
        ]
    )
    assert silent_result["final_action"] == "HOLD"
    assert silent_result["notify"] is False

    buy_result = rw.combine_signal_candidates(
        [
            rw.SignalCandidate("P1", "HOLD", "", ""),
            rw.SignalCandidate("P2", "BUY", "P2 买入", ""),
            rw.SignalCandidate("P3", "HOLD", "", ""),
            rw.SignalCandidate("P4", "BUY", "P4 买入", ""),
        ]
    )
    assert buy_result["final_action"] == "BUY"
    assert buy_result["notify"] is True


def test_watchlist_api_flow(monkeypatch) -> None:
    """验证注册、自选池加入、摘要刷新和通知出队的完整闭环。"""
    runtime = _install_runtime(monkeypatch)
    monkeypatch.setattr(rw.ak, "stock_zh_a_spot_em", _fake_spot_em)
    monkeypatch.setattr(rw.ak, "stock_zh_a_hist_min_em", _fake_hist_min_em)
    monkeypatch.setattr(rw, "datetime", _FixedDatetime)

    register_response = client.post("/auth/register", json={"username": "alice", "password": "password123"})
    assert register_response.status_code == 200
    register_payload = register_response.json()
    user_id = register_payload["user_id"]
    token = register_payload["token"]

    add_response = client.post(
        "/watchlist/add",
        json={
            "user_id": user_id,
            "token": token,
            "code": "000001",
            "stock_name": "平安银行",
            "etf_code": "510300",
            "etf_name": "沪深300ETF",
            "sector_name": "金融板块",
        },
    )
    assert add_response.status_code == 200
    add_payload = add_response.json()
    assert add_payload["item"]["code"] == "000001"

    list_response = client.get("/watchlist", params={"user_id": user_id, "token": token})
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["count"] == 1

    summary_response = client.get("/watchlist/summary", params={"user_id": user_id, "token": token})
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload["count"] == 1
    item = summary_payload["items"][0]
    assert item["signals"]["decision"]["final_action"] == "BUY"
    assert item["signals"]["decision"]["notify"] is True
    assert item["intraday_high"] >= item["intraday_low"]
    assert item["intraday_high_time"]
    assert item["intraday_low_time"]
    assert item["notification"]["message"].startswith("平安银行（000001）买入-11:00-")

    queue_response = client.get("/watchlist/notifications", params={"user_id": user_id, "token": token})
    assert queue_response.status_code == 200
    queue_payload = queue_response.json()
    assert queue_payload["count"] == 1
    assert queue_payload["items"][0]["code"] == "000001"

    # 这条引用只用于防止 runtime 被误判为未使用，且便于单测时直接调试。
    assert runtime is not None
