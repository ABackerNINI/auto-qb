# torrents 视图字段表单点化 · dup-code-audit issue 认领与修复

> 摘要: 用户「认领并修复 memory-bank/issues/26-10-11-0352-refactor-torrents-snapshot-view-field-dup.html」(上一回合卡于分析, 本回合继续修复)→ dup-code-audit 专题 torrents 侧(R19-C01)refactor issue 认领并修复。口径沿用前修复轮(hr/webui/rules/core/infra): A 类抽单点收敛 + 保守口径(行为不变)。复验定案: `torrents/compat.py` `_EXTENSION_FIELDS`(43 项)与 `torrents/view.py` `_VIEW_FIELDS`(现代码 61 项, issue 记 65)仍手抄同一批 qB 字段名, 本面唯一 pylint R0801 命中。
> 最后活动: 2026-10-15 05:01

**Refs:** memory-bank/issues/26-10-11-0352-refactor-torrents-snapshot-view-field-dup.html

## 已完成(2026-10-15 单会话收口)

- issue 复验(grep `_EXTENSION_FIELDS` / `_VIEW_FIELDS` 锚点在)后置 `In Progress`, 修复完成置 `Done`, 状态变更日志留实际修法/验证方式/测试数字痕。
- 改完前派derive 等价预实测: view 61 项 ⊆ snapshot 70 项(`view - snapshot` 空), 缺口恰 9 项(`hash`/`completed` + 重加 4 + 做种限制 3)—— 缺口清单直接落地, 行为不变判据前置钉。
- 改动面: `src/auto_qb/torrents/view.py`(`_VIEW_EXCLUDED_FIELDS` 缺口 9 项 frozenset + `_VIEW_FIELDS = _SNAPSHOT_FIELD_SET - _VIEW_EXCLUDED_FIELDS` 派derive 单点, 61 项手抄 literal 退役; `from .compat import _SNAPSHOT_FIELD_SET` 接线, 同包私有名 import 与 record.py 同口径)+ `tests/test_torrents.py`(新增守阵 `test_view_fields_derived_from_snapshot`: 缺口 ⊆ 快照含 + 缺口字段不置脏 + 非缺口全进脏判定 + 静态接线 count == 1; 头部「测试计划」清单同步一条); 全部过 `dev.fmt`。零跨包改动, `config.yml` / `auto-qb-data/` 未触碰。
- 漂移方向改: 新增快照字段默认进脏判定(多余重建无害), 手抄漏方向(字段变化不置脏、视图静默不重建)即 issue 记的漂移风险 —— 退役。
- 验证: 定向 `test.one tests/test_torrents.py` 全绿; 红验三判据闭环 —— ① 自抄 61 项 literal 回(行为不变)即静态守阵红(接线 count 0), ② 缺口拼不错 `hash`→`hsh` 即含红, ③ 手抄漏字段 `name` 即行为红(新守阵 + 既有 `test_view_dirty_intersection` 两红), 还原即绿; 收口 `test.full` 全绿 —— 实测数字唯一权威在基线切片 `testing/baselines/attachments/26-10-15-0512-torrents-view-field-dup-fix.md`(看数字 `commands run kb.baseline`, 此处不手抄)。
- 主档案 `26-10-10-backend-dup-code-audit.md` 进度记 R11 一条; torrents+tray 池 3 条全部 `Done`(hr-entry-guard 前轮, icon-path 0423, 本条 0501)。
