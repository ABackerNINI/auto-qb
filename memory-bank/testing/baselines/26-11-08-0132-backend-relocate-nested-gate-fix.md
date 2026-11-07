# 5651 passed + 2 skipped + 1 failed(存量措辞守卫) —— 计划 1300 P2-P4 实现后基线

> 摘要: 计划 1300 P2-P4 实现后基线
> 基线时间: 2026-11-08 01:32

## 验收数字

`commands run test.full` 实测 (2026-11-08, 后台执行, 整体 160.9s / pytest 140.44s):

```text
TOTAL                                                25530      6   8816     28    99%
1 failed, 5651 passed, 2 skipped, 1 warning in 140.44s (0:02:20)
```

- 覆盖率门槛 99.5 过 (实测输出 `Total coverage: 99.90%`); 缺口单位 (miss+partial) = 6+28 = 34, 上片 (26-11-07-1248) 为 5+27=32, 净额 +2 (远低于点名线 +15), 差值逐位对比看 `commands run kb.baseline -n 2`。
- **1 failed = 存量措辞守卫, 非本轮回归**: `tests/test_memory_bank_docs.py::test_wording_guard_is_green_on_current_kb`, 违规点 = 任务档案 `26-11-07-backend-relocate-nested-gate-fix.md` 18/25 行历史表述 ([等…指令] / [待提交] 时点相对措辞), 与任务提示给的已知基线 (test.quick 口径 5651 passed / 2 skipped / 1 failed) 完全一致, 失败集未超出存量 1 条; 按本轮收尾纪律不修, 留 T6 收尾回写改写措辞时自然消除。
- 2 skipped 为既有设计性跳过 (与上片同 2-skip 权限面); 副作用台账 9565 条, 越界 0 条。

## 本改动面

- 计划 1300 (relocate 嵌套闸门修正) 三批提交, 基线起点 f7ac0e46 (develop), 头 2d755751:
  - fd53c8fe (P2/R1-R7): relocate 嵌套闸门形态感知重写 (`relocate_units.py` 判据按内容根锚 + 对称嵌套 + R4/R5 放行形态) + 删链门重锚 (`relocate_exec.py` `_chain_gate_deps` 锚 job.scope 并豁免本组成员); 单测重锚扩充 `test_relocate_fastresume_gates.py` (+221 行) / `test_relocate_units.py` / `test_relocate_supersede.py` / `test_relocate_exec_verify.py` (+33 行)。
  - c7c839da (P3/R6): webui 整组迁移语义披露 —— `relocate_enabled` 旗标 (`webui/server/routes/config.py`) + 移动对话框提示行 (`static/shared/tpl/move-dialog.html`) + 确认框成员数披露 (`drawer.js`/`lifecycle.js`/`state.js`); 测试 `test_web_api_core.py` / `test_web_relocate.py` / `test_webui_static_dom_panel_traffic.py` 同批跟进。
  - 2d755751 (T4a): 真机复验 8/8 回写任务档案 (纯文档)。
- P4 真机全链路复验 8/8 场景 PASS (R-A 至 U, 零旁路零 monkeypatch), 详见任务档案 R4 段; 本切片为其后的全量回归锚点。
- 文档面: 计划 `26-11-07-1300` (含 R1 改版) + issue `26-11-07-2336` (E2c 同盘收尾链, 先于本计划存在不入修) + 任务档案与三处 `_index` 登记。
- `config.yml` 与 `auto-qb-data/` 红线未动; 本轮零 git 同步/提交 (本地分支纯提交由委派方执行)。
