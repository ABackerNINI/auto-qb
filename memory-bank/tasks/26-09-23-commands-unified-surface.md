# 26-09-23-commands-unified-surface — 项目命令统一调用面 (纯引擎 + 包式配置层)

**Status:** Open
**Added:** 2026-09-23
**Updated:** 2026-09-24
**Summary:** 同一条命令在仓库里有 8 处副本 / 5 种写法, 唯一生效的那条恰好"看起来最不正常" (POSIX `TMPDIR=x cmd` 前缀在本工具 shell 实测 rc=1), 而"该抄哪一份"没有任何提示 ⇒ 直到某次拿到假红才暴露。方案: skill 缩成**纯引擎**(只认识「包」与「命令」, 连"提交"都不知道), 命令单点定义在 `<仓库根>/.commands/<包>/config.toml`, 包是**黑盒**(私有配置引擎不读), 路由**不落盘**改为逐级查询 + `pin` 常显, 并配一条反漂移闸门让文档里的手抄形态直接判红。**W1–W5 已全部实施并提交**; 2026-09-24 优化轮补齐三处遗留 (SKILL.md 两种记法 + 恒定大小硬上限 / `pin` 数量守卫 / 格式化闸门去双写)。
**Topics:** commands-unified-surface

## 原始请求

> 实施项目中的新加的 commands-plan, 所有 waves, 然后提交

(计划: [../plans/26-09-23-2008-commands-plan.html](../plans/26-09-23-2008-commands-plan.html) v1.7, 同一轮产出)

## 思考过程与决策

### 问题的形态不是"没有规范", 而是"同一事实多份副本"

现场证据(以一条测试命令为例, 只读勘察 @ 19fa6ee): 8 处副本 / 5 种写法 ——
`uv run pytest tests -q`(AGENTS.md / README.md / memory-bank SKILL.md / copilot-instructions.md / ci.yml)、
`TMPDIR="R:/Temp/..." uv run pytest`(testing/run.md, **POSIX 前缀, 实测 rc=1**)、
`set "TMPDIR=..." && uv run pytest --no-cov`(原 `.commit-flow.toml`, **唯一生效**)、
`TMP=H:/… TEMP=H:/…`(pitfalls)、`TMPDIR=D:/tmp_pytest`(工作区记忆)。
⇒ 危害不在"抄错", 在于**没有任何信号**: 用了不生效的写法也无人发现, 直到某次拿到假红。

`pitfalls/testing/tmpdir.md` 该条已 `复发 +1`, 记录的未命中原因是"只给自己手工跑的带了 TMPDIR,
没意识到闸门是配置里的另一条执行路径" —— 处置结论是「**改配置比改记忆可靠**」。本方案把这条结论
从一个闸门推广到全部命令。

### 边界怎么划: 一句话判据

> 引擎认识的键, 必须对**任何仓库、任何命令**都成立。只要某个键的含义依赖"我们在做什么事",
> 它就**属于包, 不属于引擎**。

于是: 引擎 schema 只剩 `[pack]` / `[packs.*]` / `[tasks.*]`, 占位符只剩 `<root>` / `<skill-dir:NAME>` / `<args>`;
闸门 / 红线 / 远端寻址 / 开工同步全部留在 `my-commit-flow` 包私有配置里, 由包脚本自读。

**被纠正过两次的反面**(都在计划里留了痕): v1.0 把 ship 实现迁进 skill 的 `scripts/`(= 领域逻辑进引擎);
v1.4 把闸门与红线写进包的 `config.toml`(= 领域配置进 command-flow 的配置面)。两处都要守住:
**引擎不认领域, 配置面也不承载领域**。

### 三条设计初衷落成什么机制

| 初衷 | 机制 |
|---|---|
| 减少出错 | 命令单点定义 + `requires` 前置检查 + 反漂移闸门 |
| 隐藏复杂细节 | 环境前缀 / 远端名 / 顺序约束沉到包里; `run` 默认不 dump 命令 |
| 降低 token | 包式配置 + 逐级路由(一级只出"包 + 常显")+ 信息预算 |

**详略随风险自适应**: 带 `requires` 或 `risky = true` 的 task, `run` 先打印将要执行的命令再执行 ——
"自证"的成本只花在真正需要它的地方(`ship.commit` 这类), 高频低风险的 `test.full` / `kb.index` 不付这份钱。

## 实现计划

### W1 引擎骨架 + 六个顶级包

