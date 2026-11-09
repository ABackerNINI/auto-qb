# backend-relocate-relpath-finalize

> 摘要: 认领并修复 issue 26-11-07-2336(已翻 Done): fastresume 相对键按 profile base 解析改写 —— qB 源码实证三键 toPortablePath/basePath=BT_backup 上两级/portable 恒开, 改写器四件新增(_split_absolute/_relative_form/_resolve_relative/profile_base_of)+ retarget 接线, 解析不命中保守跳过(N10 修定不废除), 建议②预检告知失去前提不做; 评审 4 轮(轮1 blocker2+nit2 全修, 轮2-4 零 actionable), 坑档 patching 复发+1; 全量全绿见 kb.baseline, 基线切片 26-11-10-0132; 真机 E2c 同盘拓扑复验留待下次真机轮
> 最后活动: 2026-11-10 02:40

**R0(2026-11-10 01:32):** 认领并修复 issue 26-11-07-2336(已翻 Done): fastresume 相对键按 profile base 解析改写 —— qB 源码实证三键 toPortablePath/basePath=BT_backup 上两级/portable 恒开, 改写器四件新增(_split_absolute/_relative_form/_resolve_relative/profile_base_of)+ retarget 接线, 解析不命中保守跳过(N10 修定不废除), 建议②预检告知失去前提不做; 评审 4 轮(轮1 blocker2+nit2 全修, 轮2-4 零 actionable), 坑档 patching 复发+1; 全量全绿见 kb.baseline, 基线切片 26-11-10-0132; 真机 E2c 同盘拓扑复验留待下次真机轮

**R1(2026-11-10 02:40):** 真机 E2c 同盘拓扑复验(子代理): 收敛 6/6 断言 PASS —— 前提相对形态成立/daemon 窗非 mover rewritten/产物新根绝对形态/重启全员落位零 recheck/job done 别名删净/幂等零落盘; 真机窗因生产实例常驻经用户授权走 _spawn_daemon 测试接缝旁路(名册窄化镜像路径级, 两证原样), 立坑档 testing/relocate-window-machine-roster; issue 复验行与档案子任务表第 6 步同步翻 Done
