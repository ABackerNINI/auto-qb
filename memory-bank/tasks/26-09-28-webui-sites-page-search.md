# 26-09-28-webui-sites-page-search — 站点页搜索: 全字段匹配与多命中展示

**Status:** Done
**Added:** 2026-09-28
**Updated:** 2026-09-28 23:34
**Summary:** 按计划 plans/26-09-27-1852 实施 trackers 二级页搜索: 名称/域名/标签/分组/删标/规则/限速/HR 全字段前端匹配, 语法照搬种子搜索(空格 AND / -词排除 / "短语"); 命中展示 26-09-28 由分栏改搜索框下挂下拉浮层(hb-tr-drop)+详情整栏, 深夜再改跳转器交互(点命中/点外即收即清词)治下拉覆盖不消失。纯前端零后端。

## 原始请求

实施计划 `memory-bank/plans/26-09-27-1852-plan-sites-page-search.html`(五项设计问题已于 26-09-27 拍板)。

## 思考过程与决策

- **数据源即已加载配置树**: 站点搜索是 facets 同族的纯内存筛选, 不碰文件系统, 与种子搜索「服务端化」决策(26-09-26)不冲突; 匹配函数收敛前端单点(trackerNorm / trackerParseQuery / trackerRows 各一处)。
- **索引重建不用挂钩**: `hubTrackerIndex` 做成 Vue computed, 依赖遍历 cfg.tree 每站每键 —— 编辑/增删/重载天然触发重算, 不在 cfgLoad 上另挂重建钩子。
- **详情卡复用而非重写**: 搜索态右栏直接复用非搜索态的 `hb-blk` 字段编辑块(重命名/删除/hub-field 行), 用 `display: block ↔ grid` 切换容器布局, 避免模板复制两份。
- **选中态即 cfg.trackerKey**: 命中行点击 = 置 trackerKey(与 pill 一致), 左栏高亮 = `cfg.trackerKey === name` 的 class 绑定; 仅一命中自动选中走 `hubTrackerHits.hits` watcher(hits 不依赖 trackerKey, 无回环)。
- **孤儿方法顺手清**: pill 键数徽标删除后 `hubCount()` 全仓零引用, 一并移除(计划内)。

## 实现计划

见 [plans/26-09-27-1852-plan-sites-page-search.html](../plans/26-09-27-1852-plan-sites-page-search.html) §04-§07(匹配算法 / 多命中显示 / 交互细节 / 实施落点), 本档案不复制。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | config_editor.js 声明 `trackerQuery` state | Done |
| 2 | config_hub.js: norm/parse/rows 单点 + 索引/命中 computed + Esc·离开分区清空 + 单命中自动选中 | Done |
| 3 | settings.html trackers 分支: 搜索行 + 命中列表 + 左右分栏 + pill 去键数徽标 | Done |
| 4 | console_hub.css: hb-tr-* 样式(皮肤令牌, 三皮肤共用) | Done |
| 5 | 守阵 test_frontend_tracker_search_wiring + test.full 全绿 | Done |
| 6 | 命中展示改下拉: hb-tr-split 分栏废, hb-tr-drop 浮层 + 详情整栏(用户 26-09-28 要求) | Done |
| 7 | 跳转器交互收层: 点命中=选中+清词(hubTrackerPick) + 点外即收(hubOnDocClick), 治覆盖不消失(用户 26-09-28 报障) | Done |

## 进度日志

- **2026-09-28 00:14 (Done)**: 实施完成。开工同步快进合并远端 7 笔(6262d3b→c7dfbd2), `_doc-map.md` stash 施回冲突已解决并由 kb.index 重建收敛。test.full **1812 passed + 3 skipped / 91%**(基线切片 [26-09-28-0014](../testing/baselines/26-09-28-0014-webui-sites-page-search.md))。新增守阵 1 条; `_common.CAP_POLICY["index-auto"]` 12000→12100(sites-page-search 专题入册后 12,006 超 cap) + SKILL.md cap 表同步。新坑入库: pitfalls/web-ui/cjk-regex-norm.md。
- **2026-09-28 15:58 (Done)**: 用户要求「搜索结果改下拉框, 取消左右显示」。模板: 命中列表移入搜索行容器内作锚定下拉(hb-tr-drop, v-if hubTrackerActive), 详情 hb-tr-detail 整栏宽; 行为不变(点命中只选中不清词 / 单命中自动选中 / Esc·×清空)。CSS: 删 hb-tr-split 栅格与响应式降级, hb-tr-drop 视觉口径对齐 search-help-pop(--bg-elev + border-strong + shadow-3, z-40, 限高 320px/窄屏 55vh 内滚), 命中行改行间分隔线式。JS 零改动。守阵同步 hb-tr-split/hits→hb-tr-drop。stash→ff(c64b836f)→pop 与远端 tooltip 笔干净合流。
- **2026-09-28 23:34 (Done)**: 用户报障「搜索结果覆盖站点设置且不会主动消失」→ 根因: 15:58 那轮形态改下拉时 JS 零改动, 沿用分栏时代交互 —— 「点命中只选中不清词」(Q5)在覆盖式浮层下成死锁(切站效果留在浮层底下看不见), 收起仅 ×/Esc/离开分区三条显式路径。用户三选一拍板「跳转器交互」: hubTrackerPick(点命中=选中+清词收层直达详情) + hubOnDocClick 点外即收(closest .hb-tr-search 豁免搜索行内点击, 复用既有全局监听), 收起一律清词不引入 dismissed 状态位(hubTrackerActive 仍由搜索词驱动); 单命中自动选中 watcher 不变; Q5「保留搜索」拍板随下拉形态退役。守阵收起路径两条→四条断言(Esc/离开分区/点外即收/点命中即收)。test.full **1831 passed + 3 skipped / 91%**(基线切片 [26-09-28-2334](../testing/baselines/26-09-28-2334-webui-tracker-search-jump.md))。新坑入库: pitfalls/web-ui/overlays.md「形态切换要连交互一起重新评审」。
