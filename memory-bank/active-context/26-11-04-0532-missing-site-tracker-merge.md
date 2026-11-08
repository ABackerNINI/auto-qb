# missing-site-tracker-merge

> 摘要: 认领并修复 issue 26-11-04-0228: 缺失站点扫描(collect_torrent_tracker_hostnames)复用 store 记录级 tracker 惰性缓存, qB 侧改 tracker 后二次扫描吃首扫旧值; 新增 QbApi.torrents_trackers_fresh 直查(脱敏同口径, 常规读路径不动), 扫描优先走 fresh(非 facade 客户端回退); 主循环消费面核实不受影响(qbmanager 仅新增种子首读/tracker_mod 重绑有意走缓存); 复验仍复现, 红验两条新回归(test_exporter), issue 置 Done, 基线切片 26-11-04-0531
> 最后活动: 2026-11-04 23:16
**Refs:**

**R0(2026-11-04 05:32):** 认领并修复 issue 26-11-04-0228: 缺失站点扫描(collect_torrent_tracker_hostnames)复用 store 记录级 tracker 惰性缓存, qB 侧改 tracker 后二次扫描吃首扫旧值; 新增 QbApi.torrents_trackers_fresh 直查(脱敏同口径, 常规读路径不动), 扫描优先走 fresh(非 facade 客户端回退); 主循环消费面核实不受影响(qbmanager 仅新增种子首读/tracker_mod 重绑有意走缓存); 复验仍复现, 红验两条新回归(test_exporter), issue 置 Done, 基线切片 26-11-04-0531

**R1(2026-11-04 22:06):** 补齐计划 26-11-03-2337 的最后一项 M4 验收: GUI 冒烟三路径(无缺失/全单组/多域名组合并+拆分)真浏览器实跑通过, 计划 doc-status 置 Done; 真实 groups 数据面引用 RM10/RM08 双附加轮, 纯观感仍归用户目视清单

**R2(2026-11-04 23:16):** 计划级 review(3 面串行只读子代理, 8 条发现经 review.check 引文校验): blocker 0; 修复 groups 组名独立 taken 查重、前端判重改 hasOwnProperty.call、补 CLI --split-trackers 透传/缺省与追加+split 用例、明细截断三件套入接线守阵; GUI 冒烟不可复跑入池 issue 26-11-04-2312, exporter 逐种查询吞空集复核旧实现属既有语义(不修)入池 issue 26-11-04-2347, 计划仍 Done
