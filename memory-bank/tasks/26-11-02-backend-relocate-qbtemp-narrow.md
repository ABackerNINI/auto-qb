# 26-11-02-backend-relocate-qbtemp-narrow — 整组迁移 qb_temp 闸门按归属收窄

**Status:** Done
**Added:** 2026-11-02
**Updated:** 2026-11-03
**Summary:** 认领用户报障: WEBUI 单种子移动被外组 .!qB 误拦 —— 归因 relocate P5 三入口接线(现行决策) + qb_temp 收集层未走归属分类; 源码核实 lt 1.2/2.0 逐文件搬运后按归属三分收窄(own 拦 / foreign / unowned 降 note, D1), 计划 26-11-02-0134; 顺带 drawer.js 移动失败 toast 文案; R1 同族第二例(空间/同卷闸门「叶子未建」误拦)按方案A收集层祖先回退(空间+同卷两处同一机制)+方案B note 文案对齐收口; R2 全闸门扫描三项(同卷空间豁免/冲突全量去截断/target_type 闸门, D5-D7) + 覆盖补齐; 守阵累计十几案, 全量绿(数字见 kb.baseline 最新切片); 真机复验已通过(2026-11-03 RM04-10, 环境1, 1 passed: 组外 .!qB 不拦且原地不动 / 组内 .!qB 硬拦 / R1 上溯 / R2 同卷+target_type)
**Topics:** backend-relocate-qbtemp-narrow
**Refs:** memory-bank/plans/26-11-02-0134-plan-relocate-qbtemp-narrow.html

## 原始请求

1. 「WEBUI移动种子时报: 已移动失败: 内容根存在 .!qB 临时文件(413INSTC-305.mp4.!qB): 数据尚未落定, 不能迁 —— 该文件与要移动的种子无关属于误报. 该问题是否由"整组迁移"功能引起? 我记得计划中移动单个种子不触发"整组迁移"。"
2. 「一个小问题顺手修改："已移动失败"改为"移动失败"」（同会话先行落地： drawer.js:768 okText「已移动」→「移动」， 失败 toast 随变「移动失败」）
3. 「收窄后会不会影响安全，需要全面分析」（只读分析轮，产出逐形态×逐场景风险矩阵）
4. 「写计划文档，然后按建议实施」
5. 「先本地提交不推送」（commit c21d4386 未推送， 补推走 ship.push）
6. 「先分析」复测报错 GATE_SPACE「目标卷剩余空间不可判定」（同族，分析轮产出根因链与方案表）
7. 「并入之前的文档，按方案A+B修复」（D3 方案A / D4 方案B， 计划 R1）
8. 「扫描一下还有没有同族问题」→「按建议处置」（全闸门扫描三项：#1 同卷空间硬拦 / #2 冲突 [:50] 截断漏拦 / #3 目标非目录， D5-D7， 计划 R2）

## 思考过程与决策

- **归因**： relocate.enabled=true 时 WEBUI 单种子移动走整组迁移闸门 —— 计划 26-10-18-1604 P2 原表「WebUI 单个直调 setLocation」已被 P5 改版为三入口同闸门（现行决策，非实现走样）。
- **根因**： relocate_mod 收集 qb_temp_entries 时 ext 的 .!qB 在归属分类前被整类抽走；而 libtorrent RC_1_2/RC_2_0 `aux::move_storage`（src/aux_/storage_utils.cpp，源码已核）只遍历种子自己的文件表逐文件搬、只清变空目录 —— 外组/无主 .!qB 与迁移无因果作用；issue #435 的整目录连坐是 lt 1.1 时代行为；真机报告 26-10-18-0826（qB 5.2.3/lt 2.0.13）观测一致。
- **安全分析结论**： 按归属三分收窄不损失实质安全；必须保留「本组文件 .!qB 态硬拦」作 GATE_INCOMPLETE 之外的磁盘态竞态兑底；归属误判两个方向均偏保守（无放行风险）。
- **拍板**： D1 unowned 降 note（推荐 A）； D2 收窄并实施 —— 计划 `26-11-02-0134` §03/§06。
- **老闸门保留面**： gate id `qb_temp` 不改名； dir_alias 内容根专属前提不动； 三入口单点收口。

## 实现计划

