YourAce 测试与脚本使用手册

一、文档目标

这份文档只做一件事：说明当前常用测试脚本怎么运行、参数是什么、输出看什么。

说明：

- 本文档已按当前代码修订。
- 旧版基于 `score` 的筛选、阈值和强烈看多/强烈看空描述已不再适用。

二、推荐先跑的 4 条命令

1. 最小闭环分析验证（单代码）

```bash
.venv/Scripts/python.exe tests/integration/test_local_api_smoke.py --code 002384
```

2. 单标的诊股

```bash
.venv/Scripts/python.exe tests/integration/test_local_api_diagnose.py --code 600519
```

3. 反向参数筛股（多轮）

```bash
.venv/Scripts/python.exe tests/integration/test_local_api_recommend.py --signals short BUY --top-n 20 --round-size 20 --max-rounds 5 --skip-stock-list-update
```

4. 全链路集成验证

```bash
.venv/Scripts/python.exe -m pytest tests/integration/test_end_to_end_pipeline.py -q -s
```

三、可直接命令行运行的 Python 文件

1) `tests/integration/test_local_api_smoke.py`

用途：启动本地后端并调用 `/analyze`，验证最小分析链路。

命令：

```bash
.venv/Scripts/python.exe tests/integration/test_local_api_smoke.py --code 600519
```

参数：

- `--code`：证券代码，默认 `000001`
- `--include-news`：开启新闻抓取，默认关闭
- `--port`：指定端口；不传时读取 `YOURACE_API_TEST_PORT` 或默认 `8010`

当前输出重点：

- 综合标签 `label`
- 三维信号 `horizon_signals`
- 选中特征 `selected_features`

2) `tests/integration/test_local_api_diagnose.py`

用途：启动本地后端并调用 `/diagnose`，输出单标的三维看法矩阵及完整诊股结果。

命令：

```bash
.venv/Scripts/python.exe tests/integration/test_local_api_diagnose.py --code 600519
```

参数：

- `--code`：证券代码，默认 `000001`
- `--include-news`：是否开启新闻抓取，默认关闭
- `--port`：指定端口；不传时读取 `YOURACE_API_TEST_PORT` 或默认 `8010`

当前输出重点：

- 综合标签 `label`
- 三维信号：
  - `short`
  - `mid`
  - `long`
- 看法矩阵：
  - `short`
  - `mid`
  - `long`

3) `tests/integration/test_local_api_recommend.py`

用途：按看法矩阵信号扫描候选资产，筛选满足条件的代码。

命令：

```bash
.venv/Scripts/python.exe tests/integration/test_local_api_recommend.py --signals short BUY --top-n 20 --round-size 20 --max-rounds 5
```

参数：

- `--signals`：反向条件，格式为 `horizon + signal`，例如 `short BUY`
- 可选：`--signals ANY`，表示不过滤窗口信号
- `--top-n`：返回结果上限，默认 `20`
- `--universe-limit`：扫描候选资产上限，默认 `500`
- `--round-size`：每轮试验股票数，默认 `20`
- `--max-rounds`：最大轮次数，默认 `2`
- `--include-news`：分析时是否抓新闻，默认关闭
- `--skip-stock-list-update`：跳过自动更新 `stock_list`
- `--cache-file`：分析缓存文件路径，默认 `configs/recommend_signal_cache.json`
- `--refresh-cache`：忽略缓存并强制重新计算看法矩阵
- `--cache-max-age-days`：缓存保鲜天数，默认 `3`
- `--stale-refresh-budget`：单次运行最多刷新多少个过期缓存，默认 `20`
- `--port`：指定后端端口；不传时优先 `8010`，冲突自动切换

当前效率机制：

- 脚本会把已分析代码的 `label` 与 `horizon_signals` 写入 JSON 缓存
- 下次再跑相同条件时，优先读取缓存，减少重复调用 `/analyze`
- 多轮模式下会累计各轮命中结果，直到达到 `--top-n` 或跑满 `--max-rounds`

当前筛选逻辑：

