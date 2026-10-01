# 基线 · 1896 passed + 3 skipped / 91% —— 审计 M1 跟进修复(重放保护请求位消费点移到 arm 处)

> 摘要: 内核化重构审计报告(reports/26-10-01-0918)M1 跟进修复 —— 0750 两字段协议的请求位
> 消费点从刷新轮轮首移到 events_removed 相位前(take 即 arm, 相邻无窗): apply_sync/full_round/
> transitions 抛异常的失败轮不再消费请求位, 抑制跨失败轮存活到下一个成功轮(原 _suppress_events
> 语义); 否则失败轮读走请求而旗标未挂, 下一轮全量同步(rid 已失效)把存量种子全判 added,
> 事件规则对全库重放。协议单点 EventBus docstring / 坑档 suppress-request-vs-live-flag 同波改写。
> 基线时间: 2026-10-01 16:43, develop @ 1616ea1a(未提交工作树)。

TOTAL **1896 passed + 3 skipped / 91%**(13281 语句 / 1052 未覆盖 / 4408 分支 / 436 partial,
test.full 29.4s, rc=0)—— 通过数较 0750 基线 26-10-01-0838 **+1**(新增回归用例
test_suppression_request_survives_failed_round); 守阵面: 新用例红验先行(修复前单跑 1 failed,
坐实失败轮丢请求位), 修复后同用例转绿; suppress 相关既有守阵(test_modules_p5 窗口两用例 /
重建两用例 + test_module_host 全文件)15 passed 零回归。
改动面 4 源文件: qbmanager.py(消费点迁移 + 注释)/ module.py(三处 docstring 协议口径)/
rules_mod.py(docstring 一处)/ test_modules_p5.py(新用例 + 测试计划清单)。
