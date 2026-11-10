# 26-11-10-backend-recycle-daemon-instance-evidence — recycle daemon 实例级下线证据链(P7 多实例收尾窗解卡): grilling 拍板 + 计划立档

**Status:** Done
**Added:** 2026-11-10
**Updated:** 2026-11-11
**Summary:** recycle daemon 实例级下线证据链(P7 多实例收尾窗解卡): grilling 拍板(D1-D5) → 计划 26-11-10-0318 → 四波实装(W1a 观测面/W1b 判据面/W2a 接线/W2b 场景测试, 评审全程零回归) → 真机 P7 三场景 3/3 PASS 零产品缺陷 → 回写收口, 已 Done
**Topics:** backend-recycle-daemon-instance-evidence
**Refs:** memory-bank/issues/26-11-07-0528-feat-recycle-daemon-roster-machine-wide.html, memory-bank/plans/26-11-10-0318-plan-recycle-daemon-instance-evidence.html, memory-bank/pitfalls/backend/recycle-daemon-p7-evidence-chain.md, memory-bank/testing/baselines/26-11-11-0225-backend-recycle-daemon-instance-evidence.md, memory-bank/testing/baselines/26-11-11-0359-recycle-daemon-combine-tree.md

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
| 3 | W1: obs helper + 观测通道 + `_Observation` 状态机 + 单测 | Done(2026-11-10, fbcf4117 + a3c0fc1e) |
| 4 | W2: 三层判据接线 + 逐成员复验升级 + 场景测试 | Done(2026-11-10, 2ca40f43 + 76c056ee) |
| 5 | W3: P7 真机三场景验证 + 回写收口(issue 0528/docstring/pitfalls P7 专档) | Done(2026-11-11, 真机 3/3 PASS + 回写全套) |

注: 2026-11-11 合流 rebase 后提交对象重写——fbcf4117→1f36dd18, a3c0fc1e→3fd8092c, 2ca40f43→eba5ba3b, 76c056ee→972d7cd5, 202c807e→2a26dd65, f3356c1f→9ae076de; 表中旧 hash 为 pre-rebase 引用, 新 hash 见 git log。

## 进度日志

### R0 · 立档 (2026-11-10)

- issue 0528 读题 → 代码事实核查(判据/依赖/拉起方式/测试注入缝) → grilling 三轮(Q1-Q5, 含 Q4 事实翻案)收敛 → 计划 26-11-10-0318 立档(§05 无待拍板项)。
- 本轮只立档不改码; issue 0528 保持 Open(实装认领后按 plan §04 推进, 收口在 W3)。

### R1 · W1a+W1b 观测面与判据面 (2026-11-10)

- W1a(fbcf4117): obs 文件 helper 进 `relocate_journal.py`(原子写/路径单点) + 观测通道函数族(LISTENING 归属 Windows netstat / Linux procnet+fd、全机 qB (pid, create_time) 枚举、epoch 换算), 本机解析实测中英文输出均过。
- W1b(a3c0fc1e): `_Observation` 状态机 + L1 判据纯函数, 单测全桩化先立守阵; 评审 major 加固落地——零赌注吸收阈值从混域 `ct<ts_last` 升级为同域 `ct<owner.ct`, gap 带 `[owner.ct, ts_last)` 改走 30s settle 管道, 已知残余=时钟回拨跨 owner 创建边界角落(记坑档)。

### R2 · W2a+W2b 判据接线与场景测试 (2026-11-10)

- W2a(2ca40f43): run/_process_window/_window_open 接 L1/L2/L3 三层分派(L1 立即/L2 30s/L3 不动), 逐成员落盘前复验升级为同级全套(含 unclassified_faces), warn-sink 告警 60s 节流; `_proc_absent` docstring 标注 L2 语义。
- W2b(76c056ee): 六场景 7 测试端到端(立即进窗/settle 吸收/PID 复用两向/未决挡窗/obs 重启重载/通道失败退 L2), 防塌缩/防脆断言; 快速迭代全量全绿(见 kb.baseline), 评审全程零回归。

### R3 · W3a 真机 P7 三场景 (2026-11-11)

- 三场景 3/3 PASS, 零产品缺陷(证据根 `tests-real/.work/p7_w3a/`, gitignored): S1 目标死+日常活——owner 建档(obs 文件 owner pid/absorbed 日常实例走零赌注吸收), 优雅停→端口拒连→死亡→开窗+首写 2.63s(无稳定期), 双成员 rewritten 键字节核验; S2 目标复活——窗顶复验不过(refused=false+未分类面)⇒ qb_back 零落盘, 再停后重放收敛 rewritten; S3 通道故障——roster None 注入退 L2 全机口径告警 60s 节流(62.4s 实测), 110s 零开窗; 等价注入使 L2 可开窗⇒首写 37.54s(=30s 稳定期+对齐), 与 S1 2.63s 同机对照。
- 观察项(记档不改码): qb_back 可观测性缺口——run() 对 qb_back 不退出不上浮, CLI/退出码/journal/日志四处无痕; 真机下线期 obs_listen 告警 60s 节流 1 条属预期保守噪声。均已入坑档 P7 专档。
- S2 排障史(反面证据面): 初版驱动 10 次开环(a01 owner 未注册失败, a02-a10 零写入但窗开与否外部不可见), 复验不过的证据靠 s2b 驱动侧捕获 l1_calls/revive_mark 才完成取证——正是坑档「qb_back 可观测性缺口」残余的实证来源。

### R4 · W3b 回写收口 (2026-11-11)

- issue 0528 翻 Done(复验行+修复后补充: 四波实例级证据链+验证方式+真机关键数字); 计划 26-11-10-0318 翻 Done(§10 R 行 + §03.2 评审加固注记); 新建坑档 pitfalls/backend/recycle-daemon-p7-evidence-chain.md(竞争面定义/证据链边界/settle 赌注依据/已知残余四条/通道解析纪律); 既有坑档 relocate-window-machine-roster.md 追加「L1 上线后 wrapper 旁路不再需要」段; 基线切片与收尾切片见 kb.baseline / active-context。

- 2026-11-10 03:24 issue 0528 读题+代码事实核查; grilling 三轮拍板 D1-D5(实装方案A/L1立即进窗/常驻形态/远程端点不修/默认开); 计划 26-11-10-0318 立档(三层证据链+新面孔状态机+W1-W3); 任务档案 26-11-10-backend 立档; 仅立档未改码

- 2026-11-11 02:26 四波实装(W1a fbcf4117/W1b a3c0fc1e+评审加固/W2a 2ca40f43/W2b 76c056ee)+真机 P7 三场景 3/3 PASS(S1 2.63s vs 退L2 37.54s 同机对照, S2 qb_back 零落盘)+回写收口全链 Done(issue 0528/计划 26-11-10-0318/坑档 recycle-daemon-p7-evidence-chain); L1 实例级证据链上线, P7 形态产品本体直接开窗, 旧 wrapper 旁路退役为通道注入实验价值; 已知残余四条(时钟回拨角落/改 WebUI 端口不同步 config/同 profile 双开/qb_back 可观测性缺口)记坑档不改码; 全量全绿见 kb.baseline(切片 26-11-11-0225)
