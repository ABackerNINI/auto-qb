# FakeClient 默认 tracker 回退掩盖「全未配库」缺陷

> 摘要: FakeClient.torrents_trackers 在 trackers_map 未命中时默认回 HHan URL(helpers.py:122-125), 于是「全库种子 tracker 未配置」场景在桩里被静默改写成「全库已配 HHan」, 基于「无 matched_added」的守阵恒绿; 守阵必须显式把每个种子的 trackers_map 映射到未配域名, 才能真验全未配分支。
> 触发: FakeClient, torrents_trackers, trackers_map, 默认回退, HHan, 未配库, 全未配, matched_added, tracker 重匹配, 桩假绿, 守阵空跑, site_provisional, no_site_conf

### 形态一: 默认回退把「未配」改写成「已配 HHan」 (2026-11-23)

- **触发**: 写「全库种子 tracker 均未配置」的守阵/桩场景(如基础代临时态结算、真 no_site_conf、无 group_key_migrations 分支), 只把 `rec.tracker_conf` 置 None 或把合成种子的 `tracker` 留空, 没有动 `FakeClient.trackers_map`。
- **判别**: `tests/unit/helpers.py` 的 `FakeClient.torrents_trackers(h)` 在 `h not in self.trackers_map` 时返回固定 `[{"url": "https://tracker.hhanclub.net/announce.php"}]`(helpers.py:122-125)—— 这是为既有用例「每个种子默认有 HHan tracker」设的便利默认, 但任何依赖 `client.torrents_trackers` 做域名重匹配的逻辑(TrackerModule.match / full_round)都会把它读成「已配 HHan」, 于是 `matched_added` 非空、`tracker_conf` 被绑回 HHan, 全未配分支**根本没走到**。表面症状: 守阵恒绿、告警恒为 no_site_conf 之外的态、临时态按「已配」路径结算。
- **处置**: 守阵里对每个种子显式写 `mgr.client.trackers_map[h] = [{"url": "https://tracker.unconfigured.example/announce.php"}]`(未配域名, 与 config.trackers 任一 domains 都不匹配), 覆盖默认回退; 桩侧同理(ui_harness.py 的 boot-first 分支若跳过站点告警注入, 要确认 trackers_map 是否被默认回退顶掉)。断言前先读一次 `client.trackers_map` 确认每个目标 hash 都在表里 —— **不能只靠 tracker_conf/tracker 字段判定「未配」是否成立**。
- **复发**: 1(2026-11-23, 计划 26-11-23-1339 S4 收尾取证时发现)。**为什么没命中**: 既有坑档讲的是「桩恒空数据让某渲染路径测不到」, 本形态反过来 —— 桩给了**看似合理的默认值**, 把要测的「全未配」负向面直接抹成正向面, 比恒空更隐蔽(绿得理所当然)。**关联**: 同族 `stubs-sim.md` 的「桩数据保真度」纪律在此的延伸 —— 默认值本身就是数据契约的一部分, 负向场景必须显式覆盖它。
