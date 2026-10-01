# 基线 · 2143 passed + 3 skipped / 96% —— issue 清偿路线图 v2 改版收尾(纯文档)

> 摘要: plans/26-10-01-1758 v2 同文件改版(未决 31→59 条重排九波) + tasks 新档案 + activeContext 切片更新 + 索引重建后的收尾基线; 全程零代码变更。
> 档案: [tasks/26-10-02-memory-bank-issue-clearance-roadmap.md](../../tasks/26-10-02-memory-bank-issue-clearance-roadmap.md)。
> 基线时间: 2026-10-02 02:54, develop @ 29f1841a; 工作树含本轮文档回写(未提交, 待用户指令)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2143 passed + 3 skipped / 96%**(13,280 语句 / 396 未覆盖 / 4,444 分支 / 170 partial,
test.full 28.8s, rc=0; 综合口径 96.46%, 阈值 94%)。相对 P1 基线(26-10-02-0203: 13,378 语句,
96.49%)语句分母 -98 —— 差异来自 P1 基线在**未提交工作树**上实测、本基线在**提交后 HEAD** 上实测,
产品代码面无变化, 非回归。

## 本轮闸门过程记录(三跑两修)

- **首跑 2 failed → 已修**:
  ①`test_docs_forms::test_claim_chain_is_bidirectional` —— 新档案 `**Refs:**` 写成 markdown 链接,
  守阵要求**仓库根相对纯路径**(逗号分隔), 已改 `**Refs:** memory-bank/plans/26-10-01-1758-...html` 后绿。
  ②`test_no_ghost_pkg_dirs::test_src_has_no_ghost_pkg_dirs` —— `src/auto_qb/core/mixins/` 幽灵包目录
  (只剩 `__pycache__`, pyc 日期 Sep 30)再现有二: 02:21 被本 clone 外部动作恢复出来(P1 收尾时段, 非本轮),
  守阵处置=整目录删除, 删除后两轮全量**未再生**(tests 里仅 test_logging/test_notify 以字符串引用该包名,
  无真实 import)—— 已记 issue 26-10-01-1946 标 Done 后复发, 待用户决定是否重开。
- **次跑 1 failed → 判 flaky 未动**: `test_hr_service.py::test_budget_unit_wait_and_caps` 在 xdist 全量下
  偶发, 单跑与整文件(77 passed)均绿 —— 时序敏感(覆盖提升 P1 T1.1 新增的 _Budget 等待记账断言),
  与已记 throttle/mainloop sleep 容差族同族。计划外缺陷, 按范围守恒不改码、未入池(入池需用户确认)。
- **末跑全绿**: 2143+3 / 96.46%, rc=0。

## 本轮改动面(全部 memory-bank/ 文档, 零代码)

- `plans/26-10-01-1758-plan-issue-clearance-roadmap.html`: v2 改版(doc-updated → 26-10-02-0234,
  变更记录补 v2 行, doc-refs 增挂新档案)。
- `tasks/26-10-02-memory-bank-issue-clearance-roadmap.md`: 新立滚动档案(v1 会话缺档补上)。
- `activeContext/26-10-01-1758-issue-clearance-roadmap.md`: 同 slug 蒸馏更新。
- `tasks/_index.md`: kb.index 重生成; plans/issues 索引重生成后无内容变化。
