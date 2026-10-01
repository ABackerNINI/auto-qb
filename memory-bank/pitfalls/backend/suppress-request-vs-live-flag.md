# 总线事件协议: 一符两义的字段必须拆(请求位 != live 旗标)

> 摘要: EventBus suppress 曾把「重放保护请求」与「事件分派相位的抑制」混在一个 `_suppressed` 字段上 —— 注释宣称"窗口只盖两个事件相位", 实现却在置位点到下轮轮首之间吞掉一切 emit, 连续两次 L2 重建时第二次的 queue_rebuilt 静默丢失(issue 26-10-01-0750)。教训: 状态字段一符两义时注释只能描述其中一个语义, 判别与修复都以实现为准, 然后拆字段。
> 触发: 改 EventBus, 改 suppress, 抑制窗口, 重建窗口内 emit, 相位丢失, 事件被吞, queue_rebuilt, 重放保护, 一符两义, 注释与实现不符, set_suppressed, take_suppressed

## 触发

- 给「下一轮才生效」的保护挂标记时, 直接复用了 emit 正在检查的 live 旗标(置位立即生效), 而语义上要的是「请求位」(下轮轮首 take 时才消费) —— 置位点与消费点之间的所有 emit 被误吞。
- 注释/docstring 写的是设计意图(窗口精确覆盖两个事件分派相位), 实现是另一个语义 —— 读代码的人被注释带偏, 走查/真机才暴露。
- 变体: 同窗依赖被吞"碰巧正确"的逻辑(本例: 未认领段兜底重建广播恰好在窗内被吞而未暴露), 拆字段修 bug 时这类隐式依赖会翻面, 要一并核查(`qbmanager.apply_new_config` 的 rebuild_runtime 兜底 emit)。

## 判别

- 现象: 置位窗口内发生的合法 emit 无声丢失(`emit` 返回 0), 无任何报错; 拉开间隔(> 一个刷新周期)后同场景正常 —— 是时序窗口问题, 不是逻辑损坏。
- 代码判别: 对照 emit 路径检查的字段与置位方调用的方法 —— 若置位方调 `set_suppressed(True)`(live, 立即生效)而语义是"下一轮才保护", 即中招。

## 处置

- 拆两个字段: 请求位(`_replay_requested`, `request_suppression()` 挂 / `take_suppressed()` 原子读走)与 live 旗标(`_suppressed`, emit 直接检查, 仅内核刷新轮两事件相位窗口内为 True)。2026-10-01 已落地, 协议单点在 `core/module.py` EventBus docstring; 置位方语义是"下一轮才生效"时只准挂请求位, live 旗标唯一开关点在 `_refresh_torrents`(arm/close)。
- 修复走红验先行: 先写复现用例坐实红, 再改, 同用例转绿 —— 注释与实现漂移的场景里, 注释不可信, 用例才是判据。

## 守阵

- `tests/test_module_host.py::test_eventbus_registration_order_and_suppress`(两字段协议段: 挂请求不吞相位 / take 读走请求位 / 读走即清除)。
- `tests/test_modules_p5.py::test_rebuild_within_window_still_delivers_queue_rebuilt`(抑制窗内二次重建 queue_rebuilt 不被吞, issue 26-10-01-0750 回归)。
