# 基线 · 1752 passed + 3 skipped —— 限速曲线预览图重构轮(webui-curve-chart)

> 摘要: WEBUI 限速曲线预览图重构: X 轴改按各档实际流量长度比例(取代 SPD-02 等宽), 末档按
> curves.py 语义显示为 ∞ 区占宽 ≤30%(单档独占全宽), 悬停按 SVG 实际渲染缩放换算(letterbox 安全),
> 删共享 console_hub.css 残留 `height:128px` 压扁规则。改动全部是前端静态文件
> (config_editor.js / settings-detail.html / 三主题 CSS / console_hub.css), Python 零触碰。
> 数字取自实施完成实测(`commands run test.full`; 提交前已按「先同步后提交」合并远端
> ui-switch-dropdown 两笔(3d0d1d2 + 5809bdd), 合并后复跑数字不变, 基线 origin/develop @ 5809bddd)。
> 基线时间: 2026-09-27 21:38 (22:2x 合并远端后复核)
> 档案: memory-bank/tasks/26-09-27-webui-curve-chart.md

- **测试增量**: 0(无新增 Python 测试; 前端无几何单测, 以浏览器模板实测 + 真实 JS 集成冒烟页
  `resources/curve-chart-smoke.html` 兜住, 压扁容器悬停回归用例在其中)。

TOTAL 1752 passed + 3 skipped / 91%(11730 语句 / 849 未覆盖 / 3940 分支 / 351 partial, test.full 18.2s)
对比前基线(26-09-27-2022): 1752 passed + 3 skipped / 91%(11730 语句 / 849 未覆盖) —— 全部持平, 零回归。
⚠ 首跑曾出 851 未覆盖/352 partial, 复跑稳定回 849/351 —— 并行 worker 的分支归属统计抖动, 以复跑值为准。
覆盖率口径见 [baseline.md](../../testing/baseline.md)。
