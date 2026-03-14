YourAce 后端接口与最小闭环验证

说明：本文件聚焦后端接口定义与响应结构。
测试操作、脚本命令、参数说明请查看 docs/test_guide.md。

文档目的：

- 最短路径，验证“输入代码 -> 输出分数”是否正常。
- 排除 App、局域网、防火墙等外部因素，先确认评分主链路可运行。

一、接口概览

- GET /health: 健康检查
- GET /search: 证券检索
- POST /analyze: 评分分析
- GET /news: 独立资讯查询

二、/analyze 请求体

- code: 证券代码，必填
- long_fund_trend: 长期基金趋势，默认 0
- include_news: 是否抓取资讯，默认 true

三、/analyze 响应关键字段

- score: 0-100 分
- label: STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL
- horizon_signals: short/mid/long 三维信号
- selected_features: BIC 选中特征
- news_enabled: 本次请求是否开启新闻
- latest_news: 新闻列表；当关闭新闻时为空数组

四、本地最小闭环（推荐先走这条）

1. 启动后端（在仓库根目录执行）

uvicorn scripts.api.server:app --host 0.0.0.0 --port 8000

2. 电脑本机检查

http://127.0.0.1:8000/health

3. 手机同网段检查

http://你的电脑局域网IP:8000/health

4. App 内关闭新闻系统，输入代码后点分析

如果第 2 步都失败，说明后端未启动成功；先看终端报错，不要先改 App。
