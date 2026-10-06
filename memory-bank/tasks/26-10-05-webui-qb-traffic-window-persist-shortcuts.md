# 26-10-05-webui-qb-traffic-window-persist-shortcuts — 流量图窗口选择持久化 + 三条快捷键

**Status:** Done
**Added:** 2026-10-05
**Updated:** 2026-10-05 17:59
**Summary:** 用户动议三项 —— ①流量图「视图选择」(时间窗口 13 档)记入 localStorage; ②种子流量图并入种子详情面板; ③缺口 = 缺快捷键。②经核对**当前代码已实现**(2026-10-04 三挂点并入底部详情抽屉, 种子详情已有「流量」页签, 三挂点共用同一段正文块与同一拖拽高度), 本轮实施 ①③。① 持久化粒度按用户拍板 = 全局单独一份 `autoqb.ui.qbWinGlobal` / 分组与种子共用一份 `autoqb.ui.qbWinShared`, 换窗即落盘刷新保持; 档位清单收成单点 `QB_WINDOW_NAMES`(与后端 `traffic_qb.WINDOW_NAMES` 逐字一致), 同时喂模板展示(`v-for="w in qbWindowNames"`, 去原先硬编码 13 档字面量)/前后切换/持久化校验。③ 三条快捷键: 打开全局图 `Ctrl+Backslash` / 详情面板流量页签 `Alt+5` / 窗口前后切换 `[` `]`(新增引擎 **`when` 条件绑定**: 仅 `qbTrafficActive` 时消费键位, 无图时不 preventDefault 留给浏览器)。改动 4 源文件 + 2 测试文件; 新增守阵 2 条红验通过 + 一次性 node 探针 22/22; test.full **2619 passed + 4 skipped / 99% / 44.2s**(基线切片 26-10-05-1759)。

**Topics:** torrent-traffic-stats

**Refs:** memory-bank/testing/baselines/26-10-05-1759-webui-qb-traffic-window-persist-shortcuts.md

## 原始请求

用户指令: 「流量图的视图选择需要记入localstorage, 种子的流量图需并入种子详情面板, 目前发现的缺口: 缺快捷键」。

追问澄清(AskUserQuestion)三项拍板: ①本轮范围 = **持久化 + 快捷键**(并核对已并入的种子流量图); ②持久化粒度 = **全局单独, 其余两个共用**(自定义项, 非推荐的两档之一); ③快捷键范围 = **打开全局流量图 + 流量页签 Alt+5 + 窗口前后切换**(三选全要)。

## 思考过程与决策

- **② 已实现核实**: `_QB_SCOPES.torrent` 的 `active` 判据 = `drawer.kind === "seed" && drawer.tab === "traffic"`, `drawer.html` 头部有 `v-if="qbTrafficOn"` 的「流量」页签按钮, 与全局/分组共用同一 `ref="qbChartHost"` 与同一 `drawerHeightPx` —— 三挂点 2026-10-04 已并入底部详情抽屉([activeContext 26-10-04-0405](../activeContext/26-10-04-0405-webui-qb-traffic-drawer-merge.md))。故本轮**零改动**, 只在报告里说明。
- **档位清单单点**: 原先档位清单有三份潜在副本(模板 `v-for` 字面量 13 档 / `qbWindowLabel` 文案 map / 注释)。本轮新增两个消费者(前后切换 + 持久化校验), 若各写一份必与后端 `WINDOW_NAMES` 漂移(非法档 → 400)。故收成 `QB_WINDOW_NAMES` 单点(顺序即展示序 = 短窗→长窗), 模板改走 `qbWindowNames` computed, 后端清单在守阵里逐字断言。
- **持久化粒度取舍(用户自定义)**: 全局图看"整机吞吐尺度", 种子/组图看"单对象活跃尺度", 习惯常不同故全局单独一份; 组与种子常被当作同类"单对象"视图对照着看, 故共用一份。键单点 `qbWinStoreKey(scope)`(`global` → Global 键, 其余 → Shared 键)。
- **初值函数放哪**: `qbInitialWindow` 定义在 `qb_traffic_chart.js` 而非 app.js(其余 `initial*` 的位置)—— 三份 tpl-manifest 里本文件均排在 `state.js` 之前, 函数声明在 `data()` 调用时已可用; 档位域归流量图模块所有, 避免跨文件前向引用。该装载序由守阵逐皮肤断言(否则启动白屏)。
- **`when` 条件绑定(引擎新机制)**: 窗口切换键 `[` `]` 只在流量图可见时有意义。既有先例 `_kbDrawerTab` 是"消费键位后 toast 忽略", 但那会让无流量图时 `[` `]` 被无谓吞掉。故给注册表条目加可选 `when(vm) => bool`, 引擎在 `preventDefault()` **之前**分流: 假则直接 return(不消费)。条件项照常进 W6 面板与冲突检测(键位唯一性不受条件影响)。
- **两条入口键的门控**: `open-qb-traffic` 与 `drawer-tab-traffic` **不加** `when`(键位常驻, 按了要有反馈), 改为在 `run` 落点内门控 —— `openQbHistory` 补 `qbTrafficOn` 检查 + toast; `_kbDrawerTab` 补 `tab === "traffic" && !qbTrafficOn` 分支(页签按钮 `v-if=qbTrafficOn` 不渲染, 切过去会卡在没有按钮可切回的隐形页签)。
- **端点夹取不环绕**: `qbCycleWindow` 在 13 档两端夹取(从「全部」跳回「1分」是惊扰); 走 `qbSetWindow` 单点, 重拉重画 + 轮询重排 + 落盘三事一体。
- **键位选择**: 打开全局图取 `Ctrl+Backslash`(与 `Backslash`=统计面板 / `Shift+Backslash`=历史流量 成族); 窗口切换取 `[` `]`(物理键位 `BracketLeft/Right`, 无修饰键, 全仓未占用); 页签取 `Alt+Digit5`(顺 Alt+1~4)。黑名单与默认键冲突由既有守阵覆盖。

