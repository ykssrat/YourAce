YourAce 测试与脚本使用手册

一、文档目标

这份文档只做一件事：告诉你“每个 Python 文件怎么用、要加什么参数、参数含义是什么”。

二、推荐先跑的 3 条命令

1. 最小闭环评分验证（单代码）

.venv/Scripts/python.exe tests/integration/test_local_api_smoke.py --code 002384

2. 反向参数筛股（多轮）

.venv/Scripts/python.exe tests/integration/test_local_api_recommend.py --signals short STRONG BUY --min-score 80 --top-n 20 --round-size 20 --max-rounds 5 --skip-stock-list-update

3. 全链路集成验证

.venv/Scripts/python.exe -m pytest tests/integration/test_end_to_end_pipeline.py -q -s

4. 单标的诊股

.venv/Scripts/python.exe tests/integration/test_local_api_diagnose.py --code 600519

三、可直接命令行运行的 Python 文件

1) tests/integration/test_local_api_smoke.py

用途：启动本地后端并调用 /analyze，验证评分主链路。

命令：

.venv/Scripts/python.exe tests/integration/test_local_api_smoke.py --code 600519

参数：

- --code: 证券代码，默认 000001
- --include-news: 开启新闻抓取，默认关闭
- --port: 指定端口；不传时读取 YOURACE_API_TEST_PORT 或默认 8010

2) tests/integration/test_local_api_diagnose.py

用途：启动本地后端并调用 /diagnose，输出单标的三维看法矩阵及完整诊股结果。

命令：

.venv/Scripts/python.exe tests/integration/test_local_api_diagnose.py --code 600519

参数：

- --code: 证券代码，默认 000001
- --include-news: 是否开启新闻抓取，默认关闭
- --port: 指定端口；不传时读取 YOURACE_API_TEST_PORT 或默认 8010

输出示例：

  综合评分: 73
  综合标签: BUY
  三维信号:
    short: direction=BUY  strength=STRONG
    mid  : direction=BUY  strength=NORMAL
    long : direction=HOLD strength=NORMAL
  看法矩阵:
    短线(short): 强烈看多 ▲▲
    中线(mid  ): 看多      ▲
    长线(long ): 中性      —

3) tests/integration/test_local_api_recommend.py

用途：按反向参数扫描候选资产，筛选满足信号与最低分数的代码。

命令：

.venv/Scripts/python.exe tests/integration/test_local_api_recommend.py --signals short STRONG BUY --min-score 80 --top-n 20 --round-size 20 --max-rounds 5

参数：

- --signals: 反向条件，格式为 horizon + signal；例如 short STRONG BUY
	- 可选：--signals ANY（仅按分数筛选，不限制 short/mid/long）
- --min-score: 最低分数阈值，默认 80
- --top-n: 返回结果上限，默认 20
- --universe-limit: 扫描候选资产上限，默认 500
- --round-size: 每轮试验股票数，默认 20
- --max-rounds: 最大轮次数，默认 2
- --include-news: 分析时是否抓新闻，默认关闭
- --skip-stock-list-update: 跳过自动更新 stock_list，数据源不稳定时推荐开启
- --cache-file: 评分缓存文件路径，默认 configs/recommend_score_cache.json
- --refresh-cache: 忽略缓存并强制重新计算评分
- --cache-max-age-days: 缓存保鲜天数，默认 3
- --stale-refresh-budget: 单次运行最多刷新多少个过期缓存，默认 20
- --port: 指定后端端口；不传时优先 8010，冲突自动切换

效率机制（重点）：

- 脚本会把已算过的代码评分写入 JSON 缓存。
- 下次再跑同样筛选时，优先读取缓存，减少重复调用 /analyze。
- 典型场景：第一轮慢，第二轮明显变快。
- 多轮模式下会累计各轮命中结果，直到达到 --top-n 或跑满 --max-rounds，不会像之前那样“命中一只就提前结束”。

筛选诊断输出（重点）：

- 脚本会输出：评分达标、信号不匹配。
- 如果“评分达标 > 0 且 命中=0”，通常说明信号条件过严。
- 例如：score>=80 但 short=HOLD，会被 --signals short STRONG BUY 排除。

只按分数筛选示例（不加 short/mid/long 限制）：

.venv/Scripts/python.exe tests/integration/test_local_api_recommend.py --signals ANY --min-score 80 --top-n 20 --round-size 20 --max-rounds 5 --skip-stock-list-update

跨交易日策略（避免“第二天缓存作废”）：

