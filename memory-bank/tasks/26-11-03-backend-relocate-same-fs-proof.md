# 26-11-03-backend-relocate-same-fs-proof — 整组迁移同盘证明误拒：根因与修复计划

**Status:** In Progress
**Added:** 2026-11-03
**Updated:** 2026-11-04
**Summary:** 整组迁移同盘证明误拒：根因与修复计划
**Topics:** relocate-same-fs-proof
**Refs:** memory-bank/plans/26-11-03-2212-plan-relocate-same-fs-proof.html, memory-bank/plans/26-11-04-0055-plan-relocate-same-fs-proof.html

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
| P1 | 诊断先行（字段 + 回执显示全部闸门） | Done(2026-11-04, 随新计划 P1 落地) |
| P2 | 同盘证明失败归因拆分 | Done(2026-11-04, 新计划 P5 收口) |
| P3 | `relocate.assume_shared` 显式出口 | Done(2026-11-04) |
| P4 | qB 5.3 按路径直证 | Open(条件项, 无 5.3 实例) |
| P5 | 真机正反例与声明模式验证 | Done(2026-11-04, RM04-11..13; L490 小目标前置缺失待补) |

## 进度日志

### R0 · 立档 (2026-11-03)

完成只读定位：`GATE_SAME_FS` 在多成员组硬拦，单成员组因 `FORM_DIRECT` 不受该闸门影响；根因是 `free_space_on_disk` 只代表 qB 默认保存路径卷。56590 只读探针复现「默认路径不可读 ⇒ -1 ⇒ 必拒」分支，并确认 5.2.3 无按路径查剩余空间端点。已产出计划（四方案对比、P1-P5、D1-D7、G1-G11），未改 `src/`。全量测试与基线见 `commands run kb.baseline`。

- 2026-11-03 22:25 只读定位 GATE_SAME_FS 根因（qB 默认保存路径剩余空间代理判据），56590 探针复现 -1 分支，产出四方案对比计划与 grilling 11 问；未改 src/。

- 2026-11-04 00:25 R2 评审修订报告: A/G 评分算术、误放后果三层化、探测粒度 content_root、fallback 换 B′、R: 断言降级待实测

- 2026-11-04 00:58 grilling 两轮拍板 D1-D8, 立分步实施计划 26-11-04-0055(三层证据体系+六期实施)

- 2026-11-04 04:42 P1-P5 全部实施+评审修复(2 major)完成, 快进合入本地 develop(826ff778); 基线 5074 passed, 待提交指令

### R3 · P6 真机验收 (2026-11-04 05:07)

开工同步 `commands run my-commit-flow.sync`:已同步 `e80d9f8e`(快进 861e2b45→e80d9f8e)。`real.guard` 通过:环境 2,56589 pid 8228 / 56590 pid 7596,qB v5.2.3 双实例 connected,自造种子 0。

实测(新增 `tests-real/rm04_relocate/test_rm04_probe_real.py`,三例,均经 `commands run real.run -- --case ... --yes`):

| 用例 | 命令 | 实测结果 |
|---|---|---|
| RM04-11 E1 真写正向 | `commands run real.run -- --case RM04-11 --yes` | PASS;真实 qB 探测 `passed/reason=ok/env=False`,`elapsed_s=1.536`,4KiB sha1 `aed7854d…` 一致;清理 `torrent_deleted/torrent_gone=true`、`residue=[]`、两侧探针目录 0 |
| RM04-12 指纹缓存/重探 | `commands run real.run -- --case RM04-12 --yes` | PASS;首探 1.796s → 同指纹 0.000s(命中缓存,零探测)→ 改 port 指纹 `e298aa9d…→854eb950…` 后 1.312s 真重探;state 缓存 2 条均 passed,两实例零残留 |
| RM04-13 R: 闭证 + D 对照 | `commands run real.run -- --case RM04-13 --yes` | PASS;默认 `save_path=R:\Download\PTing`,`getDirectoryContent` 返回 `NotFound404Error: 目录不存在` → 产品 D 判 unavailable(不放行);C: 对照 raw 1 条 entry、size/mtime 与本机 stat 吻合 |
| RM04-05 全流程 | `commands run real.run -- --case RM04-05 --yes` | 主链 PASS(多成员组同盘迁移、dst 大小、junction、phase/job done);尾部 L490 小目标反例因 `QBT_REAL_SMALL_TARGET` 未预置显式失败(环境前置缺失,非产品回归) |

全量:`commands run test.full` 通过(数字见 kb.baseline,新切片 `26-11-04-0507`)。

两个关键发现/偏差:

1. **计划 P6「首迁触发探测」在健康同机场景不会发生**。真机上源目录对 qB 可列,B′(或修复后的 D)能判 positive ⇒ 按 D4 的 `facts.same_fs_proved` 短路,E1 被跳过。故改用两层取证:E1 行为由 RM04-11 直接驱产品 `run_probe` 真写;指纹缓存语义由 RM04-12 驱 `RelocateModule._ensure_probe`(真 facts + 真 state + 真 qB)。未改产品代码。
2. **真机发现 D 级恒降级 B′**:`relocate_proof._d_evidence` 只认 `list/tuple`,而 `qbittorrentapi` 返回 `DirectoryContentList`(UserList 子类)⇒ 判「响应形态异常」;`link_follow_evidence`(F)同函数同源失效。raw 端点本身正常(1 条 entry、元数据吻合)。该缺陷属本轮实施面但在「本轮不改 src/」约束下未修,按 scope-guard 入池 `memory-bank/issues/26-11-04-0504-bug-relocate-d-evidence-container-type.html`(Open,待指派;后由用户指派修复,见 R4)。

结论:**真机验收整体通过(qB 侧 E1 写证/清理、指纹缓存、R: 闭证、全量回归均绿);阻塞项仅 L490 小目标环境前置与上述 D/F 缺陷**。产品代码未改;未收到提交指令,未 commit/push。

### R4 · 计划外缺陷修复: D 级证据容器判据 (2026-11-04 05:52)

R3 发现的 D/F 级缺陷按用户指派修复（issue `26-11-04-0504`，状态 Done）：

- 根因：`_d_evidence` 容器判据只认 `list/tuple`，qbittorrent-api 返回的 `DirectoryContentList` 是 `UserList` 子类（`Sequence` 协议，非 list/tuple 子类），被误判「响应形态异常」。
- 修法：新增 `_is_entry_sequence()`，按 `collections.abc.Sequence` 判定并排除 `str/bytes/bytearray`（避免 `visibility_only` 假 positive）；F 级 `link_follow_evidence` 同函数同源生效；不按类名硬编码。
- 验证：`commands run test.one -- tests/test_relocate_proof.py` 改前 4 failed（复现 `形态异常(DirectoryContentList)`）→ 改后全绿；真机 `commands run real.run -- --case RM04-13 --yes` 1 passed，`control_d_only` 由 `unavailable` 转 `positive/D`，`control_final` 由 `B′` 升 `D`；全量数字见 `commands run kb.baseline`（新切片 `26-11-04-0553`；另 1 例无关线程抖动单跑通过，覆盖率 98.70% 属既有闸红）。
- 未收到提交指令，未 commit/push。

- 2026-11-04 05:54 修复 issue 26-11-04-0504: relocate_proof 容器判据改序列协议(_is_entry_sequence)+5 回归; 真机 RM04-13 D 级恢复; 新基线 26-11-04-0553
