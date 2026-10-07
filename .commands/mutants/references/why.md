# mutants 包 —— 为什么这么写 / 排障

> 包私有深读(引擎不读它, 只在 `commands run show mutants.run` 的 `doc` 指针里出现)。**排障才读, 别整读。**
> 方法论文档在 skill [mutation-testing](../../../.agents/skills/mutation-testing/SKILL.md); 实测证据在报告
> [26-10-08-0231](../../../memory-bank/reports/26-10-08-0231-report-mutation-testing-feasibility.html)。

## 为什么要有脚本(而不是四条 `run` 串)

一轮 mutmut 是六步: **刷新镜像 → uv sync → 装工具 → 清缓存 → 写 `[tool.mutmut]` → 跑 → 取结果**。
每一步都有「看着正常但不生效」的写法(镜像路径的 `~`、`uv run` 会 prune 掉 `uv pip install` 的工具、
旧 `mutants/` 缓存让 mutmut 提前收工、deselect 表随测试拆分漂移…)。写进 `config.toml` 的 `run` 串
要么拼不出来, 要么拼出来但静默跑错。收进脚本后, **改配置比改记忆可靠**。

## 已验证的命令(2026-10-08 实测, 本机 WSL2 `Ubuntu-26.04`)

```text
# mutmut(WSL, 主力) —— mutants.run 展开成这几步
git -C <mirror> fetch -q origin develop && git -C <mirror> checkout -q -f -B develop FETCH_HEAD
cd <mirror> && uv sync -q
cd <mirror> && test -x .venv/bin/mutmut || uv pip install -q mutmut==3.8.0
cd <mirror> && rm -rf mutants mutmut-cache.db
cd <mirror> && .venv/bin/python .commands/mutants/scripts/set_conf.py --target '<glob>' --pool <files...>
cd <mirror> && .venv/bin/mutmut run --max-children 4
cd <mirror> && .venv/bin/mutmut results
```

```text
# pytest-gremlins(Windows, 兜底) —— mutants.gremlins 展开成这一条
TMPDIR=R:/Temp/auto-qb/tests COVERAGE_FILE=R:/Temp/auto-qb/gremlins.cov \
  uv run --with pytest-gremlins==1.11.2 pytest <pool...> --gremlins \
  --gremlin-targets=<目标文件> -n 0 --no-cov --gremlin-workers=8
```

**实测锚点**(同一台机器): `infra/versioning.py` + `tests/test_versioning.py`
→ mutmut 155 变异 / 21.6s / 杀 147(存活 7 + 超时 1); gremlins 25 变异 / 11.9s / 杀 25(100%)。
`rules/` 整包一轮 = 3,270 变异 / 7m31s / 55.5%(报告 §07 对照五)。

## 环境事实(改脚本前先核)

| 项 | 值 | 备注 |
|---|---|---|
| WSL 发行版 | `Ubuntu-26.04` | `--distro` 可换; `wsl.exe -l -v` 看全 |
| 镜像仓 | `~/auto-qb-mut`(WSL 原生 ext4) | `--mirror` 可换; **别放 `/mnt/*`**(实测拷 116MB 要 52s) |
| 核数 | 8(`.wslconfig` 限) | Windows 侧 32 逻辑核; `--max-children` 默认 4 |
| 工具版本 | mutmut `3.8.0` / pytest-gremlins `1.11.2` | 常量在脚本顶部; 换版本要同步改这里 |
| 结果目录 | `R:/Temp/auto-qb/mutants` | `--out` 可换; 别落仓内(报告 §10 #7) |

## 排障表

| 现象 | 根因 | 处置 |
|---|---|---|
| `[FAIL] --mirror 收到 Windows 路径` | Git Bash 把未加引号的 `~` 展开成了 `C:/Users/...` | 手工调用时加引号: `--mirror '~/auto-qb-mut'`; 走 `commands run` 不受影响(cmd.exe 不展开 `~`) |
| `0 files mutated` + `could not find any test case` | 旧 `mutants/` 缓存让 mutmut 保留上一次(不同目标)的结果 | 脚本每次已 `rm -rf mutants mutmut-cache.db`; 若仍出现, 核 `--target` glob 是否匹配 |
| `skipping mutation testing because N baseline test(s) failed` | 基线不绿, 工具直接跳过 | 先 `commands run test.quick` 修绿再跑(工具硬要求) |
| 整轮基线红在两条文本层守阵 | `mutants/` 把源码撑大, 读源码文本的守阵误报 | 它们在 `set_conf.py` 的 `DEFAULT_DESELECT`; **测试文件拆分后路径会漂移**(`test_web.py` 已拆成 `tests/test_web_*.py`), 报错时按新路径改这张表 |
| 注册表类守阵(如 `test_actions_registry_complete`)在 clean test 里红, 但手跑 `mutants/` 树是绿的 | `process_isolation=fork` 继承的调用形态 | 已固定 `forkserver`(`set_conf.py` 硬写) |
| 覆盖率闸 `FAIL Required test coverage of 98% not reached` | 子集跑必然不满足全库闸 | 已固定 `--no-cov`(`set_conf.py` 的 `pytest_add_cli_args`) |
| WSL 整体失去响应 | 目标太大 / 池太宽 / `--max-children` 拉满 | `wsl --shutdown` 救回; 回按包 + 定向池 + `--children 4` |
| `exec python: not found`(wrapper 端到端用例) | WSL 里通常只有 `python3` | `mutants.setup` 已补 `~/.local/bin/python` 软链(幂等) |

## 本会话验证到哪一步(诚实交代)

- **端到端跑通**: `mutants.run`(mutmut, 用现成镜像 `--no-refresh`)与 `mutants.gremlins`(Windows)都真跑过并拿到汇总。
- **只验了构造、没跑真流程**: `mutants.setup` 的 `git clone` 分支(需联网克隆 116MB)与 `--out` 之外的路径;
  `mutants.status` 只验了正常路径。
- 首次真用 `mutants.setup` 时若失败, 先核: Gitee 可达 / 镜像路径没写错 / WSL 发行版名对得上。
