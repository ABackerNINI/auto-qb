# 26-11-21-webui-traffic-idle-dual-condition — 全局流量图空闲判据双条件修复(z 分类补 totals 持平)

**Status:** Done
**Added:** 2026-11-21
**Updated:** 2026-11-21
**Summary:** 全局流量图空闲判据双条件修复收口 Done: 根因 = qB 字段口径混杂(payload EMA vs 全部流量 totals)+ z 游程冻结吞协议流量字节 → SSE/GET 两源翻面(用户观测「前一刻上上下下, 下一刻全 0」); 修法 = 全局系列空闲判据补「totals 与上一观测持平」双条件, totals 变化的零速率字段 tick 重分类 r(差分速率, calcRate 同式, 与 qB 流量图默认曲线语义对齐); 3 新用例 + 6 既有用例适配 + 1 端到端钉面; 全绿(见 kb.baseline); 单种系列不动(payload-only 有源码背书); 评审 3 轮 7 发现全修零 actionable(检 7/7)
**Topics:** webui-traffic-idle-dual-condition
**Refs:** memory-bank/testing/baselines/26-11-21-0829-webui-traffic-idle-dual-condition.md, memory-bank/pitfalls/backend/qb-field-basis-mixing.md, memory-bank/conventions/attachments/webui-traffic-beat.md

## 本篇只回答

## 本篇只回答

本轮只回答: 全局流量图低速下「换窗全 0 / 曲线随机变 0(值跳变)」的根因是什么、修什么。qB 字段口径的领域结论进坑档(pitfalls/backend/qb-field-basis-mixing.md), 流量子系统口径进主题文档(webui-traffic-beat.md 现行权威节)。

## 原始请求

## 原始请求

1. 「流量图切换视图图形变成全0, 比如从1m视图切换到5m视图, 流量图形全部为0. 同时还观察到不切换视图流量曲线也随机变0。测试时是在低速(<2KiB/s), qb流量图。」(26-11-21)
2. 追问澄清: 「我说的是流量图曲线变化, 即其表示的值在跳变, 说明必定有一时刻其表示的值不准确, 比如前一刻曲线上上下下, 下一刻曲线都变成了0」—— 把病象钉死为「同一窗口的历史在两次取数之间被改写」(两源分歧形态)。
3. 「先查原设计文档totals到底是什么, 能否改成不显示totals, qb返回0就显示0, qb与libtorrent源码在Else可供分析」—— 引出字段口径核实。
4. 「你的根因结论描述似乎和我的描述不太相同」—— 推翻 agent 第一次「修正」(不物理误判), 重锚到两源分歧。
5. 「先分析qb的流量图用的什么语义, 需要尽量与之对齐」—— 拍板对齐方向。
6. grilling 四问 + 「按推荐」—— 修法拍板(Q1 范围/Q2 噪底接受/Q3 历史不可恢复/Q4 守阵范围)。

## 思考过程与决策

## 思考过程与决策

根因链(源码逐字核实): 全局系列 `_sample_global` 旧判据只看速率字段 (0,0) → z 游程; 而 qB `alltime_dl/up` = recvBytes+IP overhead(全部流量), peers 协议流量每 tick 推动 totals 而 payload EMA 读 0 → z 游程开启快照冻结吞掉协议流量的逐 tick 差分: 存储面 0, 事件流按实读 totals 差分非 0 → 30s 对账/换窗 GET 落袋整窗翻 0(用户的「跳变」)。单种系列盲推进 z 两源天然一致, 跳变为全局独有。

分析过程的两次翻转(记档防复发): ①最初按「totals 每 tick 动 + 字段 0」复现两源矛盾(正确); ②据 libtorrent EMA 衰减力学错判该形态「不物理」(错因 = 把 alltime 当 payload 口径 —— 坑档 backend/qb-field-basis-mixing.md 复发 1); ③用户以「值跳变」病象反驳 + 源码逐字核实 recvBytes 口径后重锚回两源分歧。

