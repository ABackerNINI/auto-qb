# 热重载换 Config 对象后, 存量记录的绑定与派生判定不会自动跟进 —— 绑定结果要显式收敛, 非快照字段要显式置脏

> 摘要: 「换对象 ≠ 下游自动跟进」家族三段 —— ①存量 `TorrentRecord.tracker_conf` 仍指向旧 Config 的 `TrackerConfig`, 重绑只有 L2 结构重建与 full_round 补 None 两条路, 配置值类变更(如 `hr_check`)两条都不触发 ⇒ 判定/锚点/规则段读到旧值(修: 认领模块 apply 显式重绑, `tracker:rebound N`); ②HR 判定这类「非 store 快照字段」的派生值变化(取数线程发布新视图)没有置脏消费方 ⇒ WebUI 快照停在旧值(修: 新鲜度基线 + flush_views 比对置脏); ③L2 重建换新 TaskQueue 后种子级任务(内置维护 + interval 规则)随旧队列丢弃且 torrents_added 对存量不触发 ⇒ 维护面停摆到重启(修: 创建入口幂等 + rules 订阅 full_round 补建, issue 26-10-01-2147)。实报(2026-10-03): 热重载开启站点 HR 在线核实后 WebUI 恒显「本地·达标」, 重启进程才显「在线·已达标」。
> 触发: 热重载, apply, 重绑, tracker_conf, hr_check, hr 规则段, 判定不刷新, 本地·达标, WebUI 快照, 置脏, revision, 取数, rebuild_runtime, 种子级任务, 补建, has_task, 任务面, full_round

### 绑定结果持的是旧对象 —— 换 Config ≠ 存量记录自动重绑

- **触发**: 给 `TrackerConfig` 上「派生/配置值」类字段(`hr_check` / `hr` 规则段)加热重载能力, 或排查
  「热重载某段后存量种子行为没变、重启才变」—— 消费方是**存量记录持有的绑定对象**, 不是每轮现读的服务。
- **判别**: 打开三条重绑路径逐一对照变更字段: ①L2 结构重建判据 `RulesModule._tracker_bindings_changed`
  只比较绑定三元组 `(domains, rules, groups)` —— 派生字段变化返回 False; ②full_round 补绑只认
  `tracker_conf is None` 的记录 —— 存量非 None 永不重绑; ③模块 apply —— `TrackerModule.apply` 修复前
  恒短路(2026-09-30 内核化时注释原话「apply 无热重载动作」)。三条都不覆盖 ⇒ 热重载对存量记录静默失效。
  影响面按消费方数: `hr_judgement()`(判「站点未接入」恒走本地兜底) / `HrRuntime._anchors()`(锚点收集
  为空, 对账管线瘫痪) / `hr` 规则段(改要求做种时长不生效) —— 同一缺陷的三个面。
- **处置**: 认领该配置段的模块在 `apply(old, new)` 里**显式收敛绑定结果** —— `old.trackers != new.trackers`
  (整段按值比较)即遍历 `store.by_hash` 中 `tracker_conf is not None` 的记录执行
  `rec.tracker_conf = self.match(rec)`, 回执 `tracker:rebound N` 供热重载日志可见; `ctx.api.client is None`
  (qB 断开)跳过不抛(留给下轮 full_round / L2 兑现), 相等即短路零动作。修一处覆盖全部三个消费面,
  **不要**改判定端现读(只修一个入口, 修不到另外两个面)也**不要**扩大 L2 判据(把配置值比较塞进
  「结构语义」单点, 会把开一个 HR 核实放大成全量重建)。
- **守阵**: `test_tracker.py` 三用例 —— 存量记录持旧 `TrackerConfig` 调 apply 断言 `hr_check` 就位 +
  回执含 rebound / client=None 防御 / trackers 段相等即短路。

### 非快照字段的派生值变化 —— store.view_changed 覆盖不到, 要显式置脏

- **触发**: 给 WebUI 视图加「非 store 快照字段」的展示值(HR 判定 / 错误原因一类由其它管线异步刷新的
  派生值), 或排查「数据明明变了、界面要等别的原因碰巧置脏才更新」。
