# 4006 passed + 2 skipped(根) —— 设定位置对话框四修: 开层期关滚动

> 摘要: 设定位置对话框四修: 开层期关滚动
> 基线时间: 2026-10-29 02:24
**Refs:** memory-bank/tasks/26-10-29-webui-move-dialog-pick-geometry.md, memory-bank/pitfalls/web-ui/dialog-geometry-jump.md

## 验收数字

`commands run test.full` 实测输出:

- 汇总行: **4006 passed, 2 skipped in 176.69s (0:02:56)**
- TOTAL 表: `20981  98   7088   100    99%`(语句 / missed / 分支 / partial / 覆盖率)
- 覆盖率门槛 99% 达标, 无 FAIL 行; 零失败零回归
- e2e 单跑(`commands run dev.e2e -- move-dialog-fit`, 双皮肤 × 3 用例): **6 passed (20.4s)**
  - 滚动条逐帧采样(开层全过程, 只从面板挂载那帧起算): `overflowY` 恒 **hidden**, 滚动条占位宽恒 **0**
  - 过渡期实测 body 溢出序列 **256 → 173 → 108 → 37 → 7 → 0**(溢出只发生在 ~110ms 内, 且被裁在 padding 盒底沿)
  - 终态: 面板底缘在 body 底沿之上 **12px**(未被裁), 对话框 515px、下缘 785 < 900
  - 收层态 `overflowY` 仍为 **auto**(矮视口 body 兜底滚动不受影响)
- e2e `@fast` 全量: **220 passed (7.0m)**

口径注记: passed/skipped/覆盖率数字由 agent 从本次实测输出誊写; 相对上基线的逐位对比不写(看差值 `commands run kb.baseline -n 2`)。

## 本改动面

用户报障「下拉框出现时弹窗有一瞬间出现滚动条」的落点, 3 个源文件 + 2 个测试件:

- `src/auto_qb/webui/static/{atlas,console,prism}/css/dialogs.css` —— 三皮肤成对: `.modal.move-dialog.pop-open .add-dialog-body` 增 `overflow: hidden`(开层期关掉 body 滚动; 收层态仍 `auto` 兜底矮视口), 并补四修注释(过渡期溢出量实测序列 + 安全性论证: 溢出的只有预留空白)
- `tests/test_webui_static_dom_panel.py` —— `test_frontend_move_dialog_combobox_wiring` 补三皮肤断言(同一条规则里既有 `padding-bottom: 272px` 又有 `overflow: hidden`), docstring 补第 8 条口径
- `e2e/move-dialog-fit.spec.mjs` —— 新增 `sbSamplerOn/sbSamplerOff` 逐帧滚动条采样器(只从面板挂载那帧开始记, 判据看计算值 `overflowY` —— 无头 Chromium 是覆盖式滚动条, 占位宽恒 0 不可用); `geom()` 增 `bodyOverflowY`/`bodyGutter`; 用例①断言开层全过程零滚动条 + 收层态仍 `auto`

