# 流量图窗口选择持久化 + 三条快捷键 (qB 口径流量图 UX 补完)

> 摘要: 用户动议三项 —— ①流量图「视图选择」(时间窗口 13 档)记入 localStorage; ②种子流量图并入种子详情面板;
> ③发现的缺口 = 缺快捷键。**②经核对当前代码已实现**(种子详情抽屉已有「流量」页签, 全局/分组/种子三挂点共用同一段
> 正文块与同一拖拽高度, 2026-10-04 并入), 本轮实施 ①③:
> ① 持久化粒度按用户拍板 = **全局单独一份 / 分组与种子共用一份**(`autoqb.ui.qbWinGlobal` / `autoqb.ui.qbWinShared`),
> 换窗即落盘、刷新后保持; 档位清单收成单点 `QB_WINDOW_NAMES`(与后端 `traffic_qb.WINDOW_NAMES` 逐字一致), 供
> 展示(模板 `v-for="w in qbWindowNames"`, 原先硬编码 13 档字面量)、前后切换、持久化校验三处共用。
> ③ 三条快捷键: **打开全局图 `Ctrl+Backslash`**(状态栏入口的键盘对应, run 内 `qbTrafficOn` 门控 + 未启用提示) /
> **详情面板流量页签 `Alt+5`**(补 Alt+1~4 缺口, `_kbDrawerTab` 内补流量门控, 未启用不许切到无按钮的隐形页签) /
> **窗口前后切换 `[` `]`**(新增引擎机制 **`when` 条件绑定**: 仅 `qbTrafficActive` 时消费键位, 无流量图时不
> preventDefault、键位留给浏览器)。
> 验证: 新增守阵 2 条(两文件)红验通过 + 一次性 node 探针 22/22 过(持久化粒度/校验/夹取/`when` 分流/三条新入口/未撞旧键);
> test.full **2619 passed + 4 skipped / 99% / 44.2s**(基线切片 26-10-05-1759)。
> 未验证面: 真浏览器交互(本 clone node 侧 Playwright 缺失, `dev.harness`/`ui_smoke.cjs` 跑不了; 桩 harness 亦未开
> `qb_traffic`, 图表本身不在冒烟覆盖内)—— 待用户真机走查。
> 最后活动: 2026-10-05 17:59

**Refs:** memory-bank/tasks/26-10-05-webui-qb-traffic-window-persist-shortcuts.md

## 现状

- **实施完成, 待用户提交**。改动面 6 文件(4 源码 + 2 测试):
  - `shared/qb_traffic_chart.js` — `QB_WINDOW_NAMES`/`QB_WINDOW_DEFAULT` 单点 + 两个存储键 + `qbWinStoreKey`
    + `qbInitialWindow`(初值读取, 定义在此因三份 tpl-manifest 里本文件均排在 state.js 之前)+ `qbWindowNames` computed
    + `persistQbWindow` + `qbCycleWindow`(端点夹取不环绕, 走 `qbSetWindow` 单点); `_qbSetWindow` 加落盘;
    `openQbHistory` 补未启用提示。
  - `shared/state.js` — 三窗口字段初值改 `qbInitialWindow("global"/"torrent"/"group")`。
  - `shared/tpl/drawer.html` — 窗口按钮 `v-for="w in qbWindowNames"`(去 13 档硬编码)。
  - `shared/shortcuts.js` — 注册表 4 条新条目(`open-qb-traffic` / `drawer-tab-traffic` / `traffic-win-prev` /
    `traffic-win-next`); 引擎加 `when` 条件绑定分流(preventDefault **之前**); `_kbDrawerTab` 补流量门控。
  - `tests/test_web.py::test_frontend_qb_traffic_window_persist_and_single_source`(新) ·
    `tests/test_web_shortcuts.py::test_qb_traffic_shortcuts`(新, 并给 `_registry()` 加 `when` 字段解析)。
- 关键判据/取舍:
  - **档位单点**同时喂三处(展示/切换/校验) —— 与后端 `WINDOW_NAMES` 逐字断言, 避免任一处硬编码漂移成 400。
  - **`when` 条件绑定**是引擎新机制(条目形状注释已补): 条件假 → 不消费按键(不 preventDefault), 区别于
    `_kbDrawerTab` 那类"消费键位后 toast 忽略"的既有先例 —— 流量图窗口键在无图时不该被吞。
  - 端点**夹取不环绕**(从「全部」跳回「1分」是惊扰)。
- 验证:
  - 新增守阵红验: 摘 `when` 分流 → `test_qb_traffic_shortcuts` 红; 摘 `persistQbWindow` 调用 →
    `test_frontend_qb_traffic_window_persist_and_single_source` 红; 恢复后绿。
  - 一次性 node 探针(`tmp-analysis/`, 已删)22/22: 持久化粒度三向 + 非法/无存储回落 + `qbCycleWindow`
    步进/两端夹取/无形态零副作用 + `persistQbWindow` 键分派 + `when=false` 不消费 / `when=true` 消费且动作正确
    + Ctrl+Backslash→openQbHistory / Alt+5→tab:traffic / Shift+Backslash 与裸 Backslash 未撞键。
  - `commands run test.full` → 2619 passed + 4 skipped / 99% / 44.2s(增量 +9 = reannounce 重构守阵 +7 经开工同步并入
    + 本轮 +2)。
- 未验证面 / 遗留: ①真浏览器走查(窗口切换后刷新是否保持 / `[` `]` 是否跟手 / Alt+5 与 Ctrl+Backslash 实际手感);
  ②`dev.harness` 桩未开 `qb_traffic`, 流量图不在既有浏览器冒烟覆盖内 —— 若后续要给图表做冒烟, 需先给 harness 加
  开 `qb_traffic` 的桩开关(本轮未做, 范围守恒); ③`kb.active` 报的切片数债务(126 > 70)非本轮引入, 转告用户另开会话清理。
