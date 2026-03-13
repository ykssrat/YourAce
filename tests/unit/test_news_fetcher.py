"""新闻抓取工具单元测试。"""

from scripts.utils.news_fetcher import fetch_latest_news


def test_fetch_latest_news_returns_three_or_less_items() -> None:
    """新闻抓取应返回不超过 limit 的列表。"""
    items = fetch_latest_news("000001", limit=3)
    assert isinstance(items, list)
    assert len(items) <= 3


def test_fetch_latest_news_item_shape() -> None:
    """新闻项应包含标准字段。"""
    items = fetch_latest_news("000001", limit=1)
    assert len(items) == 1
    item = items[0]
    assert set(item.keys()) == {"title", "source", "time", "url"}