总体思路与分步见计划 §04（S1 收集层三分 / S2 文案同步 / S3 守阵 / S4 收尾 DoD），此处不复抄。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | relocate_mod 收集层归属三分（belongs 单次扫描） | Done(2026-11-02) |
| S2 | relocate_units 文案/docstring 同步（gate id 不变） | Done(2026-11-02) |
| S3 | 守阵：原用例升级语义 + 新增 foreign/unowned 两案 | Done(2026-11-02) |
| S4 | test.full 全量 + 基线切片 | Done(2026-11-02) |
| S5 | 真机复验：内容根含外组 .!qB 执行迁移，断言其原地不动（规程 testing/real-machine.md） | Done(2026-11-03): RM04-10 1 passed(环境1 qB 5.2.3; 组外 .!qB 原地不动 / 组内 qb_temp 硬拦 / R1 上溯 / R2 同卷+target_type; 切片 26-11-03-0316-real-RM04-qbtemp) |
| S6 | R1 方案A：_volume_free_resolved 空间祖先回退 + _same_volume_resolved 同卷上溯 | Done(2026-11-02) |
| S7 | R1 方案B：same_fs 单成员 note 文案对齐实现 | Done(2026-11-02) |
| S8 | R1 守阵：祖先回退四案（含整卷不可达仍硬拦）+ 定向与全量绿 | Done(2026-11-02) |
| S9 | R2 #1：同卷空间豁免（same_volume=True 时空间预检不适用，四态守阵） | Done(2026-11-02) |
| S10 | R2 #2/#3：冲突检测全量去截断 + 新闸门 target_type | Done(2026-11-02) |
| S11 | R2 覆盖补齐（退化面四案 + 清单同步），全量回 99% | Done(2026-11-02) |

## 进度日志

### R0 · 立档 (2026-11-02)

问答轮完成归因取证与全面安全分析后，用户拍板按建议实施。本轮：计划 `26-11-02-0134` 建档 → S1-S3 落地（relocate_mod 收集层三分 / relocate_units 文案同步 / 守阵三案）→ 定向 test.one 全绿（relocate 面全部用例）→ test.full 全量绿，数字见 kb.baseline 切片 `26-11-02-0144`；S5 真机复验留 Open。同轮顺带： drawer.js 单种子移动失败 toast 文案「已移动失败」→「移动失败」（用户显式要求，见原始请求 #2）。

- 2026-11-02 01:46 qb_temp 闸门按归属收窄落地(plan 26-11-02-0134): relocate_mod 收集层把 ext 的 .!qB 剥后缀归属三分(own 对回本组→硬拦面; foreign/unowned 与普通条目同走归属分类降 notes), relocate_units 文案与 docstring 同步(gate id 不变), 守阵三案(foreign/unowned/own-matched)+全量绿数字见 kb.baseline 切片 26-11-02-0144; 依据 = lt RC_1_2/RC_2_0 aux::move_storage 逐文件搬运源码核实; S5 真机复验留 Open(计划与档案)

- 2026-11-02 02:22 R1 同族第二例收口(用户复测报 GATE_SPACE 误拦, 拍板按方案A+B修复): relocate_mod 新增 _volume_free_resolved(空间祖先回退)/_same_volume_resolved(同卷上溯, 实施中发现同根因一并收口), 全链不可达维持硬拦; relocate_units same_fs 单成员 note 文案对齐(方案B); 守阵四案+定向 69 passed+全量绿数字见 kb.baseline 切片 26-11-02-0222; 计划 R1(26-11-02-0220)/档案 S6-S8 已并入

- 2026-11-02 03:18 R2 全闸门同族扫描三项处置落地(用户拍板按建议处置): #1 同卷空间豁免(same_volume=True 时空间预检不适用, rename 不占额外空间); #2 目标冲突去 names[:50] 截断改全量(漏拦致进度清零的反向风险); #3 新增 target_type 闸门(目标存在但不是目录); 另补覆盖率退化面守阵四处(首跑 98.86% 红后回 99%); 全量绿数字见 kb.baseline 切片 26-11-02-0317; 计划 R2(26-11-02-0316)/档案 S9-S11 已并入

- 2026-11-03 03:17 S5 真机复验通过(RM04-10, 环境1 qB 5.2.3): 内容根含外组 .!qB 时单种子迁移放行且外组 .!qB/普通条目原地不动; 本组 .!qB 仍 qb_temp 硬拦; R1 目标叶子未建可上溯 + R2 同卷 note/target_type 真跑绿(1 passed); 计划与档案翻 Done
