# missing-site-tracker-merge

> 摘要: 认领并修复 issue 26-11-04-0228: 缺失站点扫描(collect_torrent_tracker_hostnames)复用 store 记录级 tracker 惰性缓存, qB 侧改 tracker 后二次扫描吃首扫旧值; 新增 QbApi.torrents_trackers_fresh 直查(脱敏同口径, 常规读路径不动), 扫描优先走 fresh(非 facade 客户端回退); 主循环消费面核实不受影响(qbmanager 仅新增种子首读/tracker_mod 重绑有意走缓存); 复验仍复现, 红验两条新回归(test_exporter), issue 置 Done, 基线切片 26-11-04-0531
> 最后活动: 2026-11-04 05:41
**Refs:**

**R0(2026-11-04 05:32):** 认领并修复 issue 26-11-04-0228: 缺失站点扫描(collect_torrent_tracker_hostnames)复用 store 记录级 tracker 惰性缓存, qB 侧改 tracker 后二次扫描吃首扫旧值; 新增 QbApi.torrents_trackers_fresh 直查(脱敏同口径, 常规读路径不动), 扫描优先走 fresh(非 facade 客户端回退); 主循环消费面核实不受影响(qbmanager 仅新增种子首读/tracker_mod 重绑有意走缓存); 复验仍复现, 红验两条新回归(test_exporter), issue 置 Done, 基线切片 26-11-04-0531
