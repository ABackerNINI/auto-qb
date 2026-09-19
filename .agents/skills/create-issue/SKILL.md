---
name: create-issue
description: '计划外问题入池: 在 memory-bank/issues/ 生成 HTML 详细报告并在 _index.md 登记状态+日期+简述。USE FOR: 需要把一个暂时不修的问题记成别人能直接开工的详细报告; 用户说"记个 issue"/"这个问题先记下来"/"创建 issue"/"入池"/"更新 issue 状态"/"issue 修完了"/"issues 索引重建" 时。DO NOT USE FOR: 本次计划内的缺陷 (直接修)、纯答疑、代码评审清单。判断"该不该现在修"见 scope-guard skill; 本 skill 只负责记。'
user-invocable: true
---

# Issue 报告 (memory-bank/issues)

把"暂时不修的问题"变成一份**别人不用重新调查就能开工**的报告, 并在索引里留一条 `状态 · 日期 · 简述 · 链接`。

- 什么该入池、什么该当场修 → 见 [scope-guard skill](../scope-guard/SKILL.md)。
- 本 skill 只负责**记录与状态流转**, 不负责判断修不修。

## 新建一条 issue (3 步)

### 1. 取当前时间(必须命令取, 禁止凭记忆)

```bash
date +"%y-%m-%d-%H%M"                 # git bash / Linux / macOS → 26-09-19-1808
Get-Date -Format "yy-MM-dd-HHmm"      # PowerShell
```

下面第 2 步的脚本会自己取时间, 但仍要**先跑一次**确认取值合理(系统时间明显不对时人工纠正)。

### 2. 生成报告

```bash
python .agents/skills/create-issue/scripts/new_issue.py <slug> \
  --title "中文标题" --summary "一句话简述(进索引)" --module "webui"
```

- `<slug>`: 英文短横线, `<领域>-<专题>`, 领域枚举复用 `webui` / `backend` / `rule` / `memory-bank` / `docs` / `test` / `deps` / `config`(不够用先扩枚举再建档)。
- 产出 `memory-bank/issues/<时间>-<slug>.html`, 例 `26-09-19-1808-webui-cols-drift.html`; 模板见 `assets/issue-template.html`, 脚本已填好 meta 与封面。
- 脚本随后**自动重建 `_index.md`** 并打印路径; 文件已存在则报错退出, 不覆盖。

### 3. 填正文(这是入池的价值所在)

脚本只填封面。必须接着把正文填成别人能直接开工的程度, 至少覆盖:

- **现象与发现场景**: 怎么撞见的(哪个任务/哪条命令/哪个文件), 触发条件。
- **证据**: 具体文件与行号、日志/报错原文、最小复现步骤 —— **贴原文, 不要转述**。
- **影响面与严重度**: 谁会踩、频率、是否数据风险。
- **根因(初步判断)**: 有结论写结论; 没结论写"待查"并列出已排除的假设 —— **不要把猜测写成结论**。
- **建议修法**: 方向 + 候选方案 + 各自代价; **不要在这里实施**。
- **涉及文件清单**: 预计会动哪些文件(供后续跨计划冲突判断)。
- **状态变更日志**: 每次改状态追加一行 `- <日期> Open → In Progress (by 谁/哪个计划)`。

## 状态机

状态写在报告 HTML 的**封面状态徽标**(`<span class="badge">`)与 `<head>` 的 `<meta name="aqb-issue-status">`(**两处一起改**, 索引只读 meta), 取值仅五种:

| 状态 | 含义 |
|---|---|
| `Open` | 未修, 待排期(新建默认) |
| `In Progress` | 已被某个计划认领, 正在修 |
| `Fixed` | 已修并验证(写清验证方式与测试数字) |
| `WontFix` | 决定不修(必须写明理由) |
| `Duplicate` | 与既有 issue 重复(写明指向哪一条) |

改状态的唯一流程: **改 HTML 的两处状态 → 追加一行状态变更日志 → 重建索引**:

```bash
python .agents/skills/create-issue/scripts/gen_issues_index.py         # 重建
python .agents/skills/create-issue/scripts/gen_issues_index.py --check # 只比对(供守卫/CI 用)
```

`memory-bank/issues/_index.md` 是**生成物**(与 `tasks/_index.md` 同款): 每行 = `状态 · 日期 · 简述 · 报告链接`, 分区按状态、区内按报告时间倒序。**不要手改它** —— 多个 worktree 并行时手改必然冲突, 冲突的解法是重跑脚本, 不是人工合并两版文本。

## 修一条 issue 时

1. 确认它已成为某次计划的一部分(用户指派, 或你开了新计划认领); 没认领就改代码 = 越界。
2. 开工置 `In Progress` 并重建索引。
3. 修完置 `Fixed`, 在报告里补"实际修法 / 验证方式 / 测试数字"; 与"建议修法"不同则保留建议原文并说明改道原因。
4. 按 `memory-bank` skill 的收尾 DoD 跑测试、回写 `memory-bank/` 主题文档; 需要时同步更新报告正文。
5. 重建索引, 让 `_index.md` 反映新状态。

## 反模式

- ❌ 报告只写"XX 有问题" —— 没有证据和建议等于没记, 下次还得重查。
- ❌ 把猜测当根因写死 —— 后续会沿着错误结论修。
- ❌ 文件名/时间戳凭记忆编 —— 必然与真实时间不符, 且与别的文件撞序。
- ❌ 手改 `_index.md` —— 生成物, 重跑脚本即可。
- ❌ 只改 meta 不改封面徽标(或反之) —— 两处漂移, 人读的和脚本读的不一致。
