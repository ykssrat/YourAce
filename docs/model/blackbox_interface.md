YourAce Model 黑箱接口说明

一、文档目的

如果把 model 当作黑箱，本文件只回答三件事：

- 外部通过哪些接口把什么数据传进来
- 黑箱内部最小必要输入是什么
- 黑箱最终会产出哪些结果

二、黑箱边界定义

黑箱内部当前核心流程：

1. 行情序列准备（本地数据优先，缺失时模拟序列降级）
2. 三窗口信号生成（`short/mid/long`）
3. 看法矩阵生成（`matrix`）
4. 标签确定（`label`，当前取中期看法）
5. 解释层输出（`selected_features`）
6. 资讯层补充（`latest_news`）

说明：

- 当前主链路已经不再输出 `score`
- 当前也不再使用 `horizon_strengths`

三、对外接口输入（API 入参）

1) `POST /analyze`

请求字段：

- `code`：string，必填
- `strategy`：string，可选，默认 `default`
- `long_fund_trend`：float，可选，默认 `0`
- `include_news`：bool，可选，默认 `true`

2) `POST /diagnose`

请求字段：

- `code`：string，必填
- `strategy`：string，可选，默认 `default`
- `include_news`：bool，可选，默认 `true`

3) `POST /screen`

请求字段：

- `asset_type`：string，可选，`"stock"/"etf"/"fund"/""`
- `horizon`：string，可选，`"short"/"mid"/"long"/""`
- `strategy`：string，可选，默认 `default`
- `opinion`：string，可选，`"BUY"/"HOLD"/"SELL"/""`
- `round_size`：int，可选，默认 `20`
- `offset`：int，可选，默认 `0`

4) `GET /search`

请求参数：

- `query`
- `limit`

5) `GET /news`

请求参数：

- `code`
- `limit`

6) `GET /health`

- 无业务参数

四、黑箱内部最小必要输入

无论外部接口如何调用，真正进入当前判断核心的数据只有两类：

- `close_series`：价格序列（由 `code` 解析得到）
- `long_fund_trend`：长期趋势先验（仅 `/analyze` 可显式传入）

说明：

- `include_news` 不参与判断计算，只影响 `latest_news` 是否拉取
- `/screen` 的筛选参数属于后处理过滤，不改变单标的策略结果

五、对外接口输出（API 出参）

1) `/analyze` 输出

- `code`
- `name`
- `as_of_date`
- `label`
- `horizon_signals`
- `matrix`
- `selected_features`
- `news_enabled`
- `latest_news`

2) `/diagnose` 输出

- `code`
- `name`
- `as_of_date`
- `label`
- `horizon_signals`
- `matrix`
- `selected_features`
- `news_enabled`
- `latest_news`

3) `/screen` 输出

- `items`
  - `code`
  - `name`
  - `label`
  - `horizon_signals`
  - `matrix`
- `scanned_count`
- `offset`
- `has_more`
- `total_available`
- `signal_miss_count`

4) `/search` 输出

- `query`
- `count`
- `items`

5) `/news` 输出

- `code`
- `count`
- `items`

6) `/health` 输出

- `status: "ok"`

六、黑箱架构示意图

```mermaid
flowchart LR
    A[客户端 App 或脚本] --> B[API 层 server.py]

    B --> C1[/analyze]
    B --> C2[/diagnose]
    B --> C3[/screen]

    C1 --> D[加载 close_series]
    C2 --> D
    C3 --> D

    D --> E[策略调度 opinion_engine\n输出三窗口结果]
    E --> F[生成 horizon_signals + matrix]
    F --> G[确定 label]
    F --> H[BIC 剪枝\n输出 selected_features]
    B --> I[新闻模块 news_fetcher]

    G --> J[统一响应 JSON]
    H --> J
    I --> J
    F --> J
```

七、接口与模型耦合点

- `/screen` 的 `opinion` 过滤直接依赖 `matrix` 与 `horizon_signals`
- `strategy` 参数决定具体策略模块是否能被正确加载
- 若后续新增策略元信息接口，移动端策略枚举与后端能力应同步维护

八、历史说明

- 旧版文档中出现过的 `score`、`score_threshold`、`horizon_strengths`、`STRONG_BUY/STRONG_SELL` 等描述，属于历史架构，不再代表当前接口
- 当前接口口径应统一理解为：
  - `BUY`
  - `HOLD`
  - `SELL`
  - 三窗口矩阵
