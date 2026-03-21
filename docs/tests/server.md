# YourAce 服务器最小运行包与部署说明

## 一、这份文档现在要解决什么问题

旧版 `server.md` 主要在讲 `scp / ssh / 重启 uvicorn`，这已经不是当前服务端说明的重点。

现在的服务器说明应该围绕下面这件事展开：

- 服务器负责承载 **已经打包进工程的策略代码**
- 手机 App 只负责通过 API 连接服务器，不直接管理策略实现
- 服务器要准备 **最小运行数据包**
- 服务器应优先通过 `akshare` 拉取并缓存：
  - A 股股票列表
  - ETF 列表
  - 场外公开基金列表
- 手机 App 连接服务器后，直接消费 `/search`、`/analyze`、`/diagnose`、`/screen` 等接口完成指标分析

一句话概括：

> 当前服务端的目标不是“手工上传一个 `server.py`”，而是“打包最小可运行策略服务，让手机 App 能稳定连接并使用”。

## 二、服务端当前职责

当前服务端应承担以下职责：

1. 承载已打包策略
   - `scripts/api`
   - `scripts/engine`
   - `scripts/strategy`
   - `scripts/features`
   - `scripts/utils`

2. 暴露统一 API
   - `GET /health`
   - `GET /search`
   - `GET /news`
   - `POST /analyze`
   - `POST /diagnose`
   - `POST /screen`

3. 为手机 App 提供最小可用资产池
   - 股票
   - ETF
   - 场外基金

4. 为指标分析准备价格序列
   - 优先读取本地缓存
   - 不应把“模拟价格序列”当作线上正式数据源

## 三、最小运行包包含什么

### 1. 代码部分

最小代码包至少包括：

- `scripts/api/server.py`
- `scripts/engine/`
- `scripts/strategy/`
- `scripts/features/`
- `scripts/utils/`
- `configs/`

### 2. 数据部分

最小运行数据包至少包括 `datas/raw` 下的这几类缓存：

- `stock_list.parquet` 或 `stock_list.csv`
- `etf_list.parquet` 或 `etf_list.csv`
- `open_fund_nav.parquet` 或 `open_fund_nav.csv`
- `runtime_asset_manifest.json`

说明：

- `stock_list` 用于 A 股股票资产池
- `etf_list` 用于 ETF 资产池
- `open_fund_nav` 用于场外公开基金资产池
- 当前仓库里的资产加载器已经会合并这三类缓存，而不是只看 `stock_list`

### 3. 真实分析时还需要什么

如果你希望 `/analyze` 或 `/diagnose` 做的是 **真实价格指标分析**，还应该准备对应标的的行情缓存，例如：

- `datas/raw/kline_000001.parquet`
- `datas/raw/kline_510300.parquet`
- `datas/raw/kline_161725.parquet`

当前代码在缺少行情缓存时仍可能降级为模拟序列，这只适合本地冒烟或离线验证，不应该作为正式线上分析依据。

## 四、推荐的数据准备命令

### 方式 A：推荐，直接准备最小服务端资产包

在项目根目录执行：

```bash
.venv/bin/python scripts/processed/package_runtime_assets.py
```

这条命令会：

- 通过 `akshare` 拉取股票、ETF、场外基金三类基础数据
- 写入 `datas/raw`
- 生成 `datas/raw/runtime_asset_manifest.json`

### 方式 B：旧脚本，只能补股票池，不再足够

```bash
.venv/bin/python scripts/processed/build_stock_list.py
```

说明：

- 这个脚本只会构建 `stock_list`
- 它不能完整覆盖 ETF 和场外基金
- 所以它不应该再作为手机 App 服务端的唯一数据准备步骤

## 五、推荐部署顺序

### 1. 上传代码到服务器

把项目同步到服务器，例如：

```bash
scp -i yourace_secret_key.pem -r ./YourAce ubuntu@your-server:~/YourAce
```

### 2. 进入服务器项目目录

```bash
ssh -i yourace_secret_key.pem ubuntu@your-server
cd ~/YourAce
```

### 3. 准备最小运行数据包

```bash
.venv/bin/python scripts/processed/package_runtime_assets.py
```

### 4. 启动 API 服务

```bash
mkdir -p logs
nohup .venv/bin/python -m uvicorn scripts.api.server:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &
```

### 5. 健康检查

```bash
curl -s http://127.0.0.1:8000/health
```

期望返回：

```json
{"status":"ok"}
```

## 六、手机 App 连接服务器后的最小验证

### 1. 搜索资产池是否已经包含股票 / ETF / 基金

```bash
curl -s "http://127.0.0.1:8000/search?query=ETF&limit=10"
```

```bash
curl -s "http://127.0.0.1:8000/search?query=基金&limit=10"
```

### 2. 单标的分析

```bash
curl -s -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d "{\"code\":\"510300\",\"include_news\":false}"
```

### 3. 单标的诊股

```bash
curl -s -X POST http://127.0.0.1:8000/diagnose \
  -H "Content-Type: application/json" \
  -d "{\"code\":\"161725\",\"include_news\":false}"
```

### 4. 资产池筛选

```bash
curl -s -X POST http://127.0.0.1:8000/screen \
  -H "Content-Type: application/json" \
  -d "{\"asset_type\":\"fund\",\"horizon\":\"\",\"opinion\":\"\",\"round_size\":20,\"offset\":0}"
```

验证重点：

- `/search` 不再只返回股票
- `/screen` 对 `etf` / `fund` 有真实候选池
- `/analyze` 和 `/diagnose` 返回 `label + horizon_signals + matrix`
- 不再使用旧版 `score_threshold`、`score_operator`、`horizon_strengths` 文案

## 七、当前正确理解方式

当前手机端接入服务端，应该这样理解：

1. 策略是跟随工程一起打包部署到服务器的
2. 手机 App 只是调用服务器接口，不直接运行策略源码
3. 服务器最少要先准备股票、ETF、场外基金三类缓存
4. 如果要做真实指标分析，还要准备真实行情缓存，而不是依赖模拟序列

## 八、结论

当前 `server.md` 应该从“上传和重启手册”升级为“最小运行包说明”。

最关键的两条结论是：

- 服务器必须先准备 `stock_list + etf_list + open_fund_nav` 三类 AKShare 资产缓存
- 手机 App 连接的是 **已打包策略 + 已准备资产缓存** 的服务端，而不是临时拼接的测试环境
