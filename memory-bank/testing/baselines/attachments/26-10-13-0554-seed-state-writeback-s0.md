# 3176 —— 种子状态 A 系 S0 前置 (P1 可达性定 A3 / P2 消歧改名 / P3 替身翻 state)

> 摘要: A 系实施计划 (plans/26-10-13-0540) 的 S0 三件落地 —— P1 按 **auto-qb 能力面** (非某份配置; 本机 config.yml 仅临时配置、不代表能力边界) 判定 G6 **可达** ⇒ 形态定 **A3** (witness: `start` 一等动作 schema/rules.py:227 + auto_start 文档化选项 :185 + actions 顺序执行 ⇒ W1 `[{start},{checking}]` 顺序保证 / W2 auto_start:true 跨任务 / W3 WEB 命令线跨相位; 26-10-13-0602 方法论订正); P2 把 qbmanager 主循环局部变量 `state_changed` 改名 `cmd_changed_state` (与 `store.state_changed` 消歧); P3 `FakeClient` 四个暂停轴方法真实翻转 seed state (含 UP/DL 完成位, None=全体)。全绿即基线.
> 基线时间: 2026-10-13 05:54

## 验收数字

- `test.full`: **3176 passed + 4 skipped** / `TOTAL 16750 159 5702 140 99%`.
- 耗时: **45.6s** (本机并行默认).
- 单文件预跑: `test.quick` 3176 passed + 4 skipped (25.3s).
- Linux 侧未重测 (改动为变量改名 + 测试替身能力, 平台无关).

## 本波改动面

- 改: `src/auto_qb/core/qbmanager.py` (P2: 517 局部 `state_changed` → `cmd_changed_state`, 连带 528/534/540/544; 附消歧注释) · `tests/helpers.py` (P3: 新增 `FakeClient._apply_paused_state`, 四方法 start/stop/pause/resume 调用它真实翻转 state; calls 形状逐字不变).
- 回写: `memory-bank/tasks/26-10-13-backend-seed-state-writeback.md` (S0 进度) · `memory-bank/activeContext/26-10-13-0538-seed-state-writeback.md` · `memory-bank/plans/26-10-13-0540-plan-...html` (变更记录 + S0 状态) · 基线切片 (本份) · `kb.index` 生成物重建.
- 未改: 值层 (S1) 与 deferral (S2) 一行未动 —— S0 只做前置, 不改生产行为.

## 已知偏差 / 移交

- 用例数与上一基线持平 (3176) —— S0 不加守阵 (§8.3 的 V1–S2 归 S1/S3); P3 只补替身能力, 其可观测性在 S1 删回写后才显形.
- P1 判据与 witness 全文落任务档案; 若团队判定这些窗口可接受, S2 (deferral 层) 可整省 ⇒ 回落 A1 (见计划 §3 P1 两出口).
- 数字差异看差值 `commands run kb.baseline -n 2` 现列.
