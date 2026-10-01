# 26-10-01-docs-doc-drift-repair — 知识库文档漂移分段修复

**Status:** In Progress
**Added:** 2026-10-01
**Updated:** 2026-10-01
**Summary:** 内核化重构+别名层处置后的全库文档漂移, 按 plans/26-10-01-1728 分五段(S1-S5)回写; S1(P1 架构描述重写 5 份)已完成并过验收, 余 S2-S5。

**Topics:** docs-doc-drift-repair

## 原始请求

用户 26-10-01 判定「底层经过重构, 文档可能出现很多漂移」, 先审计后出分段修复计划(plans/26-10-01-1728-plan-doc-drift-repair.html, 立档前已获用户确认); 本轮用户指令「实施S1: 26-10-01-1728-plan-doc-drift-repair.html」。

## 思考过程与决策

- 方案与取舍冻结在计划文档, 本档案只记执行与验证数字(计划 §8)。
- **S1 顺带收口一处计划未列项**: web-runtime.md 前端列缓存键 `autoqb_cols_v4` → `v5`(坐标 `webui/static/shared/app.js:207`, v4/v3 已入 LEGACY_COLS_KEYS `:208`)—— 该段属重写级回写, 带着已知错值进新稿违背重写本意; 计划 S3 对 core-domain.md 有同键修复, 口径一致。
- 行数/计数快照: core-runtime.md 有「快照披露」头注, 除计划点名的实测项(带 26-10-01 实测标注)外, 其余行数按计划 S5 豁免口径不动。

## 实现计划

五段路线与各段文件清单/验收口径见 [plans/26-10-01-1728](../plans/26-10-01-1728-plan-doc-drift-repair.html) §4; 本档案不复制。

## 子任务状态表

| 段 | 内容 | 状态 |
|----|------|------|
| S1 | P1 架构描述重写(5 份: systemPatterns/overview · main-loop · web-runtime · client-and-state + modules/core-runtime) | 完成(26-10-01) |
| S2 | 误导指路与机制反转单点修(9 份, 2 处 P1) | 待做 |
| S3 | modules/ 中度批(6 份) | 待做 |
| S4 | 用户面文档(4 份: README + docs/) | 待做 |
| S5 | P3 清扫 + 待决件 + 收尾基线(test.full 基线切片) | 待做 |

## 进度日志

- **2026-10-01 S1 完成并过验收**(基线 38604d07, 未提交待用户指令):
  - 5 份全部重写, 每条新断言带代码坐标(全部实测核对: qbmanager.py:142-145/158-234/339-351/441-449/485/530-535/577-578/663/679/692-701/726-832/818; webui/module.py:57-80/82-106; webui/runtime.py:52/105/192/328/556/576/581/603/613-642/116-164; webui/views.py:27/77-78/235-341; webui/server/auth.py:59/67; routes/__init__.py:6-20(11 域); core/state.py:117/149/183; core/modules/speed_curve_mod.py:280/301; core/modules/rules_mod.py:397; infra/versioning.py:28; tracker_mod.py:40/60/77; maintenance_mod.py:81/189; taskqueue.py:33; app.js:207-208)。
  - 退役名 grep 零残留 8/8: `_WEB_STATE_ALIAS` / `remove_torrent` / `flush_receipts` / `_hr_view_fields` / `SpeedCurveMixin._publish_traffic` / `ops_recheck` / `_web_token` / `web_runtime.py`。
  - 机检: `kb.index` 重建(4 份三行头有动) → `kb.check` 绿(主键纪律 OK: 251 文档 / 154 专题) → `doc.links` 绿 → `pytest tests/test_memory_bank.py` 27 passed。test.full 基线按计划留给 S5 收尾(本轮纯文档零代码变更)。
- **2026-10-01 合流 a03c3a8d 后坐标复核**(随「提交」同步合入远端 M1+M2/M3 三提交): `take_suppressed` 消费点自轮首迁 events_removed 臂(qbmanager.py:776, take 即 arm), 747-774 区段 -4 → 修正 3 处相位坐标(full_round :758→:754 / transitions :771→:767 / 删除前快照副本 :764→:760), 其余相位坐标(:778/:808/:815/:822/:826/:818)与总行数(839)经实测均未漂移; main-loop.md 内核保留职责句补 M1 消费点语义。