`.agents/skills/commands/` —— `SKILL.md`(恒定大小: 四个子命令 + 引导 + 收录协议, 不含路由表本体、
不含任何可直接执行的命令)+ `scripts/{_config.py, _tree.py, run.py}`。
**没有 `_gates.py`** —— 闸门归 my-commit-flow 包。

扫描规则: 顶级包自动扫 `.commands/*/config.toml`; 子包由上级 `[packs.<名>]` 注册(路径 `<父>/<名>/config.toml`)。
六个顶级包: `test` / `kb` / `dev` / `env` / `doc` / `my-commit-flow`(后两者含 `ship/` 子包)。
**没有 core 包** —— 一个包一个职责, 拆开之后没有任何东西还需要一个"约定名的杂项包"。

### W2 补齐 + 可插拔验证

- 临时加包 → 跑通 → **整包删掉**: 删除后引擎照常 `list` / `run`, 不留悬挂引用 ✅
- 包的黑盒性: 往包里塞一份引擎不认识的私有配置, 引擎照常工作、不报错、读不到 ✅

### W3 my-commit-flow 成包, 退役 `.commit-flow.toml`

`git mv` 保历史: 配置 → `.commands/my-commit-flow/.my-commit-flow.toml`(**内容一行未改**),
四个脚本 + `_ship_config.py` → 包内 `scripts/`, 旧 SKILL.md → 包内 `README.md`。
`_ship_config.py` 改为在**包目录**找配置(引擎注入 `COMMAND_FLOW_PACK_DIR`, 手工跑时退回脚本目录的上一级)。

顺带修掉两条既有冲突:

1. 旧 SKILL.md 教「提交 → `git pull --rebase` → 推送」, 与 `AGENTS.md` 的 rebase 禁令**直接相撞** ——
   改成「先提交 → `merge --ff-only` 快进 → 推送」, 并补上分叉时的替代路径(移出改动 → reset → ff-only → 施回)。
2. `preflight.py` 的改动清单把重命名的 porcelain 行 `R  old -> new` 整条当路径 ⇒
   `<changed:>` / `<each:>` **静默匹配不到**新路径(迁移后 `.commands/**` 冒烟闸门因此空跑)。已取新路径。

另: 全量测试闸门改成 `python <skill-dir:commands>/scripts/run.py run test.quick` ——
不在这里抄命令, 否则包里的单点定义会被第 N+1 处副本架空。

### W4 反漂移闸门 + 文档收口(成败点)

新增 `scripts/check_command_drift.py`: 扫 `AGENTS.md` / `README.md` / `memory-bank/**` / `.github/**` /
`.agents/skills/**/SKILL.md`, 凡匹配到既有 task 的**命令骨架**(忽略引号 / 空格 / 路径差异 / 环境前缀)
且没写成 `commands run <task>`, 直接判红。挂进闸门 `match = [""]`(每次提交都跑 —— 手抄可能出现在任何文档)。

- 首跑 **63 处**; 收口后 **0 处**。
- 生成物(`memory-bank/**/_index.md`)改的是**生成器**: `_common.gen_cmd()` 现在输出 `commands run kb.index`,
  重建索引后 17 个 `_index.md` 一起更新 —— 改生成物比改生成结果可靠。
- 两条**逐文件豁免**(都写了理由): `pitfalls/testing/tmpdir.md`(哪几种写法不生效**就是判据**, 换成 task id 这条陷阱没法读)、
  `pitfalls/testing/patching.md`(WSL 是另一条执行路径, 命令被 `wsl -- bash -c` 包裹且带 `-p 3.12` 变体)。
- 收录协议接到两个决策点上: `AGENTS.md`「命令」节 + `memory-bank` SKILL.md 的收尾 DoD 第 5 步。

### W5 旧 skill 退场 + 引擎纯净度

删除 `.agents/skills/my-commit-flow/` 与 `.codebuddy/skills/my-commit-flow` 悬挂链接(后者 gitignore)。
引擎目录 grep 项目词(`提交` / `测试` / `知识库` / `gate` / `red_line` / `commit` / `ship` / `gitee` / `TMPDIR`)
**实测 0**(清掉了两处注释里当示例写的 `my-commit-flow/ship` 路径)。
整包移走 `my-commit-flow/` 后引擎仍能 `list` / `run` 其它 task ✅

## 验收对照

