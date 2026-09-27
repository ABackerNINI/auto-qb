# field-changed-trigger — 字段变化触发时机 + 维护任务 tags 迁移

> 摘要: plans/26-09-27-1438 四里程碑全部落地。①新触发时机 `on_torrent_field_changed` +
> 规则键 `watch_fields`(v1: tags/category): store 跨轮基线 `field_snapshots`(state v2→v3,
> 按需写入) + 增量/全量统一"与基线对比出净变化"才分派; 首见只落基线; 程序自写不自触发
> (self-caused **值匹配**抑制, 单点 store.update_torrent_fields); 重启停机期变化首轮补捕。
> ②新顶层键 `maintenance_tag_mode`(interval|on_change, 默认 interval = 现状): on_change 时
> 站点 tags 部分改为"添加时 + tags 外部变化时重检", HR 部分恒按周期。③顺手兑现
> reset_runtime 既有契约: 全量轮重匹配被置空的 tracker_conf(热重载 L2 既有缺口, 本计划 §07
> 的前提)。生产 config.yml 零修改, 默认行为不变。
> 全量 1741 passed + 1 skipped(TOTAL 91%, 合并远端 console-skin 后复测), 基线 `26-09-27-1723`。
> 最后活动: 2026-09-27 17:40

## 本轮事实

- store 层新增五个运行态: `watch_fields`(监听并集, _load_rules 收尾推导 = 规则 watch_fields
  ∪ on_change 模式的 tags) / `field_snapshots`(与 state["field_snapshots"] 同一对象,
  update_field_snapshots **原地**更新) / `field_changed`(本轮净变化候选) /
  `external_tag_changes`(维护重检登记, on_change 消费一次) / `self_caused_fields`
  ({hash: {field: 期望值}})。
- **值匹配**取代计划 §04 细则 5 的"同字段一律抑制": 上报值与自写期望一致才按自写处理;
  被外部覆盖(值不同)按外部变化放行 —— 避免吞掉同字段的后续外部变化(测试钉住), "宁漏勿环"
  仅用于值无法区分的场景。
- 新增种子也过登记点: 有持久化基线(重启场景)与基线对比 → 停机期变化首轮补捕; 无基线只落
  基线, 不触发、不打重检标记。
- 维护 tags 部分幂等(_add_tags 无变化时无 API 调用), 行为矩阵测试用 **spy**(_spy_tags_part)
  探调用而非调用记录; HR 部分节奏不变的判据用"downloaded 增长后 HR 照常触发"表达。
- 测试基建: `_keep_refresh` 复用同一 client(增量 rid 语义) —— 字段事件考察持续运行语义,
  `_refresh` 每轮新 client 的全量重报会与自写回声纠缠; `_NoSyncClient.torrents_add_tags`
  写回种子对象模拟 qB 接受自写(全量降级路径测净变化的前提)。
- 文档回写: config-reference/keys.md(maintenance_tag_mode 行 + on_torrent_field_changed 节 +
  state.json 结构 v3) / rule-system/rules-and-triggers.md(触发时机表第五行) /
  config-reference/loading-and-write.md(trigger 五值 + watch_fields 校验)。

## 验证

- test.full 全绿记基线 `26-09-27-1723`(1739+1, TOTAL 91%, 17.2s)。
- 守卫自动覆盖: test_config_schema(顶层键/规则键/常量), 新键漏改任意一处即红。

## 待办 / 交接

- 提交轮未做(等用户显式「提交」)。
- WEB UI 回归计划内未单测(RULE_FIELDS/constants 驱动自动呈现, 计划 §06 定的口径); 下次
  开设置页时顺带看一眼规则编辑器里 watch_fields 输入框与 trigger 下拉第五项即可。
- 生产 config.yml 是否切 `maintenance_tag_mode: on_change` 由用户自行决定(红线: AI 不动)。
