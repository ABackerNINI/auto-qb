# 平台差异 · 本机复现 CI 的原文(外迁)

> 摘要: `pitfalls/testing/patching.md`「本机复现 CI 的平台差异」节原文整体外迁(2026-11-05 压缩), 正文原样照搬, 标题降一级以避开坑档条目扫描。
> 触发: test.linux, linux_ci.py, Docker, WSL, uv sync, host.docker.internal, no_proxy, 容器网络, cp -a, .venv, .coverage, canon 等价论证, posixpath

## 本机复现 CI 的平台差异(比推上去等 CI 快得多)

- **触发**: 怀疑平台差异, 想在本机验证。
- **判别**: WSL 里 `wsl -- bash -c '...'` 复制一份仓库(排除 `.venv` / `.git`)、`uv sync`、
  `uv run pytest tests -q` 即可(加 `-p 3.12` / `-p 3.13` 还能对上 CI 矩阵版本)。
  ❗**WSL 可能被安全策略拦在黑名单里**(2026-09-22 实测: `wsl.exe` 命中 Program Blacklist 被拒, **不可绕过**)。
- **Docker 等价复现 (2026-10-04 实测可用, 替代 WSL)**: 已收录为 task —— **`commands run test.linux`**
  (脚本 `.commands/test/scripts/linux_ci.py`; 传参可换镜像, 如 `python3.13-bookworm-slim`)。
  命令本体不再抄在这里(手抄即第 N 处副本, 判据见 commands skill「收录协议」)。
  ❗**三个必踩点**(脚本已内建, 手写时必踩): ① **不要删容器内 `/work/.git`** —— `test_commands_engine`
  的 `find_root()` 靠向上找 `.git`, 删了会多出 5 条假红; ② `cp -a` 会连宿主的 Windows `.venv` 一起拷进来,
  必须先 `rm -rf` 再由 `uv sync` 重建(否则 Linux 上拿到 Windows 二进制); ③ 宿主**同时**在跑 pytest 时
  仓库根的 `.coverage` 会被反复写/删, `cp -a` 可能撞 `cannot stat`。
  **为什么是脚本而不是一行 `run`**: 命令里全是 `&&` / `;` / `|` 与多层引号, 而引擎在 Windows 上走
  `cmd.exe`(`shell=True`)—— 引号地狱必踩。
  容器内 `ctypes.wintypes` **可导入**, 只有 `ctypes.windll` / `ctypes.WINFUNCTYPE` / `winreg` 缺失。
- **❗两条容器网络坑 (2026-10-11 实测, 各烧掉一轮 10 分钟)**: ①**容器内 `uv` 直连 PyPI 被墙**
  (`Failed to resolve … hatchling` / `tls handshake eof`) —— 宿主是走代理的, 而容器里
  `127.0.0.1:4085` 指向容器自己 ⇒ `uv sync` 起不来; 出口选宿主代理
  `-e http_proxy=… -e https_proxy=http://host.docker.internal:4085`(需 `--add-host=host.docker.internal:host-gateway`;
  实测宿主代理通、清华镜像 `pypi.tuna` 也通、**直连 pypi 不通**)。②**注了代理就必须同时排除回环**:
  `urllib` 会把 `127.0.0.1` 的请求也交给代理 ⇒ `tests/test_hr_server.py` 那批监听回环的端点测试
  **6 failed + 2 errors 假红**(环境造假红, 与 PYTHONUTF8 那条同族)——
  补 `-e no_proxy=127.0.0.1,localhost,::1` 后同一命令 **3128 passed + 6 skipped / 0 failed**。
  ⚠ **已内建 (2026-10-11)**: `linux_ci.py` 现在自动透传代理 —— 回环主机改写成 `host.docker.internal`
  (+`--add-host`), `no_proxy` 恒并入回环; 守阵 `.commands/test/scripts/test_linux_ci.py`(红验: 拆掉任一改写点即红)。
  脚本在, 别再手拼容器命令。
- **处置**: 退而求其次的**等价论证** —— 用
  `monkeypatch.setattr(模块, "os", types.SimpleNamespace(path=posixpath))` 再跑判据 ——
  这**精确等价**于"该代码跑在 Linux", 于是**在 Windows 上就能复现 Linux 的失败**。
  写成守阵即成防回潮(见 `tests/test_sim_corpus.py::test_fsmock_case_folding_does_not_follow_platform`:
  还原成旧写法时它在本机**立刻红**, 而原有那条 `test_fsmock_long_path_prefix_and_case` **仍然绿** ——
  后者正是"只在 Linux 现形"的原因)。
  ❗守阵判据**别用文本扫描**: `os.path.normcase` 这串字就写在 `_key` 的 docstring 里当反例,
  扫描会被注释骗过(与冒烟 `_scan_filter_facets` 必须先剥 JS 注释同一个坑)。
