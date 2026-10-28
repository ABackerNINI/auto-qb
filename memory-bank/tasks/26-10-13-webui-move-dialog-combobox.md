# 26-10-13-webui-move-dialog-combobox — 设定位置下拉+最近排序

**Status:** Done
**Added:** 2026-10-13
**Updated:** 2026-10-13
**Summary:** 给 WEBUI「设定位置…」(单种子右键/键盘、单组右键、多选批量右键三入口) 的保存路径输入, 添加「下拉候选 + 最近使用排序」—— 与添加种子对话框保存路径同口径, 复用 add_torrent.js 的 _addRecencyMaps/_addOrderByRecent/_addNormPath 单点。改三入口统一改, 用一份对话框状态机。
**Topics:** webui-move-dialog-combobox
**Refs:** memory-bank/testing/baselines/26-10-13-0642-webui-move-dialog-combobox.md, memory-bank/plans/26-10-29-0041-plan-webui-move-dialog-pick-geometry.html

## 原始请求

「WEBUI中的种子设定位置功能需要添加"添加种子"的"保存路径"相同的功能, 即下拉列表+最近排序」—— 用户拍板覆盖范围 = 单种子 + 批量 + 单组(全部三入口)。

## 思考过程与决策

- 添加种子对话框保存路径已有 combobox: 下拉候选(/api/paths 已知保存路径)按「最近使用」排序, 排序单点 `_addOrderByRecent` + 跨视图取数 `_addRecencyMaps`/`_addRecencyRows` + 路径归一 `_addNormPath`(见 pitfalls/web-ui/contract-api.md 末条 + combobox-focusout-close.md)。
- 「设定位置…」三入口原状用 generic modal 的 plain text field(editMove=_openModal fields / editMoveMulti=promptDialog+confirmDialog), 无下拉。
- 决策: 一份对话框状态机(openMoveDialog)三入口共用, 复用 meta 对话框(标签与分类)的 combobox 模板范式(popovers.html metaCatMenu 块)—— 已证明 combobox 在 modal 里 works。下拉候选按最近排序复用 add_torrent.js 单点(全局 mixin 合并, 跨模块互调逐字等价)。单种子预填当前 save_path, 批量/单组无预填(各值不同, 预填误导)。
- 三入口名/签名(editMove/editMoveMulti/editMoveGroup)与下游投递(editMove→_editPost, editMoveMulti/editMoveGroup→_bulkEditPost)不变 —— 守阵(test_webui_static_dom_panel ctx-menu 守阵)+ 触发登记表(test_webui_trigger_registry)钉这些。

## 实现计划

1. state.js: 新增 moveOpen/moveTargets/moveCount/moveSingleHash/moveScope/movePathOptions/movePathInput/movePathMenu/movePathHi/movePathMouseAt/moveBusy 反应态。
2. tpl/move-dialog.html(新分片, popovers.html 超 400 行分片上限即拆): 遮罩 + 路径 input + 下拉候选 panel + 键盘导航 + 失焦收层 + 提交钮。挂进三皮肤 manifest。
3. drawer.js: editMove/editMoveMulti 改走 openMoveDialog; 新增状态机方法(openMoveDialog/closeMove/loadMoveOptions/openMovePathMenu/moveApplyPath/onMovePathKeydown/movePathBlurClose/_movePopBlurCancel/submitMoveDialog); 新增 watch 块重限高; _bulkEditPost 改 return r.ok。
4. add_torrent.js: comboHoverIdx 加 move 分支; _fitAddPop 放行 moveOpen。
5. lifecycle.js: Esc 退栈链 + window click 兜底名单 + dialogs.js escBusy 同步 moveOpen/movePathMenu。
6. CSS 三皮肤成对: .modal.move-dialog/.move-targets/.move-note。
7. 守阵: 新增 test_frontend_move_dialog_combobox_wiring; 既有 _fitAddPop 守卫串改(三处放行)。

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 三入口统一改 + 状态机 | Done |
| 下拉候选最近排序复用单点 | Done |
| combobox 收层/限高/悬同同套口径 | Done |
| 三皮肤成对 CSS + manifest | Done |
| 守阵 + 触发登记表 + e2e | Done |

## 进度日志

- 2026-10-13 06:42 实施完成。改代码前读 pitfalls/web-ui/{contract-api,combobox-focusout-close,global-mixin-basetransition-watch,frontend-split}.md。
- 验证: test.full 全绿(见 kb.baseline); 全量 e2e 真浏览器 206 passed / 10 skipped / 0 failed(6.3m)。
- 取舍: 复用添加种子排序单点而非新后端端点(零后端改动、零新请求、零新持久化, 与添加种子同口径); 跨视图取数 _addRecencyMaps 现算(与添加种子同, 默认辅种页下排序不静退化)。
- 键盘: 开对话框即 focus 输入(与 _openModal 原行为); Enter 即提交(菜单未开时提交当前输入, 与 onMetaCatKeydown 同套)。
