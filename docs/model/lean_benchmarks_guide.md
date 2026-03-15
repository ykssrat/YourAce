# Lean Benchmarks 目录解析

`scripts/backtest/lean/Algorithm.Python/Benchmarks` 目录下存放的是 Lean 引擎的**性能压力测试脚本**。

### 1. 核心定位
这些脚本的主要目的不是为了展示盈利策略，而是为了测试 Lean 引擎在不同负载下的运行速度和资源消耗。量化开发者通常使用这些代码来验证系统在处理数千只股票或高频数据时的稳定性。

### 2. 核心文件示例
- **`CoarseFineUniverseSelectionBenchmark.py`**：测试大规模选股逻辑（Coarse/Fine Selection）的计算效率。
- **`HistoryRequestBenchmark.py`**：测试大规模并发请求历史行情数据时的加载速度。
- **`ScheduledEventsBenchmark.py`**：测试高频定时任务（如每分钟触发一次逻辑）对引擎性能的影响。

### 3. 如何复用？
对于一般交易者而言，这些代码的参考价值在于：**代码调优**。如果你想知道如何写出执行效率最高的选股逻辑，或者如何在大规模回测时不卡顿，可以参考这里的编写模式。
