# 4006 passed + 2 skipped(根) —— 设定位置对话框五修: 滚动条开关挂事实

> 摘要: 设定位置对话框五修: 滚动条开关挂事实
> 基线时间: 2026-10-29 02:49
**Refs:** memory-bank/tasks/26-10-29-webui-move-dialog-pick-geometry.md, memory-bank/pitfalls/web-ui/dialog-geometry-jump.md

## 验收数字

`commands run test.full` 实测输出:

- 汇总行: **4006 passed, 2 skipped in 195.31s (0:03:15)**
- TOTAL 表: `20981  98   7088   100    99%`(语句 / missed / 分支 / partial / 覆盖率)
- 覆盖率门槛 99% 达标, 无 FAIL 行; 零失败零回归
- e2e 单跑(`commands run dev.e2e -- move-dialog-fit`, 双皮肤 × 3 用例): **6 passed (20.0s)**
  - 开层全过程: 面板存在的每一帧 `overflowY` 恒 **hidden**、滚动条占位宽恒 **0**
  - 收层全过程(离场淡出期面板仍在 DOM): 同样恒 **hidden** / **0**; 面板真被移除后回到 **auto**
  - 收层期实测溢出序列(修前) **0 → 73 → 139 → 184 → 212 → 229 → 241 → 249 → 254**, 修后同段 `overflowY` 恒 hidden
  - 终态几何不变: 对话框 515px、下缘 785 < 900、面板底缘在 body 底沿之上 12px
- e2e `@fast` 全量: **220 passed (7.8m)**

口径注记: passed/skipped/覆盖率数字由 agent 从本次实测输出誊写; 相对上基线的逐位对比不写(看差值 `commands run kb.baseline -n 2`)。

## 本改动面

用户报障「下拉框消失时弹窗仍会有一瞬间出现滚动条」的落点, 3 个源文件 + 2 个测试件:

- `src/auto_qb/webui/static/{atlas,console,prism}/css/dialogs.css` —— 三皮肤成对: `.pop-open .add-dialog-body` 只留 `padding-bottom: 272px`; 滚动条开关改挂**事实** —— 新增 `.modal.move-dialog:has(.add-pop) .add-dialog-body { overflow: hidden }`(面板在 DOM 期间(含离场淡出 ~120ms)关掉 body 滚动, 面板真移除后自动回 `auto`), 注释补五修口径
- `tests/test_webui_static_dom_panel.py` —— 静态断言由「`.pop-open` 规则同时含 padding 与 overflow」改为「`.move-dialog:has(.add-pop) .add-dialog-body` 含 `overflow: hidden`」, docstring 补第 9 条口径
- `e2e/move-dialog-fit.spec.mjs` —— 逐帧采样器改为**只记面板存在的帧**(离场后回 `auto` 是正确状态, 混进来会假红); ③ Esc 收层段也跑一遍采样并断言全过程无滚动条 + 收完回 `auto`; `geom()` 沿用 `bodyOverflowY`/`bodyGutter`

