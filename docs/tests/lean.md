# YourAce Lean 架构与量化大师进阶指南

本指南介绍如何使用新引入的 QuantConnect/Lean 工业级生产回测引擎，以及它与 YourAce 轻量化库的平等协作关系。

## 一、双引擎架构说明

为了实现极致的可视化平等性，系统采用了以下双轴结构：

| 特性 | 轻量级引擎 (`lightweight`) | 工业级引擎 (`lean`) |
| :--- | :--- | :--- |
| **路径** | `scripts/backtest/lightweight` | `scripts/backtest/lean` |
| **原理** | 向量化计算 (Vectorized) | 事件驱动 (Event-driven) |
| **精度** | 适合快速筛选、因子预热 | 严丝合缝的实盘仿真 |
| **用途** | 0.1 秒跑完 1000 只标的 | 考虑滑点、佣金后的真实收益 |

## 二、Lean 引擎目录结构

- **核心架构**: `scripts/backtest/lean` (克隆自官方代码)
- **大师策略**: `scripts/backtest/lean/Algorithm.Python` (在此编写你的生产逻辑)
- **配置文件**: `scripts/backtest/lean/config.json`

## 三、量化大师：多标的长周期回测

简单的单只股票测试并不能体现大师水准。真正的策略需要具备**资产组合评分**与**自我净化**能力。

### 1. 核心进阶示例：`MasterAlphaStrategy.py`
在 `scripts/backtest/lean/Algorithm.Python/MasterAlphaStrategy.py` 中，我们实现了一个支持个股、ETF 与基金混合回测的模型：

```python
from AlgorithmImports import *

class MasterAlphaStrategy(QCAlgorithm):
    def Initialize(self):
        # 1. 跨越 10 年的大牛熊周期测试
        self.SetStartDate(2014, 1, 1)  
        self.SetCash(1000000) 
        
        # 2. 混合池：蓝筹、指数、行业 ETF 及场外基金
        self.tickers = ["000001", "510300", "512480", "161725"]
        for ticker in self.tickers:
            self.AddEquity(ticker, Resolution.Daily)

    def OnData(self, data):
        # 3. 动态 Alpha 评分逻辑 (不再是简单的买入)
        # 只有共振评分最高的标的才会获得仓位
        # 具体代码详见：scripts/backtest/lean/Algorithm.Python/MasterAlphaStrategy.py
        pass
```

### 2. 回测回馈：策略进化
通过分析 `lean` 的回测报告（尤其是 Sharpe Ratio 和 Drawdown），你可以反向调节 `lightweight` 引擎中的评分权重。这种“研究（轻量级）- 验证（工业级）- 生产”的闭环，才是系统进化的方向。

## 四、关于目录结构的平等性

如果你在 `scripts/backtest/` 下看到以下结构，说明你已经进入了量化高级阶段：
- `lightweight/` (包含你原有的 `engine.py`)
- `lean/` (包含世界级的量化架构)

> [!IMPORTANT]
> 所有的“硬编码”常数（如资产池）应尽量放在 `configs/asset_config.json` 中，由 `asset_loader.py` 统一分发，从而保证回测与 API 接口的逻辑一致性。
