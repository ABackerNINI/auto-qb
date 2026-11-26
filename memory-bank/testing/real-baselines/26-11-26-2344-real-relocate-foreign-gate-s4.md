# 真机 S4 五项复验按限定口径全判通过: ①②限定口径 PASS / ③④⑤ PASS —— relocate 收尾簇七件修复计划 26-11-22-1714 终验切片

> 摘要: 七件修复计划 26-11-22-1714 §04 批3 列的「真机 S4 复验清单」五项，由两个真机子代理在环境2(C盘机)完成复验，用户拍板**按限定口径全判通过**，计划翻 Done。① dir_alias 同根兄弟/删链门/收尾 = 限定口径 PASS（本机无 R: 盘，钉死环境1拓扑的现成用例 RM04-25/31/33 首行 `_require_r_topology()` 直接 pytest skip；按 D7 分工，F1 精判由单测 `tests/test_relocate_exec_verify.py:659` 守阵，真机只做端到端五项）；② foreign 活到达探针 A/B = 限定口径 PASS（armed 态连续加入 3 枚探针 rc=0/0/0，arm 兜底扫描「入池候选 3 条」= 3/3 无漏接迹象；但 F2 修的差集累积游标路径日志为 DEBUG 不落盘、探针未触发成员数 2→3、原约 1/4 漏接属概率性单次不可证伪，三点未覆盖）；③ 产品重启/daemon 三事件 = PASS（CLI 两进程 + 外来 pid 注入重启等价路径，逐字三事件均含 pid；真产品层另有 RM04-36 接管日志）；④ 首次迁移 confirm 回执 = PASS（全新 data_dir 非 dry-run，首个非 pending 回执 status=warn，reasons[].text 与 notes[] 逐字含「续跑重新过全闸链, 出现需确认态会再次询问(不代用户点头)」；RM04-14 行为面 confirm 1→blocked 1/已受理→probe verdict 消费→续跑再次 confirm 1；26-11-24-2150 UX issue 另属他案不复现判据）；⑤ 武装行形态 = PASS（逐字「形态 dir_alias」非内部名「形态 dir」）。BLOCKED 技术事实（R: 盘缺席、用例 skip、概率性漏接不可证伪、UX issue 仍复现）逐条留痕，不掩盖。
> 基线时间: 2026-11-26 23:44
> 基线 commit: 0c2ab2ecbd32a1343cd353d70cff34d9a3b2986f

**Refs:** memory-bank/tasks/26-11-22-backend-relocate-foreign-gate.md

## 01 环境指纹与执行口径

- **环境**: 环境2 / C盘机；测试 qB 副实例 56589/56590；`real.guard` 通过（端口/镜像路径白名单 + 真实种子归零）。
- **收尾态**: 实例已 `real.down` 经 WebAPI app/shutdown 优雅关闭；工作树干净（HEAD 0c2ab2ec，分支 closeout/relocate-foreign-gate-s4，全程未动）。
- **执行分工**: 物理步骤（挪目录/停启 qB/探针添加）由两个真机子代理代执行；外部种子走 `real.seed` 手工配方（默认 256K，落 `.work`，gitignored）；产品以全新 data_dir 起真进程（非 dry-run）跑 POST location(confirm=true)。
- **判据来源**: 计划 26-11-22-1714 §04 批3「真机 S4 复验清单」五项 + D7 拍板（单测钉住全部判定/游标/文案面，真机只做端到端五项）。五项按限定口径全判通过系用户拍板；本切片如实写明每项限定口径与逐字证据，BLOCKED 技术事实不掩盖。

## 02 五项判据逐条结果

### ① dir_alias 同根兄弟/删链门/收尾 —— 限定口径 PASS

- **限定口径成因**: 本机无 R: 盘；钉死环境1拓扑的现成用例（RM04-25/31/33）首行 `_require_r_topology()` 直接 pytest skip —— `real.run` 的 skip 仍 rc=0，**不可误读为 PASS**；且 RM04-31 兄弟为前缀布局，不触发 F1 等值面面。
- **守阵替代**: 按 D7 拍板，F1 精判由单测 `tests/test_relocate_exec_verify.py:659`（`test_chain_gate_deps_dir_equal_face_per_file_scope_precision`）守阵，覆盖兄弟假依赖豁免/纯落进保留/混合保留/清单不可得保守/scope 缺失旧账不精判。
- **认定**: 真机端到端口径按「现成用例不可用 + 单测守阵完整」限定认定 PASS。若后续需等值面精确真机复验，须切环境1(R:)或另造 save_path==job.src 活种子用例。

### ② foreign 活到达探针 A/B —— 限定口径 PASS

- **实跑**: `real.seed` 手工配方（默认 256K，落 `.work`）在 armed 态连续加入 3 枚探针（落旧根、场景 A），rc=0/0/0；`evidence/foreign_probe2.json` 显示 arm 全量兜底扫描「入池候选 3 条」= 3/3，识别无漏接迹象。
- **限定口径**: 仅认定**入池识别层无漏接**。以下三点如实注明未覆盖：F2 修的差集累积游标路径日志为 DEBUG 不落盘（无逐字盘证）；探针未触发成员数 2→3；原约 1/4 漏接属概率性单次事件，单次实跑不可证伪。

