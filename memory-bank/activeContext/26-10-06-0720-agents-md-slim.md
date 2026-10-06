# AGENTS.md 精简 + Copilot 入口收敛为指针

> 摘要: 两件事 —— ①`AGENTS.md` 去掉 markdown 链接 (`[文字](路径)` → 反引号路径)、中英混排多余空格与装饰
> 符号 `⚠️/✅/❗`, **7,896 → 7,492 字符**(硬上限 8,000), 判据一条没删, 只压行文; ②`.github/copilot-instructions.md`
> 由 AGENTS.md 的手抄副本 (已漂移) 收敛为**纯指针**, **2,159 → 83 字符**, 并移除那条替副本兜底的机检断言。
> **已提交并推送 `376dda34`**(`ship.push` 内含 `ls-remote` 核验远端 ref == 本地)。③ 空格精简
> **7,492 → 6,705 字符**(空格 950 → 163), 见文末「空格精简」节 —— **已提交并推送 `cba7c4f6`**。
> ④ 去日期标注 + 删首行工具名单 + 收 dark 口径同义反说 **6,705 → 6,527 字符**, 见文末同名节 —— 未提交。
> 最后活动: 2026-10-06 08:4x

**Refs:** memory-bank/testing/baselines/26-10-06-0713-agents-md-slim.md, ../../AGENTS.md

## 改动面

- `AGENTS.md`(37 增 / 46 删): 链接改反引号路径; 符号只留有锚点价值的 `⚠` 与 `🔴`。
- `.github/copilot-instructions.md`: 只留标题 + 一行指向 ../AGENTS.md。删时它仍停在 `git merge --ff-only`
  手同步流程与 `testing.md` 基线口径 (现行口径是 `commands run my-commit-flow.sync` 与 `baselines/` 切片)。
- `tests/test_memory_bank.py`: `test_session_protocol_is_exposed_in_always_on_entries` 的被查列表收成
  **只查 AGENTS.md**, 用例注释与头部「测试计划」清单同步改口径。
- `memory-bank/pitfalls/testing/parallel-run.md`: 补 xdist 下覆盖率抖动的实测区间 (原记 ±1 行)。

## 关键决策

- **留两个符号**: `⚠` 与 `🔴` —— 后者被正文「见「🔴 跨仓库操作」节」当锚点引用, `✅`/`❗` 纯装饰故删。
- **命令节字面命令串一字未动** —— `check_command_drift.py` 扫 AGENTS.md, 改写法会被判成第 N 处副本。
- **守卫字面串保住**: `.agents/skills/memory-bank/SKILL.md` 与「立档阈值」仍在 AGENTS.md 里 —— 会话协议
  仍由单点守住 (缺 token 照红), 只是不再逼每个入口重复声明。
- **改机检属红线动作**, 只在用户显式说「守卫一并移除」后才做。

## 过程中的两个坎

- **纯指针一上来会红**: `AssertionError: copilot-instructions.md 未声明立档阈值` —— 那条用例把两个入口都写进了
  被查列表, 实际上是在**替过期副本兜底**, 这正是副本长期删不掉的原因。以后遇到「文档删不干净」,
  先查是不是有机检 token 在吊着, 别急着往里补内容。
- **覆盖率数字的小差**: `test.full` 与上一条基线的未覆盖 -3 / partial -1, 经 `git diff --name-only 2be3fe79 HEAD`
  核验为零 `src/` 零 `tests/` 改动 ⇒ 是 xdist 调度抖动, 两次相邻采样一致。归因写进基线切片 `26-10-06-0713`;
  改机检后仍是 **2676 + 4 / 99%**(用例只改断言范围没增删), 故**没新建重复数字的快照**。

## 空格精简 (08:0x, 用户点名: 不影响阅读的空格全删)

- 判据: **中英交界 / 两个 ASCII 符号之间**的空格删; **字母数字之间**的一律留 (`Memory Bank`、`commands run`、
  `cp -a .git`、`--dry-run`); 标题 `# ` / 引用 `> ` / 列表 `- ` `1. ` / 嵌套缩进 全部留 (删了就不是 markdown)。
- 四个「删了会读错」的例外: `-` (CLI 标志 `排障 --all`)、`<>` (占位符 `run <task>`)、`.` (`python .agents/…`
  会连成模块路径)、`"` 且**邻着字母数字** (`grep -rn "<词>"` 两侧不能收)。`"` 邻中文照删
  (`"每天一次"等窗口语义`)。
- ⚠ 脚本坑: Python 的 `str.isalnum()` 对**汉字返回 True** —— 拿它判「英文单词内部」会把所有中英交界的空格
  全判成不可删 (第一轮只省了 607 字符, 修掉这个判断才到 787)。判词用 `c.isascii() and c.isalnum()`。
- 收成: **950 → 163 空格 / 7,492 → 6,705 字符**(余量 508 → 1,295)。机检 `doc.caps` PASS · `doc.drift` 0 处 ·
  `test.full` **2676 + 4 / 99%**(与基线 `26-10-06-0713` 同)。

## 去日期标注 (08:4x, 用户点名)

- 「(保线性, 拍板 2026-09-28)」这类**只留判据、日期删掉** —— 拍板时间不改变 agent 行为, 考据价值在日志里。
  7 处 → **6,705 → 6,596 字符**(余量 1,404)。`回写合流交脚本` 那条整段删 (「取代 2026-09-26 先合并远端再收尾」
  属沿革旁白)。保留: `(3次事故)`(次数非日期)、「stash 舞蹈自提交路径退役」(判据由来, 只去日期)。
- 追加删首行 `(Copilot/Codex/Cursor/Gemini CLI/Claude Code/ZCode/Trae通用)` —— 工具名单会过期, 「所有 AI
  编码代理的统一入口」已含其义。**6,596 → 6,538 字符**。
- 机检: `doc.caps` PASS · `doc.drift` 0 处 · `test_memory_bank.py` **32 passed**。**未提交**。

## 修锚点引文 (09:0x)

- 上一轮压空格把「」里的**引文**(指向别处小节标题的锚点) 一起压了 ⇒ grep 0 命中: 「HTML文档一律dark主题」
  vs `webui.md:61 ## HTML 文档一律 dark 主题`;「🔴跨仓库操作」vs `collaboration.md:38`。已按原文恢复
  (26/76/18 行 + 74 行自身标题, 后者为对齐 `collaboration.md:40` 的反向引用)。**6,527 → 6,533 字符**。
- 空格精简补**第五个例外**: 「」里是「引文」(能 grep 到某个 `## ` 标题) 照抄原文; 是「说法」(口令/输出串)
  可润色。新坑 `memory-bank/pitfalls/docs/anchor-quote.md`, 已 `kb.index`。

## 未闭环

- 同源文件 `.github/instructions/ai-lib.md` / `.github/agents/` 疑似同一套手抄副本, 本轮没核, 待用户发话。
- cap 债务 1 项: `memory-bank/issues/_index.md` 25,598 > 25,200 字符 —— 与本轮无关, 需另开会话清理。
