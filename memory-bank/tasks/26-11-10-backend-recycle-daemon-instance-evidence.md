# 26-11-10-backend-recycle-daemon-instance-evidence — recycle daemon 实例级下线证据链(P7 多实例收尾窗解卡): grilling 拍板 + 计划立档

**Status:** In Progress
**Added:** 2026-11-10
**Updated:** 2026-11-10
**Summary:** recycle daemon 实例级下线证据链(P7 多实例收尾窗解卡): grilling 三轮拍板(D1-D5) + 计划立档, 实装待认领
**Topics:** backend-recycle-daemon-instance-evidence
**Refs:** memory-bank/issues/26-11-07-0528-feat-recycle-daemon-roster-machine-wide.html, memory-bank/plans/26-11-10-0318-plan-recycle-daemon-instance-evidence.html

## 本篇只回答

P7 形态(同机多 qB 实例, 目标已死日常在跑)下 recycle daemon 收尾窗如何在不破 N1 铁律的前提下解卡——证据链形态、判据语义、退化路径的拍板与计划落点。实装执行进 plan 认领后另起轮次。

## 原始请求

1. 用户指派 issue 26-11-07-0528(feat: 回收 daemon 进程名册证为全机口径, P7 收尾窗让位 N1 的取舍记录+增强方向):「grilling 然后出一个方案」。
2. 三轮 grilling 答复: Q1 按推荐(实装)/Q2 方案 A 但 30s 稳定期降级(进程级证据成立即立即收尾)/Q3 daemon 常驻/Q4 事实反问(何时会有非同机收尾?)/Q5 按推荐(默认开无配置键)。
3. 「出方案」→ 计划单文件 HTML 立档;「提交」→ 收尾 DoD + 入库。

## 思考过程与决策

- 事实核查先行: 判据现状(`_proc_absent` 全机口径 `recycle_daemon.py:114`、`_window_open` :145、逐成员复验 :337); psutil 不在依赖(零新依赖锚定); daemon 由主循环自动重拉(常驻形态); 拉起与落盘单点在 `relocate_journal` daemon-state helper 家族。
- 推演发现 issue 两个候选思路的洞: 朴素端口归属记录堵不住「目标新身已创建未绑端口」尾部; 「新身完全未起的死亡间隙落盘」反而安全(写时无 qB 运行, 新身读改写件走 N4 别名加载自洽)——竞争面精确定义为同 profile 实例, 这是全机口径的病根。
- 拍板 D1 实装 / D2 L1 立即进窗(L2/L3 保留 30s, 弱证据配稳定期; 逐成员复验必须升级为全套 L1 证据)/ D3 常驻形态设计 / D4 远程端点不修(事实翻案: 迁移链 `_same_fs_proof` 硬闸, 远程走不到收尾, 误挡仅 assume_shared 越权可及)/ D5 默认开零配置键(L1 每档严于现状已有降级路径)。
- 风险诚实定性: settle 30s 是有界赌注(WebUI 绑定秒级, 10 倍余量); 配置漂移/同 profile 异常双开属「外部不可区分」原理性残余, 文档警示不复杂化判据。

## 实现计划

计划单点: `memory-bank/plans/26-11-10-0318-plan-recycle-daemon-instance-evidence.html`(§03 三层证据链 + §03.2 新面孔状态机 + §04 三波 W1 通道与状态机纯逻辑 → W2 判据接线与场景测试 → W3 P7 真机验证与回写收口; 止损: W1 通道解析不可靠 = 方案不成立, 当场停手)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 事实核查 + grilling 三轮拍板(D1-D5) | Done(2026-11-10) |
| 2 | 计划立档 26-11-10-0318(Open 待认领) | Done(2026-11-10) |
| 3 | W1: obs helper + 观测通道 + `_Observation` 状态机 + 单测 | Open |
| 4 | W2: 三层判据接线 + 逐成员复验升级 + 场景测试 | Open |
| 5 | W3: P7 真机三场景验证 + 回写收口(issue 0528/docstring/pitfalls P7 专档) | Open |

## 进度日志

### R0 · 立档 (2026-11-10)

- issue 0528 读题 → 代码事实核查(判据/依赖/拉起方式/测试注入缝) → grilling 三轮(Q1-Q5, 含 Q4 事实翻案)收敛 → 计划 26-11-10-0318 立档(§05 无待拍板项)。
- 本轮只立档不改码; issue 0528 保持 Open(实装认领后按 plan §04 推进, 收口在 W3)。

- 2026-11-10 03:24 issue 0528 读题+代码事实核查; grilling 三轮拍板 D1-D5(实装方案A/L1立即进窗/常驻形态/远程端点不修/默认开); 计划 26-11-10-0318 立档(三层证据链+新面孔状态机+W1-W3); 任务档案 26-11-10-backend 立档; 仅立档未改码