| # | 判据 | 结果 |
|---|---|---|
| A1 | SKILL.md 不含可直接执行的命令, 也不含路由表本体 | ✅ 只有四个子命令 + 引导 + 收录协议 |
| A2 | 同一命令只有一处定义 | ✅ 漂移闸门 0 处 |
| A3 | `show` 打印展开后的真实命令 | ✅ 与配置逐字一致 |
| A4 | 包写错一律 STOP rc=1 | ✅ 六类判据逐一实测 |
| A5 | 手抄判红 / task id 转绿 | ✅ 63 → 0 |
| A6 | `my-commit-flow.*` 等价于原 skill | ✅ 配置原样搬入, 预检全绿 |
| A7 | `.commit-flow.toml` 已删, 无悬挂引用 | ✅ |
| A9 | token 预算: SKILL.md 恒定; 常规 `run` 不 dump 命令 | ✅ 仅 `requires` / `risky` 自证 |
| A10 | `add` 默认 dry-run; `--when` 空 / `--pack` 不存在 / `--id` 已存在均拒绝 | ✅ |
| A13 | 引擎零领域逻辑 | ✅ grep 为空 |
| A14 | 逐级路由: `list` 只出当前层级, `pin` 浮一级 | ✅ |
| A15 | 配置层只有包一种形态; 包名与目录名不一致 / task id 重复 → STOP | ✅ |
| A16 | 引擎 schema 只有三块, 无领域词 | ✅ |
| A11 | 真实会话里 agent **自发**调 `add` | ⏳ 待观察(G7 的唯一有效判据) |

## 子任务状态表

| 波次 | 内容 | 状态 |
|---|---|---|
| W1 | 引擎三件 (`_config.py` / `_tree.py` / `run.py`) + 五个顶级包 + SKILL.md 首版 | Done |
| W2 | 补齐 kb / dev / env / doc; 临时包加删验证可插拔与黑盒性 | Done |
| W3 | `my-commit-flow` 成包, 退役 `.commit-flow.toml`, 修 rebase 冲突与 porcelain 重命名解析 | Done |
| W4 | 反漂移闸门 + 文档收口 (63 → 0); 收录协议接到两个决策点 | Done |
| W5 | 旧 skill 退场 + 引擎纯净度机检 (grep 为 0) | Done |
| 优化轮 | SKILL.md 两种记法 + description 175 字符; `pin` 数量守卫; 格式化闸门去双写; SKILL.md 恒定大小硬上限 | Done |

## 进度日志

- 2026-09-23 22:19: 开工 ff-only 快进到 `68bcbde`(本地原 `19fa6ee`, 落后 4 个提交); W1–W5 一次做完。
  实测: 引擎 STOP 判据六类逐一验证通过; 漂移闸门 63 → 0; 全量 **1189 passed + 1 skipped**(修复两处
  守卫红后); 引擎纯净度 grep 为 0。
- 踩到的守卫红(都是**改动的连带影响**, 不是回归): ① 新档案缺 `## 实现计划` / `## 子任务状态表` /
  `## 进度日志` 三个必备章节; ② `memory-bank.instructions.md` 里的 `gen_active_recent.py` 字面量被
  task id 替换后, 守卫 `test_memory_bank_instructions_match_current_structure` 找不到该 token ——
  已改成"+ 脚本名"并列写法(token 在, 但不成可执行的命令骨架, 漂移闸门仍绿)。
- 2026-09-24 01:58: 优化轮(依据计划 HTML 逐条对照, 只动 skill 与配置层)。四处改动:
  ① `SKILL.md` 新增「两种记法」段(文档记法 `commands run <task>` vs 真实入口
  `python <skill-dir:commands>/scripts/run.py <子命令>`)—— 这是档案「遗留」里那条"记法不是可粘贴命令"的收口;
  description 226 → **175 字符**(skill-creator 要求 <200)。
  ② 引擎补 `MAX_PIN_PER_LEVEL = 8` 守卫(`_config._pin_warnings`): 一层视图浮出的常显命令超限即 WARN ——
  计划 W4 说"改为检查包树完整性: 子包目录存在 / task id 全树唯一 / **pin 数量在阈值内**", 前两条引擎早已
  STOP, 只有这条从没落地。
  ③ `.my-commit-flow.toml` 格式化闸门从 `yapf -i <changed:*.py>` 改为
  `run.py run dev.fmt -- <changed:*.py>` —— 原来 `yapf -i` 在 `dev.fmt` 与闸门各有一份(第 N+1 处副本);
  改动清单仍由预检算(它是"本次改了哪些文件"的权威), 经 `<args>` 传给 task。
  ④ `check_context_caps.py` 的 `CONTEXT_CAPS` 加 `.agents/skills/commands/SKILL.md: 4200`, 闸门 `match` 同步
  加上 `.agents/skills/commands/` —— 落实 A9 的"SKILL.md 有硬上限", 此前只有设计意图没有机检。
  顺手: `run.py cmd_add` 去掉了重复的 `load_tree()`(改用 `_tree.resolve` 统一查包)。
  实测: 全量 **1201 passed + 1 skipped**(与 [testing/baseline.md](../testing/baseline.md) 基线一致, 无回归);
  漂移闸门 0 处; `doc.caps` 报 `SKILL.md 2986/4200`; 引擎纯净度 grep 仍为空; 预检 5 条自动闸门全过;
  `test_preflight.py` 34 项全过。
