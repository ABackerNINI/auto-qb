# 基线 · 1894 passed + 3 skipped / 90% —— 别名层处置 W2(测试面迁移, 4 批 + 补漏)

> 摘要: plan plans/26-10-01-0350 **W2 全量实施(只改名零行为变更, D2 按模块域 4 批 + 验收补漏)**。
> 分诊清单标 W2 名的测试消费方(别名 18 字段 + 转发 49 名, 接收者级约 750 处)全部改新名口:
> ①**批次1 web 域**(3e4231d1, 5 文件 376 处): 别名字段 → `mgr.web.*`(token/results/commands/
> group_view(+ver/dirty)/flat_view/singles_view/shows_view(+pending)/search_index(+dirty)/handle/
> last_seen/pending_ver/write_seq/reannounce_pending/traffic_view), WEB 转发 8 名 → `web.*`
> (consume_commands/check_pending/flush_truths/flush_views/rebuild_views/ensure_view/ensure_state/
> touch); test_web 假替身收尾 W1 双轨 —— SimpleNamespace 旧名属性删除, 数据全挂 `mgr.web.*`,
> token 双写改单写。②**批次2 maintenance/tags/trackers 域**(fe0cc172, 6 文件 85 处):
> `ctx.trackers.*` / `ctx.maintenance.*` / `host.get("maintenance").*` / `host.get("speed_curve").*`。
> ③**批次3 grouping 域**(e88d4e4b, 2 文件 52 处): `host.get("grouping")._*` 全组。
> ④**批次4 rules/state/ops 域**(e4c57568, 9 文件 150 处): `host.get("rules").*`(属性对同款)、
> `ctx.state.*`(load/save/maybe_flush+interval 实参/bind_field_snapshots+store 实参/
> next_flush_at/record_execution/get_exec_record/cleanup_orphan_tmp/materialize_migration)、
> `ctx.ops.*`、helpers.make_manager 装载行 `host.get("rules")._load_rules()`。
> ⑤**补漏**(5a3c8a75, 3 文件 9 处): 整仓验收 grep 抓出跨批漏迁(test_trigger_events
> `_handle_maintenance` ×6 / test_web `_assign_new_torrent` ×2 / test_hr `save_state` ×1)。
> 豁免残留: test_qbmanager 别名守阵同对象断言 9 行(计划 §04 明确留 W3 同删)。
> 基线时间: 2026-10-01 07:00, develop @ 5a3c8a75。

TOTAL **1894 passed + 3 skipped / 90%**(13316 语句 / 1106 未覆盖 / 4412 分支 / 437 partial,
test.full 35.9s, rc=0)—— 通过数与 W1 基线 26-10-01-0545(1894+3 / 91%)持平; 覆盖率 91% → 90%
系**预期漂移**: 转发方法失去唯一测试调用方后成为未覆盖语句(未覆盖 1058 → 1106, +48 与迁移
掉的转发方法数同量级), 该语句面随 W3 删除, 非行为回归。
验收: 全部 W2 名 × tests/ 整仓 grep 残留 = 别名守阵 9 行(豁免); 冻结守阵
test_qbmanager_alias_freeze 4 例绿(qbmanager.py 本体未动, 兼容层随 W3 才删)。

## 本波改动面(9 提交, 5+6+2+9+3 = 25 文件次, 约 +670/-670)

- 批次1: test_web.py / test_qbmanager.py / test_facade_modules.py / test_modules_p3.py / test_speed_curve.py。
- 批次2: test_tracker.py / test_mixins_tags.py / test_delete_tags.py / test_hr.py / test_snapshot_sync.py / test_speed_curve.py。
- 批次3: test_grouping.py / test_state_matrix.py。
- 批次4: test_checking.py / test_rule_engine.py / test_rules_core.py / test_trigger_events.py /
  test_ops.py / test_modules_p4.py / test_modules_p5.py / test_module_host.py / helpers.py。
- 补漏: test_trigger_events.py / test_web.py / test_hr.py。
- 过渡期钉子处置: test_modules_p4 两测试的「旧名委托等价/保持可用」断言随迁移改写为纯
  ctx.ops 语义(在途互斥等行为断言保留; 非计划 §04 保护的守阵)。
- src docstring(W1 边界注记移交): webui/server/__init__.py 提法改 `manager.web.commands`/`manager.web`。

## W3 边界注记

- WebviewMixin(views.py)docstring 里 `_shows_pending`/`_search_index_dirty` 等提法为模块自身
  字段名描述, 非消费方, 留 W3 回写随 qbmanager docstring 一并核对。
- run() 接线仍走 manager 旧名(_load_state/_load_rules/_next_state_flush_at 字面量等),
  test_periodic_flush_is_wired_in_run 守阵钉源码 —— W3 删除时**连同守阵同波改写**(计划风险表)。
- 别名守阵区(test_web_state_alias_proxies_to_runtime / test_qbmanager_source_has_no_web_state_fields,
  test_qbmanager.py 847-890)随 W3 删别名表同波删除。
- 机械替换的两条教训(丢接收者 / 跨批漏迁)已落 pitfalls/testing/bulk-rename.md, W3 删除波直接复用其防御。
