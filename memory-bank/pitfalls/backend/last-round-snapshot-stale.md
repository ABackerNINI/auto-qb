# 「最近一轮」快照不排空, 下轮才覆盖 —— 消费侧必须联合轮次计数防残值误判

> 摘要: 增量快照(`last_added` / `last_removed` / `delta_fields`)是「最近一轮」语义 —— **不排空, 下一轮 `_apply` 才覆盖写**。无新应用轮时它们是**残值**: 单独当键源会把上一轮的变更重复发布或把无键轮误判成有键轮(归约回空 delta → delta 客户端漏变更)。消费侧判定必须联合 `rounds_applied`(轮次计数前进)防残值误判。S5b 镜子 fuzz 220 轮抓到(effdc31a)。
> 触发: last_added, last_removed, delta_fields, rounds_applied, 残值, 最近一轮, keyed, 增量键源, 快照语义, 消费判定, fuzz, 纯命令源
**Refs:** memory-bank/tasks/26-10-07-webui-delta-sync-feasibility.md, memory-bank/pitfalls/testing/stub-bypass-apply.md

### 「无新应用轮」时最近一轮快照是残值, 不得单独当成本拍键源

- **触发**: 消费 S1 型增量快照推导本拍脏行键(如 flush_views 把 last_added/last_removed/
  delta_fields 折进增量时间线); 这三个字段由 `store._apply` 每轮**整体覆盖写**(先清后赋),
  不是 consume 式(读后复位)。
- **判别**: 本拍没有新 `_apply` 轮(`rounds_applied` 未前进)时, 三者是上一轮的残值。危害形态:
  ①纯命令源(命令自写 `update_torrent_fields` / `reset_runtime` / 标签定义删除)只置
  view_changed 不跑 `_apply` —— 若拿残值当键源, 会把**上一轮**变更的行再次发布(重复噪音)
  或误判 keyed; ②误判 keyed 的轮若键集其实是旧轮的, 归约出的 delta 与本代 rid 不匹配
  (S1 残值误置 keyed 缺口, effdc31a 修复)。S5b 镜子 fuzz(220 轮逐轮比对增量客户端 ≡
  全量客户端)是抓到它的手段 —— 单点构造难想到这个时序。
- **处置**: keyed 判定 = 「`rounds_applied` 前进」**与**「三快照非空」**同时**成立
  (runtime.py flush_views 用 `_drained_sync_rounds` 记上次排空轮次); view_changed 真
  而无键 → 本代 full 降级(`unkeyed_command_source`, R11 保守正确优先)。新增「最近一轮」
  型快照时二选一: 要么做成 consume 式(读后清空, 残值不可能存在), 要么配套一个轮次计数
  供消费侧联合判定 —— 不留第三种「覆盖写但消费侧不看轮次」的组合。
