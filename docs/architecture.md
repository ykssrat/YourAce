YourAce 项目架构说明

一、项目目标

YourAce 目标是为 A 股（股票、ETF、开放式基金）提供可解释、可复现的量化评分建议。
核心思想是通过 BIC 剪枝减少冗余参数，降低过拟合风险。

二、目录结构

- docs: 文档说明
- configs: 配置文件与发布配置
- datas/raw: 原始行情缓存
- scripts/processed: 数据拉取与清洗
- scripts/features: 特征计算与 BIC 剪枝
- scripts/strategy: 信号生成与评分
- scripts/backtest: 回测与绩效度量
- scripts/api: FastAPI 服务
- scripts/mobile/react_native_app: React Native 客户端
- scripts/utils: 资产加载与新闻抓取工具
- scripts/integration: 端到端联调脚本
- tests/unit: 单元测试
- tests/integration: 集成测试

三、核心处理链路

1. 输入证券代码
2. 读取本地行情或生成可复现实验序列
3. 计算多维特征并执行 BIC 剪枝
4. 生成短中长期信号
5. 聚合评分并映射离散标签
6. 按开关决定是否抓取资讯
7. 返回移动端展示结果

四、评分目标

当前策略优化目标聚焦三项最大化：

- 收益率
- 夏普比率
- 胜率
