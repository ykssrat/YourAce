# Lean 引擎核心架构详解

Lean 是一个模块化的事件驱动交易引擎。要理解它，首先要看清它从底层 C# 到高层 Python 的运行全貌。

---

## 1. 核心启动链路 (The Boot Sequence)

当你启动一个回测时，Lean 内部经历了以下过程：

1.  **Launcher (启动器)**：读取 `config.json`，初始化日志系统，决定是跑回测还是跑实盘。
2.  **Engine (引擎核心)**：
    - **SetupHandler**：加载你的 Python 算法脚本，初始化初始资金和起止日期。
    - **DataFeed**：开始泵入历史数据或实时数据。
3.  **Algorithm (算法实例)**：你的 Python 类被实例化，进入事件循环。

---

## 2. 三大核心循环 (The Core Loops)

Lean 的内部逻辑主要由三个独立的线程/循环驱动：

-   **数据循环 (Data Loop)**：
    - 职责：从数据源（磁盘或网络）读取 Tick/Second/Minute K线。
    - 作用：将原始数据转化为算法能理解的 `Slice` 对象，并触发 `OnData` 事件。
-   **交易循环 (Trade Loop)**：
    - 职责：监听算法发出的 `OrderRequest`。
    - 作用：在回测模式下模拟成交（Slippage & Fill Models），在实盘模式下发送给券商接口（Brokerage）。
-   **状态循环 (State Loop)**：
    - 职责：计算实时净值 (Equity)、持仓盈亏 (Unrealized PnL) 和保证金使用情况。
    - 作用：更新 `Portfolio` 对象，确保风控模型有最新数据。

---

## 3. 跨语言桥梁 (Python.NET)

为什么 C# 的引擎能跑 Python 代码？
- Lean 使用了 **Python.NET** 技术。你的 Python 类在内存中实际上被映射为一个实现了 C# `IAlgorithm` 接口的对象。
- **性能提示**：这意味着在 `OnData` 中进行的纯数学计算是很快的，但如果频繁跨语言调用复杂的 C# 对象（如深度循环查询），会有一定的通信开销。

---

## 4. 关键目录对应关系

- `Engine/`：调度中心。控制数据流、成交模拟和结果处理。
- `Common/`：数据定义。定义了什么是 `Order`, 什么是 `Trade`, 什么是 `Security`。
- `Data/`：数据处理。负责数据压缩、同步和订阅管理。
- `Algorithm.Python/`：你的工作区。存放所有的逻辑实现。

---

> [!TIP]
> 理解 Lean 的第一步是意识到：**你写的不是脚本，而是一个被装载进巨型精密机器中的“逻辑插件”**。
