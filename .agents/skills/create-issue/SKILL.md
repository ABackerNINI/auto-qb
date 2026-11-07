---
name: create-issue
description: '计划外问题入池: 在 issues 目录生成 HTML 报告(8 类类型 × 便签/标准两档)并在 _index.md 登记类型+简述+链接。USE FOR: 需要把一个暂时不修的问题记成别人能直接开工的记录; 用户说"记个 issue"/"这个问题先记下来"/"创建 issue"/"入池"/"更新 issue 状态"/"issue 修完了"/"issues 索引重建" 时。DO NOT USE FOR: 本次计划内的缺陷 (直接修)、纯答疑、代码评审清单、大改造(走 tasks/ 档案或 memory-bank/plans/ 计划)。判断"该不该现在修"见 scope-guard skill; 本 skill 只负责记。'
user-invocable: true
---

# Issue 报告 (issues 池)

把"暂时不修的问题"变成一份**别人不用重新调查就能开工**的记录, 并在索引里留一条 `类型 · 简述 · 链接`。

- 什么该入池、什么该当场修 → 见 [scope-guard skill](../scope-guard/SKILL.md)。
- 本 skill 只负责**记录与状态流转**, 不负责判断修不修。
- **核心原则: 入池成本与问题重量成正比** —— 文档漂移写三行就够, 复杂缺陷才值得停下来取证。
- **机械面已收编进 kb 命令包** (2026-11-07, 计划 26-11-07-0549): 建件 `commands run kb.new issue` ·
  翻状态 `commands run kb.status` · 索引 `commands run kb.index`。本 skill 保留**流程语义**
  (类型 / 档位 / 防过期 / 认领链 / 反模式), 脚本与模板已并入 memory-bank skill。

## 类型(8 类, 进文件名第二段)

类型 token 直接进文件名, 是**唯一**的强制分类维度(不加优先级 / 模块 —— 加了就又变成大单)。
枚举单点定义在 memory-bank skill `scripts/_common.py` 的 `TYPES`, 增删类型只改那一处。

| token | 含义 | 什么时候用它 | 默认档位 |
|---|---|---|---|
| `bug` | 缺陷 | 行为不符预期、报错、回归、平台兼容 | standard |
| `perf` | 性能 | 慢、卡顿、无谓重建、内存 / CPU | standard |
| `docs` | 文档 | 文档漂移 / 缺失 / 写错 / 与代码不一致 | light |
| `test` | 测试 | 用例缺失、失败、守卫缺口 | light(失败用例用 `--tier standard`) |
| `refactor` | 技术债 | 重构、耦合、命名 / 格式不一致、历史 TODO | light |
| `feat` | 功能 | 新增能力或增强(未排期) | standard |
| `chore` | 杂项 | 依赖升级、CI、配置、脚本维护 | light |
| `question` | 待拍板 | 缺决策就动不了手(方向二选一、等用户定调) | light |

**不单列的类型归到哪儿**:

- `security` —— **不入池**。与 scope-guard 的例外 2 一致: 当场告知用户并修; 确需留痕时用 `bug` + 严重度"高"。
- `regression` / `compatibility` —— 归 `bug`, 正文首行标注即可。
- `epic` / `RFC` / 大改造 —— 不进 issues, 走 `memory-bank/tasks/` 档案或 `memory-bank/plans/` 计划。

## 档位(类型决定, `--tier` 可覆盖)

| 档位 | 适用类型 | 必填段 | 可选段 | 时间预算 |
|---|---|---|---|---|
| **L1 便签** `light` | docs / refactor / chore / question / test 缺口 | 现象一句话 · 位置 · 状态日志 | 建议一句 | **≤ 2 分钟** |
| **L2 标准** `standard` | bug / perf / feat / test 失败 | 现象与场景 · 证据(贴原文) · 影响面(3 行) · 定位锚点 · 状态日志 | 根因(默认"待查") · 建议修法 | **≤ 10 分钟** |

超时就只写事实 + 待查, **立刻回主线** —— 入池是"顺手记一笔", 不是"先调查清楚"。

## 新建一条 issue (2 步)

### 1. 建件(一条命令, 派生面零手写)

```bash
commands run kb.new issue <slug> --type docs --title "中文标题" --summary "一句话简述(进索引)" \
  [--tier light|standard] [--module webui] [--reporter worktree] [--topic <kebab>] [--refs <路径>,<路径>]
```

