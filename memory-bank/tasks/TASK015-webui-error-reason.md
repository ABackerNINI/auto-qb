# TASK015 — WEB UI 错误种子显示具体原因 (状态列 `error_reason`)

**Status:** In Progress (代码/测试/文档已完, **未提交**; 剩用户真机走查反馈)
**Started:** 2026-09-18
**Owner:** 主线 (单会话连续实施)
**Plan doc:** (无 —— 单点特性, 未产出计划文档)

## 原始请求

> webui目前错误的种子只显示"错误", 需要显示具体错误原因

即: 种子的 qB 状态落到出错(`missingFiles` / `error`)时, 界面状态列不能再只显示笼统的「错误」,
要显示**具体原因**(文件丢失 / tracker 报错原文)。隐含要求: 两套界面(星图 atlas / 棱镜 prism)
一致生效 —— 本项目双 UI 共用 `shared/app.js` 逻辑层, 模板与 CSS 各自镜像。

## 思考过程与决策

- **先核实"原因到底有没有现成字段"**(决定整个方案的前提): 逐条查了 qB Web API 与本地安装的
  `qbittorrentapi`, 结论是 **`torrents/info` 不含任何错误文本/原因字段** —— 只有粗粒度的
  `state` 字符串(`missingFiles` / `error`)。错误文本**只**存在于 `/torrents/trackers` 的每条
  记录里(`msg` 文本 + 数值 `status`)。所以"显示具体原因"必须**派生或额外取数**, 不存在"直接透出"。
- **原因分两类, 取数成本不同, 分开处理**:
  1. `missingFiles` → 原因就是状态本身(`文件丢失`), **零 API 成本**, 直接由状态判定;
  2. `error` → 需读 `/torrents/trackers` 的 `msg`(如 `torrent not registered with this tracker`)。
- **架构约束决定"取数只能在主循环"**: 视图组装(`_member_view`/`_seed_view`/`_build_*_view`)每
  tick 都可能重建, **绝不能在视图里发 qB API**(会把主循环拖死)。因此设计成**主循环预取 + 视图只读缓存**:
  在 `TorrentRecord` 上挂两个**非快照**槽(`tracker_error_msg`/`tracker_error_ts`), 由
  `WebviewMixin.refresh_error_reasons()` 在主循环按 **TTL + 单轮预算** 限额刷新, 视图组装只读。
- **必须限额的两条理由**: ①错误种子可能**成片**(站点整站挂掉 / 批量文件丢失), 逐 tick 全量拉
  tracker 会阻塞主循环 → `ERROR_REASON_BUDGET = 5` 条/轮, 余下按轮次摊开; ②`msg` 随站点状态变化,
  不能永久缓存 → `ERROR_REASON_TTL = 300s` 过期重取。**先写时间戳再拉取**(失败也不在 TTL 内反复重试)。
- **`missingFiles` 明确不进拉取分支**: 原因自明, 再花预算去拉 tracker 是浪费 —— 而"文件成片丢失"
  恰恰是最需要保住预算的场景。实测发现该种子会吃掉预算并触发多余 tracker 调用, 已修正(见进度日志)。
- **门控复用 Web 活跃判据**: 预取与"视图重建/搜索索引构建"同一门控(`WEB_VIEW_TTL` 内的
  `_web_last_seen`), 网页关掉后不发多余的 tracker 请求(与既有 `ensure_group_view` 同纪律)。
- **脏判定必须显式**: `tracker_error_msg` **不是快照字段**(不进 `_SNAPSHOT_FIELDS`/`_raw`, 不参与
  `apply_delta` 与 `store.view_changed`), 所以"种子数据一字未变、原因却变了"这条路径**不会**自动
  触发视图重建 → 变化时由预取方显式 `_group_view_dirty = True`(与"配置派生展示值"同一判别法)。
- **取数单点放后端, 前端只展示**: 新增 `_error_reason(rec)` 作为原因文本的**唯一出口**,
  视图里以 `error_reason` 字段透出; 前端 `stateText(m)` 仅在 `kind === "error"` 且有 `error_reason`
  时改用它, 其余回落 `kindText`。**禁止前端按 state 猜原因**(与 HR 标签/hover 口径同纪律)。
  `kindText` 保留用于状态图例 / 筛选器 / 组级与集级聚合文案 —— 那里没有"某一种子的原因"可言。
- **状态列展示要防溢出**: 原因文本(tracker 原文)可能很长, 状态列窄 → 前端用
  `<span class="state-text">` 包裹文本节点 + `ellipsis`, **不能把裸文本节点直接放进 flex 子元素**
  (匿名文本节点不可压缩, `min-width: 0` 对它无效), 悬浮 `title` 看全文。

## 实现计划

1. `torrents/record.py`: 新增两个非快照槽 `tracker_error_msg`/`tracker_error_ts`(带注释说明为何不进快照)。
2. `mixins/web_view.py`: `_error_reason()`(原因单点) + `_fetch_tracker_error()`(提取 tracker 报错文本,
   跳过虚拟条目) + `refresh_error_reasons()`(主循环预取: TTL/预算/清空/显式置脏); `_member_view` 与
   `search_torrents._view` 透出 `error_reason`。
3. `qbmanager.py`: `_tick` 在 Web 活跃门控内调用 `refresh_error_reasons()`。
4. `shared/app.js`: 新增 `stateText(m)`(错误状态优先显示 `error_reason`)。
5. `atlas/index.html` + `prism/index.html`: 4 处状态单元格改用 `stateText` + `.state-text` 包裹
   (辅种行 / 明细行 / 未识别行 / 抽屉头徽标 tooltip)。
