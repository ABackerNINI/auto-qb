# review.pack 行数 ≠ review.trace 闸门实算(生成物排除口径)—— 已根治(2026-11-11)

> 摘要: review.pack 的 diff 统计与 review.trace 闸门实算口径不同(后者排除生成物/记账面), 批内混有生成物时声明行数必不等 —— 2026-11-11 起已根治: 锚点与逐笔实算收编 review_content 单点, pack「评审规模」= 闸门实算恒同源, trailer 行数照 pack 抄即可
> 触发: review.pack, review.trace, Review trailer, 声明行数, 实算, 生成物排除

**现象**(根治前): 把 `commands run review.pack` 输出的 diff 统计(+N/-M)直接抄进提交消息的 `Review: <N> 行` trailer,提交被 review.trace 拦:「声明 N 行 ≠ 实算 M 行」。两个机械面口径不同: review.pack 统计锚点→工作树**全部**已跟踪文件 + 全量 untracked;review.trace 实算时**排除生成物/记账面**且走逐笔口径,批次里混有生成物/记账改动(常见:已推送合流件带着索引重建、收尾批的切片)时两者必不等。

**动作**(根治前绕行): `Review:` trailer 的行数以 review.trace 失败行给出的实数为准(pack 值只作 400 行分档参考);首跑被拦时直接把失败行「可粘贴整行」里的实数誊进重跑,不要自己推算。

**实例**(2026-11-08, 0527-hr 任务): S1 批 pack 227 行 vs 闸门实算 169(差 58 = 已推送 7ddc6b57 合流件的 issues 索引生成物面);S4 批同型(补 2 行 docstring 后 190)。

- **复发 +3 (2026-11-08, issues-26-11-08-batch-fix)**: 同日三批各被拦一次(pack 118→gate 104 / 333→342 / 207→193;差值除生成物面外还有记账类排除与批次实算口径)。为什么没命中: 坑档存在但主会话开批时未先查 pitfalls, 仍按 pack 值预写 trailer; 处置面「以 trace 失败行实数为准」的流程本身有效, 三次均按失败行改数后过闸 —— 教训是**首个收尾批起就按 trace 实数写**, pack 值只作分档参考。
- **复发 +1 (2026-11-11, 本审计批)**: 审计轮把该坑当「新发现」入报告(P1), 检索纪律没命中 —— `grep` 用词「评审规模/分档」, 坑档用词「diff 统计」; 直到收尾回写 grep「diff 统计」才撞见本档。根治后此绕行流程作废(保留作历史)。
- **根治 (2026-11-11, 任务 26-11-11-memory-bank-review-pack-count-alignment)**: 锚点与逐笔实算(anchor_commit/numstat_batch/untracked_batch)自闸门收编进 `review_content.py` 单点, pack 评审规模改走同一实现(排除面/锚点/实算/哈希四处一份实现), pack 只报「评审规模(闸门实算口径)」一个数、树差 shortstat 行删除; 未跟踪二进制改按 0 行计(旧 pack 按换行数虚计, 60k 行 blob 报 60009 行推分面档); `--base ≠ 闸门锚点` 打可见 [warn]。回归: test_review_pkg 7 条新用例(15 行金值/逐笔≠树差/记账排除面/二进制 0 行/excludesFile/--base≠锚点警告/unborn HEAD)。**现行动作: trailer 行数直接照 pack「评审规模」抄, 两个机械面恒一致。**
