# Windows ONLOGON 计划任务注册需提权: 非提权进程 rc=1「拒绝访问」, 与 Program Blacklist 的 WinError 5 同指纹

> 摘要: Windows ONLOGON 计划任务注册需提权: 非提权进程 rc=1「拒绝访问」, 与 Program Blacklist 的 WinError 5 同指纹
> 触发: 开机自启, autostart, schtasks, ONLOGON, 计划任务, 拒绝访问, 提权, UAC, 自启注册失败, HKCU Run, 注册表自启, Run 值 260

### 用 `schtasks /SC ONLOGON` 做「开机自启」= 必然要提权, 而无人值守路径上没人点 UAC

- **触发**: 想给一个后台工具加 Windows 开机自启, 顺手选 `schtasks /Create /SC ONLOGON /TR "<命令>"`。`ONLOGON` 是「**任何用户**登录」级系统触发器, 普通用户令牌创建会被 Task Scheduler 拒; 而这类工具通常由另一个程序以普通权限拉起(本项目: auto-qb 跑 `launch.cmd`), 整条路径上没有 UAC 窗口可点。
- **判别**: ①`schtasks` 真的跑起来了(拿得到 `rc=1`), stderr 是它自己的中文报错「错误: 拒绝访问。」; ②管理员 cmd 下同一条命令成功; ③**别和 Program Blacklist 混**: 被安全策略拦是 `PermissionError [WinError 5]` 落在 `CreateProcess` 上、**拿不到 rc**, stderr 末段有 `PROGRAM BLOCKED BY SECURITY POLICY`(见 `pitfalls/ops/session-program-blacklist.md`); 有 rc + schtasks 自己的文案 = 真被 Task Scheduler 拒, 不是沙箱。
- **处置**: 换**零提权**的当前用户后端 —— `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 写一个 `REG_SZ` 值(stdlib `winreg`, 无需第三方依赖), 语义正好是「当前用户登录时起」。注意三件事: ①Run 值有 **260 字符上限**, 超了会被截断成一条跑不起来的命令 ⇒ 注册前量长度并 fail-fast 报错, 不静默截断; ②「已注册」判据取**值存在**(开关语义 = 有没有自启项), 命令漂移靠 `register()` 无条件覆盖写收敛; ③从计划任务迁过来的机器可能残留旧任务, 代码里不必为它留提权路径, 文档给一条 `schtasks /Delete /TN <名> /F` 手工清理即可。
- **守阵**: `tools/global-traffic-monitor/tests/test_installer.py` 的 Windows 段(`FakeRegistry` 替身, 含「超限 fail-fast」与「runner 一次都不该被调」两条) —— 有人把 schtasks 加回来时, `test_windows_register_runs_no_platform_command` 会红。
- **复发**: 0
