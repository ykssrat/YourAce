# Lean Alphas 目录解析

`scripts/backtest/lean/Algorithm.Python/Alphas` 目录下存放的是 Lean 引擎的 **Alpha 模块化示例**。

### 1. 核心定位
这里的代码采用了 Lean 的“框架模式” (Framework Architecture)，专门负责**发射交易洞察 (Insights)**。它们不直接处理订单，而是输出“我看多/看空、置信度是多少、预期持续多久”的信息。

### 2. 核心文件示例
- **`GreenblattMagicFormulaAlpha.py`**：实现了乔尔·格林布拉特的“神奇公式”，演示了如何结合基本面数据（EV/EBITDA, ROC）进行选股评分。
- **`VIXDualThrustAlpha.py`**：演示了如何利用波动率指数 (VIX) 的突破逻辑来辅助生成信号。
- **`MeanReversionLunchBreakAlpha.py`**：捕捉午初反转现象的典型日内 Alpha 模型。

### 3. 如何复用？
这些 Alpha 模型通常继承自 `AlphaModel` 类。你可以像 `AdaptiveEdge.py` 那样，使用 `CompositeAlphaModel` 将它们像积木一样叠加起来，构建出多因子的评分系统。
