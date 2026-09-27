# 1741 passed + 1 skipped —— 字段变化触发时机 on_torrent_field_changed + 维护任务 tags 迁移

> 摘要: plans/26-09-27-1438 四里程碑落地。①(A)新触发时机 `on_torrent_field_changed` +
> 配套规则键 `watch_fields`(v1 白名单 tags/category): store 层跨轮基线 `field_snapshots`
> (state v2→v3, 仅存被监听字段, 无监听规则零写入) + qB 增量 ∩ 监听字段后与基线对比出
> **净变化**才分派(全量 refresh 降级路径同判据, 非"全变"); 首见只落基线; 程序自写不自触发
> (self-caused **值匹配**抑制, 单点 `store.update_torrent_fields`: 上报值与自写期望一致才按
> 自写处理, 被外部覆盖则放行); 重启停机期变化首轮补捕(新增种子分支也过登记点);
> cooldown/execute_once 复用 exec_history。②(B)新顶层键 `maintenance_tag_mode`
> (interval|on_change, 默认 interval = 现状): on_change 时站点 tags 部分改为"添加时 + tags
> 外部变化时重检"(store.external_tag_changes 登记/消费一次; 热重载 L2 后首轮全量收敛),
> HR 部分恒按周期执行。⑤顺手兑现 `reset_runtime` 既有契约: 全量轮重匹配被置空的
> tracker_conf(热重载 L2 后存量记录 conf 恒 None 的既有缺口, 事件分派/维护任务依赖 conf)。
> 生产 config.yml 零修改, 默认行为逐字节等价。
> 基线时间: 2026-09-27 17:23(合并远端 console-skin/file-access-fixes 之后的新基线 68d1e243 复测)
> 档案: plans/26-09-27-1438(计划即档案)

- **测试增量**: 1723+1 → **1741+1**(+16 本轮 + 2 远端): test_trigger_events.py 新增 14 条(字段变化
  触发一次/首见基线/自写抑制/category×未监听字段/重启补捕+无风暴/cooldown/全量降级净变化/
  watch_fields 校验三态/合法加载/maintenance_tag_mode 校验/维护行为矩阵四态),
  test_versioning.py 生产迁移用例扩为 v1→v3 + v2→v3 + v3 幂等(+2);
  test_rule_engine.py 状态链用例去硬编码(STATE_V 随 CURRENT)。既有用例升级:
  v2 硬编码预期随 CURRENT_VERSIONS 抬到 v3。
- **代码触点**(14): torrents/store.py(watch_fields/field_snapshots/field_changed/
  external_tag_changes/self_caused_fields + _register_field_changes/_watch_value/
  update_field_snapshots/set_watch_fields + update_torrent_fields 值匹配登记 +
  reset_runtime 全量收敛标记) / core/mixins/rule_engine.py(_load_rules 监听集合推导 +
  _bind_field_snapshots + _dispatch_events field 分支) / core/qbmanager.py(绑定接线 +
  分派/基线刷新点 + _handle_maintenance force_tags/模式分支 + 全量轮 conf 重匹配) /
  rules/base.py(watch_fields 解析) / infra/versioning.py(state v3 + _migrate_state_2_3) /
  config/validation/rules.py(trigger 五值 + FIELD_WATCH_ALLOWED + _validate_watch_fields) /
  config/validation/core.py(maintenance_tag_mode 键+取值) / config/models.py +
  loaders.py(五件套) / config/schema/{fields,rules,groups}.py(常量/字段/守卫同源) /
  tests/helpers.py(FakeConfig.maintenance_tag_mode)。
- **语义取舍**(写入 keys.md): self-caused 用**值匹配**而非计划 §04 细则 5 的"同字段一律
  抑制" —— 值可比对时以值为准, 避免吞掉同字段的后续外部变化(测试钉住); "宁漏勿环"仅用于
  值无法区分的场景。

TOTAL 91%(11662 语句 / 850 未覆盖 / 3912 分支 / 349 partial; test.full 19.4s, 1 采样, 合并树复测;
覆盖率口径见 [../baseline.md](../baseline.md))。
