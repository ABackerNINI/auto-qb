# 单组右键菜单补齐 (与多选批量菜单同项集) · 已闭环

> 摘要: 用户命题「WEBUI辅种页单组右键菜单缺选项, 参考选中多组时右键菜单」。诊断: `shared/tpl/ctx-menus.html` 的右键菜单分四支, 其中 `menu.multi`(多选批量)分支 10 项, 而 `v-else`(单组)分支只有 开始/暂停/汇报 + 打开文件夹/流量图/删除 —— 同一批动作在「右键 1 组」与「Ctrl 选 2 组」两条路径上项集不一致。修法: 单组分支按批量菜单同序同图标补 6 项(重新校验/跳检/限速/移动/标签分类/导出), 目标 = 该组全部成员(`_groupTargets`), 下游整份复用多选链路(bulk 合单 / `_skipCheckDialog` / `_exportHashes` / `openMetaDialog`), 不为组级另开旁路。档案 [26-10-09-webui-ctx-menu-group-actions](../tasks/26-10-09-webui-ctx-menu-group-actions.md)。
>
> 最后活动: 2026-10-09 09:33

**Refs:** memory-bank/tasks/26-10-09-webui-ctx-menu-group-actions.md

## 本轮完成

- **模板** `shared/tpl/ctx-menus.html`: 单组(`v-else`)分支补 6 项, 与多选批量分支**同序同图标**(保留组菜单独有的 打开文件夹/流量图); 跳检项吃 `flags.skip_check_menu` 门控(fail-closed, 与单选/批量两处同口径)。
- **入口** `shared/commands.js`: 新增 `_groupTargets()`(目标 = 该组全部成员, 走 `memberHashesOf` 单点) + 6 组级入口(`recheckGroup` / `editLimitsGroup` / `editMoveGroup` / `skipCheckGroup` / `metaGroup` / `exportGroup`); `exportMulti` 的下载核心抽成 `_exportHashes`(多选 / 单组共用)。
- **对话框** `shared/drawer.js`: `editLimitsMulti` / `editMoveMulti` / `skipCheckMulti` 加可选 `targets`(及文案 `scope`) —— 多选缺省行为不变, 单组入口传该组成员 + 「该组的」。
- **守阵**: 新增 `test_frontend_ctx_menu_group_actions_parity`(钉单组分支六入口 / 跳检门控 / 六入口复用多选下游); 放宽 `test_skip_check_dialog_precheck_wired` 对 `skipCheckMulti` 的签名锚定(可选参)。红验通过。
- 实测数字见 `commands run kb.baseline`。

## 待办 / 移交

- 无遗留。
