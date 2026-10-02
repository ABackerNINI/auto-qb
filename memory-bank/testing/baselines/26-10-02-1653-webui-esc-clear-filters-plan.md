# 基线 · 2290 passed + 3 skipped / 99% —— ESC 清筛选兜底计划轮

> 摘要: 计划轮(生产代码零改动): issue 26-10-01-2108 混乱性分析 + 计划 plans/26-10-02-1632 + 立档 tasks/26-10-02-webui-esc-clear-filters。新增制品为 memory-bank 三件(计划 HTML / 档案 md / 切片 md), 触发认领链守阵(test_docs_forms)与档案守阵(test_memory_bank)对新增件的校验。档案: [tasks/26-10-02-webui-esc-clear-filters.md](../../tasks/26-10-02-webui-esc-clear-filters.md)。
> 基线时间: 2026-10-02 16:53, develop @ 6ea89ff4(收尾回写未提交工作树, test.full 实测)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2290 passed + 3 skipped / 99%**(13,349 语句 / 86 未覆盖 / 4,436 分支 / 81 partial,
test.full 35.18s, rc=0)。
相对上一切片(26-10-02-1631: 2290 passed + 3 skipped / 99%)**全持平** —— 本轮未动 src/ 与
tests/, 数字相同属预期。首跑曾红两次, 均守阵按设计命中: ①计划 doc-status 写了词表外
"Proposed"(5 词表只认 Open/In Progress/Done/Dropped/Superseded) → 改 Open; ②改完未重建
索引 → test_docs_index_is_regenerated 红, kb.index 后转绿。
