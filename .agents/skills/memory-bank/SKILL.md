---
name: memory-bank
description: 'Memory Bank 会话协议与知识库维护。USE FOR: 会话开始/收尾、更新知识库/回写文档、任务立档(tasks/)、activeContext/progress/pitfalls/testing 维护; 用户说"更新 memory bank"/"更新知识库"/"记一下这个任务"/"收尾"/"做到哪了"/"立档"时。DO NOT USE FOR: 单纯写代码或回答技术问题(那只需按 AGENTS.md 路由读主题文档)。'
user-invocable: true
---

# Memory Bank 会话协议

本仓库用 Memory Bank 模式维护跨会话上下文: 知识库在 `memory-bank/`, 统一入口是根 `AGENTS.md`。
本 skill 只管**会话的两个端点**(开始/收尾)与**任务立档**; 领域知识(架构/规则/配置/约定…)由 `memory-bank/` 主题文档承担, 不要写进本 skill。

## 会话开始 (5 步)

1. **先同步分支(硬性, 无豁免 —— 问答/只读分析轮次也必须先同步)**: `commands run my-commit-flow.sync`。结果行形态、失败处置与子代理豁免(只读评审豁免 · 可写子代理不豁免)的单点在 `AGENTS.md`「会话协议 · 开始」①; Git 环境约束(多 clone、rebase 解禁、ref 三处核对)的单点在 `AGENTS.md`「⚠环境硬约束:Git操作」; 完整步骤见 [my-commit-flow 包](../../.commands/my-commit-flow/README.md)。**只读轮次遇同步失败不自作主张 stash**(那是写操作) —— 贴失败行并停下, 不在陈旧基线上作答。
2. 看会话滚动状态: `commands run kb.active` —— 扫 `memory-bank/activeContext/` 的时间戳切片, 按「最后活动」倒序输出一行摘要 + 陈旧标记。
   - ⚠ **activeContext 不含长青职能**: 「下一步」与定案口径都走 `memory-bank/README.md` 细路由, 别在这里找。
3. 按任务深入主题文档 —— **路由单点是 `memory-bank/README.md` 细路由表**(根 `AGENTS.md` 只做粗路由); 动代码前必读 `pitfalls/_index.md` 与 `conventions/_index.md`。
4. 判断任务是否**已有 tasks/ 档案**: 有 → 读该档案续作并按"子任务状态表"推进; 无 → 按下方阈值决定是否立档。
5. **建件前先取时**: 任何带日期的文件 (切片 / 档案 / 计划 / 报告 / issue) 的时间戳一律取自 `commands run kb.time`, **禁用上下文里的日期与手工推算** —— 见下方「时间口径与取时」。(走 `kb.new` / `kb.wrap` 的件时间戳由命令经 timekit 单点派生, 本步针对手写件。)

## 时间口径与取时 (2026-10-06)

KB 内**任何日期**只有一个来源: `commands run kb.time` —— UTC+8 钉死, 与机器时区无关。
**禁用模型上下文里的日期与手工推算** (那正是未来日期与错体例的来源); 过去日期的错值守卫也兜不住
(无真值可比), 只能靠这条流程规避。

| 字段 | 形态 | 取法 |
|---|---|---|
| 文件名前缀 (切片 / 计划 / 报告 / issue) | `YY-MM-DD-HHMM` | `commands run kb.time stamp` |
| 文件名前缀 (任务档案) | `YY-MM-DD` | `commands run kb.time date` |
| `**Added:**` / `**Updated:**` | `YYYY-MM-DD` | `commands run kb.time date` |
| `> 最后活动:` | `YYYY-MM-DD HH:MM` | `commands run kb.time time` |
| HTML `doc-added` / `doc-updated` | `YY-MM-DD-HHMM` | `commands run kb.time stamp` |
| 正文日期 | `YYYY-MM-DD` / `YYYY-MM-DD HH:MM` | `commands run kb.time date` / `time` |

- **守卫**: `commands run kb.time -- check`(挂 `kb.check` 与提交闸门); 违规族、正文不查未来、`<!-- time:allow -->` 豁免等判据见 [timekit.py](scripts/timekit.py) docstring。

## 立档阈值 (可判定: 满足任一条**必须**立档)

