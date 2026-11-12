# 平台差异 · 本机复现 CI 的原文(外迁)

> 摘要: `pitfalls/testing/patching.md`「本机复现 CI 的平台差异」节原文整体外迁(2026-11-05 压缩); 「Docker 等价复现」节于 2026-11-13 随计划 26-11-12-0152 S6 回写改写为 **testbed 常驻容器配方**(docker exec 形态), 旧 `docker run --rm` 与 WSL 路线留痕降级为历史(见「历史」条)。
> 触发: test.linux, test.linux-env, test.linux-e2e, linux_ci.py, Docker, WSL, uv sync, host.docker.internal, no_proxy, 容器网络, cp -a, .venv, .coverage, canon 等价论证, posixpath

## 本机复现 CI 的平台差异(比推上去等 CI 快得多)

- **触发**: 怀疑平台差异, 想在本机验证。
- **判别(Docker testbed 常驻容器, 2026-11-12 起唯一主线)**: 两条命令 ——
  ① **`commands run test.linux-env`**: 幂等构建 `auto-qb-testbed` 镜像(ubuntu:24.04 基底; apt 系统依赖 + Python 3.12/3.13 双 venv 模板 + node + playwright chromium 全烘焙, tag 锁 uv.lock hash8)+ 保活常驻容器; 换机 clone 后跑一次, uv.lock 没变就是秒级 no-op。
  ② **`commands run test.linux`**: tar 流推送工作树(含 `.git` 与未提交 WIP, 排除清单剔 `__pycache__`/`.venv`/`node_modules`/`dist`/`.coverage*` 等)进容器 `/root/auto-qb-tests/<slug>/code` → cp 模板 venv 补 delta → 容器内全量 pytest。变体: `--python 3.12` 对齐 CI 矩阵另一版本; `--name <slug>` 每会话独立 workdir, 多会话并行全量互不影响(2026-11-12 双开实测)。
  e2e 走 **`commands run test.linux-e2e`**(playwright headless chromium), 变异走 **mutants.\*** 六条 —— 全部同一容器, 环境即代码可重建。
  ❗**`.git` 必须随拷**(旧坑仍成立): `test_commands_engine` 的 `find_root()` 靠向上找 `.git`, 缺了会多出 5 条假红 —— 它不在排除清单里, 别当冗余"优化"掉。
  ❗**回环代理坑仍在**(2026-10-11 实测, exec 形态继承): 容器里注了代理就必须同时排除回环, 否则 `tests/test_hr_server.py` 那批监听回环的端点测试 **6 failed + 2 errors 假红**(环境造假红, 与 PYTHONUTF8 那条同族)。已内建: `linux_ci.py` 自动透传代理 —— 回环主机改写 `host.docker.internal`(exec 下 Docker Desktop 内建 DNS 解析得到, 免旧形态的 `--add-host=host.docker.internal:host-gateway`, 2026-11-12 getent 实证), `no_proxy` 恒并入回环; 守阵 `.commands/test/scripts/test_linux_ci.py`(红验: 拆掉任一改写点即红)。脚本在, 别再手拼容器命令。
  **为什么是脚本而不是一行 `run`**: 命令里全是 `&&` / `;` / `|` 与多层引号, 而引擎在 Windows 上走 `cmd.exe`(`shell=True`)—— 引号地狱必踩。
  容器内 `ctypes.wintypes` **可导入**, 只有 `ctypes.windll` / `ctypes.WINFUNCTYPE` / `winreg` 缺失。
- **历史(留痕, 2026-11-12 testbed 落地后退役, 别再按此操作)**:
  ① **WSL 路线**: `wsl -- bash -c '...'` 复制一份仓库(排除 `.venv`/`.git`)、`uv sync`、`uv run pytest tests -q`。❗WSL 可能被安全策略拦在黑名单里(2026-09-22 实测 `wsl.exe` 命中 Program Blacklist 被拒, **不可绕过**); 2026-11-12 拍板 D1(宿主用 Docker, 理由=环境即代码可移植重建)后 WSL 不再作测试宿主, 侧残留(7 个 mutmut 镜像仓 ~1.63G + `~/.cache/uv` 258M)已随 S5 清空。
  ② **`docker run --rm` uv 官方镜像形态**(2026-10-04 上线, issue 26-11-12-0053 取证后退役): bind 挂载 `cp -a` 实测 ~1MB/s、引擎 900s 超时杀包装进程后容器成孤儿输出全丢。旧形态三必踩点的去向: 「删容器内 `/work/.git` 假红」已并入上方「.git 必须随拷」; 「`cp -a` 连宿主 Windows `.venv` 一起拷(必须先 rm 再 uv sync 重建, 否则 Linux 上拿到 Windows 二进制)」与「宿主同时跑 pytest 时 `.coverage` 被反复写/删撞 `cannot stat`」两条 —— 排除清单已结构性排除(`.venv`/`.coverage*` 不进 tar 流), 不会再踩。
- **处置**: 退而求其次的**等价论证** —— 用
  `monkeypatch.setattr(模块, "os", types.SimpleNamespace(path=posixpath))` 再跑判据 ——
  这**精确等价**于"该代码跑在 Linux", 于是**在 Windows 上就能复现 Linux 的失败**。
  写成守阵即成防回潮(见 `tests/test_sim_corpus.py::test_fsmock_case_folding_does_not_follow_platform`:
  还原成旧写法时它在本机**立刻红**, 而原有那条 `test_fsmock_long_path_prefix_and_case` **仍然绿** ——
  后者正是"只在 Linux 现形"的原因)。
  ❗守阵判据**别用文本扫描**: `os.path.normcase` 这串字就写在 `_key` 的 docstring 里当反例,
  扫描会被注释骗过(与冒烟 `_scan_filter_facets` 必须先剥 JS 注释同一个坑)。
