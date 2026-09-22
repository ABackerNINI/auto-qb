---
name: memory-bank
description: 'Memory Bank 会话协议与知识库维护。USE FOR: 会话开始/收尾、更新知识库/回写文档、任务立档 (tasks/)、activeContext/progress/pitfalls/testing 维护; 用户说"更新 memory bank"/"更新知识库"/"记一下这个任务"/"收尾"/"做到哪了"/"立档" 时。DO NOT USE FOR: 单纯写代码或回答技术问题 (那只需按 AGENTS.md 路由读主题文档)。'
user-invocable: true
---

# Memory Bank 会话协议

本仓库用 Memory Bank 模式维护跨会话上下文: 知识库在 `memory-bank/`, 统一入口是根 `AGENTS.md`。
本 skill 只负责**会话的两个端点**(开始 / 收尾)与**任务立档**; 领域知识(架构/规则/配置/约定…)由 `memory-bank/` 主题文档承担, 不要写进本 skill。

## 会话开始 (4 步)

1. **先同步分支 (硬性)**: `git remote -v` 确认主线远端 (Gitee, `origin` 也可能是 GitHub 镜像) → `git pull --rebase <remote> develop` (**分支名必须写**, 只给远端名会只 fetch 不合并) → `git status -sb` 确认不落后再动手。**禁止在落后的分支上改代码**; 拉取前先把工作区弄干净 (先提交或移出改动) —— 见 `AGENTS.md`「⚠️ 环境硬约束: Git 操作」: 脏工作区 + rebase 触发 stash 会顺着拦截层批量删掉 `.git/objects`。
   - **想省事就跑机检**: `python .agents/skills/my-commit-flow/scripts/preflight.py` —— 一张表报出远端是不是主线 / 落后几个 / 工作区脏不脏 / 有没有红线文件; 提交与推送的完整步骤见 [my-commit-flow skill](../my-commit-flow/SKILL.md)。
2. 读 `memory-bank/activeContext.md` — 最后更新、进行中事项、下一步候选。
3. 按任务深入对应主题文档 —— **读哪份看根 `AGENTS.md`「知识库路由」表(路由单点)**; 动代码前必读 `pitfalls.md` 与 `conventions.md`。
4. 判断任务是否**已有 tasks/ 档案**: 有 → 读该档案续作并按"子任务状态表"推进; 无 → 按下方阈值决定是否立档。

## 立档阈值 (可判定: 满足任一条**必须**立档)

| # | 条件 |
|---|---|
| 1 | 任务跨越 ≥2 次会话 (上下文重置后仍需继续) |
| 2 | 单会话用户指令 ≥5 轮, 或改动 ≥3 个源文件 |
| 3 | 出现"计划 / 方案 / 波次 / 第 N 轮 / 后续阶段"等长周期表述 |
| 4 | 已产出或需要产出计划文档 / 交付报告 (`docs/*.html`, `DELIVERY/`) |

不立档(只记 `activeContext.md`): 单文件小修、错字、单轮问答、纯答疑。

> 阈值命中时**不得跳过**。2026-09-17 复盘: 3 天 25 条长纪要全堆在 `activeContext.md` 而 `tasks/` 只有 1 条 — 根因是"大任务"不可判定 + 立档成本高于"追加一行"的低成本出口。改成硬阈值后按表执行。

## 收尾 DoD (5 步, 缺一不可)

