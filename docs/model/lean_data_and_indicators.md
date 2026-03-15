# Lean 数据架构与指标同步

理解 Lean 的数据流，是写出高性能策略的关键。Lean 并非简单的“数据喂入”，而是一套精密的实时同步系统。

---

## 1. 数据的“脉搏” (Bar & Slice)

在 Lean 中，数据是以 `Slice` 对象的形式按时间戳同步派发的：
- **同步器 (Synchronizer)**：即便你订阅了多个标的（如 SPY 和 BTC），同步器会确保在 `OnData(self, data: Slice)` 中，这些标的的时间戳是对齐的。如果某个时刻没有数据，Lean 会填充或跳过，保证逻辑的一致性。

## 2. 指标的自动化更新 (Auto-Updating Indicators)

这是 Lean 最省心的地方。
- **注册机制**：当你调用 `self.indicators.ema(symbol, 30)` 时，Lean 内部创建了一个 C# 指标对象，并自动将该 Symbol 的每一个新 Price 指向这个指标。
- **手动更新**：如果你想从一个非资产数据（如宏观指标）更新指标，可以使用 `indicator.update(time, value)`。

## 3. 整合计算：Consolidator (聚合器)

如果你想用“一分钟数据”算“五分钟指标”，不需要手算。
- **聚合器**：你可以定义一个 `QuoteBarConsolidator` 或 `TradeBarConsolidator`。
- **作用**：它像一个小漏斗，攒够 5 个 1min Bar 后，产出一个 5min Bar，并自动喂给对应的指标。

## 4. 数据的结构 (Lean Format)

Lean 使用一种高度压缩的二进制数据格式：
- **存放在本地**：`scripts/backtest/lean/Data/`。
- **结构**：`/equity/usa/daily/spy.zip`。
- **ToolBox**：如果你有外部 CSV 数据，必须使用 `ToolBox` 模块将其转化为 Lean 格式，否则引擎无法高效扫描。

---

## 5. 大师技巧：WarmUp (预热)

为什么回测第一天没有信号？
- 指标需要历史数据来计算（例如 EMA 30 需要前 30 天的数据）。
- **解法**：使用 `self.SetWarmUp(timedelta(30))`。Lean 会在算法逻辑真正开始前，先快进式地泵入 30 天数据来把指标“泡开”。

---

> [!TIP]
> **记住**：在 `OnData` 中，你拿到的永远是整个市场在**当前那一刻**的横截面快照。
