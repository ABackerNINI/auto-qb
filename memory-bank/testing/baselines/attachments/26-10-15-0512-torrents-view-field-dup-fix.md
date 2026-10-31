# 3210 — torrents 视图字段表单点化(R19-C01)执行基线

**Refs:** memory-bank/activeContext/26-10-15-0501-torrents-snapshot-view-field-dup-fix.md

> 摘要: 用户「认领并修复」`26-10-11-0352-refactor-torrents-snapshot-view-field-dup`(compat._EXTENSION_FIELDS ↔ view._VIEW_FIELDS 两处手抄同一批 qB 字段名, 本面唯一 pylint R0801 命中)→ 按 issue 建议第一支落地: **view._VIEW_FIELDS 从 compat 快照表派derive**(展示表 = 快照全表 - 不展示缺口 9 项 frozenset), 61 项手抄 literal 退役; 改完前实测派derive 等价(61 项同 set, 脏判定同)行为不变; 配守阵含 + 静态接线 + 红验三判据闭环。全量 3210 passed + 4 skipped / 98.64%。
> 基线时间: 2026-10-15 05:12

上一基线: memory-bank/testing/baselines/26-10-15-0423-notify-tray-icon-path-dup.md

## 验收数字

- `test.full`: **3210 passed + 4 skipped, 0 failed** / 覆盖率 `TOTAL 16841 159 5724 142 99%`(98.64%, 过 98% 闸门)。
- 耗时: pytest 128.08s(单次采样, 全绿跑; 口径见 baseline.md)。
- 单文件前置跑: `test.one tests/test_torrents.py` 62 passed(改完先跑守阵文件绿再收口)。
- 收口细节: 收口首跑 1 failed(`test_memory_bank.py::test_gen_all_check_is_green`, issue meta 改后生成物 `issues/_index.md` 漂移), `kb.index` 重建后复跑全绿 —— 生成物守阵自指, 非修复缺陷。
- Linux 侧未重测(改动零行为变化收口, 无平台分支; 字段表两侧纯数据)。

## 本波改动面

- **派derive 单点**: `src/auto_qb/torrents/view.py` 新增 `_VIEW_EXCLUDED_FIELDS` 不展示缺口 9 项 frozenset(`hash`/`completed` + 重加 4 + 做种限制 3, 各带缘由注释)+ `_VIEW_FIELDS = _SNAPSHOT_FIELD_SET - _VIEW_EXCLUDED_FIELDS`(`from .compat import _SNAPSHOT_FIELD_SET`, 同包私有名 import 与 record.py 同口径), 61 项手抄 literal 退役; 漂移方向改: 新增快照字段默认进脏判定(多余重建无害)。
- **守阵**: `tests/test_torrents.py` 新增 `test_view_fields_derived_from_snapshot`(缺口 ⊆ 快照含 + 缺口字段不置脏 + 非缺口全进脏判定 + 静态接线 count == 1)+ 头部「测试计划」清单同步一条; 红验三判据闭环(自抄 61 项回即静态红、缺口拼不错即含红、手抄漏字段即行为红两判族, 还原绿)。
- **回写**: issue(Open → In Progress → Done, 徽标+meta+状态日志含复验/实际修法/验证方式, doc-refs 认领链)+ activeContext 切片新建(反向声明闭合)+ 本基线切片。

## 已知偏差 / 移交

- 移交: dup-code-audit 池 torrents+tray 3 条全部 Done; 主线余 Phase 2 前端轮 20–23 / Phase 3 测试横切 24–25 / Phase 4 汇总 26 未开工。