- `<slug>`: 小写英文短横线, 建议 `<领域>-<专题>`(只是建议, 分类职责已交给 type); 兼作 `doc-topic` 默认主键。
- `--type` / `--summary`: **必填**, type 不在 8 类枚举里直接报错; summary 进 issues 索引行。
- `--tier`: 默认由类型推导, 显式覆盖(如 test 失败用例用 standard)。
- `--topic`: `doc-topic` 跨形态串联主键(默认 = slug)。**多条 issue 属于同一专题时显式指定同一个值**
  (如 `webui-optimistic-ui` 下挂 3 条), 这样 `commands run kb.docmap` 的专题视图才把它们串成一条线。
  不传 = 一题一专题。**该 meta 不可省** —— 缺了该 issue 会从专题视图里静默漏掉
  (守卫 `tests/test_docs_forms.py::test_issue_topics_present` 判红)。
- 模板同时带空的 `doc-refs` meta(认领链声明位): 与既有计划/档案相关时创建即可填(`--refs`);
  被 tasks 档案认领时**必须填**, 见「修一条 issue 时」第 3 步。
- 时间戳 / 命名 / 头部字段 / 封面徽标 / `_index.md` 与归档索引重建全由命令派生 ——
  **不再需要先跑 `commands run kb.time stamp` 取时确认**(那是手写建件时代的步骤): `kb.new` 经 timekit
  单点取时(UTC+8 钉死, 与机器时区无关), 值不对只可能是系统时钟问题; `kb.time` 只剩手写带日期文件时的用途。
- 产出 `memory-bank/issues/<时间戳>-<类型>-<slug>.html`, 例 `26-09-19-2359-docs-memory-bank-push-rule-drift.html`;
  目标已存在即 rc=1 不覆盖(slug 查重是档案族专属, issue 靠时间戳前缀天然区分)。
- 旧 `--dir` / `--root` / `--project` 可移植性参数已随 new_issue.py 退役(2026-11-07, D2): issues 目录固定
  `memory-bank/issues`, 移植口径见下方「可移植性」。

### 2. 填正文(按档位, 这是入池的价值所在)

命令只填封面(模板零 SLOT)。接着按档位补齐 —— **只为"别人能直接开工"而写, 不为填满字段而写**:

- **L1**: 一句话现象 + 位置(grep 锚点) + 可选一句建议。
- **L2**: 现象与场景 · 证据原文 · 影响面三行 · 定位锚点(符号名 + grep 词 + 当时行号)。

## 防过期原则(5 条)

问题会等很久才被认领, 而代码一直在动。这五条比"填什么字段"更重要:

1. **只记事实, 不记结论。** 根因与修法默认"待查"; 有结论才写, 不确定就写"已排除：X、Y"。不要把猜测写成结论。
2. **行号要标"当时"。** 定位锚点 = 符号名 + grep 关键词 + 当时的行号(注明取证时间)。代码漂移后靠符号与 grep 重新定位, 行号只是加速项。
3. **不为填单做分析。** 入池的时间预算写死在上面: L1 ≤ 2 分钟、L2 ≤ 10 分钟。
4. **证据贴原文并标时间。** 日志 / 报错 / 命令输出原样贴, 附取证时间, 让读者自己判断新鲜度。
5. **开工时先复验。** 认领后第一件事是重跑锚点、确认现象仍在; 报告里补一行"复验：`<时间>` 仍复现 / 已消失"。

## 状态机

状态写在报告 HTML 的**封面状态徽标**(`<span class="badge">`)与 `<head>` 的 `<meta name="issue-status">`(**两处一起改**, 索引只读 meta), 取值仅五种(2026-09-23 起与四形态统一 5 词表, 见 [doc-forms 约定](../../../memory-bank/conventions/doc-forms.md)):

| 状态 | 含义 |
|---|---|
| `Open` | 未修, 待排期(新建默认) |
| `In Progress` | 已被某个计划认领, 正在修 —— **认领人只能是"用户指派"或"用户已批准的计划"** |
| `Done` | 已修并验证(写清验证方式与测试数字) —— 旧词 `Fixed` |
| `Dropped` | 决定不修(必须写明理由) —— 旧词 `WontFix` |
| `Superseded` | 与他件重复 / 被取代(写明指向哪一条) —— 旧词 `Duplicate` |

