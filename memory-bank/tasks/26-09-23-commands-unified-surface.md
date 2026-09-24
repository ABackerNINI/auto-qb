# 26-09-23-commands-unified-surface — 项目命令统一调用面 (纯引擎 + 包式配置层)

**Status:** Open
**Added:** 2026-09-23
**Updated:** 2026-09-24
**Summary:** 同一条命令在仓库里有 8 处副本 / 5 种写法, 唯一生效的那条恰好"看起来最不正常" (POSIX `TMPDIR=x cmd` 前缀在本工具 shell 实测 rc=1), 而"该抄哪一份"没有任何提示 ⇒ 直到某次拿到假红才暴露。方案: skill 缩成**纯引擎**(只认识「包」与「命令」, 连"提交"都不知道), 命令单点定义在 `<仓库根>/.commands/<包>/config.toml`, 包是**黑盒**(私有配置引擎不读), 路由**不落盘**改为逐级查询 + `pin` 常显, 并配一条反漂移闸门让文档里的手抄形态直接判红。**W1–W5 已全部实施并提交**; 2026-09-24 优化轮补齐三处遗留 (SKILL.md 两种记法 + 恒定大小硬上限 / `pin` 数量守卫 / 格式化闸门去双写)。**W6 会话噪音治理**(2026-09-24, 用户走查一次真实提交流程后提出"噪音多、token 高"): 引擎输出摘要改为**异常感知**(只取末几行会让 WARN 的内容消失, 实测逼出一次预检重跑)、task id 认包路径限定写法、闸门 PASS 行从 ≈1.5 KB 命令全文收成一行、开工自检给出**可执行的同步配方**(含重叠判定)、包/引擎的 47 条脚本测试首次挂上闸门。**W7 wrapper 入口**(2026-09-24, 用户要求「真正实现 `commands run <task.id>`」): 实测三个 shell 都不搜 cwd ⇒ 生成器落 **cwd + PATH 目录**两处(生成物 gitignore, 只认自己的标记行), 并把「低噪音包」的八条判据写进收录协议。
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
| W6 | 会话噪音治理: 引擎异常感知摘要 + id 包路径写法 + 闸门摘要收敛 + 开工自检同步配方 + 包测试入闸门 | Done |
| W7 | wrapper 入口(真正实现 `commands run <task>`) + 低噪音包判据 + 收录协议同步 | Done |

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

- 2026-09-24 18:1x: **W6 会话噪音治理**(起因: 用户走查上一轮的提交流程, 指出"噪音多、没达到设计初衷")。
  先按"我在那次会话里到底多花了什么"逐条取证, 再逐条改:
  ① **摘要只取末 3 行**(`run.py` 的 `_tail`)= 最大一笔 —— 预检的末 3 行是"决策点指针 / 无 STOP;2 项 WARN",
  **WARN 的内容在中段被截掉**, 于是我把预检**跑了两遍**(21s×2)才看到那两条 WARN。改为 `_digest`:
  末 3 行 + 异常行(`[WARN]`/`[STOP]`/`[FAIL]` + 大写 `FAILED`/`ERROR`/`Traceback`, 封顶 8 行, 去重、保序),
  有省略时打印"略过 N 行 + `show` 怎么看全文"; 失败路径也封顶 40 行(原先整段 dump)。
  ② **task id 只认短 id**: `show my-commit-flow.ship.commit` 直接 STOP(真实 id 是 `ship.commit`), 而
  `AGENTS.md` 里三种写法混着写 ⇒ `_pick` 改为**两种都认**(`包/子包.<task>` 取最后一个 `/` 之后),
  STOP 提示补上可解析的写法。③ **闸门 PASS 行 ≈1.5 KB**: 把 9~11 条展开后的命令(含绝对路径)拼成一行,
  每次提交都出现却只是"过"的噪音 ⇒ 只回"11 条全过 (共 24.9s)", 明细走新加的 `--verbose`。
  ④ **开工自检只说"先同步, 树脏先停下报告"** —— 这句话不含动作, 我实测要 6 次只读 git 调用才拼出下一步 ⇒
  新增纯函数 `sync_recipe`, 打印 5 步配方(`--output=` / `restore` / `--ff-only` / `apply --3way` / `reset -q`),
  并**先判与在途改动有没有文件重叠**: 重叠就**不给配方**、只报"先停下报告"(与全库"不静默降级"同源)。
  ⑤ **入口不可解析**: 文档只写记法 `commands run <task>`, 我第一条命令就撞 `commands: command not found` ⇒
  `AGENTS.md` 命令节补**真实入口**(`uv run python .agents/skills/commands/scripts/run.py run <task>`),
  SKILL.md 的路径约定补"用项目自己的解释器跑它"。⑥ `commit.py` 结尾提示改成 `commands run ship.push`
  (原先是裸脚本路径, 绕开统一调用面); ⑦ **包/引擎的测试没人跑**: `test_preflight.py` 47 条在
  `testpaths(tests/)` 之外, 任何闸门都不跑它 ⇒ 补 task `test.pkg` + 闸门
  `match = [".commands/", ".agents/skills/commands/"]`。
  顺带**修掉两处会致败的旧文案**(都在提交流程的必经路径上, 属本轮范围):
  `references/pipeline.md` 与包 README 停手点 #1 都写"**先提交再快进**" —— 提交后再 `merge --ff-only`
  **必然失败**(本地提交不在远端 tip 的祖先链上), 已按 `AGENTS.md` 与
  [pitfalls/git/history-integration.md](../pitfalls/git/history-integration.md)「先同步远端, 后提交」订正;
  `commit.py` docstring 里"让工作区变干净再 **rebase**"与 rebase 禁令相撞(该条在 skill 退役时被漏搬)——
  已改"快进", 并在 history-integration.md 的通用教训条记 `复发 +1`。
  实测: `test.full` **1215 passed + 1 skipped**(+8 条引擎守阵; TOTAL 91% / 7768 语句 / 623 未覆盖);
  `test.pkg` **47 passed**(原 34 → +13: `sync_recipe` 判定矩阵 5 条 + `summarize_gates` / `_short` 3 条 +
  `_digest` / `_pick` 5 条另在 `tests/test_commands_engine.py`); 红验: 8 条引擎守阵在还原版上全红。
  端到端: 假远端(`commit-tree` + 临时 remote)造「落后 1 + 树脏 5」—— 无重叠出配方, 有重叠改"先停下报告"。
  文档闸门: `doc.caps` SKILL.md **2526/2600** · AGENTS.md 7499/8000 · 包 README 2831/3000; 漂移 0 处。

