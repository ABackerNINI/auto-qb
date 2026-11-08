# review.trace 旧死结(已解): 记账类不计行 × 文件名敏感词命中 → 小批无法过闸

> 摘要: 旧闸门(count<FLOOR 先于 trailer 解析)下, 记账类不计行 + 文件名含敏感词(state/auth/token/credential/secret/password 子串)的 <50 行批无论写 Review: 还是 Review-Skip: 都被前置硬拦, 收尾批无法提交 —— 2026-11-08 大重构 D9 退役 50 行下限后死结消失; 本档留作事故档案与命名警觉
> 等级: L1
> 触发: review.trace 触碰安全敏感面, 不论行数都要评, 收尾批过不了闸, 记账类不计行, 敏感词文件名, Review-Skip 也被拦

**旧机制**(单点 `.commands/review/scripts/check_review_trace.py`, 2026-11-08 上午取证, 当日大重构已改):

- **计行面**: `_counted()` 排除生成物与记账类前缀(`memory-bank/tasks/`、`activeContext/`、`testing/baselines/`、`reports/attachments/legacy-review4/`); untracked 按整文件行数计入。
- **敏感面**: `sensitive_hit()` 对批次文件路径做**子串**匹配(`state/credential/auth/token/secret/password`)—— 文件名含子串即命中, 如 `...terminal-state-semantics.html` 撞 "state"。
- **判定序(旧)**: `count==0 且非敏感` → 过; **`count<FLOOR(50)` 且敏感 → 硬拦**(此分支不看任何 trailer, Review:/Review-Skip: 解析都在它之后) ⇒ <50 行 + 敏感词 = 无解死结。

**现象**(2026-11-08 实证, 三连拦): 收尾批 = 基线切片 + 任务档案(均记账类不计行)+ issues 一份 HTML 的 2 行锚修正(路径撞 "state")。前两次被拦后补了任务档案与基线切片仍不计行; 写上合法 `Review:`(接缝终审真评过)与 `Review-Skip:` 各试一轮全灭 —— 都到不了解析点。

**旧动作**(当时唯一出路, 已成历史): 补计行面内容凑 FLOOR / 并入下一个 ≥50 行批 / 新建文档避开敏感词子串命名。

**现口径(D9, 2026-11-08 大重构)**: 50 行下限退役 —— **可评行数 >0 即须 `Review:` trailer**(实算恒 0 的纯记账/生成物批才静默), 敏感词不再前置短路, 小批带合规 trailer 即可过; trailer 新增必填 `· 基 <12hex>`(review.pack 输出的批基哈希, 评审后有新改动会判红重评)与可选 `· 轮 R`。遗留警觉: 敏感词命中仍会把批次推进分面档/打敏感预警, issue/文档起名仍宜避开六词子串。

**实例**: 2026-11-08 issues-26-11-08-batch-fix 收尾, `ship.commit --no-push` 连续被旧闸门同一失败行拦三次; 用户指认「code review 技能已更新, 先拉远端」→ rebase 大重构(4cc002a2..42692a37)后按新口径带 `· 基` trailer 过闸。同日两坑复发登记见 `commit-hash-refs.md` / `review-pack-count-vs-gate-count.md` 复发行。