6. `atlas/style.css` + `prism/css/views.css`: `.state-text` 省略规则。
7. 测试: `test_web.py` 5 项 + `helpers.FakeTorrent` 补两槽 + `test_torrents.py` 快照槽守卫补登记。
8. 验证: 全量 pytest + 临时假 qB 服务(真实 `create_app`/uvicorn)浏览器冒烟(双 UI)。

## 子任务状态表

| 项 | 内容 | 落地 | 状态 |
|---|---|---|---|
| 1 | 原因无现成字段的核实 | 查 qB Web API + `qbittorrentapi`: `info` 无错误文本, 原因只在 `trackers.msg` | ✅ |
| 2 | 记录层缓存槽 | `TorrentRecord.tracker_error_msg`/`tracker_error_ts`(非快照, 不参与 `apply_delta`/脏判定) | ✅ |
| 3 | 原因单点 | `WebviewMixin._error_reason`: `missingFiles`→`文件丢失`; `error`→预取文本, 取不到回落`错误` | ✅ |
| 4 | tracker 文本提取 | `_fetch_tracker_error`: 跳过 DHT/PeX/LSD 虚拟条目, 取首条 `status∈{4,5,6}` 的非空 `msg` | ✅ |
| 5 | 主循环预取 | `refresh_error_reasons`: TTL 300s + 预算 5/轮 + 离开错误态清空 + 变化显式置脏 | ✅ |
| 6 | 接线与门控 | `qbmanager._tick` 在 `WEB_VIEW_TTL` 活跃窗内调用(关网页不发请求) | ✅ |
| 7 | 视图透出 | `_member_view` / `search_torrents._view` 增加 `error_reason` | ✅ |
| 8 | 前端文案单点 | `shared/app.js` 新增 `stateText(m)`(双 UI 自动生效) | ✅ |
| 9 | 双 UI 模板 | 星图/棱镜各 4 处状态格改 `stateText` + `.state-text`(含抽屉头 tooltip) | ✅ |
| 10 | 双 UI 样式 | 两套 CSS 加 `.state-text` 单行省略(flex 子元素可压缩) | ✅ |
| 11 | 测试 | `test_web.py` 5 项(tracker msg/缺失文件/预算与 TTL/恢复清空/断连跳过) + 守卫同步 | ✅ |
| 12 | 验证 | 全量 `1006 passed`(基线 1001 + 5); 假 qB 服务浏览器冒烟: API 与双 UI DOM/截图实测 | ✅ |
| 13 | 文档收尾 | 本档案 + `_index` + activeContext + testing + pitfalls + modules + README | ✅ |

## 进度日志

- 2026-09-18: 会话开始, 读 `activeContext.md` + `modules.md` 前端契约 → 定位视图组装层
  (`mixins/web_view.py`) 与共享逻辑层(`shared/app.js`)。
- 2026-09-18: **核实前提**: 查 `torrents/info` 的序列化字段(qB 源码 `serialize_torrent.h` /
  `torrentscontroller.cpp`)与本地 `qbittorrentapi` 枚举 —— 确认 `info` **无**错误文本字段, 只有
  `state`; 错误文本只在 `/torrents/trackers` 的 `msg`。据此定下"预取 + 缓存 + 只读视图"的方案骨架。
- 2026-09-18: 后端改完(record 两槽 + web_view 三方法 + qbmanager 接线), 视图透出 `error_reason`;
  首跑测试两项失败: ①`test_snapshot_fields_match_record_slots` 报"有声明了但不在字段表的 slot"
  → 把两槽登记进该守卫的 `lazy_slots`(正确: 它们是派生展示字段, 非 qB 快照字段);
  ②`missingFiles` 吃掉预算并触发多余 tracker 调用 → 在预取分支排除 `MISSING_FILES`。
- 2026-09-18: `test_refresh_error_reasons_budget_and_ttl` 第二段断言偏差(期望 `HA,HB,HA,HB` 实得
  `HA,HB,HA`)→ 真因是测试里 monkeypatch 的预算没还原(仍是 1), 在 TTL 段前把预算设回 5 后通过。
- 2026-09-18: 前端改完(shared 一处 + 双 UI 模板各 4 处 + 两套 CSS 各 1 条), `node --check` 通过。
- 2026-09-18: 浏览器冒烟: 写临时假 qB 服务(`FakeQbServer` + 真实 `create_app`/uvicorn, 3 个假种子:
  missingFiles / error 带 tracker `msg` / stalledUP), 用无头 Chrome dump DOM + 截图实测双 UI ——
  API `/api/state` 分别给出 `文件丢失` / `torrent not registered with this tracker` / `""`;
  渲染 DOM 中 `.state-text` 文本与 `title` 悬浮提示一致(徽标/文本/`.state-text` 包装层三处),
  截图确认"文件丢失"完整显示、长 tracker 原文按省略号截断并带错误色。
  期间踩两坑: ①临时注入的路由被 `StaticFiles` 挂载(`/`)遮蔽 → 把注入路由插到 `app.router.routes` 最前;
  ②注入脚本放 `</body>` 时 `app.js` 已读过 `localStorage` → 改注入 `<head>`。另: `--headless=new`
  在本次环境挂起, 回落 legacy `--headless` 可用(见 pitfalls)。
- 2026-09-18: 全量测试 `uv run pytest tests -q` → **1006 passed**(基线 1001 + 5 项新测试), 覆盖率 92%。
- 2026-09-18: 文档收尾(本档案 + `tasks/_index.md` + `activeContext.md` + `testing.md` 基线单点 +
  `pitfalls.md` 三条新坑 + `modules.md` 前端契约 + 根 `README.md` 行为描述)。
