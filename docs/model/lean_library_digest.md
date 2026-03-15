# YourAce Lean 策略库全解手册

本手册对 `scripts/backtest/lean/Algorithm.Python` 目录下的 400 余个策略原型进行深度拆解。考虑到文件数量巨大，我们将它们按**金融逻辑原色**进行分类归档。

> [!NOTE]
> 目录中的 `Properties` 文件夹仅包含 C# 项目元数据。真正的策略核心位于 `Algorithm.Python` 目录下的 `.py` 文件中。

---

## 核心分类与指标定义

在查看策略前，请理解以下四个大师级评估指标：
- **Alpha 因子 (α)**：策略的超额收益来源（如：信息差、统计套利）。
- **OA (Operational Alpha)**：操作阿尔法。指通过撮合算法、滑点控制、仓位再平衡等执行细节获得的额外收益。
- **Beta 因子 (β)**：市场基准收益。策略对大盘涨跌的敏感度。
- **优缺点**：实盘环境下的落地限制。

---

## 一、 基础范式类 (Templates & Foundation)
*代表文件：`BasicTemplateAlgorithm.py`, `DailyAlgorithm.py`*

- **优缺点**：
    - 优点：逻辑极其简练，系统开销最小，适合作为所有新策略的“骨架”。
    - 缺点：无择时、无选股逻辑，纯粹的买入持有。
- **Alpha 来源**：无。
- **OA 来源**：基本的再平衡逻辑。
- **Beta 来源**：1.0 (完全暴露于目标标的的系统性风险)。

## 二、 趋势与动量类 (Momentum & Trend Following)
*代表文件：`MovingAverageCrossAlgorithm.py`, `MACDTrendAlgorithm.py`, `EmaCrossAlphaModelFramework.py`*

- **优缺点**：
    - 优点：在大牛市或持续趋势中表现极其强势，能捕捉肥尾效应。
    - 缺点：在震荡市（猴市）中会被频繁打脸（左右挨耳光），调仓成本高。
- **Alpha 来源**：价格惯性（Momentum Overlay）。利用群体心理导致的趋势自我加强。
- **OA 来源**：主要来自 EMA（指数平滑）的平滑过滤，平衡了信号滞后与过敏感。
- **Beta 来源**：动态 β。趋势确立时高暴露，趋势破位时低暴露。

## 三、 选股与动态宇宙类 (Universe Selection)
*代表文件：`FundamentalUniverseSelectionAlgorithm.py`, `CoarseFundamentalTop3Algorithm.py`*

- **优缺点**：
    - 优点：**真正的进化核心**。不再死锁于单一标的，实现了“全市场优选”。
    - 缺点：对数据依赖极高，若基本面数据延迟，选股会失效。
- **Alpha 来源**：基本面套利（Factor-based Alpha）。如低 PE、高盈利能力的溢价。
- **OA 来源**：通过 `UniverseSelection` 自动剔除低流动性、劣质标的，降低冲击成本。
- **Beta 来源**：结构性 β。通过持仓分散化降低单一行业爆发的非系统性风险。

## 四、 机器学习算法类 (ML & AI)
*代表文件：`KerasNeuralNetworkAlgorithm.py`, `TensorFlowNeuralNetworkAlgorithm.py`, `ScikitLearnLinearRegressionAlgorithm.py`*

- **优缺点**：
    - 优点：能捕捉非线性的复杂关系，具有高度的非参数化建模能力。
    - 缺点：极易陷入**过拟合**（过快拟合历史噪音），黑盒性质强，难以解释。
- **Alpha 来源**：特征发现（Feature Engineering）。通过高维空间捕捉人类肉眼难以发现的信号共振。
- **OA 来源**：通常通过在线学习（Online Learning）不断调整预测偏移。
- **Beta 来源**：不可控。模型可能在不经意间放大了某一特性的 β 暴露。

## 五、 衍生品与对冲类 (Options & Hedge)
*代表文件：`IronCondorStrategyAlgorithm.py`, `CoveredAndProtectiveCallStrategiesAlgorithm.py`*

- **优缺点**：
    - 优点：可在市价不涨、甚至微跌的情况下盈利（如卖出波动率策略）。
    - 缺点：尾部风险巨大（黑天鹅），阶梯式爆仓风险。
- **Alpha 来源**：隐含波动率与实际波动率的差额 (IV Rank/Skew Alpha)。
- **OA 来源**：对希腊字母（Delta/Vega/Gamma）的动态对冲。
- **Beta 来源**：低 β 或 Zero β（Delta Neutral 策略）。

---

## 进化建议：大师如何选取轮子？

1.  **若追求稳健理财**：应以 `FundamentalUniverseSelection`（选股）为基础，叠加热身期（WarmUp）较长的 `MACD` 择时。
2.  **若追求爆发力**：应研究 `OptionUniverseFilter` 指令，利用期权杠杆放大 Alpha。
3.  **若追求智能化**：优先参考 `ScikitLearnLinearRegression` 做基础的价格预测回归，而不是直接上神经网络。

> [!IMPORTANT]
> 每个 `.py` 文件文件头通常包含详细的注释（Algorithm Description），在引入具体代码前，请务必阅读其中的 `Regression test` 说明。
