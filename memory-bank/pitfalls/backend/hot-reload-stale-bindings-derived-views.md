# 热重载换 Config 对象后, 存量记录的绑定与派生判定不会自动跟进 —— 绑定结果要显式收敛, 非快照字段要显式置脏

> 摘要: 热重载只把 `manager.config` 换成新对象, 两类下游不会自动跟进: ①存量 `TorrentRecord.tracker_conf` 仍指向旧 Config 的 `TrackerConfig` —— 重绑只有 L2 结构重建与 full_round 补 None 两条路, 配置值类变更(如 `hr_check`)两条都不触发 ⇒ 判定/锚点/规则段读到旧值; ②HR 判定这类「非 store 快照字段」的派生值变化(取数线程发布新视图)没有任何置脏消费方 ⇒ WebUI 快照停在旧值。实报(2026-10-03): 热重载开启站点 HR 在线核实后 WebUI 恒显「本地·达标」, 重启进程才显「在线·已达标」。
> 触发: 热重载, apply, 重绑, tracker_conf, hr_check, hr 规则段, 判定不刷新, 本地·达标, WebUI 快照, 置脏, revision, 取数

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
