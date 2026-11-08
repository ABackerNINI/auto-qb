# KB 引用的提交 hash 会被 rebase 打断悬空

> 摘要: KB(backtick / `<code>` / `commit <hash>` 语境)里记 feature 分支提交, 分支 rebase 并入 develop 后旧 hash 对象不可解析; 守卫(kb.check / test_docs_forms)不查可解析性, 静默累积。另: `git cat-file --batch-check` 只报存在性不报类型, 旧 commit 被 GC 后同前缀 blob/tree 会顶占前缀, 核对结果「时好时坏」。
> 触发: KB 里写 commit hash, rebase 合流, 悬空 hash, cat-file missing, 按图索骥找不到提交, hash 时好时坏

**Refs:** memory-bank/tasks/26-10-06-memory-bank-dangling-hash-refs.md

### KB 记录的 feature 分支 hash 在合流后悬空

- **触发**: 会话把提交 hash 写进档案 / progress / 计划, 之后该分支 rebase 并回 develop(issue 26-10-06-1904 取证 40 条, 2026-10-06)。
- **判别**: `git cat-file -t <hash>` 报 missing(或返回非 commit 类型), 读者按 hash 溯源失败; 守卫不红, 只能靠提取管线主动扫。
- **处置**: **写入时优选会存活的引用** —— 计划 / 档案 / issue 路径或 develop 上的最终 hash; 分支实施期的中间 hash 只在「重写事件叙事」里以平文出现(不带 backtick / `<code>`)。已悬空的按 commit message 考古映射到 develop 等价 commit(逐条核对 message 与叙述一致), 无等价的去 hash 保留叙述; 改完用提取管线复扫归零; 生成物索引(tasks/_index 等)不手改, 修完源头重跑 `commands run kb.index`。

### `git cat-file --batch-check` 只查存在性, 不查对象类型

- **触发**: 用 batch-check 批量核对 hash 可解析性(悬空 hash 清理管线 / 复扫)。
- **判别**: 输出列是 `<name> <type>`; 旧 commit 被 GC 后, 同前缀的 blob/tree 让 `<hash> blob` 混过 `missing` 过滤 —— 同一 hash 这次查「在」下次查「没」, 呈摇摆假象(09683720 实测)。
- **处置**: 过滤条件写「type != commit 即不可用」; 单条终验用 `git cat-file -t <hash>` 必须返回 commit。
