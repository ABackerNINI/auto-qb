# 5195 —— flux全浮层玻璃化+遮罩浓度修复入库前全量

> 摘要: flux全浮层玻璃化+遮罩浓度修复入库前全量
> 基线时间: 2026-11-05 00:23
**Refs:** memory-bank/tasks/26-11-04-webui-flux-glass-popups.md

## 验收数字

- `commands run test.full` 实测(2026-11-05 00:23): **5195 passed + 10 skipped**
- 覆盖率 TOTAL 表(誊写): 24404 stmts / 228 miss / 8356 branches / 171 partial / **99%**
- 口径注记: 中途两轮红均为本轮 KB 回写自身所致(任务档案手抄「5195 passed」→ 措辞守阵族 B 冻结常数 394 溢出 +1; 改「见 kb.baseline」后清零), 非源码回归; 终态全绿如上。

## 本改动面

- `src/auto_qb/webui/static/flux/css/components.css`: 全浮层玻璃化 4 处(.col-menu/.pop-menu、.ctx-menu、.ctx-sub、.ce-chart-tip 改半透明 --bg-card + blur)+ `.modal-mask` 遮罩 .72→.5(本文件恰 700 行卡满, 新声明内联零净增行)
- `src/auto_qb/webui/static/flux/css/dialogs.css`: 玻璃化 7 处(.hr-full-modal/.add-drop-box/.speed-pop/.hr-pop/.hp-arrow/.hb-pop 覆盖/共用层 :is() 组含 .relc-pop)+ 遮罩两处降浓(.hr-full-mask .72→.5、.add-drop-mask .62→.5)
- `src/auto_qb/webui/static/flux/css/views.css`: `.hist-tip` 玻璃化
- `tests/webui_static_scan_common.py`: `_FLUX_BACKDROP_BUDGET` 4→16(全浮层玻璃化显式改预算+红绿双验)
- `tests/webui_static_scan_css.py`: `_scan_flux_modal_frost` ④ 清单反转(玻璃化浮层族双份 blur 钉 + .col-ghost 反向钉 + 共用层覆盖组逐成员锚定)+ ⑥ 遮罩 alpha ≤ .6 三处钉
- `tests/webui_static_scan_js.py`: 第 22 项 docstring 口径同步
- `tests/test_webui_relocate_chain.py`: 补 flux 侧 .relc-pop 玻璃化覆盖断言(+import re)
- `memory-bank/`: tasks/26-11-04-webui-flux-glass-popups.md 新档; pitfalls/web-ui/glass-visibility-mask-stacking.md 新坑; conventions/webui.md 令牌分工段+flux 段口径反转回写; 本切片
