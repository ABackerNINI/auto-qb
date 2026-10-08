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
# 主线后半段 —— mutants.report / mutants.verify 展开成这几步
# report: 脚本从仓库推进镜像 /tmp(stdin 传内容, 不走命令行参数 —— 多行参数会被登录壳按行拆开)
cat > /tmp/mutants_dump.py < <仓库里的 .commands/mutants/scripts/mutants_dump.py>
cd <mirror> && .venv/bin/python /tmp/mutants_dump.py --status 'survived,no tests' --target-glob '<glob>'
# verify: 逐条候选 —— apply -> 跑全套件 -> 还原(全部在镜像 src/ 上, 不碰主仓库)
cd <mirror> && git checkout -- src/ && .venv/bin/mutmut apply <mutant_id> \
  && .venv/bin/python -m pytest tests/ -q -n 8 --no-cov -x -p no:cacheprovider | tail -4 \
  && git checkout -- src/
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

## 结果怎么读 (`mutmut results` 只有 id, 没有 diff)

`mutmut results` 每行只回 `id: status` —— **没有文件:行, 也没有变异内容**, 光看它没法三分类。
两条路:

1. **要清单 + diff**: `mutants.report`(内部就是 `scripts/mutants_dump.py`, 在镜像里跑)。
   它读镜像的状态缓存、用 mutmut 的 `diff_apply` 现场重放每条变异, 输出 `@@@ <id> :: <status>`
   + unified diff, 并打按状态 / 按模块汇总 —— 三分类就基于这份清单。
2. **要单条**: `cd <mirror> && .venv/bin/mutmut show <id>`。

**状态存在哪**(改脚本 / 排障时要认准):

| 文件 | 内容 |
|---|---|
| `mutants/<源码路径>.meta` | `exit_code_by_key` —— **状态的真身**(每条变异的退出码) |
| `mutants/<源码路径>.spans` | 函数行区间索引 |
| `mutants/mutmut-stats.json` | 函数哈希 / 测试映射 / 耗时(**不含**每条变异的状态) |
| `mutmut-cache.db` | **0 字节, 别被它骗** —— 状态不在这个 sqlite 里 |

**汇总行的 emoji**(`mutmut.stats.emoji_by_status`, 顺序 = `🎉 🫥 ⏰ 🤔 🙁 🔇 🧙`):
🎉 killed · 🫥 no tests(无任何测试覆盖) · ⏰ timeout · 🤔 suspicious · 🙁 survived(有覆盖但没杀掉) · 🔇 skipped。
**`no tests` 与 `survived` 是两类**, 分母不同, 别混着比。

**首轮实测锚点(config 包, 2026-10-08)**: 4,799 变异 / 杀 3,851 / 存活 893 / `no tests` 55 → 杀死率 80.25%;
墙时 294.4s(含 setup), 变异阶段 17.41 变异/s; 补测后同池复跑 22.67 变异/s / 存活 772。

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
| `mutants.status` 恒报 `mutmut=no`(实际已装) | WSL 登录壳实为 zsh —— `cd` 改了**真实** cwd, 但 `$PWD` / `$()` 仍报 WSL 启动目录; `status` 的 `$(test -x .venv/bin/mutmut ...)` 因此读错目录 | **别据此重装工具**; 以 `cd X && <cmd>` 的**直接输出**为准。`mutants.run` 不受影响(全程 `cd X && cmd`)。详见坑档 [memory-bank/pitfalls/testing/mutants-wsl-shell.md](../../../memory-bank/pitfalls/testing/mutants-wsl-shell.md) |
| 复跑时新加的守阵"没生效"(存活数不降) | `mutants.run` 默认 `git checkout -q -f -B develop FETCH_HEAD`, 会把镜像里**未提交的测试改动冲掉** | 先把新测试 `cp` 进镜像 `tests/`, 再 `mutants.run --no-refresh`(跳过刷新) |
| 想看某条变异的 diff / 想批量三分类 | `mutmut results` 只有 id, 没有 diff | 用 `mutants.report`(带 diff 的清单 + 按状态/按模块汇总); 单条用 `mutmut show <id>` |
| `verify` 跑得极慢 / 想中断 | 每条候选都要跑一遍**全套件**(实测 ~15s/条) | 先 `mutants.report` 再用 `--only-status` 或手挑把候选缩小; 中断后重跑同一 `--out` 自动续(已验 id 跳过) |
| 想用「本地新守阵」而不是 develop 的测试跑 verify | `verify` 默认刷新镜像(测试 = develop) | 加 `--no-refresh`(镜像里是什么测试就用什么) |

## 本会话验证到哪一步(诚实交代)

- **端到端跑通**: `mutants.run`(mutmut)与 `mutants.gremlins`(Windows)都真跑过并拿到汇总。
- **config 首轮(2026-10-08)把主线全链走了一遍**: `mutants.setup`(真跑 `git clone` 分支, 12s) ·
  `mutants.run`(4,799 变异 / 294.4s) · `mutants.report`(导出 827 条带 diff 的清单 + 汇总) ·
  `mutants.verify`(逐条 apply → 全套件 → 还原, 14s/条, 274 条) · 补测后 `mutants.run --no-refresh` 复跑。
  ⇒ `report` / `verify` 与 `setup` 的 clone 分支都**已实测**, 不再是"只验构造"。
- **仍未验**: `--out` 之外的落盘路径; `mutants.status` 只验了正常路径(且本机因 zsh `$()` 恒报 `mutmut=no`,
  见排障表 —— 这条**未修**, 属计划外)。
- 首次在新机器上真用 `mutants.setup` 若失败, 先核: Gitee 可达 / 镜像路径没写错 / WSL 发行版名对得上。
