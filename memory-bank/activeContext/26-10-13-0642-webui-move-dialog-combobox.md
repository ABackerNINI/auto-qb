# 设定位置下拉+最近排序(webui-move-dialog-combobox)

> 摘要: WEBUI「设定位置…」三入口(单种子右键/键盘、单组右键、多选批量右键)统一改, 保存路径输入改走一份对话框状态机, 下拉候选按「最近使用」排序复用添加种子单点。
> 最后活动: 2026-10-13 06:42

## 已完成(迁出见 progress)

- 三入口名/签名(editMove/editMoveMulti/editMoveGroup)与下游投递不变 —— 守阵 + 触发登记表钉这些。
- 下拉候选 = /api/paths 已知保存路径按最近排序, 复用 add_torrent.js `_addOrderByRecent`/`_addRecencyMaps`/`_addNormPath` 单点(全局 mixin 合并, 跨模块互调逐字等价)。单种子预填当前 save_path, 批量/单组无预填。
- 新分片 tpl/move-dialog.html(popovers.html 超 400 行分片上限即拆), 挂进三皮肤 manifest。
- combobox 收层/限高/悬同与添加种子三下拉 + meta 分类同套口径(@focusout + 40ms合帧 + _popBlurShouldHold + watcher重限 + comboHoverIdx move 分支)。
- 验证: test.full 全绿(见 kb.baseline); 全量 e2e 真浏览器 206 passed / 10 skipped / 0 failed。

见任务档案 [26-10-13-webui-move-dialog-combobox](../tasks/26-10-13-webui-move-dialog-combobox.md)。
