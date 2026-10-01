# 基线 · 1909 passed + 3 skipped / 91% —— 审计 M3 跟进修复(订阅者异常约定明文化 + 守阵)

> 摘要: 内核化重构审计报告(reports/26-10-01-0918)M3 跟进修复 —— EventBus 订阅者异常行为此前
> 零约定零测试(横跨 10 模块的隐式契约); 按 §09 建议 3 行为不变收口: 「订阅者异常 = 牺牲本轮
> 剩余管线, 由主循环兜底」明文写进 conventions/modules.md「订阅者异常约定」节(无逐订阅者隔离 /
> 模块作者义务 / 改隔离属行为变更须拍板, 三条), module.py emit 与 ModuleHost docstring 补契约
> 指针; 守阵 2 例(test_module_host): 总线上抛 + 剩余订阅者跳过 + 总线状态不损坏, 三条 loop
> hook 线逐线上抛 + 剩余模块跳过(三个分发循环是独立代码, 逐线锁住)。
> 基线时间: 2026-10-01 18:13, develop @ d389ab01(未提交工作树, 含 M3 修复改动)。

TOTAL **1909 passed + 3 skipped / 91%**(13281 语句 / 1049 未覆盖 / 4408 分支 / 433 partial,
test.full 23.8s, rc=0)—— 通过数较 M2 基线 26-10-01-1752 **+2**(异常契约守阵 2 例);
同轮附注两笔: ①改 conventions/modules.md 后先跑测试漏了 kb.index, `test_kb_index_is_regenerated`
机检红一次, 重建后绿 —— 守卫按设计工作(失败信息直接指路), 未入坑档; ②合流 d389ab01(1758
路线图计划)后 `test_claim_chain_is_bidirectional` 红 —— 1758 声明 doc-refs 但 1728 / 2036
两目标件未反向声明, 按 M1+M2 轮 scope-guard 例外 1(阻塞)先例各补一行反向引用(非本任务范围,
已向用户点名)。
