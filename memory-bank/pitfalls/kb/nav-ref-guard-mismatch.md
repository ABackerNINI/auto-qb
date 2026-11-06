# 认领链「未入库」多半不是丢件: 导航层判据必须与 kb.check 对齐

> 摘要: 认领链「未入库」多半不是丢件: 导航层判据必须与 kb.check 对齐
> 触发: 未入库,认领链死链,关系图悬空,ref 判据不一致,归档回退,仓库根相对
**Refs:** memory-bank/tasks/26-11-07-memory-bank-nav-relation-graph.md

## 本篇只回答

导航页 / 关系图把一条 ref 判成「失效 / 未入库」时, 到底是件丢了还是判据漏了 —— 以及为什么这个判据必须跟 `gen_doc_map.check_claim_chain` 同源。

### 导航层自己写一套 ref 判据, 579 条边会假死

- **触发**: 在 `kb.nav` 之外的任何消费方重新实现"ref 指向的文件在不在", 尤其是只按 `memory-bank/` 相对路径判、或漏掉归档回退的时候。本次实测 (2026-11-07): 1812 条 ref 里 579 条被判死 —— 324 条其实是库内非台账件 (坑档 / 基线切片 / 进度件), 253 条是基线外迁进 `testing/baselines/attachments/` 后声明方没跟着改, 2 条是仓库根相对 (`resources/*.html`, 不带 `memory-bank/` 前缀)。真失效 0 条。
- **判别**: 页面/图里出现「(未入库)」「失效」而 `kb.check` 是绿的 —— 守卫绿 ≠ 页面可点, 两个判据已经分家。反向信号: 同一批 ref 里"死链"全是 `pitfalls/` `testing/` `resources/` 开头的路径。
- **处置**: 判据按 `check_claim_chain` 原样抄, 三条缺一不可 —— ① ref 是**仓库根相对**路径 (`root / ref`), 不是 memory-bank 相对; ② 归档回退**只对 `memory-bank/testing/baselines/` 开头的 ref** 生效, 否则台账件被删而同名切片还在时会把真死链说成可打开; ③ resolve 后必须仍在 `memory-bank/` 内 (穿越路径 `memory-bank/../config.yml` 判死), 仓库根命中还要挡掉 `config.yml` / `auto-qb-data/` / `.git` 这类红线。导航层只做**解析与展示**, 不扩 `collect()` 的扫描面 (那是 `kb.docmap` / `kb.check` / 索引生成的共同单点)。
- **守阵**: `tests/test_kb_nav_data.py::test_collect_nav_targets_four_states` 与 `::test_collect_nav_target_guardrails` (非 baselines 前缀不得回退 + 穿越路径判死)。
- **复发**: 0