- 2026-09-24 18:5x: **W7 wrapper 入口 + 低噪音包**(用户要求: "引导 agent 创建平台相关的命令 wrap 到当前工作目录,
  真正实现 `commands run <task.id>`, 同时更新 howto-add-command, 引导 agent 创建低噪音的命令包")。
  **先实测再设计** —— 三个 shell 对 cwd 的搜索规则不同, 这一步决定了落点:

  | shell | cwd 里有 `commands` 时 bare 调用 | 原因 |
  |---|---|---|
  | Git Bash | ❌ command not found | PATH 不含 `.` |
  | PowerShell | ❌ CommandNotFoundException | PowerShell 不搜 cwd |
  | cmd.exe | ✅ | 唯一搜 cwd 的 |

  ⇒ "只落当前工作目录"**达不到目标**, 于是与用户确认后落 **cwd + PATH 目录**两处:
  新增 `install_wrapper.py`(生成器, 幂等): ①仓库根 → `commands`(POSIX)/`commands.cmd`(Windows);
  ②PATH 目录(`~/bin` 优先, **在 PATH 上但不存在就建出来**) → **项目无关**那份, 从 `$PWD` 向上找 `.commands/`,
  任意项目 bare 调用。生成物**不入库**(`.gitignore` `/commands` `/commands.cmd`)——单点定义在生成器里;
  只认自己的标记行(别人的同名文件停手, `--force` 才覆盖); `--cwd-only` / `--uninstall` / `--dry-run`;
  装完**自证**(真跑一次 `list` 并打印 rc)。解释器优先 `uv run python`: 包脚本是以**引擎的 `sys.executable`**
  执行的, 这决定了包里 `script =` 任务跑在系统 python 还是项目 venv。
  **实现期撞到的坑(全部实测, 已写进 [pitfalls/backend/platform-fs.md](../pitfalls/backend/platform-fs.md))**:
  ①批处理 `rem` 行含**引号/括号/反引号** → 整份**静默退出 2 且无任何输出**(换成干净 rem 立刻正常);
  ②`.cmd` 行尾必须 **CRLF**; ③消息必须 **ASCII**(cmd 按 OEM 码页读); ④Windows 下 CreateProcess 不认 shebang
  ⇒ 只能经 shell 跑 `WinError 193`; ⑤Git Bash 的 PATH 条目是 **MSYS 形态**(`/c/...`), 与 `Path.home()` 直接比
  **永远不相等**(实测把"已在 PATH 上"误判成"不在", 静默跳过 PATH 落点); ⑥`os.access(W_OK)` 在 Windows 目录上
  给假否定 → 改**真实写探测**。
  **低噪音包**: 用户要求的第三条落成 `howto-add-command.md` 新增一节(**八条判据** —— 输出自带静音 /
  异常行可被机器认出 / 一条 = 一个动作 / `when` 一句话 / `note` 只写陷阱判据 / 长文进 `doc` / `timeout` 按最坏情况 /
  `pin` 稀缺 + 收完自检三句), 并在 SKILL.md 的收录协议行里点出。**wrapper 与收录无关**(它只转发)也写明了。
  文档: SKILL.md 新增「入口: 首次先装 wrapper」并把细节外置到新的 `references/wrapper.md`(1.8 KB, 按需读);
  `AGENTS.md` 命令节的"真实入口"改成"先装 wrapper, 装完 `commands run <task>` 直接可用"。
  实测: `test.full` **1224 passed + 1 skipped**(+9 条 wrapper 守阵; TOTAL 91% / 7768 语句 / 623 未覆盖);
  端到端三形态通过(`./commands run <task>` / bare `commands list` / 从子目录向上找根), 不在项目里 rc=2 + 提示,
  `--uninstall` 后重装幂等; `doc.caps` SKILL.md **2515/2600** · AGENTS.md 7616/8000; 漂移 0 处; sidefx 越界 0(台账 2051 条)
  (新增放行面收窄到"临时目录里的 `commands` / `commands.cmd`", 理由是那条端到端用例必须真跑脚本)。

## 遗留 / 下一步

- **A11 未判**: 需要一次真实会话里 agent 自发收录才算数。
- **W7 未验项**: `.cmd` 已由生成器自证 + 端到端用例覆盖, 但**没在真终端里手敲过**
  (本会话的 PowerShell 工具中途静默, 只剩生成器自证这条路); 换机器/换用户时重跑一次安装即自证。
- **`run` 摘要的信息预算还有一处可收**(未做): 失败路径现在封顶 40 行, 但若某条 task 的失败输出里
  异常行特别多, 摘要仍可能到 48 行 —— 目前没遇到, 先记着。
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
