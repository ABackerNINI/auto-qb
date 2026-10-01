# 26-10-01-commands-shipflow-staged-delete-fix — issue 0128 清偿: commit.py 逐路径 add 撞已暂存删除

**Status:** Done
**Added:** 2026-10-01
**Updated:** 2026-10-01 18:50
**Summary:** 清偿 issue 26-09-28-0128(ship.commit 逐路径 git add 撞「已暂存删除」路径必败)。复验结论: 修复已随 my-commit-flow v3 重构(4ba6cb7f, 2026-09-28)落库 —— commit.py 暂存循环按文件存在性三分流(工作区有 → add; 无而索引有 → rm --cached; 都不在(已暂存删除) → 跳过), 入池给的 git rm --cached 方向成立且已实现; 本次补未暂存删除分支的守阵用例并走完 issue 清偿链(报告 Done + 坑条反写)。
**Topics:** commands-shipflow-issue-clearance
**Refs:** memory-bank/issues/26-09-28-0128-bug-my-commit-flow-staged-delete-add.html

> 背景关联(不进机器认领链): 修复随 my-commit-flow v3 落库, 见 tasks/26-09-28-commands-shipflow-output-contract.md「顺带修复」条; 本任务是 issue 清偿路线图(memory-bank/plans/26-10-01-1758-plan-issue-clearance-roadmap.html)W1 第 1 条。

## 原始请求

用户实施 issue 清偿路线图(memory-bank/plans/26-10-01-1758-plan-issue-clearance-roadmap.html)W1 波次第 1 条, 已显式授权实施 W1 且「每个 issue 修完后单独提交」。目标 issue: 26-09-28-0128 —— ship.commit 逐路径 add 对已暂存删除(`D `)路径 pathspec 落空直接 FAIL, 入池时给的方向是删除路径改 `git rm --cached` 口径, 认领时核对。要求: 认领链(档案 ↔ issue 双向登记)+ 修复 + 针对性单测 + issue 报告改 Done + 单独提交。

## 思考过程与决策

- **复验(2026-10-01 18:30)**: 入池锚点 `commit.py:162-167`(`for path in to_stage: git("add", "--", path)`)已不存在 —— v3 重写(commit 4ba6cb7f, 2026-09-28 03:21 落地)把暂存循环改成按文件存在性三分流, 现场 `.commands/my-commit-flow/scripts/commit.py:160-175`: 工作区存在 → `git add -- <path>`; 工作区无而索引有(ls-files 命中)→ `git rm --cached -- <path>`(未暂存删除的登记口径); 两处都不在(已暂存删除)→ 跳过(删除已在暂存区, add 本就无处匹配)。现象已消失。
- **入池方向核对**: 建议方向 A(删除路径改 `git rm --cached`)成立且已实现 —— 实际实现比方向 A 更精确: `D `(已暂存删除)连 `rm --cached` 都不必(索引已无条目, 跳过即幂等), 只有 ` D`(未暂存删除)才需要 `rm --cached` 把删除登记进暂存区; 方向 B(单路径 `add -A`)未采用。docstring 与 references/pipeline.md:56 均已注明修 issue 0128。
- **修复为何先于清偿落库**: 修复是随「commands 输出契约 v3」重构(档案 26-09-28-commands-shipflow-output-contract.md「顺带修复」条)在同一天落进代码的, 但 issue 报告的状态推进(复验行/修复后补充/Done)没有跟着走 —— 本次只补清偿链, 不再动修复代码(现场核对无缺陷)。
- **守阵补强决策**: v3 已带已暂存删除用例 `test_staged_delete_skips_add`(真实临时仓库, `git rm` 进暂存区, 断言提交成功且删除进提交); 三分流中「未暂存删除 → rm --cached」分支无直接用例, 本次补 `test_unstaged_delete_uses_rm_cached` 封住该分支(工作区 unlink 不暂存, 断言提交成功且删除经 rm --cached 登记)。

## 实现计划

