# real-machine-rm04-drift-plan

> 摘要: RM04 漂移复测计划收尾: RM04-05 负向对照 Z:/ 上溯整链不可判定红验落地(issue 26-11-02-1144 闭环), RM04-09 facade shareLimitAction PASS(issue 26-11-01-2102 闭环), 计划 Done. issue 26-11-02-1208 仍 In Progress: 纯函数层四条判别红验已闭环; 真机 L490 段改为显式入口 QBT_REAL_SMALL_TARGET + 硬守卫; 上一轮「隐藏 Recovery 卷 + mklink /J」做法已废弃并彻底移除(该卷是系统恢复分区); 本轮重跑主链全过、L490 段以明确断言失败提示用户准备小容量卷(非 skip), 待前置复验.
> 最后活动: 2026-11-03 00:38
**Refs:** memory-bank/plans/26-11-01-2033-plan-real-machine-rm04-drift-plan.html, memory-bank/issues/26-11-02-1208-bug-rm04-gate-space-crossvol-branch-missing.html

**R0(2026-11-02 12:13):** RM04 漂移复测计划收尾: RM04-05 负向对照 Z:/ 上溯整链不可判定红验落地(issue 26-11-02-1144 闭环), RM04-09 facade shareLimitAction PASS(issue 26-11-01-2102 闭环), 真机 9 passed 全绿, 计划 Done. 方案B跨卷空间不足分支另立 issue 26-11-02-1208 交他环境.

**R1(2026-11-02 22:07):** 认领修复 issue 26-11-02-1208: L490 跨卷空间不足分支在纯函数闸门层补四条判别红验(严格小于才拒/恰等放行/same_volume=None 保守拒/同卷豁免), 产品代码零改动; issue 置 Done; 全量数字见基线切片 26-11-02-2206. (R1 里「真机前置本机不可造」的前提已被 R2 更正)

**R2(2026-11-02 22:43):** 前提更正重做真机验证: 接手机环境1 与撰写 issue 的环境2 不同, 隐藏 Recovery 卷(free 86,564,864)经 mklink /J 造出「跨卷 + target_free<needed」前置并跑 L490 拒绝分支 —— status=error + gate=space + 文案「空间不足」+ 零 started + 零「迁移发起」; RM04-05 单跑 1 passed 94.55s, RM04 套件 9 passed 186.99s; 改动仍在 tests-real + 纯函数红验, src/ 零 diff; issue 维持 Done 并改写错误改道理由; 真机数字见 real-baselines 26-11-02-2243. (该隐藏卷构造已废弃并移除, 见 R4)

**R3(2026-11-02 22:51):** issue 26-11-02-1208 前提更正后重做真机 RM04-05 L490 跨卷空间不足分支: 隐藏 Recovery 卷经 junction 造前置, 真跑命中拒绝分支, RM04 套件 9 passed; issue 维持 Done 并改写错误改道理由. (**该做法已废弃并移除, 见 R4**)

**R4(2026-11-02 23:46):** 磁盘安全性复验: 隐藏 Recovery 卷构造已废弃并彻底移除(用例删 _volume_roots/small_volume_junction, 文档/issue/基线改为『曾用过、已废弃并移除』并保留证据链); 新增 tests-real/lib/small_target.py 显式入口 QBT_REAL_SMALL_TARGET + 硬守卫与 tests/test_real_machine_safety.py 复发守卫(4 passed); 正向对照证明普通大容量目录不等价于真跨卷; 真机重跑 RM04-05 1 failed 8 deselected 33.09s(唯一失败为 L490 段前置缺失显式断言, 主链全过); issue 退回 In Progress 待用户准备小容量目标; 产品代码零改动; 全量 4899 passed 2 skipped

**R5(2026-11-03 00:06):** ImDisk 内存盘前置调研: 官方 CLI 语法/-o fix-rem/-s 单位/-d-强制-D 卸载确认; 本机 imdisk 2.1.1 驱动 RUNNING、AWEAlloc STOPPED; 当前进程 Medium 未提权, 非提权尝试产生半挂载设备 0 + 格式化失败(退出码 0 但 Y: 不存在), 已用 -D 清理; 配方写入 real-machine.md §2.9 作为首选; issue 1208 维持 In Progress 待用户提权实跑

**R6(2026-11-03 00:38):** issue 26-11-02-1208 真机复验跑通: 用户手动挂载 ImDisk 96M 内存盘(Y: FreeSpace 84,054,016 < needed 134,217,728, st_dev 互异), QBT_REAL_SMALL_TARGET 下 RM04-05 六条 L490 断言全成立(1 passed 32.90s), RM04 套件 9 passed 199.57s, 全量 4909 passed 2 skipped; issue 置 Done; real-machine.md §2.9 改 ImDisk 为唯一指定前置; 测试实例已关停, 内存盘保留待用户卸载; src 零 diff
