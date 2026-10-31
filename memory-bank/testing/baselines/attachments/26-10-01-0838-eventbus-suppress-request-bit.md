# 基线 · 1895 passed + 3 skipped / 91% —— issue 0750 认领修复(EventBus suppress 请求位/live 旗标拆分)

> 摘要: 用户指派认领 issues/26-10-01-0750(抑制窗内二次 L2 重建吞 queue_rebuilt → 全局任务丢失),
> 按建议修法实施 **请求位/live 旗标两字段拆分**: EventBus 增 `_replay_requested` + `request_suppression()`
> + `replay_requested` 属性, `take_suppressed()` 改读请求位(不再读 live 旗标); rules.rebuild_runtime
> 置位改挂请求; 内核刷新轮 take→arm→close 消费结构不变。挂请求不置 live 旗标 ⇒ 置位点到下轮
> 轮首之间的相位照常送达 —— 连续重建的第二次 queue_rebuilt 不再被吞, 附带恢复同窗内「未认领段
> 兜底重建」广播(qbmanager apply_new_config)的正确送达。
> 基线时间: 2026-10-01 08:38, develop @ 84473206(未提交工作树)。

TOTAL **1895 passed + 3 skipped / 91%**(13185 语句 / 1052 未覆盖 / 4408 分支 / 436 partial,
test.full 36.5s, rc=0)—— 通过数较 W3 基线 26-10-01-0800 **+1**(新增回归用例
test_rebuild_within_window_still_delivers_queue_rebuilt); 单测面: test_modules_p5 + test_module_host
21 passed(含扩展的 EventBus 两字段协议单元段), test_web 196 passed + 1 skipped。
守阵演进 3 文件: test_modules_p5(模拟置位改挂请求 + 重建断言改请求位并加「不得置 live 旗标」)、
test_web(L2 置位断言同改 + 零动作热重载补请求位断言)、test_module_host(EventBus 单测补两字段
协议段: 挂请求不吞相位 / take 读走请求位 / 读走即清除)。
红验先行: 修复前新增用例单跑 **1 failed**(现象复现坐实), 修复后同用例转绿。
