YourAce 版本整理（0.1.4）

版本号：0.1.4
整理日期：2026-03-15

一、本版本目标

- 发布可直接连接云服务器公网 IP 的移动端版本。
- 解决手机端 release 包访问 http 地址时报 network request failed 的问题。
- 保持低成本可用，不依赖域名与备案流程。

二、核心新增与修复

1) Android 明文流量策略

- 在主 Manifest 开启 android:usesCleartextTraffic="true"。
- release 包可访问 http://43.138.223.57 这类明文地址。

2) 默认后端地址优化

- App 默认后端地址改为云服务器公网 IP：43.138.223.57。
- 首次安装后无需手动输入即可直接测试连接。

3) 版本号升级

- Android versionCode 提升到 3。
- Android versionName 更新为 0.1.4。

4) 构建脚本修复

- 修复 build.gradle 中由乱码注释引发的语法异常。
- 恢复 applicationVariants 输出文件名配置，保证产物名仍为 YourAce.apk。

三、配套部署状态

- 云服务器后端已可在本机返回 /health = ok。
- 公网健康检查已可返回 /health = ok（需直连，不走代理劫持）。
- 轻量防火墙建议仅保留 22/80（3389 规则应移除）。

四、当前运行方式

- App 后端地址： http://43.138.223.57
- Nginx 对外监听 80，反代到本机 8000。
- FastAPI 在云服务器以 uvicorn 运行。

五、后续建议

- 若后续准备长期公开访问，再引入域名与 HTTPS 证书。
- 若继续使用代理环境，建议为 43.138.223.57 配置 DIRECT 规则。
- 按周进行安全更新与日志巡检。
