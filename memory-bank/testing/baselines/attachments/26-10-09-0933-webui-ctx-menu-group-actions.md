# 2825 —— 单组右键菜单补齐(与多选批量菜单同项集)

> 摘要: 辅种页单组右键菜单补齐实施轮收尾基线。单组菜单(`v-else`)此前只有 开始/暂停/汇报 + 打开文件夹/流量图/删除, 而多选批量菜单(`menu.multi`)还有 重新校验/跳检/限速/移动/标签分类/导出 —— 本轮把单组分支按批量菜单同序同图标补齐, 目标 = 该组全部成员, 下游复用多选链路。
> 档案: memory-bank/tasks/26-10-09-webui-ctx-menu-group-actions.md
> 基线时间: 2026-10-09 09:33

**Refs:** memory-bank/tasks/26-10-09-webui-ctx-menu-group-actions.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2825 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**(16479 语句 / 161 未覆盖 / 5696 分支 / 145 partial; 门槛 98% 达标)
- **耗时**: 44.59s(墙时 46.7s)
- **新增测试**: 1 个守阵函数(`test_frontend_ctx_menu_group_actions_parity`, 挂在 `tests/test_webui_static_dom_panel.py`); 另放宽 `test_skip_check_dialog_precheck_wired` 对 `skipCheckMulti` 的签名锚定(可选参)。
- **e2e**: `commands run dev.e2e` 默认轮 **100 passed / 10 skipped**(真浏览器, 无回归; 该改动未新增 e2e —— 纯加项且与既有项结构同构, 静态守阵已钉项集与接线)。
