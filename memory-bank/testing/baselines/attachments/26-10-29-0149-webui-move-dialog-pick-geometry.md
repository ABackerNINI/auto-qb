# 4006 passed + 2 skipped(根) —— 设定位置对话框三修: 开层增长只朝下

> 摘要: 设定位置对话框三修: 开层增长只朝下
> 基线时间: 2026-10-29 01:49
**Refs:** memory-bank/tasks/26-10-29-webui-move-dialog-pick-geometry.md, memory-bank/pitfalls/web-ui/dialog-geometry-jump.md

## 验收数字

`commands run test.full` 实测输出:

- 汇总行: **4006 passed, 2 skipped in 181.47s (0:03:01)**
- TOTAL 表: `20981  98   7088   100    99%`(语句 / missed / 分支 / partial / 覆盖率)
- 覆盖率门槛 99% 达标, 无 FAIL 行; 零失败零回归
- e2e 单跑(`commands run dev.e2e -- move-dialog-fit`, 双皮肤 × 3 用例): **6 passed (20.3s)**
  - 几何实测(1440x900, 桩 300): 开层前后 **rowTop 413→413**(prism) / **411→411**(atlas) —— 修复前为 413→335 / 411→333
  - 对话框上缘 **270→270**, 高度 **360→515**(prism) / **360→513**(atlas), 下缘 785 / 783 均 < 900
  - 面板 top **450 ≥ 输入框 bottom 446**(prism) / **448 ≥ 444**(atlas) —— 下拉不再盖住输入框
  - 同一屏幕坐标连点两次: 面板仍在, 输入框仍为空(修复前第二次点击命中候选 = 面板"自动弹回")
- e2e `@fast` 全量: **220 passed (7.0m)**

口径注记: passed/skipped/覆盖率数字由 agent 从本次实测输出誊写; 相对上基线的逐位对比不写(看差值 `commands run kb.baseline -n 2`)。

## 本改动面

用户报障「点下拉框, 下拉框出现后自动弹回」的落点, 4 个源文件 + 2 个测试件(几何数字全在 CSS 单点):

- `src/auto_qb/webui/static/shared/tpl/move-dialog.html` —— `<aq-modal>` 增 `mask-class="modal-mask move-dialog-mask"`(遮罩类接线; 增长方向改不了 = 面板被顶到光标底下); 头注补三修口径
- `src/auto_qb/webui/static/{atlas,console,prism}/css/dialogs.css` —— 三皮肤成对: 新增 `.modal-mask.move-dialog-mask { align-items: flex-start }`(遮罩由居中改顶端对齐), `.modal.move-dialog` 增 `margin-top: clamp(0px, calc((100vh - 360px) / 2 - 20px), calc(100vh - 560px))` 复刻收层态居中偏移 ⇒ 收层态屏位与居中逐像素相同, 开层只向下长
- `tests/test_webui_static_dom_panel.py` —— `test_frontend_move_dialog_combobox_wiring` 补 4d(模板 mask-class 接线)+ 三皮肤 `flex-start` / `margin-top` 居中补偿断言, docstring 补第 7 条口径
- `e2e/move-dialog-fit.spec.mjs` —— `geom()` 增 `dlgTop`/`rowTop`/`inputBottom`/`popTop`/`vh`; 用例①补几何不变量(输入行屏坐标不动 ≤2px / 上缘不动 / 面板 top ≥ 输入框 bottom / 下缘不溢出视口); 新增用例③「同一屏幕点连点两次 · 面板不弹回」

