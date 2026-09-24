---
name: memory-bank
description: 'Memory Bank 会话协议与知识库维护。USE FOR: 会话开始/收尾、更新知识库/回写文档、任务立档(tasks/)、activeContext/progress/pitfalls/testing 维护; 用户说"更新 memory bank"/"更新知识库"/"记一下这个任务"/"收尾"/"做到哪了"/"立档"时。DO NOT USE FOR: 单纯写代码或回答技术问题(那只需按 AGENTS.md 路由读主题文档)。'
user-invocable: true
---

# Memory Bank 会话协议

本仓库用 Memory Bank 模式维护跨会话上下文: 知识库在 `memory-bank/`, 统一入口是根 `AGENTS.md`。
本 skill 只管**会话的两个端点**(开始/收尾)与**任务立档**; 领域知识(架构/规则/配置/约定…)由 `memory-bank/` 主题文档承担, 不要写进本 skill。

## 会话开始 (4 步)

1. **先同步分支(硬性; 问答/只读轮次跳过, 首个执行动作前必须完成)**: `git remote -v` 确认主线远端 → `git fetch <主线远端> <分支>`(远端与分支名**必须写**) → `git ls-remote <主线远端> <分支>` 对比本地 HEAD 确认不落后(`status -sb` 是快照, 会给假绿灯) → 纯落后且工作区干净才 `git merge --ff-only FETCH_HEAD`。**禁止在落后的分支上改代码**; 树脏 → 停下报告, 禁止自行清理 —— 见 `AGENTS.md`「⚠️ 环境硬约束: Git 操作」(非快进合并 + 脏工作区会触发 stash, 顺着拦截层批量删掉 `.git/objects`; rebase/stash 在工具 shell 里一律禁用)。
   - **想省事就跑机检**: 开工自检 `commands run my-commit-flow.sync`(只读, 结果贴进回复); 提交/推送前跑 `commands run my-commit-flow.preflight`; 完整步骤见 [my-commit-flow 包](../../.commands/my-commit-flow/README.md)。
2. 看会话滚动状态: `commands run kb.active` —— 扫 `memory-bank/activeContext/` 的时间戳切片, 按「最后活动」倒序输出一行摘要 + 陈旧标记。
   - ⚠ **activeContext 不含长青职能**: 「下一步」看 `想法.md` + `progress/roadmap.md`, 定案口径看 `AGENTS.md`/`conventions/`/`pitfalls/` —— 走 `memory-bank/README.md` 细路由。
3. 按任务深入主题文档 —— **读哪份看根 `AGENTS.md`「知识库路由」表(路由单点)**; 动代码前必读 `pitfalls.md` 与 `conventions.md`。
4. 判断任务是否**已有 tasks/ 档案**: 有 → 读该档案续作并按"子任务状态表"推进; 无 → 按下方阈值决定是否立档。

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

