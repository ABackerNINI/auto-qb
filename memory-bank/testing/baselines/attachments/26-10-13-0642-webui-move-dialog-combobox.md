# 3177 —— 设定位置下拉+最近排序(webui-move-dialog-combobox)

> 摘要: 设定位置对话框(单种子/单组/多选批量三入口统一改)落地, 全量 test.full 全绿。
> 基线时间: 26-10-13 06:42
> 档案: memory-bank/tasks/26-10-13-webui-move-dialog-combobox.md

## 实测

- **3177 passed + 4 skipped** in 78.74s (0:01:18)
- TOTAL 16750 语句 / 159 未覆盖 / 5702 分支 / 140 partial / **99%** (Required 98% reached, Total 98.64%)
- 新增守阵: `test_frontend_move_dialog_combobox_wiring`(test_webui_static_dom_panel.py) —— 三入口名/签名 + 排序单点复用 + combobox 收层/限高/悬同同套口径 + 对话框模板接线 + 三皮肤成对 CSS + Esc 退栈链同步; 既有 `_fitAddPop` 守卫串改(三处放行 addOpen/metaOpen/moveOpen)。
- 全量 e2e 真浏览器: 206 passed / 10 skipped / 0 failed(6.3m)。

**Refs:** memory-bank/tasks/26-10-13-webui-move-dialog-combobox.md