### ③ 产品重启/daemon 三事件 —— PASS

- **路径**: daemon CLI 起两进程 + 外来 pid 注入，构成重启等价路径。
- **逐字证据**: `evidence/snap_rm04_s4_daemon_case_data_logs_recycle_daemon.log` 三事件逐字（均含 pid）：
  - `接管 daemon.json: pid 10704(无记录)`
  - `daemon.json 健康 watcher(pid 10704)在守, 本实例(pid 2464)让路续任`
  - `检测到外来 pid 2464 持有 daemon.json, 本实例(pid 10704)退位(绝不 taskkill)`
- **真产品层旁证**: `evidence/snap_rm04_rm04_36_data_logs_recycle_daemon.log` 逐字 `接管 daemon.json: pid 12008(无记录)`。

### ④ 首次迁移 confirm 回执 —— PASS

- **实跑**: 全新 data_dir 起产品（非 dry-run），POST location(confirm=true)。`evidence/f5_blocked3.json` 首个非 pending 回执 status=warn，reasons[].text 与 notes[] 两段逐字含「续跑重新过全闸链, 出现需确认态会再次询问(不代用户点头)」。
- **行为面**: RM04-14 日志 confirm 1 → blocked 1/已受理 → probe verdict 消费 → 续跑再次 confirm 1。
- **附注（不扩入本计划）**: 26-11-24-2150 UX issue 仍复现（确认后未见「已执行」成功提示，RM04-14 `1 failed`），但后端回执文案已取到，不影响本项文案判据；该 UX 问题属另一 issue，不扩入本计划。

### ⑤ 武装行形态 —— PASS

- **逐字证据**: `evidence/f5_blocked3_run.log` / `evidence/f5_armed.json` 逐字 `[INFO] ... relocate | job jr-7c05d7c1fa08: 已武装收尾(别名 1 条, 形态 dir_alias) —— 回收 daemon 将在 qB 下线窗口改写 fastresume`，显示「形态 dir_alias」而非内部名「形态 dir」。

## 03 用例真跑 vs skip 的区分说明

- **skip 不是 PASS**: RM04-25/31/33 等钉死环境1(R:)拓扑的现成用例，首行 `_require_r_topology()` 在环境2/C盘机直接 pytest skip；`real.run` 对此仍返回 rc=0，属「未跑」而非「通过」，绝不并入五项判据的 PASS 计数。
- **真跑的边界**: 五项 PASS 来自真机端到端手工程序（`real.seed` 探针、`daemon_case` CLI 双进程 + 外来 pid、`f5_blocked_case` 全新 data_dir 非 dry-run POST、`rm04_36` 真产品层）与单测守阵（F1 精判面），不是来自跳过用例的运行结果。
- **口径分工**: D7 拍板下，判定/游标/文案面的精确语义由单测钉死，真机只承担端到端五项；①的 F1 等值面精判即按此由单测守阵，真机侧只做「现成用例不可用 + 端到端不阻断」的限定认定。

## 04 证据闸留痕: real.seed.clean 拒跑 rc=1

- 收尾尝试 `real.seed.clean` 被证据闸拒跑（rc=1）：`.work` 顶层含 `rm04/`、`rm04_s4/`、`seeds/` 等 `seeds/rmNN` 之外的内容，命中守卫的「顶层有 seeds/rmNN 之外内容即拒跑」纪律。
- 证据**完整保留、未硬删**（`tests-real/.work/rm04_s4/evidence/` 全部留存，gitignored），不以清场换取绿结果；此项如实记账，不视为清理完成。

## 05 证据目录（gitignored，保留不删）

`tests-real/.work/rm04_s4/evidence/`：

- ③ `snap_rm04_s4_daemon_case_data_logs_recycle_daemon.log`（三事件逐字）、`snap_rm04_rm04_36_data_logs_recycle_daemon.log`（pid 12008 接管）。
- ④ `f5_blocked3.json`（首个非 pending 回执 status=warn + reasons/notes 逐字）、`f5_blocked3_run.log`（FIRST_STATUS/REASON/NOTE + ARMED_LINE）、`rm04_14_run.log` / `rm04_14_evidence.json`（confirm 行为面 + UX issue `1 failed`）。
- ② `foreign_probe2.json`（arm「入池候选 3 条」）、`foreign_probe_run2.log`（ARMED True、SEEDS_RC [0,0,0]）。
- ⑤ `f5_blocked3_run.log` / `f5_armed.json`（武装行「形态 dir_alias」逐字）。
- ① 单测守阵 `tests/test_relocate_exec_verify.py:659`（非本目录，源码在档）；RM04-25/31/33 的 skip 运行记录。

基线统计数字（passed/skipped/覆盖率等）以本切片为单点；档案 R4 中的 pid/rc/入池计数等系逐字证据引文（用于逐条对账判据），非基线数字复抄，精确口径以本切片为准；活动切片与计划正文以「见本切片」引用。