- 档案认领(本文档)+ issue 报告 doc-refs 回指。
- 补守阵: `.commands/my-commit-flow/scripts/test_commit.py` 加未暂存删除分支用例, 同步文件头「## 测试计划」清单。
- 验证: `commands run test.pkg`(包脚本测试)→ `commands run test.quick`; 改动的 .py 过 `commands run dev.fmt`。
- 清偿: issue 报告徽标 + `<meta name="issue-status">` 改 Done, 状态变更日志补复验/修复两行, 修复后补充写实际修法与测试数字; 反写关联坑条 `pitfalls/git/ship-commit-staged-delete.md` 处置段(「本轮未动脚本」已过时); `commands run kb.index`。
- 单独提交: gitmoji 🐛 + 中文首行, 消息入 `.git/COMMIT_MSG_AI.txt` 后 `commands run ship.commit`。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 复验锚点(现场代码核对) | ✅ 完成 | 旧锚点已不存在, 分流实现见 commit.py:160-175 |
| 认领档案(查重 + 新建 + Refs) | ✅ 完成 | 跨工作区查重无撞名; issue 报告回指本文档 |
| 补未暂存删除守阵用例 | ✅ 完成 | test_commit.py::test_unstaged_delete_uses_rm_cached |
| test.pkg + test.quick | ✅ 完成 | test.pkg 75 passed / test.quick 1909 passed + 3 skipped(收尾后全绿) |
| issue 报告 Done + 坑条反写 + kb.index | ✅ 完成 | 徽标+meta+状态日志+复验+修复后补充+doc-refs 回指; 坑条处置段反写 |
| 单独提交(ship.commit) | ✅ 完成 | hash 见进度日志末条 |

## 进度日志

- **2026-10-01 18:30** 同步成功 6f474098(工作区净)。读 issue 报告/pitfalls 索引/memory-bank SKILL/现场代码: 确认修复已随 4ba6cb7f 落库、测试已有已暂存删除用例、认领链未闭合(报告仍 Open、无复验行)。跨工作区查重(本 clone + ../auto-qb-*)无同名 slug, 建本档案。
- **2026-10-01 18:35** 补守阵 `test_unstaged_delete_uses_rm_cached`(工作区 unlink 不暂存 → rm --cached 登记删除), 同步 test_commit.py 头部测试计划; dev.fmt 过。test.pkg **75 passed**(20.70s, 含新用例)。
- **2026-10-01 18:40** issue 报告清偿: 徽标 + `<meta name="issue-status">` 改 Done, 状态变更日志补复验(In Progress)/清偿(Done)两行, 复验段写「已消失 + 与入池描述的出入」, 修复后补充写三分流实际修法与测试数字, 加 `<meta name="doc-refs">` 回指本档案; 反写坑条 `pitfalls/git/ship-commit-staged-delete.md` 处置段(workaround 标注为旧版口径, 根修已落 + 守阵指针)。首跑 test.quick 4 红(认领链双向守阵 1 + 索引未重建 3)全为立档→kb.index 间过渡态; **Refs 收敛**: 背景件(shipflow 档案/路线图计划)不进机器认领链, 只留 issue ↔ 档案双向, 避免为闭环连锁改历史件。
- **2026-10-01 18:50** 索引重建 + 全绿收口: `commands run kb.index` 重建(tasks/kb/docs 16 索引)后 issues/_index.md 仍挂 Open —— 发现 kb.index 任务定义(.commands/kb/config.toml 三条生成器)**不含 create-issue skill 的 gen_issues_index.py**, 直接跑该脚本后 0128 迁入 Done 分区(计划外缺陷, 本轮只记不改)。test.quick 复跑全绿: **1909 passed + 3 skipped**(21.08s; 6 warnings 为已入档的 starlette DeprecationWarning 在途观察, 非本轮引入)。
- **2026-10-01 18:55** 首跑 ship.commit 内部同步失败(远端新提交 0b422396 与本地 tasks/_index.md 生成物重叠)→ stash -u → sync(rebase 合流, **同步成功 0b422396**)→ stash pop 无冲突 → 重跑 gen_tasks_index/gen_issues_index 保证生成物与新基线一致 → test.quick 复跑全绿 **1909 passed + 3 skipped**(21.33s)。重跑 ship.commit 提交 —— 本档案随该提交入库, hash 以提交输出为准不预写。