1. **activeContext**: 更新"最后更新"与"正在进行"; 已完成条目沉淀到 `progress.md` 或主题文档后**从本文件删除** — 它是易变层, 不是流水账。
2. **tasks/**: 命中阈值 → 按"任务档案规范"定名(**先查重再建**)建/更新 `memory-bank/tasks/YY-MM-DD-*.md`(追加进度日志 + 更新子任务状态表 + 维护 `Summary` 与 `Updated`), 然后跑 `python <skill-dir>/scripts/gen_tasks_index.py` 重建索引 —— **不要手改 `tasks/_index.md`**。
3. **事实回写**: 代码事实变更 → 回写对应 `memory-bank/` 主题文档与根 `README.md`; 测试基线数字**只改** `testing.md` 顶部(单点事实源, 其它文档一律引用不手抄)。
4. **闸门**: 跑 `uv run pytest tests -q`, 把实测数字记进 `testing.md` 与本次结论。
5. **新坑**: 遇到非显然的失败 / 陷阱 → **按动作选类, 写进 `pitfalls/<类>/<主题>.md`** ——
   补三行头元数据(`# 标题` / `> 摘要:` / `> 触发:`), 条目写 `触发` / `判别` / `处置` **三必填**
   字段(`守阵` / `复发` 选填); 没有合适的类**先扩枚举**(见「扩类 / 扩目录」);
   写完跑 `python <skill-dir>/scripts/gen_kb_index.py` 重建索引。
   - **复发闭环**: 若这一轮踩到了**已记的坑**, 把该条 `复发` 计数 **+1**, 并在任务档案里写一句
     **为什么没命中**(路由没到 / 文件没读 / 读了没照做)。反复重踩于是变成**可排序的数字**,
     也是「下沉为守阵」的优先级依据。
   - **拆文档也算入库动作**: 任何一次把内容写进 `memory-bank`, 先看目标文件的 cap
     (`_common.CAP_POLICY`); 超了就要么拆文件、要么外迁 —— 这是「库不会重新长胖」的收口。

## 任务档案规范

- 路径 `memory-bank/tasks/YY-MM-DD-<slug>.md` — **日期到天, 不带时分**; 日期取档案 `Added:` / `Started:`(创建日), 不是修改日。
- `<slug>` 由**专题**决定, 不由序号决定: 组成为 `<领域>-<专题>`, 领域用固定枚举(不够用先扩枚举再建档): `webui` / `backend` / `rule` / `memory-bank` / `docs` / `test` / `deps` / `config`。
- **立档第一步是查重, 不是取号**: 本 clone `ls memory-bank/tasks/` **且** 跨工作区 `ls ../auto-qb-*/memory-bank/tasks/` (2026-09-20 起为**多 clone 模式**: 各工作区是平级目录、各有独立 `.git`, 已无 `../auto-qb-other/.worktrees/*` 这类嵌套子工作区), 按 **slug 部分**比对(忽略日期前缀); 命中同名 → **追加不新建**。
- **slug 禁止出现**: 轮次(`round9` / `r10` / `第十轮`)、日期(已在文件名前缀)、会话序号、编号、分支名。轮次属于档案内"子任务状态表"的一行, 不属于文件名。
- 不带时分是**特性**: 同一天同一专题必然撞到同一路径, 重复才能当场暴露(显式 add/add 冲突), 而不是静默变成两份。
- 必备章节: 标题行 `# <文件名> — 名称`、状态行(`Status`/`Added`/`Updated`/`Summary`)、`## 原始请求`、`## 思考过程与决策`、`## 实现计划`、`## 子任务状态表`、`## 进度日志`。`**Summary:**` 是 `_index.md` 摘要的数据源。
- **`**Status:**` 取值只能是这 4 个英文单词**: `In Progress` / `Pending` / `Completed` / `Abandoned` —— 守阵 `tests/test_memory_bank.py` 用正则 `\*\*Status:\*\* (In Progress|Pending|Completed|Abandoned)` 匹配, 并且 `gen_tasks_index.py` 按它决定档案落在 `_index.md` 的哪个分区。写成中文「完成」或加前缀符号(`✅ 完成` / `已完成`)会被判为**非法状态行**, 表现为两条守阵同时红(状态行缺失 + 索引分区不一致)。
- 迁移期档案保留 `**Legacy-ID:** TASKnnn`, 供历史文档与历史对话中的旧编号回溯。
- 状态取值仅四种: `In Progress` / `Pending` / `Completed` / `Abandoned`; `_index.md` 的分区必须用同样的词。
- 一个专题一个档案(不逐会话建文件): 新会话追加**结论与决策**; 历史流水账原文归档在该档案的 `## 历史会话纪要 (原文归档)` 段。
- 守卫: `tests/test_memory_bank.py` 校验索引↔文件双向一致、忽略日期前缀的 slug 唯一、命名规范、状态分区、必备章节、索引 == 生成结果 — 登记了没文件 / 有文件没登记都会让 pytest 失败。

## 知识库结构 (目录化 + 索引生成物)

超标文档一律按**同一套五步配方**拆成 `<文档>/` 目录; 索引是**生成物**, 不手写。

### 五步配方 (任何一份超标文档, 含将来新增的)

1. **量**: 按 `##` / `###` 切段统计字符数, 对照下方 cap 定目标文件数; 同时统计引用处数 (决定存根的必要性)。
2. **建**: 建 `<文档>/` 目录; 每个主题文件头部写**三行头元数据**; **原句照搬, 不重写内容** ——
   只做三件事: 按动作补 `触发`、长叙事压成一句「为什么」、散落的实测数字与守阵名收进字段。
3. **生成**: 跑生成器产出 `_index.md` (**不许手写**); 原文档位置留 ≤1 KB 存根 (一句话 + 「已迁至 <目录>/_index.md」)。
4. **接线**: 更新路由 (`memory-bank/README.md` 细路由 + `AGENTS.md` 粗路由)、改活文档互引、改 skill / DoD 里的路径。
   **历史文档 (计划 HTML / issue 报告 / 任务档案正文) 一行不改** —— 靠存根兜住。
5. **守恒核对**: 迁移前的条目 / 段落清单 (`md5` + 字节) 与迁移后逐条比对, **missing 必须为 0**; 守卫与闸门转绿。

### 主题文件的三行头元数据 (生成器的数据源)

```
# <标题>                                  ← 索引行用它
> 摘要: 一句话说清「这文件治什么病」        ← 索引行用它
> 触发: 推送, 同步, ref 核对               ← 动作词, 供 grep 与路由
```

条目型 (`pitfalls/`) 与叙述型**共用同一套** —— 新增一个主题文件 = 写三行头 + 跑生成器, 不需要新脚本、不改守卫。
`<文档>/_about.md` 同格式, 存的是**目录**的元数据 (标题 / 一句话 / 触发条件)。

### cap 分级 (`_common.CAP_POLICY` 是单点, 守卫 import 它, 不手抄)

| 角色 | 上限 (字符) |
|---|---|
| `<文档>/_index.md` 与 `memory-bank/README.md` | 3,000 |
| `tasks/_index.md` / `issues/_index.md` (自动生成, 行数随条目数增长) | 12,000 |
| `pitfalls/*` 条目集 (读法是「扫描找一条」, 比通读更贵) | 6,000 |
| 常青主题 (叙述型) | 10,000 |
| 参考速查 (`config-reference/` · `rule-system/`) | 12,000 |
| 易变层 (`activeContext.md`, 会话开始必读) | 12,000 |
| 任务档案 (`tasks/*.md`, 其中「历史会话纪要」段 ≤8,000) | 24,000 |
| append-only 历史流水 (`*-history.md`) | 24,000 |
| `AGENTS.md` (IDE 注入硬上限, 由项目脚本 `scripts/check_context_caps.py` 管) | 8,000 |

下限建议 1.5 KB **只 WARN**: 主题文件过小会让「读三个文件」取代「读一节」, 反而更贵。

### 脚本 (统一落在本 skill 的 `scripts/`; 文档里一律写 `<skill-dir>/scripts/…`)

| 脚本 | 干什么 |
|---|---|
| `_common.py` | `find_root()` / `CAP_POLICY` / `PITFALL_CLASSES` / 三行头读取 —— 各脚本共用, 守卫也 import 它 |
| `gen_tasks_index.py` | 生成 `tasks/_index.md` (状态分区专用; 2026-09-22 从仓库根 `scripts/` 迁入本目录) |
| `gen_kb_index.py` | **通用**: 任意目录 → `_index.md` (有子目录出类指针, 无则出文件指针; pitfalls 两级与 testing 一级同一实现) |
| `check_kb_structure.py` | 结构检查: cap 策略 / 元数据 / 双向一致 / 无孤儿 / 存根 / 条目三字段 |

**「索引目录」是自发现的**: 含 `_about.md` 的目录即纳入 (`tasks/` `issues/` 有自己的生成器, 天然不在结果里)。
两个生成器都有 `--check` (只比对, 闸门用); 守卫**在进程内 import 检查器** (本项目测试禁止起子进程, `tests/sidefx.py` 会记账越界)。

### 检索纪律: 先索引, 后 grep, **禁止整读**

```
memory-bank/README.md     按任务选目录
→ testing/_index.md      按动作选主题 (一句话 + 触发词)
  → testing/tmpdir.md    读一个 ≤10 KB 的文件
```

不确定关键词时 `grep -rn "<词>" memory-bank/` 是三条线共用的兜底。
**「禁止整读某个目录」不是格式洁癖, 是预算纪律** —— 整读行为一旦回来, 目录化就白做了。

### 扩类 / 扩目录: 必须同时改三处

新增一个类或目录, 要同步改: ①枚举 (`_common.PITFALL_CLASSES`, 仅类范畴) ②`memory-bank/README.md` 细路由
③该目录的 `_about.md`。少一处守卫就红。

## 反模式 (本仓库已踩过, 勿重犯)

- ❌ 只在 `activeContext.md` 追加长纪要 → 文件膨胀成流水账, 跨会话定位不到"任务档案在哪"。
- ❌ 规则写成"跨会话的**大**任务要立档"这类不可判定措辞 → 无阈值 = 不执行。
- ❌ 把维护规则只放在 `applyTo: 'memory-bank/**'` 的 instruction 里 → 编辑 `src/` 时该规则不在上下文, **决策点(该不该立档)与生效点错位**。
- ❌ 基线数字手抄到 README/AGENTS/progress → 必然漂移; 只改 `testing.md`。
- ❌ 用"全局单调序号"当档案主键(TASKnnn) → 多个并行工作区(clone)各自发号必然撞号(2026-09-18 实测)。同理不要用"精确到分"的时间戳: 每次续作都算出新文件名, 永远"看起来是新的", 而且会让"忽略日期前缀的 slug 唯一性"守卫彻底失效。
- ❌ 手改 `tasks/_index.md` → 它是生成物, 冲突的解决方式是重跑生成器, 不是人工合并两版文本。
