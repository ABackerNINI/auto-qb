# 容器化后, 一切"读宿主磁盘 / 调宿主程序 / 用桌面"的能力都会静默降级

> 摘要: 程序读的是 **qB 报回来的宿主保存路径**(如 `D:\Downloads\x`), 而容器里没有这块盘 ⇒ `os.path.exists` 恒 False、`realpath` 被拼成 `/app/D:/Downloads`; slim 镜像又缺 `xdg-open` / `notify-send` ⇒ 打开文件夹 404(挂了盘则 500)、通知静默返回 False。**最危险的是缺文件扫描**: 它把"看不见"当成"文件没了", 直接 `torrents_stop` 暂停整组 + 打 `MISSING` 标签 —— 真实写入 qB, 而 `check_missing_files` 默认 `true`、事件触发(非每轮) ⇒ 表现为"时不时一批种子被无故暂停"。
> 触发: docker, 容器, compose, 打开目标文件夹, open-path, 目录浏览, fs/dirs, mkdir, 缺文件, MISSING 标签, 跳检, check_filelist, exists(), disk_total, notify-send, xdg-open, 托盘, TZ, host.docker.internal

## 判别

代码里出现下面任一形态, 且**路径来自 qB 的 `save_path` / `content_path`**(不是 `data_dir` 派生), 就是本坑:

- `os.path.exists` / `os.path.getsize` / `os.path.isdir` —— `grouping.py::_check_missing_files`、`checking.py::check_filelist`、`rules/expr/env.py::_exists`
- `shutil.disk_usage` —— `rules/expr/env.py::_disk_total/_disk_used`(抛 `ExprError: 磁盘不可用`)
- `subprocess.run([外部程序])` —— `utils.open_path`(xdg-open)、`notify.py`(notify-send)、`checking.py::_run_custom_check`(自定义校验程序)
- `os.startfile` / 托盘 / `webbrowser.open` —— 需要桌面会话

**反例(不受影响)**: 派生自 `data_dir` 的路径(state/锁/日志/token/hr/跳检备份)、纯字符串比较(`path_normalize` 后的分组 key 与规则 `path` 匹配)、浏览器侧交付(导出 .torrent、剪贴板)、以及只经 qB API 的动作(标签/分类/限速/重校验)。这些在容器里与宿主直跑完全一致。

## 实测证据(2026-09-26, 镜像 `auto-qb:latest` / python:3.12-slim-bookworm)

```text
command -v xdg-open / notify-send / curl / wget   ->  全部 MISSING
os.path.isdir("D:/Downloads/x")                    ->  False
os.path.realpath("D:/Downloads")                   ->  /app/D:/Downloads   (被当相对路径拼上 cwd /app)
open_path("/tmp")                                  ->  FileNotFoundError: [Errno 2] 'xdg-open'  (未捕获 ⇒ 端点 500)
PlatformChannel()                                  ->  _build_linux ; send() -> False  (仅 DEBUG 一条)
```

- 因此 `/api/open-path` **先**因路径不可见返回 **404**(前端 toast「目标目录不存在或不可访问」);
  只有把下载目录挂成可见之后, 才会暴露第二层 —— `xdg-open` 缺失 ⇒ **500**。两层根因不同, 别只修一层。
- `check_missing_files` **默认 `true`** ⇒ 不显式关就会踩。2026-09-26 起 `docker/config.example.yml` 已显式写
  `false`, 并由 `tests/test_config.py::test_example_docker_config_yml_passes_fail_fast` 钉住 —— **自己手搓的容器配置仍要记得关**。

## 处置

- **容器部署的强制项**: `grouping.check_missing_files: false`(示例已关 + 守阵钉住);`notify.enabled: false`;`basic_check` 不用 `custom`;规则里不写 `exists()` / `disk_*()`;不用 `--tray`。
- **想救回磁盘类能力**: 把下载目录挂到**与 qB 完全相同的绝对路径**(`-v /volume1/downloads:/volume1/downloads:ro`)—— 只读即可救回缺文件扫描 / 跳检前置 / `exists()` / `disk_*()` / 目录浏览;要「新建文件夹」才需可写。**Windows 宿主无解**(盘符路径无法作为 Linux 挂载点), 只能关功能。
- **打开文件夹救不回来**: 它是"外部程序缺失"而非"路径不可见", 装 `xdg-open` 也没有文件管理器可开。替代方案走前端「复制路径」。
- 新增任何读盘 / 起子进程的能力时, 先问一句"容器里这条路径存在吗 / 这个程序在吗", 并在 `docs/deployment.md` §11 矩阵里补一行。

> 完整矩阵与逐项根因: [docs/deployment.md](../../../docs/deployment.md) §11(与宿主直跑的差异 / 四类根因 / 24 项清单)。
