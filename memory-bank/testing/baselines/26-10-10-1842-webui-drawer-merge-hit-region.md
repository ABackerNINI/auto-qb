# 2958 —— 合并双列右键命中区域兜底(右列空白弹左列模板修正)基线

> 摘要: 用户报「种子详情面板合并后右侧鼠标右键菜单会显示更改左边的模板选项」。根因 = 合并双列的列间隙 / 分栏两侧留白 / 短列下方留白不落在任何 `.dt-col` 元素上, `_drawerMenuTab` 命不中时裸回落当前页签(常为左列)。修 = 正文区内按指针 x 归列兜底(`_drawerMenuColByX`), 页签栏/头部不受影响。纯前端静态 JS 改动; 守阵加 3 钉(改既有测试函数)+ e2e 扩 1 场景。机理入坑档 `pitfalls/web-ui/drawer-merge-hit-region.md`。
> 档案: memory-bank/activeContext/26-10-09-2226-webui-drawer-merge-tabs.md
> 基线时间: 2026-10-10 18:42

**Refs:** memory-bank/activeContext/26-10-09-2226-webui-drawer-merge-tabs.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 已同步 `bcba4b24`, 无快进; 工作树含本轮改动 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2958 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16568 语句 / 165 未覆盖 / 5716 分支 / 142 partial; 门槛 98% 达标; 27.75s)
- 与上基线的差值: passed/skipped 与上一片(`26-10-10-1824`)持平 —— 本轮 `src/` 只改前端静态 JS(不进 `--cov=src`), 守阵为**改既有函数**(`test_drawer_tpl_menu_right_click_selection` 加 3 钉, 非新增用例)⇒ 收集面不变, 数字不挪。
- e2e 实测: `drawer-merge.spec.mjs` **8 passed**(@fast 双皮肤 atlas/prism; 用例「右键各列弹各自模板选择」扩入「右列下方空白右键仍须弹内容模板」真实坐标手势)。

## 本轮改动面

- `shared/menu.js` —— `_drawerMenuTab` 加正文区按 x 归列兜底(限 `dtSplitOn && el.closest(".drawer-body")`); 新增 `_drawerMenuColByX(event)`。
- 守阵 `tests/test_webui_static_dom_panel.py`(既有函数加 3 钉 + 头部 docstring 补一句); e2e `e2e/drawer-merge.spec.mjs`(既有用例扩 1 场景 + 文件头注释)。
- 知识库回写: `modules/webui-static-contract.md` + `progress/implemented-webui.md` + activeContext 切片 R6 段 + 坑档 `pitfalls/web-ui/drawer-merge-hit-region.md` + 本切片。
- `src/` 后端零改动。Linux(WSL 沙箱)侧未重测 —— 本轮只改平台无关的前端静态 JS 与断言面(口径见 baseline.md 常驻警告; 与近几轮切片同处理)。

## 守卫收口

- `kb.check` / `doc.caps` 见收尾复跑结果。