| # | 条件 |
|---|---|
| 1 | 任务跨越 ≥2 次会话(上下文重置后仍需继续) |
| 2 | 单会话用户指令 ≥5 轮, 或改动 ≥3 个源文件 |
| 3 | 出现"计划/方案/波次/第 N 轮/后续阶段"等长周期表述 |
| 4 | 已产出或需要产出计划文档/报告(`memory-bank/plans/` · `reports/` 的 HTML 制品) |

不立档(只写/更新一张 `activeContext/` 切片): 单文件小修、错字、单轮问答、纯答疑。

> 阈值命中时**不得跳过**。2026-09-17 复盘: 3 天 25 条长纪要全堆在 `activeContext.md` 而 `tasks/` 只有 1 条 ——
> 根因是"大任务"不可判定 + 立档成本高于"追加一行"的低成本出口。改成硬阈值后按表执行。

## 收尾 DoD (缺一不可)

> **由「提交」触发时**：直接按下面各步回写 —— 与远端的合流由 `ship.commit` **提交后 rebase** 完成（2026-10-04 起提交先行：各 `_index` 撞车由生成物自动化解兜底，手写件冲突才停下要人; 单点: my-commit-flow [pipeline.md](../../../.commands/my-commit-flow/references/pipeline.md)）。回写件仍是全体 clone 的最热写点, **随主提交一并暂存**, 不推完再补一笔。

0. **收口评审 (仅收口任务)**: 本次收尾若是某个命中立档阈值的任务的**最后一次**(收口判定与豁免表见 [code-review skill](../code-review/SKILL.md) ①), 先按该 skill 走完评审与裁决 —— 派**只读**子代理(派遣三件套照抄其 ③)→ 发现过 `commands run review.check` 引文校验 → **blocker 必修完**才可走下面各步; 相关发现当场修, 不相关按 create-issue 入池, 结论进进度日志(其 ⑥)。中途「提交」/阈值不命中的小修/纯文档任务不触发; 修复 diff > 100 行追加一轮。

