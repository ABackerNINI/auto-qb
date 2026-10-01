# 26-10-01-backend-eventbus-suppress-request-bit — EventBus suppress 请求位/live 旗标拆分(issue 0750)

**Status:** Done
**Added:** 2026-10-01
**Updated:** 2026-10-01
**Summary:** 用户指派认领 issues/26-10-01-0750(抑制窗内二次 L2 重建吞 queue_rebuilt → 全局任务从新队列丢失): EventBus 拆请求位(_replay_requested + request_suppression/take_suppressed 消费)与 live 旗标(_suppressed, emit 直接检查, 仅 _refresh_torrents 两事件相位窗口内为 True), rebuild_runtime 改挂请求位; 红验先行(新回归用例修复前 1 failed)修复后全绿, test.full 1895 passed + 3 skipped / 91%(基线 26-10-01-0838)。

**Topics:** events-suppress-window

**Legacy-ID:** 无

## 原始请求

用户: 「认领26-10-01-0750-bug-events-suppress-window-queue-rebuilt.html」—— 指派认领该计划外 bug
(别名层处置 W3 四场景 sim 走查发现: S3→S4 两次 PUT 间隔约 0.5s, S4 的 L2 重建照常发生但
queue_rebuilt 相位被总线抑制吞掉, 全局任务 delete_tags 未重注册进新队列)。按 create-issue skill
「修一条 issue 时」流程走: 置 In Progress → 复验 → 修 → 置 Done。

## 思考过程与决策

- **修法按 issue 建议方向(拆两个字段), 不走备选最小修**: 备选「emit(queue_rebuilt) 前先 take 掉旧请求
  再置位」只救连续重建场景, 窗口吞其它相位的问题仍在 —— 且复验时发现同窗还会吞
  `qbmanager.apply_new_config` 的「未认领段兜底重建」广播(`emit("rebuild_runtime")`, qbmanager.py:626,
  在 host.apply_all 之后发出; 与 L2 重建同轮热重载时被静默吞掉, 兜底失效), 拆字段一并恢复, 两案差距更大。
- **消费点结构不动**: `_refresh_torrents` 的 take(轮首)→arm(events_removed 前)→close(events_added 后)
  三点语义原样, 只把 take 的读取对象从 live 旗标换成请求位 —— 单次重建的外显行为逐字节不变
  (emit(queue_rebuilt) 本就在置位前送达), 全量轮重放保护照旧。
- **API 命名**: 挂载方 `request_suppression()`、只读 `replay_requested` 属性(测试断言用)、消费方沿用
  `take_suppressed()` 旧名(零调用方改名, docstring 改述请求位语义); `set_suppressed` 保留为 live 旗标
  唯一开关(生产调用点只剩 _refresh_torrents arm/close 两处)。
- **窗口内不可能轮中重建**(单线程核实): rebuild 只发生在热重载 apply_all(主循环命令线), 不在
  _refresh_torrents 相位消费内; 请求位无需计数, 幂等布尔即够(多次重建=同一份"保护下轮"请求)。
- **主题文档回写核查结论**: suppress 协议细节单点在 `core/module.py` EventBus docstring(已同波改写);
  `conventions/modules.md` 不含协议细节, `modules/core-runtime.md` 的行数是带日期快照且其 suppress
  描述("语义等价 _suppress_events")指外显语义、本次未变 —— 均无需回写。

## 实现计划

单轮实施(issue 自带建议修法, 无独立计划文档):

1. 复验: 锚点 4/4 核实(module.py emit / rules_mod emit+置位 / qbmanager take / maintenance 收事件才注册)
   + 新增回归用例红验(修复前 1 failed, 现象仍复现)。
2. 实施: EventBus 两字段 + rules_mod 调用点 + qbmanager 注释口径 + 三处 docstring。
3. 守阵演进: test_modules_p5(2 处)/test_web(2 处)/test_module_host(1 处扩展)+ 新回归用例。
4. 验证: 单文件绿 → test.full 全量 → 基线切片 26-10-01-0838。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 复验(锚点核实 + 红验用例坐实现象仍复现) | Done |
| 2 | EventBus 两字段拆分(请求位/live 旗标)+ rules_mod 改挂请求位 + docstring 同步 | Done |
| 3 | 守阵演进(test_modules_p5/test_web/test_module_host)+ 回归用例转绿 | Done |
| 4 | issue 状态流转(Open→In Progress→Done)+ 索引重建 | Done |
| 5 | 基线切片 + 坑档(suppress-request-vs-live-flag)+ activeContext 切片 | Done |

## 进度日志

- **2026-10-01 08:24 认领 + 复验**: `my-commit-flow.sync` 同步 84473206; 锚点 4/4 核实未漂移; 新增
  `test_rebuild_within_window_still_delivers_queue_rebuilt` 单跑 1 failed —— 现象仍复现(红验)。
  附带发现: 同窗吞 `apply_new_config` 未认领段兜底重建广播(同根, 拆字段一并恢复), 已记入 issue 复验行。
- **2026-10-01 08:38 修复收官**: 实施与守阵演进完成, 红验用例转绿; test.full **1895 passed + 3 skipped /
  91%**(36.5s, 基线 26-10-01-0838, 较 W3 基线 +1 = 新增回归用例); issue 置 Done, 索引重建; 坑档
  `pitfalls/backend/suppress-request-vs-live-flag.md` 新立(一符两义教训)。未提交(等用户显式指令)。