- 不再按 `score` 阈值筛选
- 只按 `label`、`horizon_signals` 和给定信号条件筛选
- 结果排序采用：
  - 总体标签优先级
  - 三窗口 `BUY` 数量

4) `scripts/integration/run_end_to_end.py`

用途：执行从数据处理到 API 分析的端到端联调。

命令：

```bash
d:/QMT/YourAce/.venv/Scripts/python.exe scripts/integration/run_end_to_end.py
```

当前输出重点：

- `code`
- `label`
- `as_of_date`
- `news_count`

5) `scripts/api/server.py`

用途：FastAPI 服务入口（通常用 `uvicorn` 启动）。

命令：

```bash
d:/QMT/YourAce/.venv/Scripts/python.exe -m uvicorn scripts.api.server:app --host 0.0.0.0 --port 8000
```

当前端点：

- `GET /search`
- `GET /health`
- `GET /news`
- `POST /analyze`
- `POST /screen`
- `POST /diagnose`

当前请求/响应要点：

- `/analyze` 请求：`{ code, strategy?, include_news?, long_fund_trend? }`
- `/screen` 请求：`{ asset_type, horizon, strategy, opinion, round_size, offset }`
- `/diagnose` 请求：`{ code, strategy?, include_news? }`

当前主输出不再依赖 `score`，而是：

- `label`
- `horizon_signals`
- `matrix`

四、pytest 常用命令

跑全部测试：

```bash
d:/QMT/YourAce/.venv/Scripts/python.exe -m pytest -q
```

只跑集成测试：

```bash
d:/QMT/YourAce/.venv/Scripts/python.exe -m pytest tests/integration -q -s
```

只跑单元测试：

```bash
d:/QMT/YourAce/.venv/Scripts/python.exe -m pytest tests/unit -q
```

五、常见问题

1) 端口占用

- 现象：`8010` 被占用
- 处理：脚本会自动切换到 `8011`、`8012` 等可用端口

2) `stock_list` 更新失败

- 现象：数据源返回异常
- 处理：使用 `--skip-stock-list-update` 跳过更新，先完成筛选流程

3) 多轮无命中

- 常见原因：信号条件偏严，例如 `short=BUY` 同时还要求方向一致
- 处理：先把条件放宽到：
  - `--signals short BUY`
  - 或 `--signals ANY`

六、如果你就是想找“短期看多，准备买入”的票

更实用的做法：

1. 先保留短期条件，不限制其他窗口

```bash
.venv/Scripts/python.exe tests/integration/test_local_api_recommend.py --signals short BUY --top-n 20 --round-size 20 --max-rounds 5 --skip-stock-list-update
```

2. 先看全部候选，再人工筛节奏

```bash
.venv/Scripts/python.exe tests/integration/test_local_api_recommend.py --signals ANY --top-n 20 --round-size 20 --max-rounds 5 --skip-stock-list-update
```

一句话建议：

- 短线买点：先看 `short=BUY`
- 更稳一点：再看 `mid/long` 是否没有明显转空

七、如何使用诊股（`/diagnose`）

诊股是在筛股命中标的之后的“深看”动作，用于判断当前介入时机是否合适。

典型工作流：

1. 用筛股脚本或 App 选股 Tab 找到候选标的
2. 对候选标的调用 `/diagnose`
3. 结合 `matrix` 与三窗口信号判断是否进一步研究

当前矩阵看法含义：

- `BUY`：看多
- `HOLD`：观望
- `SELL`：看空

常见诊股场景：

场景 A：确认短线买点

- 期望：`matrix.short = BUY`

场景 B：确认中线趋势向好

- 期望：`matrix.mid = BUY`

场景 C：三维共振强势

- 期望：`short + mid + long` 全部为 `BUY`

命令行快速诊股：

```bash
.venv/Scripts/python.exe tests/integration/test_local_api_diagnose.py --code 000001
```

加入新闻抓取：

```bash
.venv/Scripts/python.exe tests/integration/test_local_api_diagnose.py --code 000001 --include-news
```

一句话总结：

- 筛股找候选，诊股做确认
- 当前以三窗口看法矩阵作为主判断，而不是以总分作为主判断
