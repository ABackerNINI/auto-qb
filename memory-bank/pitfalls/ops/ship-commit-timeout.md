# ship.commit 大批撞引擎 600s 超时: 提交落库后被杀在推送段

> 摘要: ship.commit 大批撞引擎 600s 超时: 提交落库后被杀在推送段
> 触发: ship.commit 超时, 卡住的命令, 提交被杀, 推送未完成, 补推前先补验

## 本篇只回答

ship.commit 被引擎 600s 超时杀掉后(输出只有 `[FAIL] ship.commit 超时(600s) —— 卡住的命令: ...commit.py`)怎么安全收场 —— 提交可能已落库、复跑闸门可能没跑完, 盲推或盲目重跑都不对。

### ship.commit 带代码批时长批在两轮闸门上, 引擎 600s 默认超时把 commit.py 杀在推送段附近

- **触发**: 改动含包代码(闸门展开 test.pkg ~110s + test.quick ~30s, commit 后若分叉 rebase 合入远端则 6b **复跑一轮**再翻倍), 机器还有余温(刚跑过全量测试)时, 全程可超引擎 task 默认 600s。纯文档批无此风险(实测 23.7s)。
- **判别**: 引擎行 `[FAIL] ship.commit 超时(600s) —— 卡住的命令: ...commit.py`。随即核实四件事: `git log -1`(提交落了没) / `git status --porcelain`(消息文件是否已消费、有无 index.lock) / `git ls-remote origin develop`(远端真值, **别信本地 refs/remotes**) / `commands run my-commit-flow.verify-ref`(三处一致)。实测案例(2026-11-07): 提交已落库且 rebase 重放到远端 tip 之上、ref 三处一致、远端落后本地一笔 = 死在推送段。
- **处置**: ①提交已落库 → **直送 `commands run ship.push`**(commit.py 自身指引; 不要重跑 ship.commit —— 那会再烧一轮闸门); ②但被杀时点未知 = **6b 复跑闸门是否跑完无法证实**, 盲推会跳过「合并后的树才算数」—— 补推前先补验两道重闸门: `commands run test.pkg` + `commands run test.quick`(合并后的树, 树净), 全绿再补推; ③提交没落库 → 树净后直接重跑 ship.commit(机器空闲时 ~400s 内可完成)。
- **守阵**: 暂无机检 —— 引擎超时是配置面(`commands run <task>` 默认 600s), 若复踩频繁, 入池议题: 给 my-commit-flow 提交类 task 配置更长 timeout(改动面在引擎/包配置, 不属本次顺手改)。
