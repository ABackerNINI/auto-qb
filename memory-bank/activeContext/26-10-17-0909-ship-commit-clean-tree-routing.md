# ship-commit-clean-tree-routing — 树净拒跑按远端真值分流 / 核 ref 假红不再自相矛盾

> 摘要: 用户转述另一会话现场「`ship.commit` 首跑 提交成功但报『没有可提交的改动』并中止推送」→ 分析原因 → 「按建议修」→「提交」。根因 = **两次调用被读成一跑**: 首次 `ship.commit` 因同步/推送失败停在「提交成功 <hash>(未推送)」, 随后**又跑 `ship.commit`(而非 `ship.push`)** ⇒ 树已净 ⇒ 撞 `resolve_stage_plan` 的树净拒跑出口(该出口在 commit/sync/push 之前 `return 1`)。旧拒跑文案「工作区干净(改动在别的 clone 或未保存?)」在「提交已在本地、只差推送」时为错误归因; 核 ref 假红出口在**已判定落稳**时仍写「提交可能没落稳」, 两处合起来诱导重跑 `ship.commit`。落盘: ①`commit.py` 新增 `clean_tree_route(cfg)` —— 树净拒跑行按**远端现查真值**(`ls-remote`, `attempts=1`)三档分流(本地领先 → 直送 `ship.push`; 一致 → 确实无事可做; 取不到 → 如实说「无法核实」并摆两条出路); ②核 ref 假红出口去掉自相矛盾(保留 rc=1 与「提交失败」前缀 —— ref 不一致仍可能是分支指针真被回退, 不改写成假装成功), 结果行如实写「提交已落稳, 仅分支 ref 未核对通过」+ 直送补推; ③`sync.py::remote_sha` 加 `attempts` 形参(旁证查询收紧到 1)。变更集 3 个源文件 ⇒ 已立档 `memory-bank/tasks/26-10-17-ship-commit-clean-tree-routing.md`; 坑档 `pitfalls/git/push.md` 已增条目。测试数字见基线切片。**已完结**。
> 最后活动: 2026-10-17 09:09

**Refs:** memory-bank/tasks/26-10-17-ship-commit-clean-tree-routing.md,memory-bank/testing/baselines/26-10-17-0909-ship-commit-clean-tree-routing.md

## 结论与决策

- **根因定性**: 不存在内部幂等步骤 —— 「提交成功」与「没有可提交的改动」逻辑上不可能同出一跑(拒跑出口在 `git commit` 之前)。现场是**两跑**: 提交已在首次落稳于本地, 第二次跑错了命令(`ship.commit` 而非 `ship.push`)。
- **修复不猜**: 树净有两种真相, 必须现查 `ls-remote`(`refs/remotes/*` 写入本环境被静默丢弃、`status -sb` 是快照, 皆不可信)。
- **有意偏离建议②**: 不把已落稳改写成「提交成功(未推送)」语义 —— ref 三处不一致含「分支指针真被回退」一档, 假装成功会放行推送一个可能被回退的指针; 改为保留 rc=1 + 去掉自相矛盾 + 直送 `ship.push`。

## 下一步

- 无(本专题完结)。后续若再现同类误读, 先看 `pitfalls/git/push.md` 新条目。