- 通过 --cache-max-age-days 控制缓存保鲜期（默认 3 天）。
- 超过保鲜期的缓存不会一次性全量重算，而是按 --stale-refresh-budget 增量刷新。
- 当后端请求临时失败时，脚本会优先回退到已有缓存，保证流程不中断。

跨日推荐命令：

.venv/Scripts/python.exe tests/integration/test_local_api_recommend.py --signals short STRONG BUY --min-score 80 --top-n 20 --round-size 20 --max-rounds 5 --skip-stock-list-update --cache-max-age-days 3 --stale-refresh-budget 20

3) scripts/processed/fetch_data.py

用途：拉取股票/ETF/基金基础数据并写入 datas/raw。

命令：

d:/QMT/YourAce/.venv/Scripts/python.exe scripts/processed/fetch_data.py

参数：

- 无命令行参数。
- 配置来自 configs/data_config.yaml。

4) scripts/processed/clean_data.py

用途：清洗 datas/raw 下表格，统一列名、去重、标准化时间列。

命令：

d:/QMT/YourAce/.venv/Scripts/python.exe scripts/processed/clean_data.py

参数：

- 无命令行参数。
- 配置来自 configs/data_config.yaml。

5) scripts/processed/build_stock_list.py

用途：单独构建 datas/raw/stock_list 供反向筛股使用。

命令：

d:/QMT/YourAce/.venv/Scripts/python.exe scripts/processed/build_stock_list.py

参数：

- 无命令行参数。
- 配置来自 configs/data_config.yaml。

6) scripts/integration/run_end_to_end.py

用途：执行从数据处理到 API 分析的端到端联调。

命令：

d:/QMT/YourAce/.venv/Scripts/python.exe scripts/integration/run_end_to_end.py

参数：

- 无命令行参数。
- 文件内默认 enable_online_fetch=True（会尝试在线抓取）。

7) scripts/api/server.py

用途：FastAPI 服务入口（通常用 uvicorn 启动，不直接 python 运行）。

命令：

d:/QMT/YourAce/.venv/Scripts/python.exe -m uvicorn scripts.api.server:app --host 0.0.0.0 --port 8000

参数：

- --host: 监听地址，局域网联调用 0.0.0.0
- --port: 端口，默认可用 8000

服务启动后可用的 API 端点说明：

GET  /search?query=贵州&limit=10     搜索标的
GET  /health                         健康检查
POST /analyze    { code, include_news?, long_fund_trend? }                               评分分析
POST /screen     { asset_type, horizon, score_operator, score_threshold, opinion?, ... } 批量筛股
POST /diagnose   { code, include_news? }                                                 单标的诊股（含看法矩阵）

/diagnose 与 /analyze 的区别：

- /analyze 返回基础评分 + 信号；适合只需要 score/label 的场景。
- /diagnose 在此基础上额外返回 matrix 字段，给出短/中/长三个维度的具体看法
  （STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL），供 APP 诊股页展示。

/diagnose 返回字段说明：

- code: 标的代码
- as_of_date: 分析日期
- score: 综合评分（0-100）
- label: 综合看法（BUY / HOLD / SELL）
- horizon_signals: { short, mid, long } 三档信号对象，每档含 direction/strength
- matrix: { short, mid, long } 三档最终看法，取值 STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL
- selected_features: BIC 剪枝后保留的特征名列表
- latest_news: 最新资讯列表（include_news=true 时有内容）

四、全部 Python 文件清单与“怎么用”

说明：

- “可直接运行”表示建议命令行直接执行。
- “pytest 运行”表示通过 pytest 调用。
- “被导入模块”表示不建议直接运行，供其他脚本 import。

A. tests/integration

- tests/integration/test_local_api_smoke.py: 可直接运行 + pytest 运行
- tests/integration/test_local_api_diagnose.py: 可直接运行 + pytest 运行
- tests/integration/test_local_api_recommend.py: 可直接运行
- tests/integration/test_api_server.py: pytest 运行
- tests/integration/test_end_to_end_pipeline.py: pytest 运行
- tests/integration/test_pipeline_placeholder.py: pytest 运行

B. tests/unit

- tests/unit/test_backtest_engine.py: pytest 运行
- tests/unit/test_bic_pruner.py: pytest 运行
- tests/unit/test_calc_features.py: pytest 运行
- tests/unit/test_news_fetcher.py: pytest 运行
- tests/unit/test_placeholder.py: pytest 运行
- tests/unit/test_scoring.py: pytest 运行
- tests/unit/test_signal_generator.py: pytest 运行

