
# YourAce 后端接口与云端自动化测试说明

本文件聚焦于 YourAce 云端后端 API 的接口定义、推荐的自动化测试脚本、以及典型用法示例。
更详细的脚本参数与进阶用法，请参考 `docs/tests/test_guide.md`。

---

## 一、接口概览

- `GET /health`：健康检查，服务可用性探测
- `GET /search`：证券检索
- `POST /analyze`：单标的分析（主力接口）
- `POST /diagnose`：单标的诊股（深度分析）
- `POST /screen`：批量筛股
- `GET /news`：独立资讯查询

---

## 二、推荐自动化测试脚本

所有接口均推荐通过 `/tests/integration/` 下的自动化脚本进行验证，支持本地和云端 API 地址。

### 1. 最小链路验证（推荐）
```bash
$env:PYTHONPATH="D:\QMT\YourAce" #进入python环境

python tests/integration/test_local_api_smoke.py --code 600519 --port 8000 #测试贵州茅台600519
```
用途：快速验证 `/analyze` 接口主流程，输出 label、horizon_signals、matrix。

### 2. 单标的诊股

```bash
python tests/integration/test_local_api_diagnose.py --code 600519 --port 8000 #只生成看法矩阵和剪枝后信号
```
用途：调用 `/diagnose`，输出三窗口矩阵及诊股详情。

### 3. 批量筛股

```bash
python tests/integration/test_local_api_recommend.py --signals short BUY --top-n 20 --port 8000 #在每轮20个标的中查看短期买入信号
python tests/integration/test_local_api_recommend.py --signals  BUY --top-n 20 --port 8000 #在每轮20个标的中查看买入信号
```
用途：调用 `/screen`，批量筛选满足信号条件的标的。

### 4. 全链路集成测试

```bash
pytest tests/integration/test_end_to_end_pipeline.py -q -s
```
用途：验证数据处理、API、回测等全流程。

---

## 三、云端 API 典型请求示例

### 1. 健康检查


```bash
curl http://43.138.223.57:8000/health
```

### 2. 单标的分析


```bash
curl -X POST http://43.138.223.57:8000/analyze \
	-H "Content-Type: application/json" \
	-d '{"code": "600519", "strategy": "ema_cross_substrategy", "include_news": false}'
```

### 3. 诊股


```bash
curl -X POST http://43.138.223.57:8000/diagnose \
	-H "Content-Type: application/json" \
	-d '{"code": "600519"}'
```

### 4. 批量筛股


```bash
curl -X POST http://43.138.223.57:8000/screen \
	-H "Content-Type: application/json" \
	-d '{"asset_type": "stock", "horizon": "short", "opinion": "BUY", "round_size": 20}'
```

---

## 四、典型响应字段说明

- `label`：主标签（BUY/HOLD/SELL）
- `horizon_signals`：三窗口信号（short/mid/long）
- `matrix`：三窗口详细看法
- `selected_features`：BIC 选中特征
- `news_enabled`：是否抓取新闻
- `latest_news`：新闻内容数组

> 说明：所有主流程均已切换为 label + horizon_signals + matrix，score 字段已废弃。

---

## 五、常见验证建议

1. 推荐优先用自动化脚本批量验证云端 API，避免手动反复测试。
2. 若需排查单接口问题，可用 curl/httpie 直接请求云端。
3. 重点关注 label、horizon_signals、matrix 字段是否合理。
4. 关闭新闻后 latest_news 应为空数组。

如需进阶参数与调试技巧，请查阅 `docs/tests/test_guide.md`。
