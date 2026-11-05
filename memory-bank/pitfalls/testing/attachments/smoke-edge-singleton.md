# 浏览器冒烟 · Edge 同 user-data-dir 单例移交(外迁)

> 摘要: `pitfalls/testing/smoke.md`「Edge 同 `user-data-dir` 会单例移交」条原文整体外迁(2026-11-05 压缩), 正文原样照搬, 标题降一级以避开坑档条目扫描。
> 触发: Edge, user-data-dir, 单例移交, 残留页面, 幽灵操作, 10048, Stop-Process, 父子进程

## Edge 同 `user-data-dir` 会单例移交

- **触发**: 反复起冒烟服务。
- **判别**: 新进程**立即退出**, `/json/list` 拿到**旧实例的旧页面**;
  且**残留页面的轮询会在新服务起来后自动重连并继续执行"幽灵操作"**(实测把新环境里同名组删了)。
- **处置**: 每轮**独立 profile**; 起服务前按命令行过滤清 smoke edge
  (`CommandLine -match "edge-smoke"`, **不能全杀 msedge**), 并确认端口无监听
  (kill 后端口释放有延迟, 立即重启必 **10048**)。
  收尾用 **PowerShell** 关端口(`Get-NetTCPConnection -LocalPort N` → `Stop-Process`):
  `uv run python` 是**父子进程**, 按 netstat 的 PID 杀经常**杀不掉父进程** ⇒
  新桩服务 bind 失败而旧服务继续应答 ⇒ **你以为换了参数, 实际还在用旧服务**。
