# 26-11-22-backend-relocate-foreign-gate — foreign 判定门内容根收窄与收尾进展同步呈现: 计划 26-11-21-1600 S1-S3 实施

**Status:** Done
**Added:** 2026-11-22
**Updated:** 2026-11-22
**Summary:** foreign 判定门内容根收窄与收尾进展同步呈现: 计划 26-11-21-1600 S1-S3 五批落地 + 接缝终审钉档, 全绿见 kb.baseline
**Topics:** backend-relocate-foreign-gate
**Refs:** memory-bank/plans/26-11-21-1600-plan-relocate-foreign-gate.html, memory-bank/issues/26-11-21-1500-bug-relocate-foreign-sibling-mismatch-flood.html, memory-bank/issues/26-11-21-1326-refactor-relocate-foreign-notified-cleanup.html, memory-bank/testing/baselines/26-11-22-0533-backend-relocate-foreign-gate.md, memory-bank/issues/26-11-22-0604-refactor-content-root-of-duplicate-join-semantics.html, memory-bank/issues/26-11-22-0604-refactor-curves-syntaxwarning-invalid-escape.html, memory-bank/testing/baselines/26-11-22-0821-backend-relocate-foreign-gate.md

## 本篇只回答

计划 26-11-21-1600(B1 判定门内容根预筛 / B2 账面终态清理+文案 / B3 可观测性+WEBUI 行同步)的 S1-S3 怎么实施、做到哪了 —— 方案细节与拍板 D1-D9 单点在计划。

## 原始请求

1. <!-- wording:allow --> 「先拆解任务, 然后派子智能体分阶段实施下面的任务, 大任务需要拆分成稍小任务防止子智能体长任务过长和出错后进度全部丢失……待拍板的先询问, 你只负责委派总结, 不负责实际实施, 开新的本地分支, 每步完成后使用 ship.commit --no-push 本地 commit……全程在本地分支上工作, 完成后同步到本地 develop(rebase 保线性), 完成后等待提交指令……任务: 26-11-21-1600-plan-relocate-foreign-gate.html S1-S3」。
2. 派遣纪律: 并发数任何时刻不超过 2(含主会话), 可能写冲突的串行、只读可并行 2; 子智能体失败/超时可用 SendMessage 续跑, 非正常失败 3 次停止等待人工。
3. 后续: 「提交, 然后入池, 最后提交入池」—— 触发收尾回写 + 推送 + 两条范围外发现入池。

## 思考过程与决策

- 拆解: S1/B1 与 S2/B2 各一批, S3/B3 按前后端拆两批(后端=daemon 日志+等待提示+rewritten 日志, 前端=WEBUI 行状态+e2e), 收口=全量+接缝终审; 每批独立评审独立本地提交, 批间零牵连。
- 流程: 每批走「写入子代理 → ship.gate 预跑 → review.pack → 只读评审子代理(本地分支态三钉) → review.check 引文校验 → 修复增量 → 复评到零 actionable → ship.commit --no-push」; 615/557 行超 400 走分面派遣(2/3 面), trailer 记 `· 派发`。
- 环境坑: 本 shell 外部 TMPDIR 触 rc=4(坑档复发 12)——所有 pytest 链(ship.gate/ship.commit 内含)一律 `env -u TMPDIR` 前缀。
- 计划内裁决 1 处: S3a 实现者报「daemon 无 INFO 流程行, S4-④ 将落空」——判为计划内(§01 成事判据+验收④的直接前置)当场补进本批。
- 用户拍板 1 处(接缝终审): mismatch 条目终态清理后种子仍在场会重判重发一次 WARNING, D4「自然重判为场景 B」只对 kind=A 成立 —— 选 a) 接受现状+钉档, 零行为改动, docstring 按终态类别写全 + done/failed 双面守阵。
- 评审战果: 5 批 11 轮(含分面 2/3), 检 16/16 全过、修 16、入池 0、blocker 0; major 1 个(S2 崩溃窗恢复路径漏挂清理, 恰是 1326 滞留的恢复面)+ 接缝级语义缺口 1 个, 均已处置。
- 提交链(本地分支 relocate-foreign-gate-s1-s3, 后 rebase 进 develop): 41d40168(S1/B1)→ 1d4ae8cb(S2/B2)→ 42a9face(S3/B3 后端)→ de73d571(S3/B3 前端)→ 4e0c6662(接缝钉档; rebase 后 hash, 原 1d38c458/2be15c87/c8fbb05f/e6f60909/2d35627d)。

## 实现计划

按计划 §04: S1 内容根预筛(纯函数入 relocate_units + _foreign_drain 接线 A/B 两路) → S2 终态清理单点(非终态→终态边沿, kind 分流) + mismatch 文案改口径 → S3 后端可观测性(daemon 日志落盘/流程 INFO 行/WAIT 提示/rewritten 合并日志) → S3 前端行状态细化(finalize_state 三态投影 + decorate 单点 + e2e 四皮肤) → 收口(全量 test.full + 接缝终审)。S4 真机验收不在本任务范围(计划独立步骤, 需真机环境)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | B1 内容根预筛(纯函数+接线+DEBUG 丢弃) | Done(2026-11-22) |
| S2 | B2 终态清理(kind 分流, 三接线)+mismatch 文案改口径 | Done(2026-11-22) |
| S3 | B3 后端(daemon 日志+流程行+WAIT 提示+rewritten 日志) | Done(2026-11-22) |
| S3 | B3 前端(WEBUI 行三态+保存路径+e2e 四皮肤) | Done(2026-11-22) |
| 接缝 | 终审 3 轮零 actionable + 拍板 a 钉档批 | Done(2026-11-22) |
| 收尾 | 文档回写+基线切片+issue 翻 Done+推送 | Done(2026-11-22) |
| S4 | 真机验收(完整整组迁移全链复验, 计划验收⑤六条) | Open |

## 进度日志

### R0 · 立档 (2026-11-22)

- S1-S3 五批 + 接缝钉档全部落地: 评审 5 批 11 轮检 16/16 修 16 零 blocker; test.full 全绿(见 kb.baseline); e2e @fast 三分片 515 passed/0 失败(四皮肤); 本地分支 rebase 进 develop 保线性, 随本专题入库。
- 接缝终审 1 项语义出入(mismatch 重判重发)经用户拍板 a) 接受现状+钉档, 未改行为。
- 范围外发现 2 条(grouping_mod._content_root_of 副本口径差 / core/curves.py:53 存量 SyntaxWarning)按用户指令转正入池(issues 池, 时间戳 slug 可 grep)。

- 2026-11-22 05:36 计划 26-11-21-1600 S1-S3 五批落地(预筛/终态清理+文案/daemon日志+流程行/WEBUI行三态)+接缝终审3轮钉档, 全绿见 kb.baseline; 真机 S4 待窗口