C. scripts/api

- scripts/api/server.py: uvicorn 启动

D. scripts/processed

- scripts/processed/fetch_data.py: 可直接运行
- scripts/processed/clean_data.py: 可直接运行
- scripts/processed/build_stock_list.py: 可直接运行

E. scripts/integration

- scripts/integration/run_end_to_end.py: 可直接运行

F. scripts/strategy（被导入模块）

- scripts/strategy/scoring.py
- scripts/strategy/signal_generator.py
- scripts/strategy/livermore.py

G. scripts/features（被导入模块）

- scripts/features/calc_features.py
- scripts/features/bic_pruner.py

H. scripts/backtest（被导入模块）

- scripts/backtest/engine.py

I. scripts/utils（被导入模块）

- scripts/utils/asset_loader.py
- scripts/utils/news_fetcher.py
- scripts/utils/market_scanner.py
- scripts/utils/audit_logger.py

J. scripts/portfolio（被导入模块）

- scripts/portfolio/position_manager.py

五、pytest 常用命令

跑全部测试：

d:/QMT/YourAce/.venv/Scripts/python.exe -m pytest -q

只跑集成测试：

d:/QMT/YourAce/.venv/Scripts/python.exe -m pytest tests/integration -q -s

只跑单元测试：

d:/QMT/YourAce/.venv/Scripts/python.exe -m pytest tests/unit -q

六、常见问题

1. 端口占用

- 现象：8010 被占用。
- 处理：脚本会自动切换到 8011、8012 等可用端口。

2. stock_list 更新失败

- 现象：akshare 返回 HTML 或解析失败。
- 处理：使用 --skip-stock-list-update 跳过更新，先完成筛选流程。

3. 多轮无命中

- 常见原因：条件偏严（如 short=BUY 且 score>=80）。
- 处理：先降 --min-score 到 70 或 60 观察候选分布。

七、如果你就是想找“短期看多，准备买入”的票

不要把条件定成：

- short=BUY 且 score>=80

原因：

- score>=80 往往要求中期、长期也同时偏强。
- 这更像“中短共振强势股”，不是纯短线买点筛选。

更实用的做法：

1. 先保留短期条件，不放宽 short

.venv/Scripts/python.exe tests/integration/test_local_api_recommend.py --signals short BUY --min-score 60 --top-n 20 --round-size 20 --max-rounds 5 --skip-stock-list-update


2. 先看全体高分，再人工挑短线节奏，才用 ANY

.venv/Scripts/python.exe tests/integration/test_local_api_recommend.py --signals ANY --min-score 80 --top-n 20 --round-size 20 --max-rounds 5 --skip-stock-list-update

一句话建议：

- 短线买入：优先看 short=BUY，再看 score 是否 >=60
- 波段/中线配置：再要求 score >=80

八、如何使用诊股（/diagnose）

诊股是在筛股命中标的之后的"深看"动作，用于判断当前介入时机是否合适。

典型工作流：

1. 用筛股脚本或 APP 选股 Tab 找到候选标的（如 600519）
2. 对候选标的调用 /diagnose，拿到三维看法矩阵
3. 结合矩阵决策是否操作

矩阵看法含义（matrix.short / mid / long）：

- STRONG_BUY : 强烈看多——信号方向 BUY 且综合评分 >=80
- BUY        : 看多——信号方向 BUY 且综合评分 <80
- HOLD       : 中性——信号方向不确定
- SELL       : 看空——信号方向 SELL 且综合评分 <80
- STRONG_SELL: 强烈看空——信号方向 SELL 且综合评分 >=80

常见诊股场景：

场景 A：确认短线买点
- 期望：matrix.short = BUY 或 STRONG_BUY
- 参考：score >= 60，mid/long 不限

场景 B：确认中线趋势向好
- 期望：matrix.mid = BUY 或 STRONG_BUY
- 参考：score >= 70

场景 C：三维共振强势（最严格）
- 期望：short + mid + long 全部 BUY/STRONG_BUY
- 参考：score >= 80

命令行快速诊股（脚本自动启动后端）：

.venv/Scripts/python.exe tests/integration/test_local_api_diagnose.py --code 000001

加入新闻抓取：

.venv/Scripts/python.exe tests/integration/test_local_api_diagnose.py --code 000001 --include-news


- 筛股找候选，诊股做确认。
- matrix 三维全为 BUY/STRONG_BUY 才是最放心的介入信号。
