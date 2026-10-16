# 3475 passed + 4 skipped —— 全局流量监视小工具 S7 auto-qb 接收面(根集新增 24 条守阵)

> 摘要: 用户「实施S7:26-10-16-0541-plan-global-traffic-monitor.html」(对 S7 的显式授权, S8–S10 不动)。改动面: ①路由 `POST /api/traffic/monitor/notify`(接收面: 六键事件体校验 + 事件号/冷却双闸 per app 实例); ②新文件 `webui/tool_client.py`(工具控制面客户端上移为共享件 + 订阅客户端 `TrafficMonitorSubscriber`); ③`webui/module.py` 订阅生命周期三时刻接线; ④`webui/commands.py` 新命令 `refresh_traffic`; ⑤`speed_curve_mod.py` 数据源读法单点 + 只读刷新入口 `refresh_traffic_view`; ⑥前端 `dialogs.js` 历史弹层快照 ts 变化即重拉; ⑦两个新守阵文件。本切片为根 test.full 回归闸门数字。
> 基线时间: 2026-10-16 14:04

- test.full: 3475 passed + 4 skipped / TOTAL 17633 245 5990 177 98%(98.21%); 耗时三次采样 242.34s / 221.9s / 217.29s(墙钟 244.8s / 231.5s / 222.6s; 末次 = 提交前 dev.fmt 后的终态 —— dev.fmt 只动了路由模块的排版, 行为零变化; 报耗时带区间, 口径见 testing/baseline.md)。
- 合流后复测(与远端他人提交 d58ad0c5「前端旁路裸 fetch 无超时」合并后的同一棵树): **3476 passed + 4 skipped**(TOTAL 同上, 耗时 214.42s / 墙钟 216.9s) —— 多出的 1 条来自对方提交对该轮测试文件的改动, 与本步零关系。
- 根集 passed 较本轮改动前同 clone 基线(3451 passed + 4 skipped)增 24 —— 新增守阵 `tests/test_traffic_monitor_client.py`(16 条)+ `tests/test_web_traffic_monitor_notify.py`(8 条); 无存量用例增删。
- 工具侧自测未跑(本轮零 `tools/` 改动; 工具仍为 S6 后的 173 passed)。
- 红验(临时脚本 `.zcode-tmp/s7_redverify.py`: 解释器钉死仓库 venv、bytes 层读写、锚点 count==1 兜底、突变前先跑无变异基线、还原后逐字节恒等 + 复跑基线复绿、子进程 300s 超时且接住 `TimeoutExpired`): **6 条锚点突变全判 RED** —— 事件号去重失效(1 红)/ 冷却窗口失效(1 红)/ 曲线未启用也刷新(1 红)/ 期望态整体退回真值判(4 行同改, 1 红)/ 订阅载荷丢回调凭证(1 红)/ 命令表漏注册(2 红); 还原后基线 24 passed 复绿, 四文件字节恒等。
- **未闭合项**: 计划 S7 出口原文的**真机联调**一段(真 gtm 进程发事件 → 浏览器里看历史图与顶栏刷新, 对照 E2)未做 —— 需工具进程在跑 + 浏览器; 本轮以**进程内端到端**守阵钉住同一条链路。留待 S10 或工具在跑时补。

## 出口判据逐条(计划 §04 S7)

- **端点鉴权 / 冷却 / 重复事件单测**: `tests/test_web_traffic_monitor_notify.py` 8 条 —— 无 Bearer 401 / 路由路径与 `tool_client.NOTIFY_PATH` 同源 / 六键事件体逐个校验(400 且一个命令都不投)/ 合法事件投递 `refresh_traffic` 并唤醒主循环 / 同一事件号重复投递 skipped:duplicate / 冷却窗口内新事件号 skipped:cooldown 且冷却归零后放行 / 联动总开关关 action=disabled 不投递 / 接收闸 per app 实例。
- **订阅生命周期**: `tests/test_traffic_monitor_client.py` 16 条 —— 期望态四闸 / 回调 endpoint 形状 / 注册记住 id 与心跳周期 / 已注册只心跳 / 注册键变化重注册 / 心跳 404 重注册 / 联动关掉注销并收线 / 失败同因只 WARNING 一次 / stop 有界且超时不摘线程引用 / 线程 sync→注册→stop→注销 / 线程自收线 / 桩配置(MagicMock)不起线程 / 只读刷新不碰 qB 限速 / 跳过三形态 / 命令经主循环 drain / 端到端。
- **只读刷新口径**: qB 限速读写被替身为记录器, 守阵断言**一次都没发生**; `history`/`periods` 重算, `state`/`limit` 沿用上一份快照(不查档、不改限速决策)。
- **红验判红后还原复绿**: 见上(6 条)。

## 本改动面

- `src/auto_qb/webui/server/routes/traffic_monitor.py`(接收面端点 + `NotifyGate` + 事件体校验; HTTP 与密钥定位单点改从 `...tool_client` 别名导入, S6 守阵打桩点逐字不变)
- `src/auto_qb/webui/tool_client.py` **新文件**(工具控制面客户端 + `TrafficMonitorSubscriber`)
- `src/auto_qb/webui/module.py`(start 后 sync / apply 后 sync / stop 先注销再停服务)
- `src/auto_qb/webui/commands.py`(`refresh_traffic` 命令 + handler)
- `src/auto_qb/core/modules/speed_curve_mod.py`(`_read_source_rows` 读法单点 / `_history_rows` / `_period_rows` / `refresh_traffic_view`)
- `src/auto_qb/webui/static/shared/dialogs.js`(历史弹层开着时 `status.traffic.ts` 变化即重拉)
- `tests/test_traffic_monitor_client.py` / `tests/test_web_traffic_monitor_notify.py` **新文件**
- `tests/helpers.py`(FakeConfig 补 `global_traffic_monitor` 段, 与真 Config 同默认)+ `tests/test_web_route_manifest.py`(金清单 80→81)
- 文档: 计划 HTML(§04 R0 增 S7 行 + 状态行/脚注)· 档案 R8 · 坑档 `pitfalls/ops/agent-write-guard-secret-false-positive.md`(扩写: 判据连带拦下**记录类**文件 + 处置优先级)
- 经验: 期望态/订阅注销寻址两处按单测反馈收紧(见档案 R8 的「实施期发现」)

**Refs:** memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md, memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html
