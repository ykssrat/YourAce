# AdaptiveEdge：动态市场风格切换策略

`AdaptiveEdge` 是一套基于状态机机制的宏观择时策略，旨在通过识别市场不同的运行风格（Regime），动态调用 Lean 库中对应的子策略模块。

---

## 一、 策略架构：状态机 (Regime Switching)

策略将市场分为三个核心阶段，并为每个阶段匹配最优的逻辑：

1. **趋势阶段 (Trend Regime)**：
   - **判定条件**：ADX > 25 且价格处于长短期均线上方。
   - **子策略逻辑**：参考 `MovingAverageCrossAlgorithm.py`。
   - **执行细节**：采用金字塔式加仓（Pyramiding），在确认趋势后逐步放大由于趋势带来的 Alpha。

2. **震荡阶段 (Oscillation Regime)**：
   - **判定条件**：ADX < 20 或价格在均线附近窄幅波动。
   - **子策略逻辑**：参考 `MeanReversionPortfolioAlgorithm.py`。
   - **执行细节**：利用回归逻辑进行低买高卖。

3. **风险爆发阶段 (Crash/Risk-off Regime)**：
   - **判定条件**：波动率（ATR）斜率骤增或价格快速下穿支撑位。
   - **自保逻辑**：强制清仓观望，规避结构性断裂风险。

---

## 二、 奥卡姆剃刀：因子自动评估与剪枝

为了解决多因子模型中的冗余和噪声，策略内置了启发式的因子剔除机制：

- **动态相关性分析**：在回测过程中实时计算各因子（如 RSI, MOM, MACD）之间的相关性。
- **因子简化**：若两个因子相关性持续高于 0.85，算法将根据其近期的信息比率（Information Ratio）自动弃用解释力度较低的一个，确保模型的最简性与泛化能力。

---

## 三、 代码组织与调用

策略主体位于 `scripts/backtest/lean/Algorithm.Python/AdaptiveEdge.py`。它不重新发明轮子，而是整合了 `Algorithm.Python` 目录下的成熟模式：

- **选股逻辑**：统一使用 `UniverseSelectionDefinitionsAlgorithm.py` 中的多资产配置。
- **风险管理**：挂载 `TrailingStopRiskManagementModel.py` 实现动态止盈止损。

---

## 四、 代码实现逻辑详解 (v2.0)

根据 `AdaptiveEdge.py` 的最新源代码，策略的执行逻辑如下：

### 1. 动态注入与订阅 (Initialize)
- **参数化资产**：通过 `get_parameter("tickers")` 获取资产列表。这实现了代码与投资目标的完全解耦。应用端只需输入以逗号分隔的代码字符串（如 `510300,512480`），策略即可自动完成多资产订阅。
- **时间与资金**：默认回测起点为 2023 年 1 月 1 日，初始资金 50,000 元。

### 2. 复合模型架构 (Alpha Composition)
策略不再手写单一评分逻辑，而是采用 **CompositeAlphaModel** 拧合了库中的两个经典维度：
- **RSI 因子 (`RsiAlphaModel`)**：负责捕捉超买超跌的均值回归机会。
- **EMA 趋势因子 (`EmaCrossAlphaModel`)**：复用 `MovingAverageCross` 逻辑，负责捕捉 15/30 日均线交叉的动量机会。

### 3. 持续评分映射 (Portfolio Construction)
- 使用 **InsightWeightingPortfolioConstructionModel**。
- **逻辑**：两个子 Alpha 模型会不断发射 `Insight`（看多/看空信号）。该模型会根据每个信号的预测强度和置信度，自动计算出投资组合中每个标的的实时持仓比例。

### 4. 自动风控 (Risk Management)
- 挂载 **MaximumDrawdownPercentPortfolio(0.05)**。
- 策略会在全局净值回撤达到 5% 时强制执行保护性止损，确保在“非预期波动”中生存。

### 5. 状态机调优 (Regime Tuning)
在 `on_data` 事件中，策略通过第一标的的 **ADX** 指标实时监控市场强度：
- **ADX < 20**：市场进入震荡风格。策略逻辑上应通过降低趋势因子的权重（Alpha Pruning）来减少磨损。
- **ADX > 30**：市场进入强趋势风格。策略全面解锁动量因子，执行金字塔加仓。

---

> [!NOTE]
> 该策略实现了“资产悬置”与“逻辑拼装”的深度解耦，是 YourAce 系统迈向工业级回测的关键一步。
