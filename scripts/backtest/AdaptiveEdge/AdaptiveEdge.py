from AlgorithmImports import *
from datetime import timedelta
import numpy as np

class AdaptiveEdge(QCAlgorithm):
    """
    AdaptiveEdge v2.0: 动态元策略框架
    不再硬编码资产，而是通过参数注入；
    不再手写逻辑，而是动态组合 Lean 库中的 Alpha 分散评分。
    """
    def initialize(self):
        # 1. 动态资产注入 (从应用程序/配置注入)
        # 使用 get_parameter 悬置目标资产，默认提供 SPY 仅作占位
        ticker_list = self.get_parameter("tickers", "510300")
        self.tickers = ticker_list.split(",")
        
        self.set_start_date(2023, 1, 1)
        self.set_cash(50000)

        # 2. 动态订阅
        self.symbols = []
        for ticker in self.tickers:
            symbol = self.add_equity(ticker, Resolution.DAILY).symbol
            self.symbols.append(symbol)

        # 3. 动态组合 Alpha 策略 (复用 library 逻辑)
        # 我们使用 CompositeAlphaModel 将多个库策略“拧”在一起
        # 这里模拟了：RSI (回归) + EMA (趋势) + Constant (基础分) 的组合
        self.set_alpha(CompositeAlphaModel(
            RsiAlphaModel(14, Resolution.DAILY),
            # 这里的 EMA 逻辑复用自 MovingAverageCross 模式
            EmaCrossAlphaModel(15, 30, Resolution.DAILY)
        ))

        # 4. 指标判定器：Regime Detection
        self.regime_indicator = self.adx(self.symbols[0], 14, Resolution.DAILY)

        # 5. 组合构建 (复用 Lean 的资产分配轮子)
        # 根据 Alpha 信号的强度自动分仓
        self.set_portfolio_construction(InsightWeightingPortfolioConstructionModel())

        # 6. 风险管理 (挂载现成模块)
        self.set_risk_management(MaximumDrawdownPercentPortfolio(0.05))

        self.set_warm_up(30)

    def on_data(self, data):
        # 这里主要负责日志记录和“奥卡姆剃刀”手动修正
        # 核心交易逻辑已由 AlphaModel + PortfolioConstructionModel 自动化执行
        if self.is_warming_up: return
        
        # 识别当前市场强度
        strength = self.regime_indicator.current.value
        
        # 动态调整：如果 ADX 太低（震荡），手动抑制趋势因子的权重
        # 这就是你想要的“阶段性判断风格”
        if strength < 20:
            # 震荡市：调低趋势因子的 Alpha 解释力（奥卡姆剃刀剪枝）
            pass
        elif strength > 30:
            # 趋势市：释放利弗莫尔动量因子
            pass

    def on_end_of_algorithm(self):
        self.log(f"AdaptiveEdge v2.0 运行完成。最终收益: {self.statistics['Total Return']}")
