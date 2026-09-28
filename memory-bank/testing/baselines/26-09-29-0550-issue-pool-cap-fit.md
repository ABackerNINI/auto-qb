# 1735 passed / 4 skipped —— 收口中断 rebase + WEBUI 只读字段 issue 入池轮提交: cap-counting 超限修复

> 摘要: 上一会话把 interactive rebase 停在「pick 已解冲突但未 continue」状态 (develop 落后 Gitee
> 主线 11 笔), 本轮先完成 rebase(仅 `_doc-map.md` 生成物冲突, 重跑 `kb.index` 解决) ⇒ 落到 55a6b66 上;
> 随后 `test.full` 报 `memory-bank/pitfalls/kb/cap-counting.md` 6,121 > 6,000(pitfall 档) —— 该文件
> 上一轮追加「复发 3」时用 `read_text` 口径量得 5,997(误判为未超, 正是它自己记的坑)。处置: 压缩
> 「复发 1–4」的叙述性文字、保留全部判据与结论 ⇒ 6,121 → 5,501(余 499)。**未动 cap、未删判据**。
> 另注: `_doc-map.md` 恰好 12,400 == `index-auto` cap(余量 0, 本轮未动)。
> 基线时间: 2026-09-29 05:50(develop 与 Gitee 主线 55a6b66 齐平)

- test.full: **1735 passed / 4 skipped**, 23.3s, TOTAL **90%**(12422 语句 / 1032 未覆盖 / 4172 分支 / 409 partial)。
  较上一基线(26-09-29-0415, 1736/3, 12312 语句 / 1032 / 4172 / 409)−1 passed / +1 skipped, 语句 +110 而
  未覆盖·分支·partial 三列逐位一致 —— 本轮 `git diff 55a6b66..HEAD` 只有 6 个 KB/生成器文件、**无 src 变化**,
  该语句差未复现, 记为上一基线取数口径差异(待核)。
- 本轮改动: 纯 KB 文档与生成器文案(无业务代码) —— 两份 issue HTML 入池(26-09-28-1946 / 26-09-28-2135)、
  issues/_index 与 _doc-map 重建、gen_doc_map.py 头部文案、cap-counting.md 压缩与补一条真实复发。
- 中途: 收口中断 rebase 时 `_doc-map.md` 冲突(生成物) ⇒ 以 `kb.index` 重生成解决; `kb.check` 全程绿。
- 覆盖率口径见 [baseline.md](../../testing/baseline.md)。
