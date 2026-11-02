# relocate-qbtemp-narrow

> 摘要: qb_temp 闸门按归属收窄落地(plan 26-11-02-0134): relocate_mod 收集层把 ext 的 .!qB 剥后缀归属三分(own 对回本组→硬拦面; foreign/unowned 与普通条目同走归属分类降 notes), relocate_units 文案与 docstring 同步(gate id 不变), 守阵三案(foreign/unowned/own-matched)+全量绿数字见 kb.baseline 切片 26-11-02-0144; 依据 = lt RC_1_2/RC_2_0 aux::move_storage 逐文件搬运源码核实; S5 真机复验已通过(2026-11-03 RM04-10, 环境1, 1 passed; 切片 26-11-03-0316-real-RM04-qbtemp)
> 最后活动: 2026-11-03 03:17
**Refs:**

**R0(2026-11-02 01:46):** qb_temp 闸门按归属收窄落地(plan 26-11-02-0134): relocate_mod 收集层把 ext 的 .!qB 剥后缀归属三分(own 对回本组→硬拦面; foreign/unowned 与普通条目同走归属分类降 notes), relocate_units 文案与 docstring 同步(gate id 不变), 守阵三案(foreign/unowned/own-matched)+全量绿数字见 kb.baseline 切片 26-11-02-0144; 依据 = lt RC_1_2/RC_2_0 aux::move_storage 逐文件搬运源码核实; S5 真机复验留 Open(计划与档案)

**R1(2026-11-02 02:22):** R1 同族第二例收口(用户复测报 GATE_SPACE 误拦, 拍板按方案A+B修复): relocate_mod 新增 _volume_free_resolved(空间祖先回退)/_same_volume_resolved(同卷上溯, 实施中发现同根因一并收口), 全链不可达维持硬拦; relocate_units same_fs 单成员 note 文案对齐(方案B); 守阵四案+定向 69 passed+全量绿数字见 kb.baseline 切片 26-11-02-0222; 计划 R1(26-11-02-0220)/档案 S6-S8 已并入

**R2(2026-11-02 03:18):** R2 全闸门同族扫描三项处置落地(用户拍板按建议处置): #1 同卷空间豁免(same_volume=True 时空间预检不适用, rename 不占额外空间); #2 目标冲突去 names[:50] 截断改全量(漏拦致进度清零的反向风险); #3 新增 target_type 闸门(目标存在但不是目录); 另补覆盖率退化面守阵四处(首跑 98.86% 红后回 99%); 全量绿数字见 kb.baseline 切片 26-11-02-0317; 计划 R2(26-11-02-0316)/档案 S9-S11 已并入

**R3(2026-11-03 03:17):** S5 真机复验通过(RM04-10, 环境1 qB 5.2.3): 内容根含外组 .!qB 时单种子迁移放行且外组 .!qB/普通条目原地不动; 本组 .!qB 仍 qb_temp 硬拦; R1 目标叶子未建可上溯 + R2 同卷 note/target_type 真跑绿(1 passed); 计划与档案翻 Done
