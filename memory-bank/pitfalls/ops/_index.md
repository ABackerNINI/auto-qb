# ops — 生产文件与环境

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 不许碰的生产文件(`config.yml` / `auto-qb-data/`) —— 已在 `.commands/my-commit-flow/.my-commit-flow.toml` 的 `red_lines` 里, 提交时会被直接拒交。
> **触发**: 改配置示例, 提交前扫红线, 整理仓库, 统一格式, 运行时数据

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [alert-levels.md](alert-levels.md) | 本仓把 WARNING 以上**推成系统通知**(2026-09-27 起 min_level 默认 ERROR, 只有真正危险才弹窗, WARNING 收窄为纯排障等级 —— 口径单点见 `conventions/code-style.md`「日志规范」), 而取数/后台线程是… | 通知太多, 弹窗, 告警疲劳, WARNING, 日志刷屏, 每分钟一条, 节流, 限速, 未到可取时刻, partial, 启动日志, 后台线程日志, notify 推送, 轮询, 重复告警, 两条通知 |
| [console-encoding.md](console-encoding.md) | Windows 上被管道接住的 Python 子进程按**本地码页(cp936)**输出 stdout, 而调用方按 UTF-8 硬解 ⇒ 中文变一串 U+FFFD; 退出码照旧 0, **一个报错都没有** —— 只有人读输出时才发现。**反方向也一样会炸**: 非 Pytho… | 输出乱码, 乱码, 中文变问号, U+FFFD, 子进程 stdout, cp936, GBK, PYTHONIOENCODING, 引擎打印外部输出, 包装脚本, 命令行工具输出, UnicodeDecodeError, subproce… |
| [docker-host-features.md](docker-host-features.md) | 程序读的是 **qB 报回来的宿主保存路径**(如 `D:\Downloads\x`), 而容器里没有这块盘 ⇒ `os.path.exists` 恒 False、`realpath` 被拼成 `/app/D:/Downloads`; slim 镜像又缺 `xdg-open` /… | docker, 容器, compose, 打开目标文件夹, open-path, 目录浏览, fs/dirs, mkdir, 缺文件, MISSING 标签, 跳检, check_filelist, exists(), disk_total… |
| [msys-container-path.md](msys-container-path.md) | 工具 shell 是 Git Bash, `docker exec / docker run / docker compose run` 的**容器内**路径参数(如 `/data/web.token`、`/config/x.yml`)会被 MSYS 按"POSIX 绝对路径"自… | docker exec, docker run, docker compose run, 容器路径, 找不到文件, 配置文件读取失败, Git Bash, 路径转换, MSYS, web.token, token 文件 |
| [port-kill-prod-instance.md](port-kill-prod-instance.md) | 起 dev 桩时 18788(生产发现端点默认端口)绑不上, netstat 看到陌生 pid LISTENING, **没查它是什么程序**就跑 `commands run dev.port-kill -- 18788` 强杀 —— 杀掉的是用户的生产 auto-qb 主程序。… | 端口绑不上, WinError 10013, 端口被占, port_kill, 杀进程, dev 桩起不来, 残留清理, 生产实例, 发现端点 18788, 核实进程身份 |
| [prod-files.md](prod-files.md) | `config.yml` 与 `auto-qb-data/` 是用户真实生产数据, 不许改、不许提交 —— 示例一律用 `minimal.yml` / `test_yamls/`。 | 改配置示例, 新增示例 yml, 提交前扫红线, 整理仓库, 统一格式 |
| [shell-env.md](shell-env.md) | 本工具的终端是**长驻会话**(环境变量跨命令保留) —— 为拿到机器级 PATH 里的工具而反复执行 `$env:PATH = $env:PATH + ';' + 机器PATH` 会把它撑到 240+ 项, **子进程的环境块被截断** ⇒ `cmd.exe` 里连 `pyth… | PATH, 环境变量, python 不是内部或外部命令, not recognized, node 找不到, 命令引擎, kb.check 失败, 子进程环境块, 长驻终端, 沙箱, commands 装了没用, wrapper 不识别,… |
