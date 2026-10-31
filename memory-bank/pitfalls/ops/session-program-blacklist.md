# 会话内的「程序黑名单」: 系统命令被拦, 真机冒烟做不了 (WinError 5 是双重误导)

> 摘要: 本工具的**命令安全策略**把某些系统程序列入 Program Blacklist (实测 `schtasks.exe`)。从 Bash / PowerShell 工具起的**任何**进程链一旦碰到它, 整条调用失败, 且第一层报错是 `PermissionError: [WinError 5] 拒绝访问。` 落在 `subprocess` 的 `CreateProcess` 上 —— 看着像权限/文件系统问题, 真判据是 stderr 末段那条 `PROGRAM BLOCKED BY SECURITY POLICY ... This block cannot be approved or bypassed from the current command`。⇒ 依赖该程序的动作(计划任务注册、`schtasks` 查询、任何以它为前置的真机冒烟)**在本会话内不可完成**, 这不是代码 bug。处置 = 降级冒烟 + 明确报告缺口, **绝不换壳重试**(消息本身明令禁止)。
> 等级: L0
> 触发: 计划任务, schtasks, 真机冒烟, 命令被拦, Program Blacklist, 程序黑名单, 命令安全策略, PermissionError, WinError 5, 拒绝访问, CreateProcess, 沙箱, 系统命令不可用, 自启注册, installer 验收, launchctl, systemctl, 换壳重试

## 现象与判别 (2026-10-16, gtm S5 自启 installer 轮)

- **触发**: 写 gtm S5 的真机冒烟(注册 Windows 计划任务 → 拉起来 → `GET /status` → 卸载),
  脚本第一步 `schtasks /Query /TN gtm-autostart` 就炸。
- **第一层报错(误导)**: `PermissionError: [WinError 5] 拒绝访问。`, 堆栈落在
  `subprocess._execute_child` → `_winapi.CreateProcess`。**这条指纹在本仓另有所指** ——
  `pitfalls/backend/platform-fs.md`「Windows 原子写与并发读者的双向瞬时拒绝」用的就是
  WinError 5 ⇒ 先怀疑错方向(文件系统/句柄)是很容易的。
- **真判据**: stderr 末段那行 `PROGRAM BLOCKED BY SECURITY POLICY - The sandbox prevented a
  program on the configured Program Blacklist from starting: - schtasks.exe
  (C:\WINDOWS\SYSTEM32\schtasks.exe)`。**有这行才是被策略拦**, 没有则回到 platform-fs 那条查。
- **不可绕**: 同一条消息明写「This block cannot be approved or bypassed from the current
  command. Do NOT retry this program, launch it through another shell or script, or attempt an
  equivalent workaround.」⇒ 换 shell / 换包装脚本 / 用 `os.system` / 用 PowerShell 调
  `New-ScheduledTask` **都是被禁的等价绕行**, 不许试。

## 处置

1. **先分档**: WinError 5 + `PROGRAM BLOCKED` 行 = 环境策略; WinError 5 无该行 = 回
   `platform-fs.md` 的原子写/句柄族。两者不许混记。
2. **降级冒烟**: 把「注册项里那条命令」单独拿出来真跑一遍 —— 例如 gtm S5 用
   `subprocess.Popen(plan.windows_command(), shell=True)` 经 `cmd.exe` 解析 TR 字符串,
   验证解释器解析 + `-m gtm run --data-dir` + 引号往返 + `GET /status` + token 401 + 收尾停干净。
   覆盖「除被拦程序之外」的全部真机事实。
3. **缺口明写**: 被拦掉的那一段(计划任务真注册 / 登录自起)写进计划实施记录与基线切片,
   标注「环境拦截, 待解锁后重跑」—— **不许静默当作验过**, 也不许拿 mock 单测冒充真机。
4. **解锁路径**: 用户从 Security Center → Command Security → Program Blacklist 移除该项后重跑;
   或用户在自己的终端里手动跑 `gtm install-autostart`(用户终端不经本会话策略)。
5. **设计侧收益**: 这类动作的命令层**本来就应该可 mock**(gtm S5 的 `Runner` 注入), 被拦时才
   不会整步失去验证手段 —— 反过来说, 「真机只此一条路」的动作设计要预先留出 mock 面。

**Refs:** memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md, memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html, memory-bank/pitfalls/backend/platform-fs.md