1. **activeContext 切片 (机械面走命令)**: `commands run kb.wrap --topic <slug> --did "一句话"` —— 抬「最后活动」+ 追加 R 行(编号 = 现有最大 + 1); 同专题档案抬 `**Updated:**` + 进度日志追加带日期行(裁定 A5); 动了档案即重建 `tasks/_index.md`。**只做机械面 (D6)** —— 蒸馏与判断仍是 agent 的活(slug 复用 / 沉淀后删除 / 超 14 天蒸馏, 四条约定与体例见 [references/kb-structure.md](references/kb-structure.md) 与 [collaboration.md](../../../memory-bank/conventions/collaboration.md))。切片不存在时 kb.wrap 按模板建(零 SLOT 即合规, 裁定 A6)。伞形档案与派生计划各持不同 key 时加 `--archive <档案 Topics 键>` 单独锚定档案(切片仍按 `--topic` 落; 不传则沿用 `--topic` 匹配, 行为不变), 别为此改档案 Topics。文件名与「最后活动」的时刻由 kb.wrap 经 timekit 单点派生。
2. **tasks/**: 命中阈值 → `commands run kb.new task --title ".." --topic <领域>-<专题>` 建档(命名/头部/SLOT/查重全派生, 查重含跨 clone; 建后只填 SLOT), 续作既有档案直接编辑(进度日志日期行由 kb.wrap 追加, 追加时精修 `Summary`, 裁定 A1), 然后 `commands run kb.index` 重建索引 —— **不要手改 `tasks/_index.md`**。体例与必备章节见下方「任务档案规范」。
3. **事实回写**: 代码事实变更 → 回写对应 `memory-bank/` 主题文档与根 `README.md`; 测试基线数字**只写** `testing/baselines/` 下的新切片(最新一条 = 单点事实源), 命名/体例/逐位对比与守卫口径全在 [testing/baseline.md](../../../memory-bank/testing/baseline.md)。
4. **闸门**: 跑 `commands run test.full`, 新建基线切片记录实测数字(`kb.new baseline --total ..` 从实测输出誊写)。**裸数字只进切片这一处** —— 回复里可报数字, 写进档案/切片的段落一律「全绿(见 kb.baseline)」这类引用措辞; 建档任务的切片补一行 `**Refs:** <档案路径>`(认领链, 见「任务档案规范」)。
   - **真机自检 (2026-11-04 起)**: 完工功能落入真机轨两类准入(qB 真执行才成立 / 必须碰真文件系统·进程·注册表; 桩数据失真足以改变结论的观感面按失真理由) ⇒ **当轮 agent 自跑真机验收**(`real.guard` → `real.run` / `dev.webui` + 浏览器自动化 / `dev.run` 指向测试 qB —— 四实例本机免token, 无需用户提供任何凭据; 判据与两种触发形态见 `testing/real-machine.md` §00/§06), 没做的须在档案/切片明示理由(环境不可用 / 纯桩可验 / 记 BLOCKED)。真机仍**不挂自动闸门**。
5. **收录命令**: 遇到**反复要跑/难拼/有"看起来正常但不生效"写法**的命令 → 自己 `add` 进 `.commands/` 的对应包, 别在文档里抄(手抄会被 `commands run doc.drift` 判红)。判据见 [commands skill](../commands/SKILL.md)「收录协议」。
6. **新坑**: 非显然的失败/陷阱 → **按动作选类, 写进 `pitfalls/<类>/<主题>.md`**: 补三行头(`# 标题`/`> 摘要:`/`> 触发:`; 建档任务再补一行 `**Refs:** <档案路径>` 反向声明), 条目写 `触发`/`判别`/`处置` **三必填**(`守阵`/`复发` 选填); 没有合适的类**先扩枚举**; 写完 `commands run kb.index`。
   - **复发闭环**: 踩到**已记的坑** → 该条 `复发` **+1**, 并在档案里写一句**为什么没命中**(路由没到/文件没读/读了没照做)。反复重踩于是变成**可排序的数字**, 也是「下沉为守阵」的优先级依据。
   - **拆文档也算入库动作**: 写进 `memory-bank` 前先看目标文件的 cap(见下方 cap 表); 超了按触顶固定动作处置(**禁止压文案**)。
7. **cap 债务转告**: 提交输出出现 `[债务]` 行 → **在回复里提醒用户「文档数字已超标, 需另开新会话清理」**, 并**不在本会话动手改**(返工留在原处; 债务清单现算不转抄); `AGENTS.md` 例外(硬规定, 超限当场削薄)。口径见下方 cap 分级的债务制。

## 回写措辞: 禁时点相对的状态断言 (2026-10-07)

回写件 (activeContext 切片 / tasks 档案) **不写「待提交」这类断言** —— 它必然在提交后过期。

**为什么必然过期 (自指不可能)**: `commit` 的 hash 由 tree + parent + author + 时间戳共同决定 ——
想把它写进文件就改变了 tree, hash 随之变化, 循环无解 ⇒ **一个提交永远无法包含自己的 hash**。
而收尾 DoD 要求回写件**随主提交一并暂存** (见上), 于是那句断言写在 hash 逻辑上尚不存在的时点。
2026-09-27 审计 (`reports/26-09-27-1547`) 已实证「提交后靠收尾回扫修正」这条兜底会失败:
切片停在「等待提交」而提交实际已完成 —— 切片与计划 meta 双陈旧。

| | 写法 |
|---|---|
| ✗ 禁 | `待提交` · `未提交`(作状态用) · `等用户「提交」指令` · `等显式指令` · `**未 commit**` |
| ✓ 用 | **时不变措辞**「随本专题入库」(提交前=将要, 提交后=已); 或**直接省去** —— git 状态自证, hash 需要时 `git log --grep <专题键>` 找回 (与坑档 `pitfalls/kb/commit-hash-refs.md` 同旨: 写入时优选会存活的引用) |

- **豁免① 带日期前缀的行**: 流水条目自带时点、不会过期, 改写反而是篡改日志 (38 处存量按此保留)。
- **豁免② 行内 `<!-- wording:allow -->`**: 引述他人原文等一次性场景。
- **豁免③ `未提交` + 名词** (`未提交改动` / `未提交的工作树`): 这是**树态描述**, 不是状态断言。
- **机检**: `commands run kb.check` 含 `check_wording.py --check` (扫描面 = `tasks/` + `activeContext/`);
  守阵 `tests/test_memory_bank_*.py`(四分)。**baselines 不在扫描面** —— 它是出厂即冻结的测量快照, 其
  「未提交」描述「这条基线测在哪棵树上」, 是解释数字差异的必需元数据 (例: `26-10-06-0547` 用它
  解释 passed 对不齐), 不是会过期的状态断言; 冻结件不随提交更新, 该缺陷形态在那里不成立。

## 手抄测试数字: 只留切片一处 (2026-10-08 方案 C)

KB 正文 (`tasks/` + `activeContext/`) 不写裸测试数字(`2772 passed` 这类) —— 数字的唯一权威是 `testing/baselines/` 最新切片; 切片正文也只写自己的 TOTAL。口径、存量冻结(只拦新增)与机检(`check_wording.py` 判据族 B)见 [testing/baseline.md](../../../memory-bank/testing/baseline.md); 现算 `--count-numbers`, 全量清单 `--list-numbers`; 豁免 = 带日期前缀的行 · 代码/围栏 · `<!-- wording:allow -->`。

## 任务档案规范

- 路径 `memory-bank/tasks/YY-MM-DD-<slug>.md` —— **日期到天, 不带时分**; 日期取 `Added:`/`Started:`(创建日), 不是修改日; 日期本身取 `commands run kb.time date`。
- `<slug>` 由**专题**决定, 不由序号决定: `<领域>-<专题>`; 领域用固定枚举(不够用先扩枚举再建档): `webui`/`backend`/`rule`/`memory-bank`/`docs`/`test`/`deps`/`config`。
- **立档第一步是查重, 不是取号**: 本 clone `ls memory-bank/tasks/` **且**跨工作区 `ls ../auto-qb-*/memory-bank/tasks/`(2026-09-20 起多 clone 模式: 各工作区平级、各有独立 `.git`), 按 **slug 部分**比对(忽略日期前缀); 命中同名 → **追加不新建**。
- **slug 禁止出现**: 轮次(`round9`/`r10`/`第十轮`)、日期(已在文件名前缀)、会话序号、编号、分支名 —— 轮次属于档案内"子任务状态表"的一行, 不属于文件名。不带时分是**特性**: 同一天同一专题必然撞到同一路径, 重复才能当场暴露(显式 add/add 冲突), 而不是静默变成两份。
- 必备章节: `# <文件名> — 名称`、状态行(`Status`/`Added`/`Updated`/`Summary`)、`## 原始请求`、`## 思考过程与决策`、`## 实现计划`、`## 子任务状态表`、`## 进度日志`。
- **`**Status:**` 只能取这 4 个英文词**: `In Progress`/`Open`/`Done`/`Dropped` —— 守卫用正则匹配、`gen_tasks_index.py` 按它决定索引分区; 写成中文「完成」或加前缀(`✅ 完成`)会被判**非法状态行**, 两条守卫同时红。旧词映射见 [doc-forms 约定](../../../memory-bank/conventions/doc-forms.md)(`Pending`→Open · `Completed`→Done · `Abandoned`→Dropped)。
- `**Summary:**` 是 `_index.md` 摘要的数据源 —— 索引里按 `gen_tasks_index.SUMMARY_MAX` **截断成一行**, 全文留在档案, 摘要写长不会撑爆索引。
- 引用他件 (issue/计划/报告/基线切片/坑档) 写 `**Refs:**` 行: 值 = **仓库根相对路径**, **多目标一律英文逗号、全写一行** (`·`/`、`/`;` 会被整串当成单一路径判红)。认领链**双向**: 每个被引目标都必须反向声明本档案 (HTML `doc-refs` meta / md `**Refs:** <档案路径>` 行), 单向链提交闸门判红 —— 协议单点见 [doc-forms「认领链」](../../../memory-bank/conventions/doc-forms.md)。
- 迁移期档案保留 `**Legacy-ID:** TASKnnn`, 供历史文档与历史对话中的旧编号回溯。
- 一个专题一个档案(不逐会话建文件): 新会话追加**结论与决策**; 历史流水账原文归档在该档案的 `## 历史会话纪要 (原文归档)` 段。
- 守卫 `tests/test_memory_bank_*.py` 校验索引↔文件双向一致、忽略日期前缀的 slug 唯一、命名规范、状态分区、必备章节、索引 == 生成结果 —— 登记了没文件/有文件没登记都会让 pytest 失败。

