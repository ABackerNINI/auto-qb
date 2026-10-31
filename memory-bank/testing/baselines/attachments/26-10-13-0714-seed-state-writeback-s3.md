# 3191 —— 种子状态 A 系 S3 收尾 (§8.3 全守阵 + 可选件 A2 幂等意图标记)

> 摘要: A 系实施计划 (plans/26-10-13-0540) 的 **S3 收尾**落地 —— 机检闭环。补 §8.3 余下守阵 7 条: **S1 静态**(剥注释扫描 `qbapi.py`/`store.py` 无合成 state 写点, 三条判据: `update_torrent_fields` 调用块内无 `state=` / 无 `.state=` 直接赋值 / 无 `setattr(..., "state", ...)`) · **V1 值层**(动作后快照逐字不变 → 下一轮同步落替身真值, 含 `checkingUP` 非四值枚举) · **V2 值域**(快照可持有 `queued*/forced*/checking*/moving/missingFiles`, 未被压平) · **E1 发射**(自有停种经下一轮同步回流触发转移扫描, 源无关, 且不重复触发) · **E2 一致性**(qB 自身 WebUI 暂停 与 auto-qb WebUI 暂停 行为逐字一致) · **D1 G6 端到端**(陈旧快照窗口存在 → deferral 拦下 → 回流后 G6 保护恢复, 证明 deferral 是「推迟到新鲜时」而非「放弃保护」) · **I1 幂等**(同 tick 二次 stop/start 被拦下, 且不写任何假 state 值)。**可选件 A2 采纳**: 幂等门**复用 `own_writes` 同一容器**(新增 `group=False` 形参取自身维度, 登记/清理单点不变) —— 从根上避免双轨, 不新增 `pending_writes`。全绿即基线。
> 基线时间: 2026-10-13 07:14

## 验收数字

- `test.full`: **3191 passed + 4 skipped** / `TOTAL 16785 159 5720 140 99%`.
- 耗时: **33.9s** (本机并行默认); `test.quick` 同绿 (3191 passed, 4 skipped).
- 较 S2 基线 (3184/16778/5714): 用例 **+7**(新增 S3 守阵), 语句 **+7**、分支 **+6**(A2 幂等门的代码量; 守阵本身是测试代码).
- Linux 侧未重测 (改动为纯 Python 值层/动作层与测试, 平台无关).

## 本波改动面

- **源**: `torrents/store.py` (`own_write_pending` 增 `group: bool = True` 形参 —— `False` = 自身维度, 供幂等门用; docstring 写明两种语义共用同一登记/清理单点) · `rules/actions/basic.py` (`StartAction`/`StopAction` 加同 tick 幂等门 + `_OWN_WRITE_PENDING_MSG` + **方向自洽性**注释).
- **测试**: `tests/test_sync.py` (S1 静态 / V1 / V2 + 新增 `_code_without_comments` 剥注释辅助) · `tests/test_grouping.py` (E1 / E2 + 新增 `_scan_scenario` 场景工厂) · `tests/test_ops.py` (D1 G6 端到端) · `tests/test_actions.py` (I1 幂等; 既有用例两处适配: `test_start_stop_idempotent` 补「回流」清登记、`test_stop_preserves_completeness` 三个标的改显式不同 hash) · `tests/test_rules_core.py` (`test_rule_interval` 补清登记 —— 该例用模拟时钟推进 60s 且期间不跑同步, 生产里 sync 每 1.5s 必逐出).
- **文档**: `pitfalls/backend/concurrency.md` · `testing/guards.md` · 任务档案 · activeContext 切片 · 计划件 (状态流转 Open → Done) · 基线切片 (本份) · `kb.index` 生成物重建.

## 已知偏差 / 移交

- **A2 的方向自洽性**(已写进 `basic.py` 注释): 反向操作由传统 `is_stopped` 判据先拦(快照不动 ⇒ start 后同 tick stop 读到 `is_stopped` 为真 ⇒ skip「已停止」), 落到幂等门的只有同向重复 ⇒ **判据无需带方向字段**。
- **WEB 命令路径不享 A2**: `webui/commands.py` 直调 `api.torrents_start/stop`(不经动作), 故用户手动连点仍会重复下发 (qB 侧幂等、无害)。未纳入本次范围。
- 两处既有用例适配属**新语义下的真实节奏**, 不是掩盖: 两者都是「同 tick 内对同一 hash 连续起停」, 生产里由状态回流或传统判据先行拦下。
- 计划 §8.3 九条守阵至此全覆盖 (S1/V1/V2/E1/E2/D1/D2/I1/S2); 其中 D2(TTL 有界) 与 S2(不落盘) 已于 S2 批次落地。