拍板(grilling 四问全按推荐): Q1 修法范围 = 只改全局系列分类判据, 重分类样本 dl_rate 存差分速率(用户「参考1」拍板), 单种零改动(torrent.cpp:10909 payload-only 背书); Q2 协议噪底常驻图面 = 接受(qB 默认曲线同款), payload 叠层另案; Q3 历史 z 行已塌缩不可恢复, 不迁移; Q4 守阵 = 3 新用例 + 端到端一致性钉面 + 既有 z 快照钉面不动。qB 流量图语义核实(对齐依据): DOWN/UP 默认曲线 = 全部流量 calcRate 差分、每 tick 恒出样本、显示层分桶平均(speedwidget.cpp:134-139 / preferences.cpp:2147 / speedplotview.h:134-139)—— 我们速率面基与 qB 同 counter 同式, 唯一偏离就是 z 冻结。

## 实现计划

## 实现计划

单批落地(判据单点 + 测试三层), 每步独立可验:

1. 写侧分类: `_sample_global` 空闲判据补双条件 + `_global_idle_at_totals` 单点(游标 `_ev_prev_obs`)+ `_delta_rate` 差分速率(calcRate 同式)。
2. 采样层守阵: 协议流量形态逐 tick r / 真静默与协议混合记录序 / 断连重连重分类 r 封 n 三用例(test_traffic_sample_core.py)。
3. 端到端钉面: 5m 全段窗 GET 与 SSE 事件帧全量 120 帧逐点同值(修前整窗全 0 直接复现, test_web_traffic_qb.py)。
4. 既有用例语义适配(6 个: 形态 D 两档合流/重置记录改 r/跨天与改间隔封口真静默化)+ docstring 测试计划同步。
5. 收尾: 评审(3 轮零 actionable)/ test.full 全绿(见 kb.baseline)/ 坑档/主题文档回写/立档。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 根因分析与两次翻转(源码逐字核实 qB/libtorrent 字段口径) | Done(26-11-21) |
| 2 | grilling 四问拍板(Q1-Q4 全按推荐)+ qB 图语义核实 | Done(26-11-21) |
| 3 | 写侧分类实现(_sample_global/_global_idle_at_totals/_delta_rate) | Done(26-11-21) |
| 4 | 三层守阵(采样 3 用例 + 端到端 1 钉面 + 6 既有适配) | Done(26-11-21) |
| 5 | 评审 5 轮(送检 11: 工具过检 6, 修 10[nit 留痕 1], 如实申报口径见 R0)+ 收尾回写 | Done(26-11-21) |
| 6 | 真机冒烟(用户环境低速形态复验图面不再翻面) | Open |

## 进度日志

### R0 · 立档 (2026-11-21)

### R0 · 立档与修复落地 (2026-11-21)

根因闭环(两次分析翻转 + 源码逐字核实)→ grilling 四问拍板 → 单批落地(分类判据 + 三层守阵)→ 评审 5 轮(轮1 两面: 正确性零发现/测试缺口 6 发现 6/6 过检 → 修 5 + 1 nit 留痕; 轮2 复评 1 nit 修; 轮3 收口零发现; 轮4 收口批 4 条[3 minor 引文行号 + 1 nit 坑档触发行体例]修; 轮5 引文修正收口零发现 —— 送检 11, 工具过检 6/6, 轮2/4 的 5 条未走工具即修[流程缺口, 如实申报])→ test.full 全绿(见 kb.baseline)→ 坑档(backend/qb-field-basis-mixing.md, 复发 1)/主题文档(webui-traffic-beat.md 现行权威节)/本档案回写。真机冒烟待用户环境(qB 离线不可达, 改约)。

- 2026-11-21 08:32 全局流量图空闲判据双条件修复收口: 根因(qB 字段口径混杂+z 冻结吞协议字节→SSE/GET 翻面)→修法(全局 z 分类补 totals 持平+差分速率, qB 图语义对齐)→3 轮评审 7 发现全修→全绿(见 kb.baseline); 单种不动; 真机冒烟改约