- 踩到的坑(新记一条, 已写进 [pitfalls/testing/tmpdir.md](../pitfalls/testing/tmpdir.md)): 在工具**沙箱内**跑
  `test.full` 假红 —— 沙箱拒写 `R:\Temp` ⇒ task 自带的 `TMPDIR` 等于没设 ⇒ pytest 回落 `H:\Temp` ⇒
  收尾 `cleanup_dead_symlinks` 抛 `PermissionError`, **用例其实全过**。关沙箱即绿, 命令本身不用改。
- 踩到的守卫红(1 条, 已修): 往 `tmpdir.md` 补新坑后该文件 `6,060 > 6,000`(角色 pitfall)⇒
  `test_kb_files_respect_cap` 红。**为什么没命中**: `pitfalls/kb/cap-counting.md` 已记了 cap 相关判据,
  但记的是"怎么数"(CRLF 口径)与"撞了怎么轮转", **没有"追加前先看余量"这一步** ——
  已在该文件补一条同名小节; 处置是把新写的那段压到 ~700 字符(不动别人的判据), 压完复绿。
- 2026-09-24 02:0x: 用户点头把 **W3 遗留的文档漂移**并入本轮修完 —— `AGENTS.md` 3 处死链
  (指向已删除的 skill 与已搬走的 `.commit-flow.toml`)改指 `.commands/my-commit-flow/README.md` /
  `.my-commit-flow.toml`; `pitfalls/ops/_about.md`(连带生成索引)/ `pitfalls/ops/prod-files.md` /
  `pitfalls/git/push.md` / `pitfalls/testing/tmpdir.md` / `conventions/collaboration.md` /
  `conventions/process.md` 的旧名一并订正(顺带修 `process.md` 的"23 用例"→ 34)。
  `tmpdir.md` 已贴 cap, 为腾地方把本轮新写的那节又压了一遍。冻结快照(`plans/*.html`)、
  档案纪要(`tasks/*.md`)、叙述性文档(`progress/suggestions.md`)与别的专题的切片**刻意没动**。
  实测: `doc.caps` 报 `AGENTS.md 6999/8000`; 漂移 0 处; 全量 **1201 passed + 1 skipped**。
- 2026-09-24 02:28: 用户反馈 skill 的 description"不清"、要突出"命令" ⇒ 重写 `commands` 的 description
  (**175 → 307 字符**, 对齐同族 skill 的 220–315 区间): 首句改成"要跑测试 / 格式化 / 同步 / 提交 / 建索引
  这类项目命令, 都先来这里找 —— 别自己拼、别去文档里抄"; USE FOR 里写进两件行为 —— ①**先 list 查重**
  (想跑的 / 想加的多半已收录) ②带用户原话触发("跑一下测试"/"同步一下"/"提交"/"建索引"); DO NOT USE FOR 保留。
  **教训: 上一版为压到 200 字符(套 skill-creator 的通用建议)丢掉了触发语, 反而更不清** —— 本项目同族
  skill 本就在 220–315, 该跟的是同族写法。另: 查命令全树(`list --all`)时发现**常显命令被打印两遍**
  —— 用户点头后**同轮修掉**: `_tree._level` 在 `show_all` 时不再把子包的 pin 往上浮(全树本就铺开,
  每包由自己那层列, `★` 仍标 pin); 复验 `--all` 由 25 行(21 条 + 4 条重复)回到 **21 行零重复**,
  且 `list` / `list <包>` / `list <包>/<子包>` / `list <包> --all` 四个视图逐一核过, 无重复无缺失。
- 2026-09-24 02:35: 用户纠正描述 —— **"该 skill 与 scope-guard skill 并没有关系, 不应该提"**。
  已删掉 DO NOT USE FOR 里那句"(见 scope-guard skill)"(全文再无 scope-guard 引用, 正文本来也没有),
  并把随之悬空的"判断该不该做"补成自洽说法: "**只管"怎么跑", 不管"该不该跑"**"。终稿 **310 字符**
  (仍在同族 220–315 区间)。口径已写进 activeContext 切片: **描述里不写与别的 skill 的交叉引用**。
