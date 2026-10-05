# AGENTS.md 精简 (去 markdown 链接 / 去多余空格与符号)

> 摘要: 用户嫌 `AGENTS.md` 的 markdown 链接形式冗余 —— 路径已经是 agent 能直接读的有效信息,
> 链接语法只是装饰。全文 `[文字](路径)` → 反引号路径, 中英混排的多余空格收掉, `⚠️/✅/❗` 之类叠床架屋的
> 符号删到只剩有引用锚点价值的 `⚠` 与 `🔴`。**7,896 → 7,492 字符**(硬上限 8,000, 余量 508)。
> 最后活动: 2026-10-06 07:20

**Refs:** memory-bank/testing/baselines/26-10-06-0713-agents-md-slim.md, ../../AGENTS.md

## 现状

- 改动面: `AGENTS.md`(37 增 / 46 删) + `.github/copilot-instructions.md`(**改为指针**, 2,159 → 551 字符)。
  **工作树未提交**。
- 机检全绿: `doc.caps` 7,492/8,000 PASS · `doc.drift` 0 处手抄 · `test.one tests/test_memory_bank.py`
  32 passed · `test.full` **2676 + 4 / 99%**(基线 `26-10-06-0713`)。

- 原来它是 AGENTS.md 的手抄副本且已漂移 (`git merge --ff-only` 手同步流程 / `testing.md` 基线口径),
  **两处各自演化正是漂移本身** ⇒ 一股脑删掉, 只留"内容以 ../AGENTS.md 为准"。
- ⚠ **删不干净**: `test_session_protocol_is_exposed_in_always_on_entries` 把本文件写进了被查列表,
  强制含字面串「立档阈值」与 `.agents/skills/memory-bank/SKILL.md` —— **纯指针版实测 1 failed**
  (`AssertionError: copilot-instructions.md 未声明立档阈值`)。
  ⇒ 折为"指针 + 一行机检 token", 并在文件里写明为什么这行不能删、要真删得**先改那条用例**。
  (这也解释了旧副本为什么不敢删 —— 守卫在替它兜底。)

## 关键决策

- **留两个符号**: `⚠`(字符上限行 / TMPDIR 行 / git 硬约束标题)与 `🔴`(跨仓库红线标题) —— 后者被正文
  「见「🔴 跨仓库操作」节」当锚点引用, 删了那句要跟着改写。✅ 与 ❗ 纯装饰, 删。
- **命令节的字面命令串一字未动** —— `check_command_drift.py` 扫 AGENTS.md, 改写法会被判成第 N 处副本。
- **守卫要求的字面串保住**: `.agents/skills/memory-bank/SKILL.md` 与「立档阈值」仍在文件里
  (`test_session_protocol_is_exposed_in_always_on_entries` 会查这两个 token)。
- **判据一条没删**: 每条硬约束的判据与由来 (为什么有这条) 原样保留, 只压行文 —— 精简的是形式, 不是信息。

## 未闭环 / 下次注意

- ✅ **已闭环 (07:2x, 用户拍板改指针)**: `.github/copilot-instructions.md` 原是 AGENTS.md 的手抄副本且
  已漂移 —— 仍在写旧的手动 `git merge --ff-only` 流程 (现口径是 `commands run my-commit-flow.sync`) 与旧的
  `testing.md` 基线口径 (现体例是 `baselines/` 切片)。现改为纯指针 + 一行机检 token, 见上文追加段。
- ⚠ 同源文件 `.github/instructions/ai-lib.md` / `.github/agents/` 疑似同一套副本, 本轮**没有核过**,
  要不要一并收敛待用户发话。

### 07:3x 追加: 那条守卫一并移除 (用户授权)

- 用户拍板「守卫一并移除」 ⇒ 改了 `tests/test_memory_bank.py::test_session_protocol_is_exposed_in_always_on_entries`:
  被查列表从 `(AGENTS.md, copilot-instructions.md)` 收成**只查 AGENTS.md**, 并把"为什么不再查"写进用例注释
  + 头部「测试计划」清单同步改口径。**属改机检, 只在用户显式授权后做**。
- 随之把 copilot-instructions.md 里那行机检 token 删掉 ⇒ 现在是**真正的纯指针**(551 → 322 字符)。
- **为什么这条守卫原本害周围**: 它逼得每个"入口"都得重复声明阈值与 skill 路径, 于是 AGENTS.md 的手抄副本
  一旦想改成不重复的指针就判红 —— 守卫在**替过期副本兜底**。副本收敛的阻力一半来自这里。
- **没新建基线切片** —— `test.full` 改后仍是 **2676 + 4 / 99%**(与上一条 `26-10-06-0713` 逐项同;
  用例**只改断言范围没增删**, 数字不变是对的)。同数字快照无信息量, 记在这里而不单开一条。
- cap 债务 1 项: `memory-bank/issues/_index.md` 25,598 > 25,200 字符 —— 与本轮无关 (未改动该文件),
  `doc.caps` 要求**提醒用户另开新会话清理**。
- `test.full` 与上一条基线有未覆盖 -3 / partial -1 的差, 归因与留给后人的判据写进基线切片 `26-10-06-0713`。
