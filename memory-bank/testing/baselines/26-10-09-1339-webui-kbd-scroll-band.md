# 2845 —— 键盘滚动跟随可见带: 首个/末个种子不再只显示一半

> 摘要: 修「WEBUI 键盘移动光标到第一个/最后一个种子只显示一半」的收尾基线。滚动跟随的上下边界各漏一层随正文滚动的 chrome: 上界只取顶栏高 `_headH`, 漏了吸在顶栏下缘的吸顶列头 `.group-head`; 下界只取 `window.innerHeight`, 漏了底部固定状态栏 `.statusbar`。修法 = 上下各收单点 `_kbViewTop()`(顶栏 + 列头自身高) / `_kbViewBottom()`(补状态栏让位, 与停靠面板取更紧者), `_kbScrollRowIntoView`(渲染行 + 窗口化两路)与 `_kbViewportRow` 三处消费全改走单点。守阵: 新增静态 `test_kb_view_band_single_points` + 新 e2e `e2e/kbd-scroll-band.spec.mjs`(双皮肤 Home/End, @fast), 均红验(退回 HEAD 版双皮肤转红)。
> 档案: memory-bank/tasks/26-10-09-webui-kbd-scroll-band.md
> 基线时间: 2026-10-09 13:39

**Refs:** memory-bank/tasks/26-10-09-webui-kbd-scroll-band.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2845 passed + 4 skipped + 0 failed, 覆盖率 TOTAL 99%**(16553 语句 / 169 未覆盖 / 5708 分支 / 145 partial; 门槛 98% 达标)
- **耗时**: 两次采样 37.15s / 40.15s(命令墙时 40~46s; 单次数字无意义, 口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **新增用例**: 静态守阵 **1 个新测试函数** —— `tests/test_web_shortcuts.py::test_kb_view_band_single_points`(两个单点在 + 三处消费 + 上界不得裸写 `_headH`, 同文件头部「## 测试计划」同步清单)

## dev.e2e 实测

- 命令: `commands run dev.e2e -- --grep @fast`(桩服务 8137 自动起, Windows 单次采样)
- **实测**: **20 passed**(原 18 + 新 2, 双皮肤各 1 条), 耗时 30.6s
- **新增 spec**: `e2e/kbd-scroll-band.spec.mjs` —— `End` 落末行不被固定状态栏盖 / `Home` 落首行不被吸顶列头盖, 且断言光标**确在极值行**(否则「没被遮」可能只是光标没走到极值, 断言退化成恒真)
- **红验**: 把 `src/auto_qb/webui/static/shared/shortcuts.js` 临时退回 HEAD 版 → 双皮肤 2 条双双转红(实测量级: prism 末行被状态栏遮 21px / 首行被列头遮 23px; atlas 16 / 28px), 还原后双绿

## 说明

- **代码事实变更**: 有 —— `shared/shortcuts.js` 新增 `_kbViewTop()` 上界单点、`_kbViewBottom()` 补固定状态栏让位、三处消费改走单点(渲染行 rect / 窗口化前缀和 / 无光标回落); 文件头补一条边界单点口径。零 CSS / 零后端改动。
- **真浏览器旁证**(临时桩 `scripts/ui_harness.py --torrents 300 --port 8139`, 探针脚本在系统 TEMP 未入库): 三视图 1440x900 真实按键实测 —— 种子页(prism/atlas)、辅种页、追剧页 `Home`/`End` 落点零遮蔽: 首行 top 恰等于列头 bottom(完整可见), 末行 bottom 858 < 状态栏 top 866; 修复前同路径分别遮 23~28px(列头)/ 16~26px(状态栏)。零 pageerror。
- **未验证面**: ①`_kbMovePage`(PageUp/PageDown)仍按整流视口高算每屏行数, 比可见带宽约 100px —— 属**计划外**, 本轮一行未动(跟随会把光标带回可见带, 用户无感); ②窄屏 ≤900px(面板转 fixed 全屏)下 PgUp/PgDn 与可见带的交互未专项走查。
