from __future__ import annotations

from pathlib import Path

from scripts.utils.asset_loader import detect_asset_type, get_asset_name, load_assets


def test_load_assets_merges_stock_etf_and_open_fund_caches(tmp_path: Path) -> None:
    (tmp_path / "stock_list.csv").write_text("code,name\n600123,测试股票\n", encoding="utf-8")
    (tmp_path / "etf_list.csv").write_text("代码,名称\n515999,测试ETF\n", encoding="utf-8")
    (tmp_path / "open_fund_nav.csv").write_text("基金代码,基金简称\n169999,测试基金A\n", encoding="utf-8")

    assets = load_assets(keyword="", limit=1000, raw_dir=str(tmp_path))
    assets_by_code = {item["code"]: item["name"] for item in assets}

    assert assets_by_code["600123"] == "测试股票"
    assert assets_by_code["515999"] == "测试ETF"
    assert assets_by_code["169999"] == "测试基金A"
    assert detect_asset_type("515999", assets_by_code["515999"]) == "etf"
    assert detect_asset_type("169999", assets_by_code["169999"]) == "fund"
    assert get_asset_name("515999", raw_dir=str(tmp_path)) == "测试ETF"
    assert get_asset_name("169999", raw_dir=str(tmp_path)) == "测试基金A"
