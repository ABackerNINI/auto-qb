# 冒烟桩绕过生产推导函数 → 与生产判定失真(增量被静默降级为 full)

> 摘要: 桩直改字段/手写派生产物(绕过生产单点函数)当时能过, 生产侧后来加了**以生产函数副作用为判据**的新判定后, 桩链路静默退化成另一条路径 —— 表现是「生产对、桩错」且无报错。本仓实例: ui_harness 直写 delta_fields 绕过 store._apply, S5b 给 flush_views 加 keyed 判定(rounds_applied 前进才算键级源)后, 桩真值轮恒 unkeyed → **恒 full**(S4→S5b 间事故, 2ca5491f 修复)。
> 等级: L0
> 触发: ui_harness, 冒烟桩, delta_fields, rounds_applied, keyed, unkeyed_command_source, 恒 full, store._apply, 桩失真, 手写派生字段, view_changed, 增量降级, seed_store, rid, full_update, full_round, tracker_conf, site_alert, no_site_conf, add_torrent, 控制端点
**Refs:** memory-bank/tasks/26-10-07-webui-delta-sync-feasibility.md, memory-bank/pitfalls/testing/stubs-sim.md, memory-bank/issues/26-11-03-1135-test-e2e-site-alerts-order-pollution.html

### 桩改状态必须走生产同一条推导(`store._apply`), 不得手写派生字段

- **触发**: 桩/冒烟需要「状态变化进视图/增量时间线」时, 直接改替身属性或手工预写派生字段
  (`delta_fields` / `view_changed` / `dirty_groups`) —— S4 期 `_publish_with_delta` 就是这么写的, 当时能过。
- **判别**: 生产侧存在以生产函数副作用为输入的下游判定(本仓: flush_views 的 keyed 判定要求
  `rounds_applied` **前进** —— 只有真 `store._apply` 才推进它); 绕过 ⇒ `keyed=False` ⇒
  `unkeyed_command_source` ⇒ **真值轮恒 full**(增量被静默降级为全量, 违背「增量成为默认路径」)。
  pytest 全绿(镜子测试走真 _apply, 测不到桩失真), 只有真浏览器冒烟看得到 —— S7 收尾冒烟
  净树 stash 对照确认非 S7 引入。
- **处置**: 桩走生产同一条推导: 目标值作为**增量 patch** 喂给真 `store._apply`(patch 形状与
  生产增量响应同形, 只含变化种子的变化字段), 不再手工预写任何 store 增量字段;
  **回弹(_restore_state)同款** —— 否则回弹版推不出脏行, 前端行永久停在陈旧增量上
  (旧全量前端每轮整表替换, 天然掩盖这类失真)。守阵: 冒烟断言 delta 轮 `full===false`
  (e2e/delta-sync.spec.mjs 已有)。

### 桩替身的快照字段集与真记录**不同源**(FakeTorrent._SNAPSHOT_FIELDS 缺速度/调度字段)

- **触发**: 桩里想模拟「活跃传输种子每拍速度变化」, 给 `FakeTorrent.apply_delta` 喂
  `dlspeed` / `upspeed` / `eta` / `num_seeds` 等 patch(真 `TorrentRecord` 的合法快照字段)。
- **判别**: `FakeTorrent._SNAPSHOT_FIELDS`(tests/helpers.py 手写元组)只含 name/save_path/
  state/size/tags/category/downloaded/uploaded/seeding_time/ratio/progress 等十几个字段,
  **不含 dlspeed/upspeed/eta/num_seeds/num_leechs/tracker 等**; apply_delta 对不在集内字段
  **静默跳过**(返回空 frozenset) ⇒ rounds 前进而 delta_fields 恒空 ⇒ keyed 判定失败 →
  unkeyed → 恒 full, 且无任何报错。
- **处置**: 桩里模拟变化只用**在集字段**(state / uploaded / downloaded / ratio / progress /
  seeding_time / tags / category 等); 或把替身字段集与真 `compat._SNAPSHOT_FIELDS` 对齐
  (那是另一个独立改动, 需评估波及面)。给真记录加快照字段时, 记得检查替身元组是否同步
  (同「替身漂移」家族, 见 stubs-sim.md)。

### 桩直写 store.by_hash 不推进同步游标 → 首个探针触发 full_round, 静默重写注入的配置派生态

- **触发**: 桩为了保留对象身份用 `seed_store()` 直写 `store.by_hash`(未经 `apply_sync`), 之后又提供
  `/__harness__/add_torrent|remove_torrent` 这类「走生产路径」的控制端点。
- **判别**: `store.rid` 仍为 0 ⇒ 首个探针触发 `_refresh_torrents` → `apply_sync(rid=0)` ⇒ FakeClient
  回 `full_update=true` ⇒ `need_validate` 真 ⇒ 内核 `emit("full_round")` ⇒
  `TrackerModule._on_full_round` 把所有 `tracker_conf is None` 的记录按 `client.torrents_trackers`
  重匹配。桩此前注入的 `tracker_conf=None`(no_site_conf)因此在**第一次 add/remove 后静默变成
  真实站点配置**, 依赖它的断言全红; `tracker_health_msg` 类注入不经 full_round 而幸存 —— 症状是
  「只有一半注入态消失」, 且隔离跑绿、全量跑红(取决于哪个 spec 先用了探针)。
- **实证**(2026-11-03, issue 26-11-03-1135): 未修桩时 `/api/state` 注入后 2 条 site_alert,
  `POST /__harness__/add_torrent` 后只剩 tracker_error(1 条), remove 后也不恢复; 修桩后
  add/remove 前后恒为 2 条。
- **处置**: 启动时在 `seed_store` + client 数据灌入之后、注入派生状态之前补一次真实全量同步
  (`mgr.store.apply_sync(mgr.api)`) 对齐 `rid`(生产首轮本就是全量轮); 注入必须放在其后, 否则
  全量 delta 会覆盖注入的 `tracker` 字段。守阵: 用控制端点的 spec 与依赖注入态的 spec 同轮全量
  跑必须全绿。

### 替身 to_dict 用 vars() 全导出、非快照对象字段漏出 → 详情端点恒 500(实爆实例)

- **触发**: 替身 `FakeTorrent.to_dict` 图省事用 `vars()` 全导出 —— 真记录「快照字段 / 非快照
  字段」的分则被抹平, 非快照字段 `hr_link`(HrRuntime 对象, 按设计不进 JSON)随 dict 漏出。
- **判别**: `/api/torrents/{hash}` 详情端点**恒 500**(对象不可 JSON 序列化); 列表路径走字段
  白名单不炸, 只有详情整 dict 直传的路径暴露 —— 2026-10-07 S10 e2e 复测才逮到, pytest 全绿
  测不到(镜子走自己的替身契约, 同上节「只有真浏览器冒烟看得到」的盲区)。
- **处置**: 替身 to_dict 弃 `vars()` 全导出, 口径改为与真记录 `compat._SNAPSHOT_FIELDS` 同源
  对齐(快照字段照抄 + 非快照字段按真记录分则), 947c0fb0 修复 —— 上一节「把替身字段集与真
  compat._SNAPSHOT_FIELDS 对齐」的预警成真实爆点。
