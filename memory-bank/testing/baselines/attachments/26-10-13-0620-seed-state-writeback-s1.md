# 3176 —— 种子状态 A 系 S1 值层 (删合成回写 + 三条守阵翻面 + 4 调用点迁移)

> 摘要: A 系实施计划 (plans/26-10-13-0540) 的 **S1 值层**落地 —— 删除「自有停/起/暂停/恢复后按快照推合成 state 写回」这条第二回写通道: `QbApi._sync_paused_state` 整段删(四入口只调 raw client)、`store.update_torrent_fields` 的 `state=` 形参与相关分支删(保留 tags/category/save_path 通道)、两处 docstring 与两处相位/副作用注释重写。快照语义收敛为「严格 = 最近一次同步的应用结果」⇒ 自有停/起与外部变更**源无关**: 状态变化只经下一轮真实 delta 进入 `state_changed`, 被转移检测与状态事件看见。连带: 三条守阵按新契约重写(其一改名, 契约方向翻面)、4 处 `state=` 直接调用点迁移、`test_grouping` 两条用例承认「整组停种经同步回流再触发一次(一轮即收敛)」。全绿即基线。
> 基线时间: 2026-10-13 06:20

## 验收数字

- `test.full`: **3176 passed + 4 skipped** / `TOTAL 16728 159 5692 140 99%`.
- 耗时: **47.4s** (本机并行默认); `test.quick` 同绿 (用例数与上一基线持平 —— 只重写/改名, 未增删).
- 语句/分支数较上一基线各减 (合成回写整段与 state 分支删除的直接量).
- Linux 侧未重测 (改动为纯 Python 值层与测试, 平台无关).

## 本波改动面

- **源**: `core/qbapi.py` (删 `_sync_paused_state` + 四入口第二行; `torrents_pause/resume` docstring 重写为「纯透传 + 不回写」口径) · `torrents/store.py` (`update_torrent_fields` 删 `state=` 形参与相关分支/docstring; `update_state_snapshot` docstring 重写) · `core/qbmanager.py` (`transitions` 相位注释重写 —— 原「必须排在自有动作之前」理据消失) · `core/modules/grouping_mod.py` / `core/modules/ops_mod.py` (两处引用已删符号的注释重写).
- **测试**: `tests/test_actions.py` (三条守阵重写; `test_pause_resume_sync_store_snapshot` → `test_pause_resume_no_same_tick_writeback`, 契约翻面; 头部测试计划同步) · `tests/test_sync.py` (`test_store_update_state_snapshot_from_by_hash` 改钉「同轮不动 → 下一轮同步落真值」) · `tests/test_torrents.py` (视图脏用例字段面收敛) · `tests/test_webui_delta_mirror.py` (`state=` 两处调用点迁移为 category / save_path 承载的「无键命令源」) · `tests/test_grouping.py` (两条转移触发用例承认自触发回流一轮并收敛 + 7 处 mock 缘由注释重写) · `tests/helpers.py` (`_apply_paused_state` docstring 改口径).
- **文档**: `pitfalls/backend/concurrency.md` (「QbApi 写方法必须同步 store」补 `state` 例外) · `testing/guards.md` (A-04 守阵结论按反转更新) · 任务档案 · activeContext 切片 · 计划件 · 基线切片 (本份) · `kb.index` 生成物重建.

## 已知偏差 / 移交

- **契约翻面是刻意的**: 原 26-10-06-0028 (A-04) 要求 pause/resume 与 start/stop 对称写回; S1 把整条合成回写删掉 ⇒ 该守阵方向反转(登记见 `testing/guards.md`)。同 tick 幂等退到 qB 侧(qB 幂等无功能错误), 补回件见计划 §4.4 `pending_writes`(归 S3 可选件)。
- **grouping 自触发**是源无关的应有之义(2229 裁定): 整组停种结果下一轮经同步回流, 会再满足「上传转暂停」谓词一次 ⇒ 追加一次扫描+停种(幂等), **一轮即收敛**; 两条用例已按此改写并注明。
- **§8.3 新增守阵未落** (静态 S1: `qbapi.py`/`store.py` 无 `state=` 落点; V1/E1/E2/D1/D2/I1/S2) —— 按计划归 **S3 收尾**, 故本波只做「重写既有守阵 + 迁移调用点」。
- 数字差异看差值 `commands run kb.baseline -n 2` 现列.
