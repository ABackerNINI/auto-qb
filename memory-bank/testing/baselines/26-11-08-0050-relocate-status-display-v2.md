# 5635 passed + 2 skipped —— relocate-status-display-v2 S6 前半基线

> 摘要: relocate-status-display-v2 S6 前半基线
> 基线时间: 2026-11-08 00:50

## 验收数字

`commands run test.full` 实测 (2026-11-08, 命令整体 144.9s):

```text
TOTAL                                                25513      5   8802     27    99%
5635 passed, 2 skipped, 1 warning in 143.15s (0:02:23)
```

- 差值看上片: `commands run kb.baseline -n 2`。上一基线(relocate-retarget-real-file-guard) 5626 passed
  → 本片 5635 passed, **+9 passed**(迁移展示 v2 守阵: 浮窗调度/组装单测 + 组级聚合补 src 红验转绿 +
  chain:406 死断言改活断言), skipped 持平 2, 覆盖率 99% 持平(TOTAL 25505→25513 statements, +8)。

## 本改动面

迁移状态展示 v2(计划 S1-S5, 分支 relocate-status-display-v2, 59743c6b..5945b248):

- `src/auto_qb/webui/static/shared/decorate.js`: 行渲染替换 —— 撤 rel-badge 药丸, 改着色 A→B 两排 +
  右缘弧形箭头; S1 组级聚合补 src(去重唯一值口径)。
- `src/auto_qb/webui/static/shared/relocate_pop.js`(新增 156 行): 迁移悬停浮窗逻辑面 —— 照 hrPop 同参
  调度 + 行载荷零请求组装; `lifecycle.js` 加 ESC 收口; `tpl/popovers.html` 加浮窗锚。
- `tpl/xtpl-cells.html`: 迁移列单元格改零点击单点; `views_relocate.py` 指纹补 src(+5 行)。
- 四皮肤接线: `--path-src` 令牌入 prism tokens.css / atlas / console / flux, script 接线各 index.html;
  `row_lang.css` 浮窗 `.relpop-*` 定稿视觉(色条全出血/--path-src 固定标签/圆点 calc 自适应)。
- 测试面: `tests/test_webui_relocate_pop.py` 新增(浮窗调度+组装单测, 191 行); `test_webui_relocate_visibility.py`
  守阵 3 例红验转绿改写(+160 行); `test_webui_relocate_chain.py` chain:406 死断言改活断言(零点击+链入口
  只在 drawer); skins skin/widget 断言同步; `webui_static_scan_common.py` console 方角白名单入列(D12)。
- e2e views 36 绿; mockup 规格件入 `plans/attachments/relocate-status-display-v2-mockup.html`。
