# 26-11-28-test-z-r-ramdisk-tmp-guard — Z:\R 内存盘共享接入(测试/真机落点)与 TMPDIR 候选守卫

**Status:** Done
**Added:** 2026-11-28
**Updated:** 2026-11-28
**Summary:** Z:\R 内存盘共享接入(测试/真机落点)与 TMPDIR 候选守卫
**Topics:** test-z-r-ramdisk-tmp-guard

## 本篇只回答

本机(环境2, VM)的 `Z:\R`(宿主机 `R:\` ImDisk 内存盘的 VMware HGFS 共享)能接入哪些磁盘重 I/O 面、不能接入哪些, 以及随之而来的口径/守卫怎么改。落点结论: 测试 TMPDIR 实例根**不可用**(映射盘 UNC + 无 junction, 实测撤回); 真机大种子与搬迁 RAM 落点**可用**(候选探测 + junction 试建探针)。机制负结果单点在坑档 [tmpdir.md](../pitfalls/testing/tmpdir.md) 与 [coverage-xdist-zero.md](../pitfalls/testing/coverage-xdist-zero.md)。

## 原始请求

1. 「本机环境 Z:\R 是宿主机的 R:\(内存盘), 即共享文件夹, 在测试/真机测试等需要读写磁盘的场景可以使用, 更改相关代码(路径探测?)与口径」。
2. (环境准备前置轮, 已收口)新环境装机: uv/Node/JRE 全局 + commands wrapper + env.sync。

## 思考过程与决策

- **Z:\R 实测能力面**: 可写(普通文件)✓; junction 不可建(cmd mklink /J 报「需要本地 NTFS 卷」)✗; **映射盘被 realpath 解析成 `\\vmware-host\Shared Folders\R\...` UNC**(relocate 用例 save_path 实证)✗。
- **D1 拍板(撤回)**: TMPDIR 自举候选**不加** Z:\R —— 全量 187 failed(卷语义/搬迁闸门把 src 判远程卷 + junction 类用例真建失败), 已回退为 `R: → H: → 系统 %TEMP%`, 元组尾注留守卫文案 + 守卫用例断言「Z: 永不入候选」。
- **D2 拍板(保留)**: 纯写面接入 —— `tests/real/seed.py` RAM_ROOT 候选探测(`R:/qbt-fake` → `Z:/R/qbt-fake`, mkdir+写探针, None 兼容); rm04 `_ram_root` 同候选 + `_junction_ok` 试建探针(junction 需求面探不过退 `.work`) + 候选否决后 `_reclaim_empty` 回收空目录。
- **D3 拍板**: rm04 负向对照由钉死 `Z:` 改 `_absent_drive()` 动态选本机不存在盘(Q:/W:/X:/Y:/V: 逐个探, 全在响亮失败) —— Z: 于 2026-11-28 起真实存在, 原前提翻转。
- **D4 拍板**: sidefx 放行清单登记 `RAM_SCRATCH_ROOTS`(`R:\qbt-fake` / `Z:\R\qbt-fake`)为 FSDEL/SYMLINK 放行面(内存盘探针的删除/建链是刻意行为), 两侧同经 `_norm_path` 归一比对(映射盘 UNC 形态)。
- **D5 拍板**: dev.run 的 state/logs **不挪**(黄金法则 3 状态持久化, 内存盘重启即清); sim 面不改默认根, 只补 `AUTOQB_SIM_ROOT=Z:/R/auto-qb-sim` 口径。
- 顺带实证(与本批改动无关, 已入坑档): 本机 `pytest tests` 形态覆盖率恒 0% 且闸静默放行(rc=0), 等价收集面 `pytest tests/unit` 正常(99.51% 闸过); 另本机 VM 算力较基线校准机慢 ~2.2x, traffic bucket perf 阈值(150ms 线)确定性翻红 —— 均属环境面, 未动公共任务与阈值。

## 实现计划

总体思路: 先探针实证能力面(junction/UNC/可写) → 依证据定接入面(纯写面进、语义面退) → 代码候选探测 + 守卫 → 口径文档同步 → 全量验证 + 基线切片 + 评审循环。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | Z:\R 能力探针(可写/junction/UNC) | Done(2026-11-28) |
| 2 | TMPDIR 候选接入 Z:\R → 全量 187 红 → 撤回 + 守卫钉死 | Done(2026-11-28) |
| 3 | seed.py RAM_ROOT 候选探测 + None 兼容 + 叙述面 | Done(2026-11-28) |
| 4 | rm04 _ram_root 候选+junction 探针+回收; 负向对照动态缺盘 | Done(2026-11-28) |
| 5 | sidefx RAM_SCRATCH_ROOTS 放行 + 守卫用例 + 判定表同步 | Done(2026-11-28) |
| 6 | 口径文档 4 件 + .commands 注释 + kb.index | Done(2026-11-28) |
| 7 | 评审循环(轮1 5 发现 → 全修 → 轮2 零 actionable) | Done(2026-11-28) |
| 8 | 全量验证 + 基线切片(26-11-28-0402) | Done(2026-11-28) |
| 9 | 真机端到端回归(seed/rm04 需真实 qB) | Open(待 qB 环境) |

## 进度日志

### R0 · 立档 (2026-11-28)

用户请求 Z:\R 接入; 完成探针实证、TMPDIR 撤回守卫、真机纯写面接入(候选探测)、负向对照动态化、sidefx 放行、口径 4 件与坑档 2 件(tmpdir 增段 + coverage-xdist-zero 新档)、基线切片 26-11-28-0402; 评审两轮(3 minor + 2 nit 全修, 复评零 actionable); 终版 test.full 7073P/6S([ok], 含远端同步进的 Web 鉴权守阵 +15; 覆盖率面按 unit 形态 99.51% 闸过背书, 见坑档)。待办: 真机 qB 环境下跑 real.seed/rm04 端到端(子任务 9 Open)。

- 2026-11-28 04:38 环境装机(uv/Node/JRE 全局 + commands wrapper + env.sync) 与 Z:\R 接入: TMPDIR 候选撤回守卫、真机纯写面候选探测(seed/rm04/junction 探针)、负向对照动态缺盘、sidefx 内存盘放行、口径 4 件 + 坑档 2 件、基线切片 26-11-28-0402; 评审两轮 5 发现全修零 actionable
