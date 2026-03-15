YourAce Model 黑箱接口说明

一、文档目的

如果把 model 当作黑箱，本文件只回答三件事：

- 外部通过哪些接口把什么数据传进来
- 黑箱内部最小必要输入是什么
- 黑箱最终会产出哪些结果

二、黑箱边界定义

黑箱内部核心流程（不关心具体算法细节）：

1. 行情序列准备（本地数据优先，缺失时模拟序列降级）
2. 三窗口信号生成（short/mid/long）
3. 三窗口强度计算（horizon_strengths，范围 [-1, 1]）
4. 综合评分聚合（score，0-100，当前保留 1 位小数）
5. 标签映射（label）
6. 解释层输出（selected_features、matrix）

三、对外接口输入（API 入参）

1) POST /analyze

请求字段：

- code: string，必填，证券代码
- long_fund_trend: float，可选，默认 0，范围 [-1, 1]
- include_news: bool，可选，默认 true

2) POST /diagnose

请求字段：

- code: string，必填，证券代码
- include_news: bool，可选，默认 true

3) POST /screen

请求字段：

- asset_type: string，可选，"stock"/"etf"/"fund"/""（"" 表示不限）
- horizon: string，可选，"short"/"mid"/"long"/""（"" 表示不限）
- score_operator: string，可选，"gte"/"lte"
- score_threshold: float，可选，默认 60，范围 [0, 100]
- opinion: string，可选，"STRONG_BUY"/"BUY"/"HOLD"/"SELL"/"STRONG_SELL"/""
- round_size: int，可选，默认 20，范围 [1, 100]
- offset: int，可选，默认 0

4) GET /search

请求参数：

- query: string，可选，关键词
- limit: int，可选，默认 20

5) GET /news

请求参数：

- code: string，必填
- limit: int，可选，默认 3

6) GET /health

- 无业务参数

四、黑箱内部最小必要输入

无论外部接口如何调用，真正喂给评分核心的数据只有两类：

- close_series: 价格序列（由 code 解析得到）
- long_fund_trend: 长期趋势先验（/analyze 可传，其他接口默认 0）

说明：

- include_news 不参与评分计算，只影响 latest_news 是否拉取。
- /screen 的筛选参数属于后处理过滤，不改变单标的评分公式。

五、对外接口输出（API 出参）

1) /analyze 输出

- code: string
- as_of_date: string
- score: float（0-100，1 位小数）
- label: string（STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL）
- horizon_signals: object（short/mid/long -> BUY/HOLD/SELL）
- horizon_strengths: object（short/mid/long -> [-1, 1] 连续值）
- selected_features: string[]
- news_enabled: bool
- latest_news: object[]

2) /diagnose 输出

- code: string
- as_of_date: string
- score: float
- label: string
- horizon_signals: object
- horizon_strengths: object
- matrix: object（short/mid/long -> STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL）
- selected_features: string[]
- news_enabled: bool
- latest_news: object[]

3) /screen 输出

- items: object[]，每项包含：
  - code
  - name
  - score
  - label
  - horizon_signals
  - horizon_strengths
- scanned_count: int
- offset: int
- has_more: bool
- total_available: int
- score_pass_count: int
- signal_miss_count: int

4) /search 输出

- query: string
- count: int
- items: object[]

5) /news 输出

- code: string
- count: int
- items: object[]

6) /health 输出

- status: "ok"

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

    D --> E[信号生成器 signal_generator\n输出 horizon_signals + horizon_strengths]
    E --> F[评分聚合 scoring\n输出 score + label]
    F --> G[看法矩阵构建\noutput matrix]
    F --> H[BIC 剪枝\noutput selected_features]
    B --> I[新闻模块 news_fetcher]

    G --> J[统一响应 JSON]
    H --> J
    I --> J
    F --> J
    E --> J
```

七、接口与模型耦合点（你最该盯的地方）

- /screen 的 opinion 过滤依赖 _derive_opinion 规则，阈值变化会直接影响命中率。
- score_threshold 是筛选阈值，不是模型阈值；两者不要混淆。
- 若后续调整 label 分段（80/60/40/20），会影响 App 的文案展示与筛选结果分布。
