YourAce 量化交易系统开发规划大纲

一、 项目架构定义 (Lean Architecture)
本工程命名为 YourAce，旨在通过“信息干扰理论”剔除冗余参数，为用户提供纯净的 A 股（股票、ETF、开放式基金）投资决策支持。

1.1 目录结构 (QMT_YourAce/)
code
Text
QMT_YourAce/
├── docs/               # 技术文档、BIC算法说明、API手册
├── configs/            # 配置文件（data_config.yaml、strategy_config.yaml）
├── datas/raw/          # 原始行情数据缓存（CSV/Parquet格式）
├── scripts/
│   ├── processed/      # 数据获取与清洗（fetch_data.py、clean_data.py）
│   ├── features/       # 因子计算与BIC参数剪枝（calc_features.py）
│   ├── strategy/       # 策略逻辑（livermore.py、signal_generator.py）
│   ├── backtest/       # 回测引擎（基于收益率、夏普、胜率计算）
│   ├── portfolio/      # 组合优化与仓位管理
│   └── utils/          # 工具类（asset_loader.py、market_scanner.py、audit_logger.py）
└── tests/
    ├── unit/           # 单元测试
    └── integration/    # 集成测试

二、 核心研发 12 步长计划
第 1 步：基础设施与环境搭建
初始化 Git 仓库，构建上述 QMT_YourAce 文件夹物理结构。
配置 Python 虚拟环境，安装 akshare, pandas, statsmodels (用于BIC计算), pyyaml 等基础库。
第 2 步：数据获取模块 (Data Ingestion)
编写 fetch_data.py，调用 akshare 接口获取 A 股全市场股票列表、ETF 列表及场外开放式基金净值。
实现增量更新逻辑，将原始数据存入 datas/raw/ 缓存，统一时间序列格式。
第 3 步：特征工程与参数空间定义
在 features/ 目录下封装常用技术指标函数。
定义参数搜索空间（例如：均线周期、RSI 阈值等），为后续 BIC 评估准备多组备选参数组合。
第 4 步：基于 BIC 的参数剪枝算法实现
构建数学模型评估器：利用 statsmodels 的似然函数计算。
核心逻辑：针对每一个因子，计算加入新参数前后的 BIC 值变化。若新参数引入导致 BIC 增加（代表惩罚项超过了拟合增益），则强制剔除该参数，确保模型简洁性。
第 5 步：三维时间窗信号生成器
开发 signal_generator.py，实现离散化预测逻辑。
短期：计算 1-10 日动能与偏离度。
中期：计算 10-30 日趋势形态与支撑压力位。
长期：计算 30-120 日均线系统与基本面因子（基金净值趋势）。
第 6 步：评分系统与分类器设计
建立 0-100 分的线性映射模型。
实现离散标签映射：
80-100: 强烈看多 (Strong Buy)
60-80: 较为看多 (Buy)
40-60: 观望 (Hold)
20-40: 较为看空 (Sell)
0-20: 强烈看空 (Strong Sell)
第 7 步：回测引擎与绩效度量
编写 backtest/ 逻辑，计算模拟交易的已实现盈亏。
计算核心指标：年化收益率、夏普比率（Sharpe Ratio）、胜率（Win Rate）。
对比剪枝前后的绩效变化，验证 BIC 剔除噪声的有效性。
第 8 步：后端 API 服务封装
使用 FastAPI 或 Flask 搭建后端接口。
提供 /search 接口用于股票检索，提供 /analyze 接口用于触发本地计算逻辑并返回分数和三维建议。
第 9 步：移动端跨平台框架选型
选择 Flutter 或 React Native 作为 App 开发框架。
设计简单的 UI 展示层：包含搜索框、自选列表、以及红绿灯风格的评分仪表盘。
第 10 步：App 数据层与本地分析联调
实现 App 与后端的高并发接入。
App 端搜索自选股时，实时触发后端 Python 脚本进行 akshare 数据拉取 -> 因子计算 -> BIC 剪枝评分 -> 结果返回。
第 11 步：实时新闻爬虫与展示层集成
在 utils/ 中增加新闻抓取工具，对接主流财经网站或 akshare 的新闻接口。
在 App 详情页展示相关个股新闻，确保新闻内容仅作为参考信息流，不参与底层计算分数的权重。
第 12 步：系统集成测试与打包发布
进行全链路集成测试（从数据拉取到 App 显示）。
将后端部署于本地服务器（或云端），将 App 打包为 .apk (Android) 和 .ipa (iOS) 安装包。

三、 用户交互逻辑说明
搜索层：用户输入代码/简拼（如：000001 或 平安银行）。
触发层：App 发送请求至 YourAce 后端。
计算层：
后端抓取该股历史行情。
进行多维度指标计算。
执行 BIC 剪枝，剔除此时无效的参数。
展示层：
核心分值：例如 85分。
离散建议：强烈看多。
三维视图：短期（看多）、中期（观望）、长期（看多）。
周边资讯：关联该股的最新的三条重大公告或研报。

四、 移动端近期操作同步
图标：Android 端统一使用同一款 1024 标准版方形图标，已覆盖各分辨率启动图标资源，项目内无 .ico 文件残留。
网络：分析与检索接口增加多基地址回退（10.0.2.2、127.0.0.1、localhost），降低点击分析出现 network request failed 的概率。
自选：自选列表支持通过代码自由添加和删除，支持股票、ETF、基金代码形式输入。
