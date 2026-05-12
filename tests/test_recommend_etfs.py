"""测试 recommend_etfs 的持仓命中与回退逻辑。"""

from __future__ import annotations

from scripts.services import realtime_watchlist as rw


def _make_runtime() -> rw.WatchlistRuntime:
    return rw.WatchlistRuntime(config=rw.RuntimeConfig(), backend=rw._MemoryJsonStoreBackend())


def test_recommend_etfs_with_holdings(monkeypatch):
    runtime = _make_runtime()

    # 限定资产池只有一个 ETF
    monkeypatch.setattr(rw, "load_assets", lambda keyword="", limit=10000: [{"code": "510300", "name": "沪深300ETF"}])
    monkeypatch.setattr(rw, "detect_asset_type", lambda code, name: "etf" if code == "510300" else "stock")

    # 模拟该 ETF 的成分包含目标股票 000001
    monkeypatch.setattr(rw.WatchlistRuntime, "_fetch_etf_holdings", lambda self, etf_code: ["000001"])

    res = runtime.recommend_etfs("000001", stock_name="平安银行", limit=5)
    assert isinstance(res, list)
    assert len(res) >= 1
    assert res[0]["code"] == "510300"
    assert "display_name" in res[0]
    assert "510300" in res[0]["display_name"]


def test_recommend_etfs_fallback_to_industry(monkeypatch):
    runtime = _make_runtime()

    # 资产池包含一个行业相关 ETF
    monkeypatch.setattr(rw, "load_assets", lambda keyword="", limit=10000: [{"code": "515999", "name": "白酒ETF"}])
    monkeypatch.setattr(rw, "detect_asset_type", lambda code, name: "etf" if code == "515999" else "stock")

    # 模拟无法拿到成分（返回空），迫使回退到行业匹配
    monkeypatch.setattr(rw.WatchlistRuntime, "_fetch_etf_holdings", lambda self, etf_code: [])
    monkeypatch.setattr(rw.WatchlistRuntime, "_get_stock_industry", lambda self, c, n: "白酒")

    res = runtime.recommend_etfs("000002", stock_name="测试股票", limit=5)
    assert any(item["code"] == "515999" for item in res)
    found = next(item for item in res if item["code"] == "515999")
    assert ("白酒" in found.get("matched_keywords", [])) or found.get("score", 0) >= 1


def test_recommend_etfs_broad_defaults(monkeypatch):
    runtime = _make_runtime()

    # 资产池中包含默认推荐列表里的一个代码
    default_code = rw._DEFAULT_RECOMMENDED_ETF_CODES[0]
    monkeypatch.setattr(rw, "load_assets", lambda keyword="", limit=10000: [{"code": default_code, "name": "默认ETF"}])
    monkeypatch.setattr(rw, "detect_asset_type", lambda code, name: "etf")
    monkeypatch.setattr(rw.WatchlistRuntime, "_fetch_etf_holdings", lambda self, etf_code: [])

    res = runtime.recommend_etfs("999999", stock_name="不存在的股票", limit=5)
    assert any(item["code"] == default_code for item in res)