- 2026-09-24 02:50: 用户要求**省 token**: 去不必要的空格 + 把收录协议细节外置。三处改动 ——
  ① 新建 `.agents/skills/commands/references/howto-add-command.md`(**1293 字符, 按需读**): 三条判据的判法、
  命令的归宿表、`add` 的必填项与理由、防滥用, 全搬过去; SKILL.md 只留摘要 + 一行指针。
  ② SKILL.md **2986 → 2068 字符(降 30.7%)**: 除搬走的细节外, 还删了与别节重复的内容(反模式两条、
  引擎设计原理压成一句、表格去掉重复的"什么时候用"列), 并去掉半角逗号/斜杠/括号后的空格(**327 → 171 个**);
  description 310 → 262。③ `CONTEXT_CAPS` 的 commands/SKILL.md **4200 → 2600**(实测 ~2140 含 CRLF, 留 ~20% 余量)
  —— **上限跟着实测收, 才叫"恒定大小"**, 否则收完的成果会被慢慢吃回去。
  另: 反漂移闸门扫描面从 `.agents/skills/**/SKILL.md` 扩到 `.agents/skills/**/*.md` —— 细节搬进 `references/`
  后只扫 SKILL.md 会给搬出去的内容留盲区; 扩前实测 **0 命中**(不误伤别的 skill)。
  实测: `doc.caps` SKILL.md **2068/2600** · AGENTS.md 6999/8000; 漂移 0 处; `kb.check` 全绿;
  全量 **1201 passed + 1 skipped**。
- 2026-09-24 03:05: 用户"修复 run doc.drift" —— 根因不是那条 task, 而是引擎**静默丢掉**调用方传的参数。
  两处修: ① `_config.task_commands` 加判据 —— 传了参数而 `run` 里没有 `<args>` 占位符 → **STOP(rc=1)**
  并提示"要么去掉参数, 要么在包里补 `<args>`"(`_takes_args`; **脚本类例外**: 额外参数直接接 argv 末尾);
  ② `.commands/doc/config.toml` 的 `doc.drift` 补上 `<args>`(可传 `--list` 看正在盯的命令骨架)。
  SKILL.md 的 STOP 清单同步补一条"参数给了不接参数的 task"(2089/2600)。
  实测: `run doc.drift -- --list` 转发成功; `run doc.caps -- --strict` STOP rc=1 **且不执行**;
  脚本类 `ship.commit -- --message-file … <路径>` 仍接 argv; 无参数路径不变; 全量 **1201 passed + 1 skipped**。

## 遗留 / 下一步

- **A11 未判**: 需要一次真实会话里 agent 自发收录才算数。
- **记法问题**: 已在 SKILL.md 写成「两种记法」段(2026-09-24); 仍然**不做**跨平台 shim ——
  `commands` 只是给人看的短记法, 真敲时展开成 `python <skill-dir:commands>/scripts/run.py <子命令>`。
- ~~**闸门仍有一处双写**: 格式化闸门 `yapf -i <changed:*.py>` 尚未收进 `dev.fmt`~~ ——
  2026-09-24 已收口: 闸门改成 `run.py run dev.fmt -- <changed:*.py>`, 改动清单仍由预检算, `yapf` 只剩一处定义。
  (`.my-commit-flow.toml` 的 `run.py run test.quick` 本来就是**引用**不是副本, 保持。)
- **W3 遗留的文档漂移**: 2026-09-24 用户点头**并入本轮修完** —— `AGENTS.md` 3 处死链改指
  `.commands/my-commit-flow/README.md` / `.my-commit-flow.toml`; 6 份 pitfalls/conventions 文档的旧名订正。
  刻意没动 `plans/*.html` 与 `tasks/*.md`(冻结快照 / 纪要)、`progress/suggestions.md`(叙述)、
  别的专题的 activeContext 切片(按「各 clone 只写自己的切片」约定)。
  ⚠ 顺带记一条**机检缺口**(仍未修, 属计划外): `check_doc_links.py` 默认只扫 `memory-bank/` 与 `.github/`
  (根级 md 要 `--all` 才扫), 所以 `AGENTS.md` 这类引导文件的死链一直**没有守卫** ——
  这次那 3 处死链就是它漏掉的。
