# 基线 · 2415 passed + 3 skipped / 99% —— 抽屉显式打开行让位修复轮(双击末尾行被停靠面板遮挡)

> 摘要: 用户报障「WEBUI 双击查看最后几个种子时被抽屉挡住」: 抽屉停靠化(W4)把列表可视下界收成
> `_kbViewBottom()` 单点, 但只接了键盘跟随; 双击/右键/Enter 共用的显式打开 `openTorrentDrawer`
> 是浮层时代遗留路径, 打开后无让位滚动。修法: `shortcuts.js` 新增 `_kbRevealRow(hash)` 单点
> (nextTick 等面板挂载再量, 行下缘低于下界才 scrollBy, 不用 scrollIntoView / 不裸用 innerHeight,
> 行不在 DOM 静默放弃), `openTorrentDrawer` 一处接入覆盖全部显式入口; 守阵
> `test_drawer_open_reveal_row`(test_web_shortcuts.py) + 坑档 dock-panel.md 补第三条与复发闭环
> (单点收口 ≠ 路径都接上)。
> 基线时间: 2026-10-03 21:06, develop @ 7ca46436 + 工作区(本轮回写件未提交)。
> 同步撞「树脏 + 远端重叠」按失败行配方 stash push -u → sync → pop 零冲突化解(.git 已备份仓库外)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2415 passed + 3 skipped / 99%**(14,395 语句 / 130 未覆盖 / 4,810 分支 / 104 partial,
test.full 49.8s, rc=0)。
相对上一切片(26-10-03-2014: 2413 passed + 3 skipped / 99%, 14,395 语句 / 131 未覆盖 / 4,810 分支,
@ 181d90c3) **passed +2** —— 本单新增守阵 1 条(`test_drawer_open_reveal_row`) + 远端合流件 1 条
(70bfc383 与 7ca46436 两笔, 会话中途推进); 语句/分支数持平、未覆盖 131→130 为远端合流与本单
净变化之和, 未逐文件归因。test.quick 同口径 37.7s 全绿。
