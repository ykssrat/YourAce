# Lean 交易生命周期：成交与模拟

在 Lean 架构中，一个订单从生成到成交，经历了一个精密的物理模拟过程。

---

## 1. 订单工厂 (The Order Factory)

当你在 Python 代码中调用 `self.buy("SPY", 100)` 或 `self.set_holdings(...)` 时：
1.  **Order Request**：生成一个订单请求，包含了标的、数量、方向、类型（Market/Limit/Stop）。
2.  **Order ID**：系统分配一个唯一的 ID，并立即返回给算法。

## 2. 模拟器：Fill Models (成交模型)

在回测模式下，Lean 处理订单的“心脏”是 `FillModel`。
- **职责**：模拟真实市场的撮合压力。
- **默认逻辑**：采用买卖价差（Bid/Ask Spread）的中间价。
- **自定义**：你可以参考 `ImmediateFillModel.py`。如果你在跑 A 股，你可能需要考虑 T+1 的成交限制，这可以通过自定义模型来模拟。

## 3. 滑点与佣金 (Slippage & Fee Models)

- **滑点 (Slippage)**：模仿由于订单量太大导致的成本上升。小资金（如 1w~10w）滑点极低，但如果你买入几千万，Lean 会根据成交量权重自动增加你的入场成本。
- **佣金 (Fee)**：在 `Initialize` 中设置，例如 `self.set_fee_model(...)`。

## 4. 跨平台券商集成 (Brokerage Interface)

Lean 架构设计的精妙之处在于：**算法在回测和实盘下代码完全一致**。
- **接口 (IBrokerage)**：定义了统一的交易指令。
- **实现类**：
    - `BacktestingBrokerage`：回测。
    - `AlpacaBrokerage` / `IBBrokerage`：连接真实交易所。
- **工作区映射**：位于 `scripts/backtest/lean/Brokerages/` 下。

---

## 5. 订单事件 (Order Events)

订单状态的任何变化都会触发 `on_order_event` 回调：
- **Submitted**：已发送。
- **Filled**：已部分或全部成交。
- **Canceled**：已撤单。
- **Invalid**：由于资金不足或价格无效被拒绝。

---

> [!IMPORTANT]
> **大师级风控提示**：永远要在 `on_order_event` 中监听订单失败。即便你的 Alpha 模型完美无缺，如果资金不足或市场波动导致交易所拒单（Invalid），没有捕获这些事件会让你失去对系统的控制。
