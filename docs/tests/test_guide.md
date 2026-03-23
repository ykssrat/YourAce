YourAce 测试与脚本使用手册

一、这份文档现在解决什么问题

这份文档只根据当前仓库里真实存在的 `tests/*.py` 来写。

旧版测试向导的问题主要有两个：

- 只讲了诊股、荐股、新闻几个脚本，没把服务接口测试和单元测试说清楚
- 命令路径已经失效，仓库里现在是 `tests/test_xxx.py`，不是以前的 `tests/integration/...`

下面所有命令都按当前仓库结构更新过，可以直接照着跑。

二、先决条件

在项目根目录 `D:\git_project\YourAce` 执行命令。

建议统一使用项目虚拟环境：

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\pytest.exe --version
```

如果上面两条命令能输出版本号，说明 Python 测试环境已经可用。

三、当前 tests 目录里到底有什么

当前仓库可见测试文件如下：

- `tests/test_api_server.py`
- `tests/test_asset_loader.py`
- `tests/test_backtest_engine.py`
- `tests/test_bic_pruner.py`
- `tests/test_local_api_smoke.py`
- `tests/test_local_api_news.py`
- `tests/test_local_api_diagnose.py`
- `tests/test_local_api_recommend.py`

按用途分成三类：

1. 服务接口测试

- `tests/test_api_server.py`

2. 会自动拉起本地后端的脚本/烟雾测试

- `tests/test_local_api_smoke.py`
- `tests/test_local_api_news.py`
- `tests/test_local_api_diagnose.py`
- `tests/test_local_api_recommend.py`

3. 纯单元测试

- `tests/test_asset_loader.py`
- `tests/test_backtest_engine.py`
- `tests/test_bic_pruner.py`

四、最推荐先跑的 6 条命令

1. 健康检查 + search/analyze/news 接口基础验证

```powershell
.\.venv\Scripts\pytest.exe tests/test_api_server.py -q
```

这组测试不需要你手动先起服务，它直接用 FastAPI 的 `TestClient` 调 `app`。

它验证的是：

- `/health` 能否返回 `{"status":"ok"}`
- `/search` 是否能返回 `items`
- `/analyze` 是否返回 `label`、`horizon_signals`、`latest_news`
- `/news` 是否能返回资讯列表

2. 本地自动起服务，验证 analyze 最小闭环

```powershell
.\.venv\Scripts\python.exe tests/test_local_api_smoke.py --code 000001
```

这个脚本会自动：

- 启动本地 `uvicorn`
- 轮询 `/health`
- 请求 `/analyze`
- 打印标签、三维信号、选中特征、原始 JSON

适合用来确认“服务能不能真的在本地跑起来”。

3. 本地自动起服务，验证 diagnose 接口

```powershell
.\.venv\Scripts\python.exe tests/test_local_api_diagnose.py --code 600519
```

这个脚本会请求 `/diagnose`，输出重点是：

- `label`
- `horizon_signals.short / mid / long`
- `matrix.short / mid / long`

如果你要看某个具体标的的诊股结果，这个脚本最直接。

4. 本地自动起服务，验证新闻抓取链路

```powershell
.\.venv\Scripts\python.exe tests/test_local_api_news.py --include-news --code 600519
```

这个脚本只关注一件事：

- `include_news=True` 时，`/analyze` 返回的 `latest_news` 是否非空

如果你怀疑新闻链路挂了，先跑它。

5. 自动起服务，按信号批量筛资产

```powershell
.\.venv\Scripts\python.exe tests/test_local_api_recommend.py --signals short SELL --top-n 20 --round-size 20 --max-rounds 5
```

这个脚本会：

- 自动启动本地后端
- 从资产池里批量扫标的
- 按 `horizon_signals` 过滤
- 输出命中的推荐结果

最近如果市场整体下跌，用 `SELL` 比 `BUY` 更容易出结果。

6. 跑纯单元测试，检查基础模块

```powershell
.\.venv\Scripts\pytest.exe tests/test_asset_loader.py tests/test_backtest_engine.py tests/test_bic_pruner.py -q
```

这组不依赖启动本地 API，适合快速确认底层逻辑有没有被改坏。

五、服务怎么测

这部分是旧文档缺得最明显的地方。

当前仓库里“服务测试”有两种方式。

第一种：直接测 FastAPI app，不起外部服务

```powershell
.\.venv\Scripts\pytest.exe tests/test_api_server.py -q
```

特点：

- 快
- 不需要手动启动 `uvicorn`
- 适合先验证接口字段结构是不是正常

限制：

- 它验证的是应用内部逻辑
- 不是完整的“真实本地服务进程”联调

第二种：让脚本自动起本地服务，再发 HTTP 请求

```powershell
.\.venv\Scripts\python.exe tests/test_local_api_smoke.py --code 000001
.\.venv\Scripts\python.exe tests/test_local_api_diagnose.py --code 600519
.\.venv\Scripts\python.exe tests/test_local_api_news.py --include-news --code 600519
```

特点：

- 更接近真实联调
- 会走 `uvicorn -> /health -> /analyze 或 /diagnose`
- 能更早暴露端口占用、服务起不来、依赖缺失等问题

如果你是要测“服务到底能不能跑”，优先跑这一组。

六、每个测试文件具体怎么用

1. `tests/test_api_server.py`

推荐命令：

```powershell
.\.venv\Scripts\pytest.exe tests/test_api_server.py -q
```

用途：

- 测 `/health`
- 测 `/search`
- 测 `/analyze`
- 测 `/news`

适用场景：

- 改了 `scripts/api/server.py`
- 改了接口返回字段
- 想快速看接口有没有明显回归

2. `tests/test_local_api_smoke.py`

推荐命令：

```powershell
.\.venv\Scripts\python.exe tests/test_local_api_smoke.py --code 000001
```

可用参数：

- `--code`：股票 / ETF / 基金代码，默认 `000001`
- `--include-news`：是否抓新闻
- `--port`：指定测试端口，默认读 `YOURACE_API_TEST_PORT`，否则用 `8010`

它会打印：

- 接口地址
- 代码
- 新闻开关
- 综合标签 `label`
- 三维信号 `short / mid / long`
- 选中特征
- 原始响应 JSON

3. `tests/test_local_api_diagnose.py`

推荐命令：

```powershell
.\.venv\Scripts\python.exe tests/test_local_api_diagnose.py --code 600519
```

可用参数：

- `--code`：待诊股代码
- `--include-news`：是否带新闻
- `--port`：指定测试端口

它会自动挑可用端口，并调用 `/diagnose`。

适用场景：

- 改了诊股逻辑
- 改了矩阵输出
- 想看某个标的当前三维结论

4. `tests/test_local_api_news.py`

推荐命令：

```powershell
.\.venv\Scripts\python.exe tests/test_local_api_news.py --include-news --code 600519
```

可用参数：

- `--code`
- `--include-news`
- `--port`

它主要验证：

- `news_enabled` 为 `True`
- `latest_news` 是非空数组

如果只是想确认新闻功能有没有死掉，不用跑别的，先跑它就够。

5. `tests/test_local_api_recommend.py`

推荐命令：

```powershell
.\.venv\Scripts\python.exe tests/test_local_api_recommend.py --signals short SELL --top-n 20 --round-size 20 --max-rounds 5
```

这个脚本参数最多，也是当前最接近“批量筛选”实际使用方式的测试脚本。

常用参数：

- `--signals`
  用来看法过滤条件
  支持以下几种写法：

```powershell
.\.venv\Scripts\python.exe tests/test_local_api_recommend.py --signals SELL
.\.venv\Scripts\python.exe tests/test_local_api_recommend.py --signals short SELL
.\.venv\Scripts\python.exe tests/test_local_api_recommend.py --signals short SELL mid SELL long HOLD
.\.venv\Scripts\python.exe tests/test_local_api_recommend.py --signals ANY
```

- `--universe-limit`
  扫描候选资产上限，默认 `500`

- `--top-n`
  返回结果数上限，默认 `20`

- `--round-size`
  每轮扫描多少个标的，默认 `20`

- `--max-rounds`
  最多跑几轮，默认 `2`

- `--include-news`
  扫描时是否顺便抓新闻

- `--skip-stock-list-update`
  跳过自动更新 `stock_list`

- `--cache-file`
  信号缓存文件，默认 `configs/recommend_signal_cache.json`

- `--refresh-cache`
  忽略旧缓存，强制重新计算

- `--cache-max-age-days`
  缓存保鲜天数，默认 `3`

- `--stale-refresh-budget`
  单次运行最多刷新多少条过期缓存，默认 `20`

- `--port`
  指定服务端口，默认 `8010`

补充说明：

- 这个脚本会自动尝试起本地后端
- 如果缺少 `datas/raw/stock_list.*`，它会尝试运行 `scripts/processed/build_stock_list.py`
- 它会把分析结果写进 `configs/recommend_signal_cache.json`

如果结果是 0 命中，不一定是程序有问题，也可能只是当天市场条件不满足。

6. `tests/test_asset_loader.py`

推荐命令：

```powershell
.\.venv\Scripts\pytest.exe tests/test_asset_loader.py -q
```

它验证的是：

- `stock_list`
- `etf_list`
- `open_fund_nav`

三类缓存能不能被统一加载、识别资产类型、反查资产名称。

如果你改了 `scripts/utils/asset_loader.py`，优先跑这个。

7. `tests/test_backtest_engine.py`

推荐命令：

```powershell
.\.venv\Scripts\pytest.exe tests/test_backtest_engine.py -q
```

它验证的是：

- 回测结果是否返回核心指标
- 是否按代码拆分 `by_code`
- 前后结果差分是否正确
- 缺字段时是否抛异常

如果你改了轻量回测引擎，先跑它。

8. `tests/test_bic_pruner.py`

推荐命令：

```powershell
.\.venv\Scripts\pytest.exe tests/test_bic_pruner.py -q
```

它验证的是：

- 相关特征能不能被选中
- 缺失特征是否正确报错
- 空输入是否正确报错

如果你改了特征剪枝逻辑，先跑它。

七、推荐测试顺序

如果你刚改完服务端，推荐按下面顺序来：

1. 先跑接口基础测试

```powershell
.\.venv\Scripts\pytest.exe tests/test_api_server.py -q
```

2. 再跑本地服务烟雾测试

```powershell
.\.venv\Scripts\python.exe tests/test_local_api_smoke.py --code 000001
```

3. 再按功能专项测试

```powershell
.\.venv\Scripts\python.exe tests/test_local_api_diagnose.py --code 600519
.\.venv\Scripts\python.exe tests/test_local_api_news.py --include-news --code 600519
.\.venv\Scripts\python.exe tests/test_local_api_recommend.py --signals short SELL --top-n 20 --round-size 20 --max-rounds 5
```

4. 最后补底层单元测试

```powershell
.\.venv\Scripts\pytest.exe tests/test_asset_loader.py tests/test_backtest_engine.py tests/test_bic_pruner.py -q
```

八、如果你只想验证“服务能不能跑”

最小命令组合如下：

```powershell
.\.venv\Scripts\pytest.exe tests/test_api_server.py -q
.\.venv\Scripts\python.exe tests/test_local_api_smoke.py --code 000001
```

第一条看接口逻辑。
第二条看真实本地服务进程。

这两条都过了，至少说明当前服务基础链路是通的。

九、常见问题

1. PowerShell 提示找不到 `.venv/Scripts/python.exe`

请用 Windows 风格路径：

```powershell
.\.venv\Scripts\python.exe
```

不要写成：

```powershell
.venv/Scripts/python.exe
```

2. 本地服务启动失败

优先检查：

- `.venv` 是否存在
- `fastapi`、`uvicorn` 是否装好
- `8010` 端口是否被占用

部分脚本会自动换端口，但不是所有脚本都会。

3. 推荐脚本 0 命中

不一定是 bug。

先确认：

- 你的筛选条件是不是太严格
- 当天市场是不是整体偏弱
- `stock_list` 缓存是不是太旧
- 是否需要改用 `SELL` 或 `ANY` 先确认链路

4. 新闻脚本没有返回新闻

先跑：

```powershell
.\.venv\Scripts\python.exe tests/test_local_api_news.py --include-news --code 600519
```

如果还是空，再看新闻抓取源是否异常。

十、一句话结论

当前仓库的测试不只是在测诊股、荐股、新闻。

真正应该这样理解：

- `test_api_server.py` 负责接口层
- `test_local_api_*.py` 负责本地服务链路
- `test_asset_loader.py / test_backtest_engine.py / test_bic_pruner.py` 负责底层模块

以后你要看“服务怎么测”，先看第五节，不要再只盯着诊股和荐股脚本。