- **判别**: 该值的更新走的是独立管线(取数线程发布 / 后台预取)而非主循环同步写 store 快照 ⇒
  `store.consume_view_changed()`(快照字段变化驱动)与热重载 `WebUIModule.apply` 置脏都覆盖不到它。
  库内同构先例是「错误原因」: 预取注释明说「该值非快照字段, store.view_changed 覆盖不到, 变化时显式
  `mark_dirty()`」。HR 判定(`HrViewPublisher.revision` 自增)修复前正是缺这同一个机关 —— 取数刷新后
  `revision` 自增却无人消费, 界面挂在旧快照, 只能等重启。
- **处置**: 仿「错误原因」形态加**新鲜度基线**: 视图重建完成时记基线
  (`WebUIRuntime._hr_rev_at_build = hr.revision`, 挂 `_publish_locked` 末尾, 判空防御),
  `flush_views()` 先比对当前 `hr.revision` 与基线, 不等即 `mark_dirty()` —— 下一轮重建后基线自然前移,
  无循环置脏。全部发生在主循环两条线上, 与 `web.group_view_dirty` 既有跨线程语义一致。
- **守阵**: `test_web.py` 两用例 —— 直推 publisher 抬 `hr.revision` 后 `flush_views` 断言
  `group_view_dirty` 置位且重建后基线前移不再置脏。
- **同族**: [hot-reload-held-config.md](hot-reload-held-config.md) 管服务/线程构造期**拷贝**配置那类
  静默失效; 本条管**存量记录绑定**与**派生视图消费** —— 三者都是「换对象 ≠ 下游自动跟进」的变体。

### 换队列 ≠ 任务面自动跟进 —— L2 重建后种子级任务要显式补建

- **触发**: 给 L2 结构重建(`RulesModule.rebuild_runtime`)加新的种子级任务创建面(内置任务/interval
  规则任务), 或排查「热重载后存量种子的维护/规则任务消失、重启才恢复」(issue 26-10-01-2147)。
- **判别**: 顺着任务的唯一创建触发源走到 L2 重建轮 —— `rebuild_runtime` 换新 `TaskQueue()` 后只有
  **全局任务**(delete_tags* / speed_limit_curve, `queue_rebuilt` 相位 + `has_named` 幂等重入队)有人管,
  **种子级任务**(内置 maintenance + interval 规则)的唯一创建点 `_create_torrent_tasks` 挂在
  `torrents_added` 相位上, 而 `store.reset_runtime()` 保留记录(conf=None)⇒ 下轮全量 `_apply` 对存量
  记录不走 added 分支 ⇒ 全量轮重匹配兑现后绑定补上了、任务面没人管。旁证: `reset_runtime` 登记的
  `external_tag_changes`(on_change 模式「首轮全量收敛」的输入)唯一消费方是 `handle_maintenance`,
  任务不存在则无人消费。
- **处置**: 种子级任务创建入口**幂等化**(队列查重 `TaskQueue.has_task(kind, name, hash)`, 以「内置
  maintenance 任务在队」为任务面整面判据) + rules 模块订阅 `full_round`(装配序在 TrackerModule 之后,
  emit 契约: 前序订阅者异常即中断本相位)为 conf 已就位的存量记录补建; conf 仍 None(未匹配站点)留待
  下一全量轮。补建任务 `immediate`(next_run=now)下一 tick 兑现一次维护 —— 消费 `external_tag_changes`
  的语义与 added 管线的 force_tags 等价, 不阻塞 full_round 相位。**不要**在 `queue_rebuilt` 相位补建
  (conf 未就位, `_rules_for_torrent` 对 conf=None 刻意早崩溃); **不要**同步直调
  `handle_maintenance(force_tags)`(逐种子 qB API 批量阻塞相位)。
- **守阵**: `test_modules_p5.py` 三用例 —— `test_full_round_restores_torrent_tasks_after_rebuild`
  (重建→补建→立即到期→重复 emit 幂等) / `test_full_round_skips_unmatched_records`(conf None 不补建) /
  `test_startup_round_tasks_not_duplicated`(首轮全量轮补建与 added 管线双入口任务面恰一份)。
