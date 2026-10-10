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

**hr 包首轮(2026-10-10, 大包样本)**: 8,027 变异 / 杀 5,554 / 存活 2,440 / `no tests` 23 / 超时 10 → 杀死率 **69.2%**;
墙时 ≈**96 min**(60 min 撞 timeout 截断 + 35m52s 续跑), 整体 ≈**1.4 变异/s**(比 config 慢约 5x, 且前 85% 快、
长尾慢); S4 抽验 24/24 SURVIVED —— **池宽(15 文件覆盖整包)⇒ 零假存活**, `verify` 在此场景不缩小候选。

### 什么时候**不用** `mutants.verify`(自己写脚本更快 / 更准)

`mutants.verify` 是**按 mutmut 的 id** 工作的: `apply <id>` → 跑**全套件** → 还原。两种情形它用不上或划不来,
这时自己写一份临时脚本(落 `tmp-analysis/`, gitignored)更快:

1. **候选只有「形态」没有 id** —— 真洞 issue 常只写「`_get(...)` 默认值换成 None」「删掉某个关键字实参」。
   手搓同构变异 + 跑**定向池**(实测 ≈3s/条)vs 全套件(≈15s/条), 40 条 ≈2.6min 对 ≈10min, 且同一份脚本
   跑两遍即得「形态复验(补测前存活几条)」+「红验(补测后是否全红)」。
2. **要验的变异工具根本不会生成** —— mutmut 只在现存代码上做变换, 造不出「能让差别显形的输入」
   (如派生值恰等于字段默认时, 删实参是等价变异)。手搓可以自己造变异 + 自己造输入。

**别越界**: 手搓变异**不是** mutmut 编号, 它的条数**不能**报进存活数 / 杀死率; 量化只认 `mutants.run`
同目标同池复跑(规程与锚点纪律见 `mutation-testing` skill 硬约束 13 与「形态级手搓复验」节)。

## 跑完之后: 数字要落到哪几处(收尾别漏)

一轮跑完, 同一批数字有**四个落点**, 各有唯一职责(缺一处这轮不算收尾):

| 落点 | 放什么 | 何时 |
|---|---|---|
| 基线切片 `memory-bank/testing/baselines/<stamp>-mutants-<包>.md` | **完整**实测字段(池 / 变异数 / 杀死率 / 耗时 / 版本 / 真洞数) | 每轮 |
| 任务档案 `memory-bank/tasks/<…>-mutation-audit.md` | 追加一行轮次 | 每轮 |
| **常驻锚 §07 覆盖进度总表** `memory-bank/issues/<stamp>-test-mutation-audit-standing.html` | 该包一行的**汇总刻度 + 切片指针**(日期 / 变异数 / 杀死率 / 轮次 / 状态) | **每轮实施完成后必更** |
| 真洞各自的 issue `memory-bank/issues/` | 每条真洞(填 `doc-refs`) | 有真洞时 |

⚠ **别把切片数字抄进切片之外的正文** —— 回写守卫判据族 B 只允许测试通过数出现在切片里; 常驻锚那张表填的是
**变异数 / 杀死率**(不是 `N passed`), 只做汇总与指针。规程见 skill 的「覆盖进度总表(收尾必更)」节与硬约束 12。

## 环境事实(改脚本前先核)

