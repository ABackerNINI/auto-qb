# 26-11-03-backend-relocate-same-fs-proof — 整组迁移同盘证明误拒：根因与修复计划

**Status:** In Progress
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** 整组迁移同盘证明误拒：根因与修复计划
**Topics:** backend-relocate-same-fs-proof
**Refs:** memory-bank/plans/26-11-03-2212-plan-relocate-same-fs-proof.html

## 原始请求

1. 分析现场「单组 3 个种子从一个盘移动到另一个盘失败」的 `批量移动失败 / 无法证明 auto-qb 与 qB 看到同一块盘` 报错，产出修复计划，不实施修复。
2. 只读定位判定点，讲清为什么 3 成员组必失败、单成员组为何可过；区分已验证与推测。
3. 用 delivery-artifact 落单文件 HTML 计划，用 grilling 做至少 6 条自我压测，列出必须由用户拍板的问题。
4. 本轮不改 `src/`；如撞见计划外缺陷按范围守恒入池。

## 思考过程与决策

计划：`memory-bank/plans/26-11-03-2212-plan-relocate-same-fs-proof.html`（D1-D7 待拍板）。

- 根因不是链接语义或硬链接跨卷：多成员组走「一个 mover + src 链接指向 dst」，单成员走 `FORM_DIRECT`；拦人的是 `same_volume_proof(qB 默认保存路径剩余, src/dst 剩余)` 这个代理判据（`relocate_plan.py:247-260`、`relocate_units.py:702-714`）。
- 已验证：qB 的 `free_space_on_disk` 是默认保存路径卷；本机测试实例 56590 的默认路径指向不存在的 R:，该字段返回 `-1`；WebAPI 2.15.1 / qB 5.2.3 上 `getFreeSpaceAtPath` 为 404。
- 未验证（需现场事实）：用户现场属于「同机第三块盘」「默认路径不可读」「path_map 未覆盖」「真远程/容器」中的哪一种；现有文案四者同形。
- 取舍：不做跨卷复制降级（破坏做种连续性、双倍空间）；不取消闸门；首选「诊断先行 + 显式同机声明（默认关）+ 归因拆分」，qB 5.3 按路径直证列为条件项。

## 实现计划

P1 诊断先行（不改行为）：预检/日志输出 qB 版本、默认 save_path、`free_space_on_disk`、src/dst 本机剩余、容差、path_map 命中、能力 verdict、全部未过闸门；WebUI 回执显示有界前三条。
P2 归因拆分（不改放行）：同盘证明失败拆为 `unavailable` / `default_path_elsewhere` / `mismatch`，各给下一步。
P3 显式出口（行为变更）：新增 `relocate.assume_shared`（默认 false），跳过代理判据但保留能力/冲突/空间/`!qB` 闸门，需风险确认 + 审计日志；新键进 `validate_config` 与 `schema.py`。
P4 5.3 直证（条件项）：qB ≥5.3 对 src/dst 各查一次剩余空间；5.2.3 回落 P1/P3 路径，404 不产生噪音。
P5 真机与回归：环境 1（D: + R:）用伪造种子做正例、第三卷反例、声明模式三场景；真实种子全程非活跃；测试后清理。

验收：现场同类 3 成员组在 `auto` 或声明后可完成；拒绝时消息含数字与唯一归因；远程/跨 OS 容器仍拒绝；单测覆盖四类判据分支 + 配置键 + 回执契约。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|

| A1 | 只读定位判定点与调用链 | Done(2026-11-03) |
| A2 | 测试实例 56590 只读探针（版本/默认路径/free/-1/5.3 端点） | Done(2026-11-03) |
| A3 | 计划 HTML + grilling + 待拍板清单 | Done(2026-11-03) |
| A4 | 收尾：kb 守卫、全量测试、基线切片、提交 | Done(2026-11-03) |
| P1 | 诊断先行（字段 + 回执显示全部闸门） | Open |
| P2 | 同盘证明失败归因拆分 | Open |
| P3 | `relocate.assume_shared` 显式出口 | Open |
| P4 | qB 5.3 按路径直证 | Open |
| P5 | 真机正反例与声明模式验证 | Open |

## 进度日志

### R0 · 立档 (2026-11-03)

完成只读定位：`GATE_SAME_FS` 在多成员组硬拦，单成员组因 `FORM_DIRECT` 不受该闸门影响；根因是 `free_space_on_disk` 只代表 qB 默认保存路径卷。56590 只读探针复现「默认路径不可读 ⇒ -1 ⇒ 必拒」分支，并确认 5.2.3 无按路径查剩余空间端点。已产出计划（四方案对比、P1-P5、D1-D7、G1-G11），未改 `src/`。全量测试与基线见 `commands run kb.baseline`。

- 2026-11-03 22:25 只读定位 GATE_SAME_FS 根因（qB 默认保存路径剩余空间代理判据），56590 探针复现 -1 分支，产出四方案对比计划与 grilling 11 问；未改 src/。