1. **activeContext 切片**: 写/更新 `memory-bank/activeContext/YY-MM-DD-HHMM-<slug>.md`(含 `# 标题`/`> 摘要:`/`> 最后活动: YYYY-MM-DD HH:MM`)。**同一专题跨会话沿用同一个 slug** —— 新会话更新「最后活动」与「正在进行」, 不新建文件(只在换专题时新建); 已完成条目沉淀到 `progress/` 或主题文档后**从切片删除**; 超 14 天没动 → 蒸馏后删除。它是易变层, 不是流水账。四条约定见 [references/kb-structure.md](references/kb-structure.md)。
2. **tasks/**: 命中阈值 → 按下方「任务档案规范」定名(**先查重再建**)建/更新 `memory-bank/tasks/YY-MM-DD-*.md`(追加进度日志 + 更新子任务状态表 + 维护 `Summary` 与 `Updated`), 然后 `commands run kb.index` 重建索引 —— **不要手改 `tasks/_index.md`**。
3. **事实回写**: 代码事实变更 → 回写对应 `memory-bank/` 主题文档与根 `README.md`; 测试基线数字**只改** `testing/baseline.md` 顶部(单点事实源, 其它文档一律引用不手抄 —— `testing.md` 自 2026-09-22 目录化起只是存根)。
4. **闸门**: 跑 `commands run test.full`, 把实测数字记进 `testing/baseline.md` 与本次结论。
5. **收录命令**: 遇到**反复要跑/难拼/有"看起来正常但不生效"写法**的命令 → 自己 `add` 进 `.commands/` 的对应包, 别在文档里抄(手抄会被 `commands run doc.drift` 判红)。判据见 [commands skill](../commands/SKILL.md)「收录协议」。
6. **新坑**: 非显然的失败/陷阱 → **按动作选类, 写进 `pitfalls/<类>/<主题>.md`**: 补三行头(`# 标题`/`> 摘要:`/`> 触发:`), 条目写 `触发`/`判别`/`处置` **三必填**(`守阵`/`复发` 选填); 没有合适的类**先扩枚举**; 写完 `commands run kb.index`。
   - **复发闭环**: 踩到**已记的坑** → 该条 `复发` **+1**, 并在档案里写一句**为什么没命中**(路由没到/文件没读/读了没照做)。反复重踩于是变成**可排序的数字**, 也是「下沉为守阵」的优先级依据。
   - **拆文档也算入库动作**: 写进 `memory-bank` 前先看目标文件的 cap(`_common.CAP_POLICY`, 人读镜像见下方 cap 表); 超了要么拆文件、要么外迁。

## 任务档案规范

- 路径 `memory-bank/tasks/YY-MM-DD-<slug>.md` —— **日期到天, 不带时分**; 日期取 `Added:`/`Started:`(创建日), 不是修改日。
- `<slug>` 由**专题**决定, 不由序号决定: `<领域>-<专题>`; 领域用固定枚举(不够用先扩枚举再建档): `webui`/`backend`/`rule`/`memory-bank`/`docs`/`test`/`deps`/`config`。
- **立档第一步是查重, 不是取号**: 本 clone `ls memory-bank/tasks/` **且**跨工作区 `ls ../auto-qb-*/memory-bank/tasks/`(2026-09-20 起多 clone 模式: 各工作区平级、各有独立 `.git`), 按 **slug 部分**比对(忽略日期前缀); 命中同名 → **追加不新建**。
- **slug 禁止出现**: 轮次(`round9`/`r10`/`第十轮`)、日期(已在文件名前缀)、会话序号、编号、分支名 —— 轮次属于档案内"子任务状态表"的一行, 不属于文件名。不带时分是**特性**: 同一天同一专题必然撞到同一路径, 重复才能当场暴露(显式 add/add 冲突), 而不是静默变成两份。
- 必备章节: `# <文件名> — 名称`、状态行(`Status`/`Added`/`Updated`/`Summary`)、`## 原始请求`、`## 思考过程与决策`、`## 实现计划`、`## 子任务状态表`、`## 进度日志`。
- **`**Status:**` 只能取这 4 个英文词**: `In Progress`/`Open`/`Done`/`Dropped` —— 守卫用正则匹配、`gen_tasks_index.py` 按它决定索引分区; 写成中文「完成」或加前缀(`✅ 完成`)会被判**非法状态行**, 两条守卫同时红。旧词映射见 [doc-forms 约定](../../../memory-bank/conventions/doc-forms.md)(`Pending`→Open · `Completed`→Done · `Abandoned`→Dropped)。
- `**Summary:**` 是 `_index.md` 摘要的数据源 —— 索引里按 `gen_tasks_index.SUMMARY_MAX` **截断成一行**, 全文留在档案, 摘要写长不会撑爆索引。
- 迁移期档案保留 `**Legacy-ID:** TASKnnn`, 供历史文档与历史对话中的旧编号回溯。
- 一个专题一个档案(不逐会话建文件): 新会话追加**结论与决策**; 历史流水账原文归档在该档案的 `## 历史会话纪要 (原文归档)` 段。
- 守卫 `tests/test_memory_bank.py` 校验索引↔文件双向一致、忽略日期前缀的 slug 唯一、命名规范、状态分区、必备章节、索引 == 生成结果 —— 登记了没文件/有文件没登记都会让 pytest 失败。

## cap 分级(`_common.CAP_POLICY` 是机器单点; 下表是它唯一的人读镜像)

> 守卫 `test_skill_cap_table_matches_cap_policy` 钉住本表与 `CAP_POLICY` 的**数值集合与行数**一致 —— 改了源忘了改表会红;
> ⚠ 判不出「两行数值互换角色」, 那种改动只能靠人读表。**别在别处抄第三张表**。

| 角色 | 上限 (字符) |
|---|---|
| `<文档>/_index.md` 与 `memory-bank/README.md` | 3,000 |
| `tasks/_index.md` / `issues/_index.md`(自动生成) | 12,000 |
| `pitfalls/*` 条目集(「扫描找一条」比通读更贵) | 6,000 |
| 常青主题(叙述型) | 10,000 |
| 参考速查(`config-reference/` · `rule-system/`) | 12,000 |
| 易变层(`activeContext.md`; 目录化后原位只留 ≤1 KB 存根) | 12,000 |
| `activeContext/` 会话切片(per-专题) | 6,000 |
| 任务档案(`tasks/*.md`, 「历史会话纪要」段 ≤8,000) | 24,000 |
| append-only 历史流水(`*-history.md`) | 24,000 |
| `AGENTS.md`(IDE 注入硬上限, 由 `scripts/check_context_caps.py` 管) | 8,000 |

## 结构 / 索引 / 脚本 → 见 references

拆超标文档的**五步配方**、三行头元数据、cap 与流水轮转、脚本清单、activeContext 切片四条约定、
检索纪律(先索引后 grep 禁止整读)、扩类扩目录三处同步 —— 全在 **[references/kb-structure.md](references/kb-structure.md)**, 要动知识库结构时才读。

## 反模式

- ❌ 在 activeContext(单文件或切片)里追加长纪要 → 膨胀成流水账, 跨会话定位不到"任务档案在哪"。
- ❌ 规则写成"跨会话的**大**任务要立档"这类不可判定措辞 → 无阈值 = 不执行。
- ❌ 基线数字手抄到 README/AGENTS/progress → 必然漂移; 只改 `testing/baseline.md`。
- ❌ 用"全局单调序号"当档案主键(TASKnnn) → 并行 clone 各自发号必然撞号(2026-09-18 实测); 同理不要用"精确到分"的时间戳(每次续作都算出新文件名, 且会让"忽略日期前缀的 slug 唯一性"守卫失效)。
  ⚠ **此条只针对 tasks/ 档案主键** —— `activeContext/` 切片恰恰**故意**带时分(用它避撞名), 两者意图相反, 所以必须分目录。
- 结构类反模式(切片截断 / `_recent.md` 缓存 / clone 标记 / 长青内容 / instructions 错位 / 手改索引)见 [references/kb-structure.md](references/kb-structure.md)。
