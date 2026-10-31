# 基线 · 1907 passed + 3 skipped / 91% —— 审计 M2 跟进修复(_rebuild_needed 判据矩阵参数化守阵)

> 摘要: 内核化重构审计报告(reports/26-10-01-0918)M2 跟进修复 —— `_rebuild_needed` 六判据此前只有
> interval 被单测单独触发过, 实现漏掉任一成员现有守阵全绿; 补参数化矩阵 11 例(test_modules_p5):
> 五个段级判据(rules_config/interval/delete_tags/delete_tags_if_has_no_torrents/global_speed_limit_curve)
> 逐段单独变更 + trackers 绑定三元组逐成员(domains/rules/groups)与增删各一例断言 rebuilt,
> 另 1 例负例锁「三元组外运行时现读字段(tags/remove_tags/限速/hr_check)变化不重建」(过度重启族防线)。
> 变异验证两例(删 rules_config 判据成员 / 三元组比较漏 groups)均被矩阵精准抓红, 修复前修复后守阵有效。
> 基线时间: 2026-10-01 17:52, develop @ 38604d07(未提交工作树, 含 M1 修复改动)。

TOTAL **1907 passed + 3 skipped / 91%**(13281 语句 / 1050 未覆盖 / 4408 分支 / 434 partial,
test.full 24.4s, rc=0)—— 通过数较 M1 基线 26-10-01-1643 **+11**(矩阵 10 例 + 负例 1 例);
同轮顺手处理一笔认领链阻塞(38604d07 新计划 1728 声明 3 条 doc-refs 而目标件未反向声明,
test_claim_chain_is_bidirectional 红): 按 scope-guard 例外 1(阻塞)给 1819/0350 两计划与 0918 审计报告
的 doc-refs 补反向引用闭环, 非本任务范围、收尾已向用户点名。
