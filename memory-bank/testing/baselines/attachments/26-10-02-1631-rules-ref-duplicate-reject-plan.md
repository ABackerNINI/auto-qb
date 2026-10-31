# 基线 · 2290 passed + 3 skipped / 99% —— 站点引用规则判重计划轮

> 摘要: 计划轮(生产代码零改动): 用途分析 + 计划 plans/26-10-02-1621 + 立档 tasks/26-10-02-backend-rules-ref-duplicate-reject。新增制品为 memory-bank 三件(计划 HTML / 档案 md / 切片 md), 触发认领链守阵(test_docs_forms)与档案守阵(test_memory_bank)对新增件的校验。档案: [tasks/26-10-02-backend-rules-ref-duplicate-reject.md](../../tasks/26-10-02-backend-rules-ref-duplicate-reject.md)。
> 基线时间: 2026-10-02 16:31, develop @ c02e9e14(收尾回写未提交工作树, test.full 实测)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2290 passed + 3 skipped / 99%**(13,251 语句 / 86 未覆盖 / 4,436 分支 / 81 partial,
test.full 29.40s, rc=0)。
相对上一切片(26-10-02-0707: 2290 passed + 3 skipped / 99%)**全持平** —— 本轮未动 src/ 与
tests/, 数字相同属预期; 首跑曾红 test_docs_forms 认领链(Refs 路径基准写错 + 计划侧缺
doc-refs 反向声明), 按守卫口径改为仓库根相对路径并双向声明后转绿 —— 守阵按设计命中。