改状态的唯一入口: `commands run kb.status <件> <新状态>`(2026-11-07 W4 收编) —— 两处状态一起改、
追加一行状态变更日志、重建索引(含归档)全由命令派生; 幂等(同状态翻转不抬时间戳不重建索引),
翻进终态(`Done` / `Dropped` / `Superseded`)带提醒, 词表校验单点 import(表外值直接拒绝)。

`_index.md` 是**生成物**(与 `tasks/_index.md` 同款): 按状态分区, 每行 = `类型 · 简述 · 报告链接`, 顶部有 Open 状态的按类型计数表。**不要手改它** —— 多个工作区并行时手改必然冲突, 冲突的解法是重跑
`commands run kb.index`, 不是人工合并两版文本。
文件名合规(含合法 type)与状态取值由生成器守卫, 不合规直接报错退出。

## 修一条 issue 时

1. 确认它已成为某次计划的一部分(**用户指派**, 或用户已批准的计划认领)。❗**Agent 不得自行认领**
   "我提议认领 → 用户说继续"不算指派, 那样入池和认领都是越界;
   没认领就改代码 = 越界, 没认领就置 `In Progress` 同样是越界。用户没指派时, 正确动作是把
   issue 留在 `Open`, 在回复里说明"要不要认领 / 什么时候修", 等一句明确的话。
2. 开工置 `In Progress`(`commands run kb.status <件> "In Progress"`), 先**复验**(防过期原则第 5 条)。
3. **填认领链反向声明**: 认领方(任务档案/计划)会在它的 `Refs` 里列本 issue —— 本件同步把 head 的
   `doc-refs` meta 填上认领方路径(仓库根相对路径, 多目标英文逗号)。缺了就是单向链, 提交闸门
   `gen_doc_map --check` 判红; 协议单点见 [doc-forms「认领链」](../../../memory-bank/conventions/doc-forms.md)。
4. 修完置 `Done`(`commands run kb.status <件> "Done"`), 在报告里补"实际修法 / 验证方式 / 测试数字"; 与"建议修法"不同则保留建议原文并说明改道原因。
5. 按 `memory-bank` skill 的收尾 DoD 跑测试、回写 `memory-bank/` 主题文档; 需要时同步更新报告正文。
6. 索引随 `kb.status` 自动重建; 若另手改过报告的标题 / 摘要 meta, 跑 `commands run kb.index` 让索引行同步。

## 可移植性(换项目怎么用)

**随整套 memory bank 搬走**(2026-11-07 D2 拍板, 不再单飞): 本 skill 的脚本 / 常量 / 模板已并入
memory-bank skill, 换项目时把 `.agents/skills/memory-bank/`(连带本 skill)与 `memory-bank/` 库一起带走,
步骤见 [memory-bank skill references/PORTING.md](../memory-bank/references/PORTING.md)。
issues 目录固定 `memory-bank/issues`, 独立 `--dir` / `--root` / `--project` 参数随 new_issue.py 退役;
类型枚举等常量单点在 memory-bank skill `scripts/_common.py`。

## 反模式

- ❌ 报告只写"XX 有问题" —— 没有证据和位置等于没记, 下次还得重查。
- ❌ 把猜测当根因写死 —— 后续会沿着错误结论修。
- ❌ 为填满字段去读代码 —— 分析会过期(见防过期原则), 且违背"入池不改码"的初衷。
- ❌ 轻问题走标准档 —— 文档漂移写 7 段是纯浪费。
- ❌ 文件名 / 时间戳凭记忆编 —— 必然与真实时间不符, 且与别的文件撞序(走 `kb.new issue` 由命令派生)。
- ❌ 手改 `_index.md` —— 生成物, 重跑 `commands run kb.index` 即可。
- ❌ 手工改状态(只改 meta 不改封面徽标, 或反之) —— 两处漂移, 人读的和脚本读的不一致;
  翻状态一律 `commands run kb.status`, 两处 + 日志行 + 索引一条命令跑齐。
- ❌ 认领 issue 后不填 `doc-refs` —— 认领方的 `Refs` 列了本件就是单向链, 提交闸门判红(见「修一条 issue 时」第 3 步)。
- ❌ 把大改造塞进 issues —— 那该是 `tasks/` 档案或 `memory-bank/plans/` 计划。
