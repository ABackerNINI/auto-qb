# 3172 —— kb.nav Esc 退栈计划出厂 (纯文档轮, 代码零改动)

> 摘要: 纯文档轮 —— 计划件 `plans/26-10-13-0324-plan-kb-nav-esc.html` (Open, 待拍板) + 任务档案 + 坑档条 + activeContext 切片; nav_page.html / test_kb_nav.py 零改动, 全绿即基线.
> 基线时间: 2026-10-13 03:43

## 验收数字

- `test.full`: **3172 passed + 4 skipped** / `TOTAL 16750 159 5702 140 99%`.
- 耗时: **48.6s** (本机并行默认).
- Linux 侧未重测 (纯文档轮, 改动为平台无关的 markdown/HTML).

## 本波改动面

- 新增: `memory-bank/plans/26-10-13-0324-plan-kb-nav-esc.html` (doc-status Open) · `memory-bank/tasks/26-10-13-memory-bank-kb-nav-esc.md` (Open) · 基线切片 (本份).
- 回写: `memory-bank/activeContext/26-10-04-0952-kb-nav-page.md` (第十六跟进轮) · `memory-bank/pitfalls/web-ui/overlays.md` (全屏遮罩 dismiss 条 + Refs 合并) · `kb.index` 21 生成物重建.
- 代码零改动 —— 实施 (nav_page.html 链 + 守阵 +4) 待拍板四拍点, 属子任务 3.

## 已知偏差 / 移交

- 纯文档轮: 守阵集合不变 (nav_page.html / test_kb_nav.py 零改动); 数字差异看差值 `commands run kb.baseline -n 2` 现列.
- 计划待拍板: 四拍点 P1-P4 见 plan §04; 实施后此档案子任务 3/4 推进.
