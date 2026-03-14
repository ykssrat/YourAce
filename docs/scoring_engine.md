YourAce 评分器底层结构说明

一、文档目标

本说明聚焦“输入代码后，评分是如何被算出来的”，用于解释分数、标签、三维信号与特征选择结果。

二、评分器总体流程

1. 接收 analyze 请求（code、long_fund_trend、include_news）
2. 加载收盘价序列
3. 生成短期/中期/长期三维信号
4. 聚合三维信号得到 0-100 分
5. 映射离散标签（STRONG_BUY 等）
6. 执行 BIC 剪枝并返回 selected_features
7. 按开关决定是否拉取新闻

三、输入数据与降级逻辑

- 优先读取 datas/raw 下本地行情文件
- 若本地不存在对应代码行情，则使用“确定性模拟序列”降级，保证离线可测
- 因此在未落地真实行情前，分数是“可复现实验值”，不是实盘结论

四、三维信号生成逻辑

短期（short）：

- 使用 10 日动量与 10 日均值偏离度
- 分数超过阈值映射为 BUY，低于阈值映射为 SELL，其余 HOLD

中期（mid）：

- 使用 30 日趋势（MA10 相对 MA30）
- 加入价格在支撑-压力区间中的位置偏置
- 综合映射为 BUY/HOLD/SELL

长期（long）：

- 使用 120 日结构（latest、MA30、MA120）
- 叠加 long_fund_trend 基本面输入
- 综合映射为 BUY/HOLD/SELL

五、评分映射规则

信号值映射：

- BUY -> 1
- HOLD -> 0
- SELL -> -1

默认权重：

- short: 0.35
- mid: 0.35
- long: 0.30

连续分值计算：

- weighted_sum = sum(weight_h * signal_value_h)
- score = (weighted_sum + 1) * 50
- 再裁剪到 0-100

标签映射：

- [80, 100] -> STRONG_BUY
- [60, 80) -> BUY
- [40, 60) -> HOLD
- [20, 40) -> SELL
- [0, 20) -> STRONG_SELL

六、BIC 剪枝如何影响结果

- BIC 剪枝作用于特征解释层（selected_features），当前不会直接改写 score 计算公式
- 规则是“新增特征必须让 BIC 下降才保留”，否则剔除
- 如果 selected_features 为空，常见原因：
  - 当前样本对候选因子没有显著增益
  - 输入数据质量不足
  - 剪枝阶段异常被容错为 []

七、示例解释

当输出为：

- short=HOLD, mid=BUY, long=BUY

则默认权重下：

- weighted_sum = 0.35*0 + 0.35*1 + 0.30*1 = 0.65
- score = (0.65 + 1) * 50 = 82.5
- label = STRONG_BUY

八、与市场状态耦合的下一步（建议）

可在评分器上层新增“市场状态路由器”，先判断 bull/bear/range，再选择执行子策略：

- bull/bear: 趋势跟随与阶段性加减仓（可融入 Livermore）
- range: 做 T / 网格交易

这样可避免在单一市场状态下过拟合，同时保持评分器作为统一的风险闸门与排序器。
