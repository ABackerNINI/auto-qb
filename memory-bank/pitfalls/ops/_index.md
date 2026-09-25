# ops — 生产文件与环境

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 不许碰的生产文件(`config.yml` / `auto-qb-data/`) —— 已在 `.commands/my-commit-flow/.my-commit-flow.toml` 的 `red_lines` 里, 提交时会被直接拒交。
> **触发**: 改配置示例, 提交前扫红线, 整理仓库, 统一格式, 运行时数据

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [alert-levels.md](alert-levels.md) | 本仓把 WARNING 以上**推成系统通知**, 而取数/后台线程是分钟级轮询 —— 只要把「按设计在等 / 自己决定要做」的状态(未到取数时机、被自己的频控拦下、启动关闭重挂)记成 WARNING, 用户就会被弹窗淹没, 然后**开始忽略所有告警**。四条判据: ①故障才 WARNING ②同一根因只说明白一次 ③同一事件只由一个角色告警 ④持续状态不静默消失。 | 通知太多, 弹窗, 告警疲劳, WARNING, 日志刷屏, 每分钟一条, 节流, 限速, 未到可取时刻, partial, 启动日志, 后台线程日志, notify 推送, 轮询, 重复告警, 两条通知 |
| [console-encoding.md](console-encoding.md) | Windows 上被管道接住的 Python 子进程按**本地码页(cp936)**输出 stdout, 而调用方按 UTF-8 硬解 ⇒ 中文变一串 U+FFFD; 退出码照旧 0, **一个报错都没有** —— 只有人读输出时才发现。**反方向也一样会炸**: 非 Python 子进程(如 node)输出就是 UTF-8, 而 `text=True` 按 locale 去解 ⇒ 直接抛 `UnicodeDecodeError`。 | 输出乱码, 乱码, 中文变问号, U+FFFD, 子进程 stdout, cp936, GBK, PYTHONIOENCODING, 引擎打印外部输出, 包装脚本, 命令行工具输出, UnicodeDecodeError, subprocess text=True, node 输出, encoding |
| [msys-container-path.md](msys-container-path.md) | 工具 shell 是 Git Bash, `docker exec / docker run / docker compose run` 的**容器内**路径参数(如 `/data/web.token`、`/config/x.yml`)会被 MSYS 按"POSIX 绝对路径"自动改写成 Windows 形态(`D:/Program Files/Git/data/web.token`) —— 命令能跑、退出码正常, 但容器里报「找不到文件/配置文件读取失败」, 看着像容器坏了其实是参数在进容器前就被改了。 | docker exec, docker run, docker compose run, 容器路径, 找不到文件, 配置文件读取失败, Git Bash, 路径转换, MSYS, web.token, token 文件 |
| [prod-files.md](prod-files.md) | `config.yml` 与 `auto-qb-data/` 是用户真实生产数据, 不许改、不许提交 —— 示例一律用 `minimal.yml` / `test_yamls/`。 | 改配置示例, 新增示例 yml, 提交前扫红线, 整理仓库, 统一格式 |
| [shell-env.md](shell-env.md) | 本工具的终端是**长驻会话**(环境变量跨命令保留) —— 为拿到机器级 PATH 里的工具而反复执行 `$env:PATH = $env:PATH + ';' + 机器PATH` 会把它撑到 240+ 项, **子进程的环境块被截断** ⇒ `cmd.exe` 里连 `python` 都报「不是内部或外部命令」, 而 `where.exe python` 仍找得到; 症状看着像「命令引擎坏了」。判据: ①裸名解析不到时先数 PATH 项数 ②拼之前先按项去重 ③本项目自己的命令一律走 `commands run <task>`。 | PATH, 环境变量, python 不是内部或外部命令, not recognized, node 找不到, 命令引擎, kb.check 失败, 子进程环境块, 长驻终端, 沙箱 |
