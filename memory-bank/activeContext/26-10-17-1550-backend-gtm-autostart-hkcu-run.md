# backend-gtm-autostart-hkcu-run

> 摘要: gtm Windows 自启改 HKCU Run（移除 schtasks 路径），注册失败原因落 endpoint.json 的 autostart_error 并在设置页显示
> 最后活动: 2026-10-17 15:50

**R0(2026-10-17 15:50):** gtm Windows 自启改 HKCU Run（移除 schtasks 路径），注册失败原因落 endpoint.json 的 autostart_error 并在设置页显示

## 现状

已完结（代码 + 测试 + 文档 + 真机验证）。起点是 issue `issues/26-10-17-1455-bug-gtm-autostart-elevation.html`，档案 `tasks/26-10-17-backend-gtm-autostart-hkcu-run.md`，基线 `testing/baselines/26-10-17-1549-gtm-autostart-hkcu-run.md`。

## 关键事实（后续接手先看这几条）

- Windows 自启机制 = `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 值 `global-traffic-monitor`（零提权）；**代码里已无任何 `schtasks` 调用**，坑档 `pitfalls/backend/windows-onlogon-autostart-elevation.md` 记了为什么不能走 `ONLOGON`。
- 「已注册」= 值存在即算；命令漂移由 `register()` 覆盖写收敛，所以换了 venv/数据目录**不需要**先卸载再注册（旧 README 那句已删）。
- 失败原因走 `endpoint.json` 的 `autostart_error`（可选字段，schema 仍为 1）：启动期注册失败 → 进程内暂存 → `ControlServer` 写指针时落盘 → auto-qb 状态接口透传 → 设置页显示在「未注册」后。
- Run 值 260 字符上限在写入前 fail-fast；本机命令 158 字符。

## 未做 / 下一步

- **重启/注销后的真实登录自起未验证**（需真实登录会话，不可自动化）——这是本 issue 唯一剩余缺口。
- 真机验证时注册的那条值**已卸载**：它指向 clone4 开发目录，留着会与 `D:\Projects\auto-qb` 的生产实例抢登录自启。真实部署由生产 clone 的 `launch.cmd` 自行注册。
- 旧 schtasks 计划任务若在某些机器上残留，按文档手工清：`schtasks /Delete /TN global-traffic-monitor-autostart /F`（管理员）。
