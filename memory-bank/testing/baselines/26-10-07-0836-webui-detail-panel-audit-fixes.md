# 基线切片 26-10-07-0836 — 详情面板变体审计修复轮收尾(8 笔提交)

> 摘要: 专题 webui-detail-panel-audit-fixes 收尾 —— 按摸排报告 26-10-07-0542 的修复顺序,
> 8 个子任务串行完成 8 笔提交(`9726b12f..2367555d`), 修复 Q1-Q4 + P2×3 + P3-4..P3-7
> (P3-8 重复代码重构属重构批次未做)。Python 产品代码零改动(全部改动在 WebUI 静态 JS/CSS
> 与 test_web.py 守阵)。
> 基线时间: 2026-10-07 08:36
**Refs:** memory-bank/tasks/26-10-07-webui-detail-panel-audit-fixes.md

- 分支: feat/webui-detail-panel-audit-fixes @ `2367555d`(工作树含本轮收尾回写的未提交改动)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2712 passed + 4 skipped, 52.13s, 覆盖率 TOTAL 99%**
  (16061 语句 / 163 未覆盖 / 5496 分支 / 143 partial; 门槛 98% 达标)
- 相对上基线 (26-10-07-0548: 2705 passed + 4 skipped / 99% / 56.94s): passed **+7** =
  本轮 8 笔提交新增守阵 7 个测试函数(peek 换目标 / 渲染抛错回落 / 限宽纪律 / 字段行图标 /
  表格 scrollLeft 恢复 / a11y+fetch 错误态 / 跨种子折叠与选择器宽; 第 4 笔「去档位后缀」
  并入既有 registry wiring 守阵 +0), 与逐笔 test.quick 2706→2712 递增吻合。
- 语句 16061 与分支 5496 全同(零 Python 产品代码改动), 未覆盖 166→163 / partial 144→143
  属覆盖率采样噪声级(上基线同款差异), 无回归信号。
- 耗时 56.94s→52.13s 为单次采样波动(同机历史采样 34-57s 区间内), 按口径不更新区间结论。