| 项 | 值 | 备注 |
|---|---|---|
| WSL 发行版 | `Ubuntu-26.04` | `--distro` 可换; `wsl.exe -l -v` 看全 |
| 镜像仓 | `~/auto-qb-mut`(WSL 原生 ext4) | `--mirror` 可换; **别放 `/mnt/*`**(实测拷 116MB 要 52s); **多 clone 并行时各用一份**(如 `~/auto-qb-mut-hr`) |
| 核数 | 8(`.wslconfig` 限) | Windows 侧 32 逻辑核; `--max-children` 默认 4(有并行会话时降到 3) |
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
| `mutants.status` 恒报 `mutmut=no`(实际已装) | WSL 登录壳实为 zsh —— `cd` 改了**真实** cwd, 但 `$PWD` / `$()` 仍报 WSL 启动目录; `status` 的 `$(test -x .venv/bin/mutmut ...)` 因此读错目录 | **已修(2026-10-08)**: `cmd_status` 的回显改 `cd {mq} && <直接命令>` 形态(不再用 `$()` 取相对路径); 顺带把末行 `only_mutate` 加 fallback(镜像未跑过 run 时不再误报 `[FAIL]`)。若又见到本现象, 核脚本是否被改回 `$()` 写法。详见坑档 [memory-bank/pitfalls/testing/mutants-wsl-shell.md](../../../memory-bank/pitfalls/testing/mutants-wsl-shell.md) |
| 复跑时新加的守阵"没生效"(存活数不降) | `mutants.run` 默认 `git checkout -q -f -B develop FETCH_HEAD`, 会把镜像里**未提交的测试改动冲掉** | 先把新测试 `cp` 进镜像 `tests/`, 再 `mutants.run --no-refresh`(跳过刷新) |
| 想看某条变异的 diff / 想批量三分类 | `mutmut results` 只有 id, 没有 diff | 用 `mutants.report`(带 diff 的清单 + 按状态/按模块汇总); 单条用 `mutmut show <id>` |
| `verify` 跑得极慢 / 想中断 | 每条候选都要跑一遍**全套件**(实测 ~15s/条) | 先 `mutants.report` 再用 `--only-status` 或手挑把候选缩小; 中断后重跑同一 `--out` 自动续(已验 id 跳过) |
| 想用「本地新守阵」而不是 develop 的测试跑 verify | `verify` 默认刷新镜像(测试 = develop) | 加 `--no-refresh`(镜像里是什么测试就用什么) |
| 跑到一半崩在 `FileNotFoundError: mutants/.../<file>.meta` | **并行会话**共用同一镜像, 对方的 `mutants.run` 执行了 `rm -rf mutants`, 删掉你正在跑的 `.meta` | 每会话用**专用镜像** `--mirror '~/auto-qb-mut-<pkg>'`(`report` / `verify` 带同一个); 并存时降 `--children`(实测 4+4 会互相拖慢)。判别与处置见坑档 [mutants-shared-mirror](../../../memory-bank/pitfalls/testing/mutants-shared-mirror.md) |
| 大包单轮被 3600s timeout 截断 | `mutants.run` 的 `timeout = 3600`; 大包实测会超(hr: 8,027 变异 ≈96 min) | **别从零重跑**: 在镜像里 `cd <mirror> && .venv/bin/mutmut run --max-children 4` **续跑**(mutmut 对未变函数保留既有 `exit_code`, 跳过已有结果, 与整跑等价); 更稳的是按模块切 |
| `only_mutate` 不是你设的目标 / `mutants/` 下出现别的包 | 同一个镜像被**另一个会话**改过配置 | 同上: 用专用镜像; 排障时先 `grep -m1 only_mutate <mirror>/pyproject.toml` 核对 |

## 本会话验证到哪一步(诚实交代)

- **端到端跑通**: `mutants.run`(mutmut)与 `mutants.gremlins`(Windows)都真跑过并拿到汇总。
- **config 首轮(2026-10-08)把主线全链走了一遍**: `mutants.setup`(真跑 `git clone` 分支, 12s) ·
  `mutants.run`(4,799 变异 / 294.4s) · `mutants.report`(导出 827 条带 diff 的清单 + 汇总) ·
  `mutants.verify`(逐条 apply → 全套件 → 还原, 14s/条, 274 条) · 补测后 `mutants.run --no-refresh` 复跑。
  ⇒ `report` / `verify` 与 `setup` 的 clone 分支都**已实测**, 不再是"只验构造"。
- **仍未验**: `--out` 之外的落盘路径。(`mutants.status` 的 zsh `$()` 失真已在 2026-10-08 修复并实测复验, 见排障表。)
- 首次在新机器上真用 `mutants.setup` 若失败, 先核: Gitee 可达 / 镜像路径没写错 / WSL 发行版名对得上。
