# 26-11-02-backend-relocate-qbtemp-narrow — 整组迁移 qb_temp 闸门按归属收窄

**Status:** In Progress
**Added:** 2026-11-02
**Updated:** 2026-11-02
**Summary:** 认领用户报障: WEBUI 单种子移动被外组 .!qB 误拦 —— 归因 relocate P5 三入口接线(现行决策) + qb_temp 收集层未走归属分类; 源码核实 lt 1.2/2.0 逐文件搬运后按归属三分收窄(own 拦 / foreign / unowned 降 note, D1), 计划 26-11-02-0134; 守阵三案+定向与全量绿(数字见 kb.baseline 26-11-02-0144); 顺带 drawer.js 移动失败 toast 文案; 真机复验留 Open
**Topics:** backend-relocate-qbtemp-narrow
**Refs:** memory-bank/plans/26-11-02-0134-plan-relocate-qbtemp-narrow.html

## 原始请求

1. 「WEBUI移动种子时报: 已移动失败: 内容根存在 .!qB 临时文件(413INSTC-305.mp4.!qB): 数据尚未落定, 不能迁 —— 该文件与要移动的种子无关属于误报. 该问题是否由"整组迁移"功能引起? 我记得计划中移动单个种子不触发"整组迁移"。"
2. 「一个小问题顺手修改："已移动失败"改为"移动失败"」（同会话先行落地： drawer.js:768 okText「已移动」→「移动」， 失败 toast 随变「移动失败」）
3. 「收窄后会不会影响安全，需要全面分析」（只读分析轮，产出逐形态×逐场景风险矩阵）
4. 「写计划文档，然后按建议实施」

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
| S5 | 真机复验：内容根含外组 .!qB 执行迁移，断言其原地不动（规程 testing/real-machine.md） | Open |

## 进度日志

### R0 · 立档 (2026-11-02)

问答轮完成归因取证与全面安全分析后，用户拍板按建议实施。本轮：计划 `26-11-02-0134` 建档 → S1-S3 落地（relocate_mod 收集层三分 / relocate_units 文案同步 / 守阵三案）→ 定向 test.one 全绿（relocate 面全部用例）→ test.full 全量绿，数字见 kb.baseline 切片 `26-11-02-0144`；S5 真机复验留 Open。同轮顺带： drawer.js 单种子移动失败 toast 文案「已移动失败」→「移动失败」（用户显式要求，见原始请求 #2）。

- 2026-11-02 01:46 qb_temp 闸门按归属收窄落地(plan 26-11-02-0134): relocate_mod 收集层把 ext 的 .!qB 剥后缀归属三分(own 对回本组→硬拦面; foreign/unowned 与普通条目同走归属分类降 notes), relocate_units 文案与 docstring 同步(gate id 不变), 守阵三案(foreign/unowned/own-matched)+全量绿数字见 kb.baseline 切片 26-11-02-0144; 依据 = lt RC_1_2/RC_2_0 aux::move_storage 逐文件搬运源码核实; S5 真机复验留 Open(计划与档案)
