# 抽屉显式打开行让位 — 双击末尾行被停靠面板遮挡修复 (Done)

> 摘要: 修复 2026-10-03 用户报障「WEBUI 双击查看最后几个种子时被抽屉挡住」: W4 下界单点只接了
> 键盘跟随, 显式打开路径漏接让位; shortcuts.js 新增 `_kbRevealRow` 单点 + `openTorrentDrawer`
> 接入 + 守阵 `test_drawer_open_reveal_row` + 坑档 dock-panel.md 第三条与复发闭环。
> 最后活动: 2026-10-03 21:06

## 已完成 (2026-10-03)

- **定位**: 抽屉 26-10-03 方案A 停靠化(W1-W5)后, 列表可视下界 = 面板顶缘; W4 几何走查收了
  `_kbViewBottom()` 单点但只接了键盘跟随(`_kbViewportRow` / `_kbScrollRowIntoView`),
  双击/右键/Enter 共用的 `openTorrentDrawer` 是浮层时代遗留路径(浮层不占文档流, 从不需要让位),
  打开后无任何让位滚动 → 末尾几行被面板顶缘压住。坑档族: pitfalls/web-ui/dock-panel.md。
- **修复**: `shortcuts.js` 新增 `_kbRevealRow(hash)` —— nextTick 等面板挂载再量(面板 DOM 随
  open v-if, 同帧量不到), 行下缘低于 `_kbViewBottom() - 4` 才 scrollBy, 本来可见不动, 行不在
  DOM(窗口化折叠)静默放弃; 不用 scrollIntoView(文件头禁令)、不裸用 innerHeight(坑档口径)。
  `drawer.js openTorrentDrawer` 挂状态后调用一处 —— 双击/右键菜单/Enter/Alt+数字四个显式入口
  一次全修。
- **守阵**: `tests/test_web_shortcuts.py::test_drawer_open_reveal_row`(open 调让位单点 / nextTick /
  下界走单点 / 禁 scrollIntoView 与 innerHeight / 无行静默放弃) + 文件头测试计划登记。
- **回写**: 坑档 `pitfalls/web-ui/dock-panel.md` 第三条「显式打开路径同样要让位 —— 单点收口不等于
  路径都接上」(触发/判别/处置三字段 + 触发词 + 守阵行) + 首条复发 +1(为什么没命中: 处置只覆盖
  「新写算式走单点」, 没覆盖「既有路径族全部接入」)。用户直接报障, 未入池 issue。
- 收尾: 收「收尾DoD然后提交」指令; 提交前同步撞「树脏 + 远端重叠」双向锁, 按失败行配方
  stash push -u → sync(7ca46436) → pop 零冲突化解(.git 已备份仓库外待用户清理); 基线切片
  baselines/26-10-03-2106(2415 passed + 3 skipped / 99% @ 7ca46436 + 工作区)。不满足立档阈值
  (2 源文件 + 1 测试), 沿用 copytext 轮口径只留切片、不动 tasks 档案。

## 状态

任务完结, 随本轮 ship.commit 入库(用户已授权「收尾DoD然后提交」)。
真浏览器双击末尾行复验待用户下一轮 UI 冒烟(静态与全量测试已覆盖)。
