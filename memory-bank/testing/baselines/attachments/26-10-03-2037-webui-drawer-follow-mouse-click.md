# 基线 · 2414 passed + 3 skipped / 99% —— 种子行单击接详情面板跟随挂点(计划 26-10-03-0917 §1.3 相邻预留)

> 摘要: 用户报「WEBUI 鼠标单击种子无法切换详情抽屉」—— 详情面板跟随此前**只有键盘路径**
> (`shortcuts.js::_kbApplyCursor` 尾部挂 `_kbFollowDrawer`), 鼠标点种子行只落光标不跟随
> (报告 26-09-30-1806 同源: 两条输入没接同一行状态)。修法 = 计划 §1.3 预留的鼠标路径接**同一个挂点**:
> `selection.js::onTorrentClick` 普通单击分支末尾调 `this._kbFollowDrawer()`, 防抖 200ms / page+kind
> 守卫 / hash 短路 / FX-29 软切换全部复用既有实现; 两条边界 —— 面板关着**不打开**(开面板仍归双击 /
> Enter / 右键「详情」, 免得点一下弹出 42vh 面板压掉列表, 与「列表当前行必须看得清」硬约束冲突)、
> Ctrl/Shift 修饰键点击是**选择手势**不跟随(圈选 N 行不该让面板逐行翻)。守阵新增
> `test_drawer_follow_mouse_click`(单击接挂点 / 写在两修饰键分支之后 / 单击不得调 openTorrentDrawer /
> 挂点首守卫挡关闭态 / 双击开面板入口仍在)。src 改动 1 处, 模板与三皮肤 CSS 零改动。
> 基线时间: 2026-10-03 20:37, develop @ 70bfc383 + 工作区(本轮改动未提交)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2414 passed + 3 skipped / 99%**(14,395 语句 / 131 未覆盖 / 4,810 分支 / 104 partial,
test.full 33.7s, rc=0)。
相对上一切片(26-10-03-2014: 2413 passed + 3 skipped / 99%, 语句 / 分支数同) **passed +1** ——
即本轮新增守阵 1 条(`tests/test_web_shortcuts.py::test_drawer_follow_mouse_click`)。
**包内脚本测试不在本数字内**(testpaths 之外): 本轮未动 `.commands/`, 未跑 `test.pkg`。
未做真浏览器冒烟: `dev.harness` 目前**无 drawer 场景**(grep 零命中), 补桩属另一范围, 已转告用户。
