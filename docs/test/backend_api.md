YourAce 后端接口与最小闭环验证

说明：本文件聚焦当前后端接口定义与最小验证路径。
更详细的脚本命令与测试参数，请查看 `docs/test/test_guide.md`。

一、文档目的

- 用最短路径验证“输入代码 -> 输出标签与看法矩阵”是否正常。
- 先确认后端主链路可运行，再排查 App、局域网、防火墙等外部问题。

二、当前接口概览

- `GET /health`：健康检查
- `GET /search`：证券检索
- `POST /analyze`：单标的分析
- `POST /diagnose`：单标的诊股
- `POST /screen`：批量筛股
- `GET /news`：独立资讯查询

三、`/analyze` 请求体

- `code`：证券代码，必填
- `strategy`：策略名，可选，默认 `default`
- `long_fund_trend`：长期趋势输入，默认 `0`
- `include_news`：是否抓取资讯，默认 `true`

四、`/analyze` 当前响应关键字段

- `code`
- `name`
- `as_of_date`
- `label`：当前综合标签（`BUY/HOLD/SELL`）
- `horizon_signals`：`short/mid/long` 三窗口信号
- `matrix`：当前三窗口看法矩阵
- `selected_features`：BIC 选中特征
- `news_enabled`
- `latest_news`

说明：

- 当前接口已不再返回 `score`。
- 主输出已经切换为 `label + horizon_signals + matrix`。

五、本地最小闭环（推荐先走这条）

1. 启动后端（在仓库根目录执行）

```bash
uvicorn scripts.api.server:app --host 0.0.0.0 --port 8000
```

2. 电脑本机检查

```text
http://127.0.0.1:8000/health
```

3. 手机同网段检查

```text
http://你的电脑局域网IP:8000/health
```

4. App 内输入代码后执行分析或诊股

如果第 2 步都失败，说明后端未启动成功；先看终端报错，不要先改 App。

六、当前验证建议

最小推荐验证顺序：

1. `GET /health`
2. `POST /analyze`
3. `POST /diagnose`
4. `POST /screen`

建议优先确认：

- `label` 是否正常返回
- `horizon_signals` 是否包含 `short/mid/long`
- `matrix` 是否和三窗口结果一致
- 关闭新闻后 `latest_news` 是否为空数组
