# 后台长跑 (dev.sim / dev.run) 停不干净: 杀了外层, python 子进程还活着占着锁与端口

> 摘要: 本工具环境里 `commands run dev.sim/dev.run` 这类长跑命令挂后台后, TaskStop / kill 只杀外层 (uv 或 commands 包装进程), 真正的 python 子进程继续持有 state.lock / 日志文件 / 端口 —— 复跑撞锁 (`Device or resource busy`) 或端口占用; 必须按命令行匹配进程再补一刀。
> 触发: 后台进程, dev.run 停不下来, state.lock 删不掉, Device or resource busy, 端口占用, TaskStop, 杀进程, 孤儿进程

### TaskStop 之后锁/端口仍被占

- **触发**: `run_in_background` 起 `commands run dev.run -- <cfg>` (或 dev.sim) 做完验证后用 TaskStop 停 (2026-10-04, P6 桩验证实测: 杀完后 `rm state.lock` 报 busy, `netstat` 仍见 ESTABLISHED)。
- **判别**: `powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match '<特征串>' } | Select ProcessId, CommandLine"` 还能看到目标进程; 特征串用配置路径或脚本名 (如 `auto-qb.py H:` / `sim_qb` + 端口号), 别只 match `python.exe` —— 会误伤无关进程。
- **处置**: `Stop-Process -Id <pid> -Force` 补杀后再删锁/复用端口; 复跑前顺手清 `state.lock` + `state.lock.meta.json`。⚠ 排查时可能发现**前会话遗留**的孤儿进程 (本机曾见两个连 R: 盘自家 sim 的 auto-qb), 确认它们的连接目标与自己不冲突即可放过, 不必代杀。
- **关联**: Git Bash 的 `/tmp` 映射到真实盘 (如 `H:\Temp`), bash 工具与 Windows python 传同一路径时要用 Windows 形式 (`H:/Temp/...`), 否则 python 侧 FileNotFoundError。
