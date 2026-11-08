# review.pack 行数 ≠ review.trace 闸门实算(生成物排除口径)

> 摘要: review.pack 的 diff 统计与 review.trace 闸门实算口径不同(后者排除生成物面), 批内混有生成物时声明行数必不等 —— trailer 行数以 trace 失败行实数为准
> 触发: review.pack, review.trace, Review trailer, 声明行数, 实算, 生成物排除

**现象**: 把 `commands run review.pack` 输出的 diff 统计(+N/-M)直接抄进提交消息的 `Review: <N> 行` trailer,提交被 review.trace 拦:「声明 N 行 ≠ 实算 M 行」。两个机械面口径不同: review.pack 统计锚点→工作树**全部**已跟踪文件;review.trace 实算时**排除生成物面**(`gen_all.py --list` 清单,如 issues/_index.md、attachments/_archive.md 等),批次里混有生成物改动(常见:已推送合流件带着索引重建)时两者必不等。

**动作**: `Review:` trailer 的行数以 review.trace 失败行给出的实数为准(pack 值只作 400 行分档参考);首跑被拦时直接把失败行「可粘贴整行」里的实数誊进重跑,不要自己推算。批次含生成物时,可在消息正文注明「实算含/不含生成物面」避免读者困惑。

**实例**(2026-11-08, 0527-hr 任务): S1 批 pack 227 行 vs 闸门实算 169(差 58 = 已推送 7ddc6b57 合流件的 issues 索引生成物面);S4 批同型(补 2 行 docstring 后 190)。

- **复发 +3 (2026-11-08, issues-26-11-08-batch-fix)**: 同日三批各被拦一次(pack 118→gate 104 / 333→342 / 207→193;差值除生成物面外还有记账类排除与批次实算口径)。为什么没命中: 坑档存在但主会话开批时未先查 pitfalls, 仍按 pack 值预写 trailer; 处置面「以 trace 失败行实数为准」的流程本身有效, 三次均按失败行改数后过闸 —— 教训是**首个收尾批起就按 trace 实数写**, pack 值只作分档参考。
