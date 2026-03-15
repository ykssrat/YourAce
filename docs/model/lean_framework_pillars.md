# Lean Framework：模块化交易的五大支柱

Lean 的核心竞争力在于它的 **Framework（框架架构）**。它将一个复杂的交易策略拆解为五个互相独立、可插拔的模块。这种设计让你能够像拼乐高一样构建策略。

---

## 1. 选股池 (Universe Selection)
- **职责**：决定今天“有哪些标的进入我的视线”。
- **分类**：
    - **Manual**：手动指定（如 `["SPY", "AAPL"]`）。
    - **Fundamental**：基于财务数据动态筛选（如“PE < 10 且市值前 100”）。
- **库文件参考**：`scripts/backtest/lean/Algorithm.Python/FundamentalUniverseSelectionAlgorithm.py`

## 2. 预测模型 (Alpha Creation)
- **职责**：生成交易信号（Insights）。
- **逻辑**：不决定买多少，只决定“方向（涨/跌）、置信度、持续时间”。
- **优势**：你可以叠加多个 Alpha（如 EMA + RSI），Lean 会自动汇总。
- **库文件参考**：`scripts/backtest/lean/Algorithm.Python/Alphas/`

## 3. 投资组合构建 (Portfolio Construction)
- **职责**：决定“每只股票买多少（权重分配）”。
- **典型模型**：
    - **EqualWeighting**：平均分配。
    - **InsightWeighting**：根据 Alpha 信号的强度分配（强信号多买）。
    - **MeanVarianceOptimization (MVO)**：马科维茨均值方差最优分配。

## 4. 执行模型 (Execution)
- **职责**：决定“怎么买最省钱”。
- **典型模型**：
    - **Immediate**：市价单立即成交。
    - **Standard (VWAP/TWAP)**：将大单拆细，降低对市场的冲击。

## 5. 风险管理 (Risk Management)
- **职责**：决定“什么时候该逃命”。
- **典型模型**：
    - **TrailingStop**：移动止损。
    - **MaxDrawdown**：单日或单标的最大回撤控制。
- **库文件参考**：`scripts/backtest/lean/Algorithm.Python/AddRiskManagementAlgorithm.py`

---

## 为什么这种架构很强大？

1.  **逻辑解耦**：你修改了“怎么选股”，不需要动“怎么止损”的代码。
2.  **代码复用**：你可以写一个完美的 `RiskManagement` 模块，然后通过 `self.AddRiskManagement(...)` 挂载到你所有的策略中。
3.  **标准化评估**：Lean 可以分别量化你的 Alpha 预测准不准，以及你的 Execution 买得值不值。

---

> [!IMPORTANT]
> **顶级玩家的秘诀**：在 Lean 中，你应该尽可能避免在 `OnData` 中手写复杂的逻辑，而是通过实现这五个 Model 来构建策略。这才是实现“进化”和“BIC 剪枝”的基础。
