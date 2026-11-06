# ops — 生产文件与环境

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 不许碰的生产文件(`config.yml` / `auto-qb-data/`) —— 已在 `.commands/my-commit-flow/.my-commit-flow.toml` 的 `red_lines` 里, 提交时会被直接拒交。
> **触发**: 改配置示例, 提交前扫红线, 整理仓库, 统一格式, 运行时数据

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [agent-write-guard-secret-false-positive.md](agent-write-guard-secret-false-positive.md) | 本工作区的写入判据(`artifact_secret_detected`)对**整文件**扫描「形如凭据赋值的字面量」, 命中即拒绝**整个写入** —— 而命中项可能是**既有行**(不在本次改动里)。实测: `src/auto_qb/webui/static/shared/a… | artifact_secret_detected, 写入被拦, 凭据字面量, 误判, 文件写不进去, edit 失败, 安全判据, 明文密钥, 工作区写入, 不要绕过 |
| [alert-levels.md](alert-levels.md) | 本仓把 WARNING 以上**推成系统通知**(2026-09-27 起 min_level 默认 ERROR, 只有真正危险才弹窗, WARNING 收窄为纯排障等级 —— 口径单点见 `conventions/code-style.md`「日志规范」), 而取数/后台线程是… | 通知太多, 弹窗, 告警疲劳, WARNING, 日志刷屏, 每分钟一条, 节流, 限速, 未到可取时刻, partial, 启动日志, 后台线程日志, notify 推送, 轮询, 重复告警, 两条通知 |
| [console-encoding.md](console-encoding.md) | Windows 上被管道接住的 Python 子进程按**本地码页(cp936)**输出 stdout, 而调用方按 UTF-8 硬解 ⇒ 中文变一串 U+FFFD; 退出码照旧 0, **一个报错都没有** —— 只有人读输出时才发现。**反方向也一样会炸**: 非 Pytho… | 输出乱码, 乱码, 中文变问号, U+FFFD, 子进程 stdout, cp936, GBK, PYTHONIOENCODING, 引擎打印外部输出, 包装脚本, 命令行工具输出, UnicodeDecodeError, subproce… |
| [docker-host-features.md](docker-host-features.md) | 程序读的是 **qB 报回来的宿主保存路径**(如 `D:\Downloads\x`), 而容器里没有这块盘 ⇒ `os.path.exists` 恒 False、`realpath` 被拼成 `/app/D:/Downloads`; slim 镜像又缺 `xdg-open` /… | docker, 容器, compose, 打开目标文件夹, open-path, 目录浏览, fs/dirs, mkdir, 缺文件, MISSING 标签, 跳检, check_filelist, exists(), disk_total… |
| [msys-container-path.md](msys-container-path.md) | 工具 shell 是 Git Bash, `docker exec / docker run / docker compose run` 的**容器内**路径参数(如 `/data/web.token`、`/config/x.yml`)会被 MSYS 按"POSIX 绝对路径"自… | docker exec, docker run, docker compose run, 容器路径, 找不到文件, 配置文件读取失败, Git Bash, 路径转换, MSYS, web.token, token 文件 |
| [port-kill-prod-instance.md](port-kill-prod-instance.md) | 起 dev 桩时 18788(生产发现端点默认端口)绑不上, netstat 看到陌生 pid LISTENING, **没查它是什么程序**就跑 `commands run dev.port-kill -- 18788` 强杀 —— 杀掉的是用户的生产 auto-qb 主程序。… | 端口绑不上, WinError 10013, 端口被占, port_kill, 杀进程, dev 桩起不来, 残留清理, 生产实例, 发现端点 18788, 核实进程身份 |
| [prod-files.md](prod-files.md) | `config.yml` 与 `auto-qb-data/` 是用户真实生产数据 —— 提交面禁令由 `.commands/my-commit-flow/.my-commit-flow.toml` 的 `red_lines` **机器预检强制执行**(预检与 `commit.py… | 改配置示例, 新增示例 yml, 提交前扫红线, 整理仓库, 统一格式 |
| [sandbox-junction.md](sandbox-junction.md) | skill junction 在代理命令沙箱里新建即断 | skill 链接同步, junction, sync_agent_skills, ship.commit 闸门失败, Path.exists 假 False, codebuddy skills 断链 |
| [session-program-blacklist.md](session-program-blacklist.md) | 本工具的**命令安全策略**把某些系统程序列入 Program Blacklist (实测 `schtasks.exe`)。从 Bash / PowerShell 工具起的**任何**进程链一旦碰到它, 整条调用失败, 且第一层报错是 `PermissionError: [Win… | 计划任务, schtasks, 真机冒烟, 命令被拦, Program Blacklist, 程序黑名单, 命令安全策略, PermissionError, WinError 5, 拒绝访问, CreateProcess, 沙箱, 系统命令… |
| [shell-env.md](shell-env.md) | 本工具的终端是**长驻会话**(环境变量跨命令保留) —— 为拿到机器级 PATH 里的工具而反复执行 `$env:PATH = $env:PATH + ';' + 机器PATH` 会把它撑到 240+ 项, **子进程的环境块被截断** ⇒ `cmd.exe` 里连 `pyth… | PATH, 环境变量, python 不是内部或外部命令, not recognized, node 找不到, 命令引擎, kb.check 失败, 子进程环境块, 长驻终端, 沙箱, commands 装了没用, wrapper 不识别,… |
| [ship-commit-timeout.md](ship-commit-timeout.md) | ship.commit 大批撞引擎 600s 超时: 提交落库后被杀在推送段 | ship.commit 超时, 卡住的命令, 提交被杀, 推送未完成, 补推前先补验 |
| [taskkill-image-name-ban.md](taskkill-image-name-ban.md) | taskkill 任何形态一律禁止 —— 本机生产 qB(26586)与测试实例同名映像 qbittorrent.exe, /IM 按映像名全杀 = 静默误杀生产(2026-11-05 E1.6 实际发生); bash 裸跑还有 MSYS 路径改写假失败层诱人换 python s… | taskkill, 杀进程, IM, 映像名, 误杀生产, MSYS 路径改写, Stop-Process, real.down, qbittorrent.exe, 强杀 |
| [uv-trampoline-broken.md](uv-trampoline-broken.md) | `.venv/Scripts/` 下的工具入口 exe(pytest.exe / yapf.exe 等)是 uv 的 trampoline 薄壳, 一旦壳与目标 venv 的相对位置/路径解析对不上就整体失效: 直接跑 `<tool>.exe` 报 `uv trampoline… | uv trampoline, canonicalize, pytest.exe, yapf.exe, .venv/Scripts, 打不开工具, env.sync 不自愈, uv sync --reinstall-package |
| [venv-trampoline-clone-copy.md](venv-trampoline-clone-copy.md) | clone 连 .venv 复制致 uv trampoline 内嵌路径失效, env.sync 假自愈 | uv trampoline failed to canonicalize script path,uv run pytest 报错,console script 起不来,uv sync 后仍坏,uv run python 却正常 |
| [vnu-gate-bootstrap.md](vnu-gate-bootstrap.md) | check_html --vnu 首跑自举: GitHub 直连被墙且本机无 java | vnu, check_html, vnu.jar, java 不可用, SSL CERTIFICATE_VERIFY_FAILED, release-assets 超时, HTML 规范级检查 |
| [wsl-mutation-memory.md](wsl-mutation-memory.md) | 12 GiB 的 WSL VM 里, 中池变异目标的并发上限由**单 worker RSS**(实测 5.2–5.8 GB)决定, 不是由 8 核决定 —— `--children 2` 合计就顶穿 11.68 GiB, 三轮都死在第 80/1804 条; 另外 2026-11-… | WSL, 变异测试, mutmut, 内存, OOM, 并发, children, RSS, setsid, nohup, distro, 失联, 常驻会话, vmIdleTimeout, 91秒回收, 客户端被切 |
