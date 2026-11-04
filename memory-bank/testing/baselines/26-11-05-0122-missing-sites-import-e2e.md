# TOTAL 24444 / 227 miss / 99%; 5205 passed, 10 skipped in 155.91s (test.full) —— 缺失站点导入三分支 e2e 回归补齐后全量基线

> 摘要: 缺失站点导入三分支 e2e 回归补齐后全量基线
> 基线时间: 2026-11-05 01:22
**Refs:** memory-bank/issues/26-11-04-2312-test-webui-sites-import-gui-smoke.html

## 验收数字

- `commands run test.full` 实测(2026-11-05 01:22, Windows 本机):
  - 覆盖率 TOTAL 表: **TOTAL 24444 / 227 miss / 99%**(statements 24444, missed 227, branch 8382, brMiss 167)
  - 汇总行: **5205 passed, 10 skipped in 155.91s (0:02:35)**
  - 口径: 全量 pytest 含覆盖率报表; 10 skipped 为平台条件跳过; 数字为该次运行实测, 非均化

## 本改动面

- `e2e/missing-sites-import.spec.mjs`(新增): 设置→站点「导入缺失站点」三分支 GUI 回归, `page.route('**/api/sites/missing')` 注入三形态载荷;
  断言分支选型(两钮/三钮)、按钮类(拆分 ghost)、默认焦点、Enter 默认合并、拆分逐域名、填入 pill 集合、全程零 `PUT /api/config`; prism/atlas 双皮肤各 4 条, 共 8 条。
  `commands run dev.e2e -- e2e/missing-sites-import.spec.mjs --retries=0` 实测 **8 passed (21.9s)**; 红绿双验两轮(临时改产品代码分别打红 6 条, 还原后复绿)。
- `memory-bank/testing/smoke.md`: spec 分工清单补 `missing-sites-import.spec`; 措辞由「按旧断言块拆分」改为「spec 分工」(该 spec 由 issue 驱动补齐, 非旧块拆分)。
- `memory-bank/issues/26-11-04-2312-test-webui-sites-import-gui-smoke.html`: 认领(In Progress) → 修复完成(Done), 补状态日志/复验/修复后补充。
- 产品代码零改动(`git diff src` 为空), 仅测试与文档。