## cap 分级(`_common.CAP_POLICY` 是机器单点; 下表是它唯一的人读镜像)

> 守卫 `test_skill_cap_table_matches_cap_policy` 钉住本表与 `CAP_POLICY` 的**数值集合与行数**一致(判不出「两行数值互换角色」—— 那种只能靠人读); **别在别处抄第三张表**。
> **触顶处置 (2026-11-05 用户重定调)**: 目标**刚好 ≤ cap**, **禁止压文案**; 固定动作「外迁 `attachments/` → 删除死段 → 合并邻近件」; `log` 例外: append-only, 从最老一端轮转(细则见 [kb-structure.md](references/kb-structure.md))。
> **触顶后要不要当场改? (2026-09-30 债务制, 单点 [plan 26-09-30-2112](../../../memory-bank/plans/26-09-30-2112-plan-memory-bank-cap-debt.html))**: 除 `AGENTS.md` 外**一律不当场改** —— 尺寸是债务, 不是提交前置条件(违反只是读起来更贵, 事实源完好); 触顶总在任务后期, 当场返工成本远大于文件变长; 债务是**派生**的(`commands run doc.caps` 现算, 不设手写债务表)。**触发点 = 提交闸门输出**: 读到的人转告用户, 由用户**另开一场会话清理**, 收口 `commands run doc.caps -- --strict`。
> ❗**`AGENTS.md` 是唯一例外**: 越过 8,000 发生的是 IDE 注入 `slice(0, 8000)` **截断**(尾部对模型真不可见), 不是「读起来贵」—— 所以超限即拦、**不进债务清单**; 削薄只需回到 ≤ 8,000(细节下沉, 原位留指针)。

