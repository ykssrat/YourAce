YourAce 测试与脚本使用手册

一、文档目标

本文档：说明当前常用测试脚本怎么运行、参数是什么、输出看什么。

说明：

二、推荐先跑的 4 条命令

2. 单标的诊股

```bash
.venv/Scripts/python.exe tests/integration/test_local_api_diagnose.py --code 600519
```

3. 反向参数筛股（多轮）

```bash
.venv/Scripts/python.exe tests/integration/test_local_api_recommend.py --signals short BUY --top-n 20 --round-size 20 --max-rounds 5 --skip-stock-list-update #每轮20个，最多5轮
```

4. 全链路集成验证

```bash
.venv/Scripts/python.exe -m pytest tests/integration/test_end_to_end_pipeline.py -q -s #端到端测试，passed代表存在全部输出
```

三、可直接命令行运行的 Python 文件

(1)新闻：

```bash
.venv/Scripts/python.exe tests/integration/test_local_api_news.py --include-news --code 600519 #查询贵州茅台新闻
```

参数：

- `--code`：证券代码，默认 `000001`
- `--include-news`：开启新闻抓取，默认关闭
- `--port`：指定端口；不传时读取 `YOURACE_API_TEST_PORT` 或默认 `8010`

当前输出重点：

- 综合标签 `label`
- 三维信号 `horizon_signals`
- 选中特征 `selected_features`

2) 诊股：

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
  - 取值：`BUY`、`HOLD`、`SELL`

(3)荐股:

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

- 只按 `label`、`horizon_signals` 和给定信号条件筛选
- 结果排序采用：
  - 总体标签优先级
  - 三窗口 `BUY` 数量



当前输出重点：

- `code`
- `label`
- `as_of_date`
- `news_count`


五、常见问题

1) 端口占用

- 现象：`8010` 被占用
- 处理：脚本会自动切换到 `8011`、`8012` 等可用端口


一句话总结：

- 筛股找候选，诊股做确认
- 当前以三窗口看法矩阵作为主判断