## 实现计划

1. 持久化: `qb_traffic_chart.js` 加 `QB_WINDOW_NAMES`/`QB_WINDOW_DEFAULT`/两存储键/`qbWinStoreKey`/`qbInitialWindow`/`qbWindowNames` computed/`persistQbWindow`/`qbCycleWindow`; `_qbSetWindow` 加落盘; `state.js` 三字段初值接 `qbInitialWindow`; `drawer.html` 窗口按钮改 `v-for="w in qbWindowNames"`。
2. 快捷键: `shortcuts.js` 注册表 4 条新条目 + 引擎 `when` 分流 + `_kbDrawerTab` 流量门控; `openQbHistory` 补未启用提示; 文件头与条目形状注释同步。
3. 守阵: `test_web.py::test_frontend_qb_traffic_window_persist_and_single_source` + `test_web_shortcuts.py::test_qb_traffic_shortcuts`(并给 `_registry()` 加 `when` 解析); 两文件头部「## 测试计划」清单同步。
4. 红验 + node 行为探针 + `test.full` 基线 + memory-bank 回写(activeContext / 基线切片 / progress / 本档案 / `kb.index`)。

## 子任务状态表

| # | 子任务 | 状态 |
|---|--------|------|
| 1 | 窗口档位单点 + 持久化(粒度: 全局单独 / 组与种子共用) | Done |
| 2 | 三条快捷键(打开全局图 / 流量页签 Alt+5 / 窗口前后切换, 含引擎 `when` 条件绑定) | Done |
| 3 | 守阵 2 条 + 测试计划清单同步 + 红验 + node 行为探针 | Done |
| 4 | test.full 基线 + memory-bank 回写 | Done |

## 进度日志

- **2026-10-05 17:59**: 全部实现完成。改动面 4 源文件(`shared/qb_traffic_chart.js` / `shared/shortcuts.js` / `shared/state.js` / `shared/tpl/drawer.html`)+ 2 测试文件(`tests/test_web.py` / `tests/test_web_shortcuts.py`)。守阵红验: 摘 `when` 分流 → `test_qb_traffic_shortcuts` 红; 摘 `persistQbWindow` 调用 → `test_frontend_qb_traffic_window_persist_and_single_source` 红; 恢复后绿。一次性 node 探针(`tmp-analysis/`, 已删)22/22 过: 持久化粒度三向 + 非法/无存储回落 + `qbCycleWindow` 步进/两端夹取/无形态零副作用 + `persistQbWindow` 键分派 + `when=false` 不消费 / `when=true` 消费且动作正确 + Ctrl+Backslash→openQbHistory / Alt+5→tab:traffic / Shift+Backslash 与裸 Backslash 未撞键。`commands run test.full` **2619 passed + 4 skipped / 99% / 44.24s / 44.15s(两次采样)**(15802 语句 / 167 未覆盖 / 5392 分支 / 140 partial; 增量 +9 = reannounce 重构守阵 +7 经开工同步并入 + 本轮 +2)。基线切片 [baselines/26-10-05-1759](../testing/baselines/26-10-05-1759-webui-qb-traffic-window-persist-shortcuts.md)。未验证面: 真浏览器交互未跑(本 clone node 侧 Playwright 缺失 ⇒ `dev.harness`/`ui_smoke.cjs` 不可用; 且桩 harness 未开 `qb_traffic`, 图表本不在既有冒烟覆盖内)—— 待用户真机走查窗口保持 / `[` `]` 手感 / 两条入口键。改动留工作树未提交, 等用户显式提交指令。