| 角色 | 上限 (字符) |
|---|---|
| `memory-bank/README.md`(手写) | 6,000 |
| `*/_index*.md`(自动生成: tasks / issues / 各目录 / 分卷页 `_index-<n>.md`; 已完结区 `CLOSED_KEEP` 是上限) | 8,000 |
| `pitfalls/*` 条目集(「扫描找一条」比通读更贵) | 8,000 |
| 常青主题(叙述型) | 8,000 |
| 参考速查(`config-reference/` · `rule-system/`) | 24,000 |
| 易变层(`activeContext.md`; 目录化后原位只留 ≤2 KB 存根) | 24,000 |
| `activeContext/` 会话切片(per-专题) | 12,000 |
| `testing/baselines/` 基线切片(一次性快照) | 8,000 |
| 任务档案(`tasks/*.md`, **仅新建**; 2026-11-05 前存量整类豁免) | 8,000 |
| append-only 历史流水(`*-history.md`) | 8,000 |
| `AGENTS.md`(**硬规定**: IDE 注入截断, 超限即拦; 由 `scripts/check_context_caps.py` 管) | 8,000 |

> **2026-11-05 用户重定调**: 存量 tasks 整类豁免(排障才读, 改造收益低 —— `CAP_TASK_FREEZE` 按文件名日期 `< 26-11-05` 判), 此后新建 task 与 `log` / `evergreen` / `pitfall` / `index-auto` 四类统一 ≤ 8,000(存量清零); 目标**刚好 ≤ 8,000**, 旧 50% 收缩口径作废。个案豁免须在文档头写明理由、由用户逐件确认; 整类豁免只认 `CAP_POLICY` / `CAP_TASK_FREEZE`。

## 结构 / 索引 / 脚本 → 见 references

拆超标文档的**五步配方**、三行头元数据、cap 与流水轮转、脚本清单、activeContext 切片四条约定、
检索纪律(先索引后 grep 禁止整读)、扩类扩目录三处同步 —— 全在 **[references/kb-structure.md](references/kb-structure.md)**, 要动知识库结构时才读;
换项目怎么把整套 skill 搬走见 **[references/PORTING.md](references/PORTING.md)**。

## 反模式

- ❌ 在 activeContext(单文件或切片)里追加长纪要 → 膨胀成流水账, 跨会话定位不到"任务档案在哪"。
- ❌ 规则写成"跨会话的**大**任务要立档"这类不可判定措辞 → 无阈值 = 不执行。
- ❌ 基线数字手抄到 README/AGENTS/progress/档案 → 必然漂移; 只写切片, 正文写「见 kb.baseline」(守卫判据族 B)。
- ❌ 用"全局单调序号"当档案主键(TASKnnn) → 并行 clone 各自发号必然撞号(2026-09-18 实测); 同理不要用"精确到分"的时间戳(每次续作都算出新文件名, 且会让"忽略日期前缀的 slug 唯一性"守卫失效)。
  ⚠ **此条只针对 tasks/ 档案主键** —— `activeContext/` 切片恰恰**故意**带时分(用它避撞名), 两者意图相反, 所以必须分目录。
- 结构类反模式(切片截断 / `_recent.md` 缓存 / clone 标记 / 长青内容 / instructions 错位 / 手改索引)见 [references/kb-structure.md](references/kb-structure.md)。
