"""数据获取模块入口。"""


def fetch_all_assets() -> None:
    """拉取股票、ETF、开放式基金基础行情数据。"""
    raise NotImplementedError("待实现：接入 akshare 并写入 datas/raw")


if __name__ == "__main__":
    fetch_all_assets()
