# 3422 passed + 4 skipped —— 流量图轮询悬挂兜底(tick 的 loading 判据加计时兜底)

> 摘要: 用户「认领并修复 memory-bank/issues/26-10-16-0954-bug-webui-chart-fetch-no-timeout.html」的**半落态**测量。落盘 = 方案 #2(`qb_traffic_chart.js` 轮询 tick 的 `loading` 判据加悬挂兜底: 置位超 `_QB_LOAD_STALL_MS`=30s 视为悬挂、强制续拉 + 一条 `console.warn`; `_qbLoad` 置位处写计时起点且 `finally` 不擦) + 新守阵 1 条(三层静态锚 + node 行为电池; 既有 `test_frontend_qb_traffic_chart_wiring` 的「tick 三判据」断言按被修复语义改钉 —— 原文钉的合体式书写形态正是本次缺陷成因)。方案 #1(`auth.js::_request` 请求级超时)**未落盘**: 两次写盘均被工作区「凭据字面量」判据误判拦下(整文件扫描命中既有行 `this.pendingToken = "";`), 代码备在交接件 `.openclaw/tmp/auth_js_timeout_patch.txt`, 待人工应用。前端静态件 / 配置 / 运行数据零触碰(除本仓两文件)。
> 基线时间: 2026-10-16 12:26
> 档案: memory-bank/tasks/26-10-16-webui-chart-fetch-timeout.md

- test.full: 3422 passed + 4 skipped / TOTAL 17196 语句 185 未覆盖 5860 分支 160 partial / 98%(`Required test coverage of 98% reached. Total coverage: 98.48%`, 闸门过)。耗时 **185.7s / 205.2s**(本片两次采样, 区间 185–205s; 另有一次较早采样 151.1s, 取改前树仅作参考 —— 本机负载波动大, 单次数字不当基准, 口径见 baseline.md)。
- 本轮新增 1 条守阵用例(`test_frontend_qb_traffic_load_stall_fallback`); 同轮另有一次改写既有断言(见「本改动面」), 不改数量。相对上基线的差值不在此手抄(`kb.baseline -n 2` 现列)。
- **一次偶发红(与本改动无关, 已复验)**: 本片两次采样里第一次报 `tests/test_hr_discovery.py::test_start_binds_first_free_candidate` 失败 —— 断言「首位被占 ⇒ 顺延次位」实测绑到 `base+2`(`54422 == 54420 + 1`), 是**并行全量下的端口抢占竞态**(同族已记 `issues/26-10-16-0348-test-hr-runtime-channel-port-race`), 与前端改动无交集。孤立复跑 **3/3 全过**, 第二次全量亦绿 ⇒ 判为既有偶发, 非本轮引入。
- 红绿双验(3 类突变, 逐类判红后字节还原): ①tick 守卫退回合体式 `document.hidden || this[def.loading]` ⇒ 新守阵判红(两处: 静态锚 + 行为电池); ②tick 对 `loading` 无条件挡拍(修复前行为) ⇒ 判红; ③摘掉 `_qbLoad` 的计时起点写入 ⇒ 判红。还原过程中一次漏行(漏掉 `console.warn` 那一句)被行为电池的「警告只一条」判据当场抓住, 补回后复绿 —— 即该守阵确实读行为、不只看字符串。
- 复验/验收探针 scratch `.openclaw/tmp/probe_webui_fetch_timeout.js`(未入库): 同一探针在修复前后各跑一次 —— ② 读数 `loading` 卡死后 8 拍续拉次数 **0 → 8**(①请求层仍为「无 signal / 零定时器 / 400ms 仍 pending」, 正是待人工应用的 #1)。
- Linux 侧未跑 —— 改动是前端静态件与静态守阵, 无平台分支; 本条 Windows 侧数字为事实源。

## 本改动面

- `src/auto_qb/webui/static/shared/qb_traffic_chart.js`: 新增 `_QB_LOAD_STALL_MS = 30000` 与 `_qbLoadStalled(scope)`; `_qbLoad` 置位 `loading` 处写 `this._qbLoadAt[scope] = Date.now()`(`finally` 不擦, 理由见注释); 轮询 tick 三判据拆开 —— `!def.active(this) || document.hidden` 早退照旧, `this[def.loading]` 单独一段经 `_qbLoadStalled` 判悬挂(未悬挂挡拍 / 悬挂放行 + 一条警告)。
- `tests/test_webui_static_dom_panel.py`: 新增 `test_frontend_qb_traffic_load_stall_fallback`(静态三层锚 + node 行为电池 8 项)与头部测试计划一行; `test_frontend_qb_traffic_chart_wiring` 的「轮询 tick 三判据」断言改按语义钉(原字符串锚已随修复消失, 语义三判据仍在)。
- `memory-bank/`: issue `26-10-16-0954-bug-webui-chart-fetch-no-timeout` 认领(Open → In Progress, meta + 徽标 + 状态日志 + 复验小节 + `doc-refs`); 档案 `tasks/26-10-16-webui-chart-fetch-timeout.md` 新建; activeContext 切片 `26-10-16-1214-webui-chart-fetch-timeout.md` 新建; 索引重建(`kb.index` 21 个生成物)。

**Refs:** memory-bank/tasks/26-10-16-webui-chart-fetch-timeout.md
