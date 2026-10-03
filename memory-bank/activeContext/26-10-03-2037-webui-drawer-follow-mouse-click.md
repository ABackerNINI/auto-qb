# 详情面板跟随接鼠标路径(种子行单击换目标)

> 摘要: 用户报「WEBUI 鼠标单击种子无法切换详情抽屉」—— 跟随此前只有键盘路径, 已接 §1.3 预留的同一挂点;
> 面板关着不打开 / 修饰键点击不跟随两条边界已钉守阵。test.full 2414 passed + 3 skipped / 99%。
> 最后活动: 2026-10-03 20:37

## 已完成 (2026-10-03)

- **根因**: 详情面板跟随的触发单点 `_kbFollowDrawer`(计划 26-10-03-0917 §2.3)只挂在
  `shortcuts.js::_kbApplyCursor` 尾部 —— **只有键盘路径**; 鼠标点种子行走
  `selection.js::onTorrentClick`(只落 kbCursor + 落起点), 面板纹丝不动。与报告 26-09-30-1806
  同源: 同一行状态的两套输入没接到一起。
- **修法**: `onTorrentClick` 普通单击分支末尾调 `this._kbFollowDrawer()`(200ms 防抖 / page+kind
  守卫 / hash 短路 / FX-29 软切换全部复用, 零新增状态)。两条边界: ① 面板关着**不打开**
  (开面板仍归双击 / Enter / 右键「详情」—— 点一下弹出 42vh 面板压掉列表, 与「列表当前行必须
  看得清」硬约束冲突); ② Ctrl/Shift 点击是选择手势, 不跟随(圈选 N 行不该让面板逐行翻)。
- **守阵**: `test_web_shortcuts.py::test_drawer_follow_mouse_click`(单击接挂点 / 写在两修饰键
  分支之后 / 单击不得出现 openTorrentDrawer / 挂点首守卫挡关闭态 / 双击开面板入口仍在),
  文件头测试计划同步登记。基线 [26-10-03-2037](../testing/baselines/26-10-03-2037-webui-drawer-follow-mouse-click.md)。

## 待用户定夺 / 未做

- **未提交**(等显式「提交」指令)。
- 真浏览器冒烟未做: `dev.harness` 无 drawer 场景(grep 零命中), 补桩属另一范围。
- 用户若想「面板关着时单击也打开」(qB 原生观感), 是另一条口径改动 —— 等显式指令。
