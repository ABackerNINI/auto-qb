# 3363 passed + 4 skipped —— qB 流量图重启缝尖峰 P4 呈现层接缝标记实施轮

> 摘要: 用户「实施计划P4」→ 落地 plan `26-10-15-0829` 的 P4(呈现层接缝标记, 消除「无采样区延伸到观察时刻」误读)。改动面: `src/auto_qb/webui/server/traffic_qb.py`(meta 新键 `server_started_at` = 模块级进程出生锚点 `_SERVER_STARTED_AT`) + `src/auto_qb/webui/static/shared/qb_traffic_chart.js`(判据纯函数 `_qbSeamHint` + computed `qbCurSeamHint`) + `src/auto_qb/webui/static/shared/tpl/drawer.html`(「数据接缝中」提示行, 三挂点共用正文块一处) + 两个测试文件。断线语义零改动(null 不连线 spanGaps:false×2 + 斜纹钩子原样)。
> 基线时间: 2026-10-15 14:18

**Refs:** memory-bank/activeContext/26-10-15-0728-qb-traffic-restart-spike-gap.md, memory-bank/plans/26-10-15-0829-plan-qb-traffic-restart-spike-gap.html

## 验收数字

- test.full: 3363 passed + 4 skipped / TOTAL 16916 153 5730 140 99%; 耗时 128.3s(单次采样, 口径见 baseline.md)。
- 对上一基线(P3, 3363+4)同数对账: P4 全部落为**既有用例内的断言扩展**(`test_web_traffic_qb.py` 折入 meta 契约断言)与 **node 电池用例追加**(`test_webui_static_dom_panel.py` 电池 +12 用例), 无新测试函数 → 用例总数不变, 本轮新增断言全部 passed。
- 守阵红绿双验(突变判红后还原复绿, 5 类): ①后端 meta 新键删除 → 2 红 / ②前端尾部未观测区判据删除 → 1 红 / ③链末桶覆盖端判据删除(链内重启误报面放开) → 1 红 / ④新键存在判据删除(旧后端误报) → 1 红 / ⑤模板提示行删除 → 1 红; 还原复绿 `test.one -- tests/test_web_traffic_qb.py tests/test_webui_static_dom_panel.py` 61 passed。活性探针 = node 电池正例 3 条(尾区含重启→提示, 边界含尾区起点与右沿两端)。
- E2E5(观测面验收) = 计划判据为重启后人工观察, 本轮无法在本机完成, 留待真机重启时兑现; E2E1/E2E3(P2 已闭环面)随全量绿不回归。
- 包内脚本测试(commands run test.pkg): 本轮未触 `.commands/` 与 `.agents/skills/commands/`, 未跑。
- Linux(WSL)侧未重测 —— 纯呈现层/meta 加键无平台分支, 本条 Windows 侧数字为事实源。

## 本改动面

- `src/auto_qb/webui/server/traffic_qb.py`: 模块常量 `_SERVER_STARTED_AT`(模块首次导入 ≈ 进程启动后 webui 装配期, 恒先于主循环首拍的首个采样入账; web 热重载重建 router **不重导入**模块, 时刻不漂移 —— 锚点钉进程级而非 router 实例级) + `_meta` 加 `server_started_at`(全部出口同一装配单点: 正常/空态/组空态/降级 last-good 按键展开同样携带); 模块常量非配置键(无 validate_config 面, 黄金法则 4 不触发)。
- `src/auto_qb/webui/static/shared/qb_traffic_chart.js`: `_qbSeamHint(points, interval, meta)` 纯函数(数据链末点早于右沿 ⟺ 末非 null 下标 < n-1; 期间服务重启 ⟺ meta.server_started_at ∈ [链末桶覆盖端, 右沿]; 旧后端无新键/全 null/interval 非法一律 null 不猜) + computed `qbCurSeamHint` 消费单点。
- `src/auto_qb/webui/static/shared/tpl/drawer.html`: 提示行 `<p v-if="qbCurSeamHint" class="qb-stale qb-seam">数据接缝中 · 服务于 {{ fmtTime(...) }} 重启, 之后无采样</p>`(样式复用 .qb-stale 三皮肤同源零新增 CSS, .qb-seam 仅判据/守阵锚点类; 文案单源守阵按字面量计数)。
- `tests/test_web_traffic_qb.py`: 未启用空态用例折入 P4 meta 契约(三端点+空态携带 / 旧 4 键逐字不变 / 改常量新响应立即携带=无实例级缓存面), 24h 用例 meta 全量形状断言含新键; **连带收敛**(用户拍板): 17 处内联鉴权头字典字面量收敛成模块级 `_auth(mgr)` 单点(键名常量拆写, 消写入侧凭据判据误报, 行为零变化 —— 坑档 `pitfalls/testing/credential-shape-write-guard.md`)。
- `tests/test_webui_static_dom_panel.py`: node 电池追加 12 条 `_qbSeamHint` 用例 + 第 6 节静态守阵(判据定义单点 / computed 消费单点 / 模板提示行+文案单源 / spanGaps:false×2 断线语义不变); 两处 docstring 测试清单同步。
- 滚动面: activeContext 切片(追加 R7) · 计划 doc P4 实施记录(doc-updated 抬行) · tasks 立档(触 5 源文件 ≥3, 阈值 #2) · plans 与 tasks 索引(kb.index 重建) · 新坑档 pitfalls/testing/credential-shape-write-guard.md。
