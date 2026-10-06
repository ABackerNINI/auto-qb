# 搜索待响应期空命中集接管列表(塌列表跳动)

> 摘要: 搜索匹配是服务端单点(search_torrents)、前端消费 searchHits 的模式下, "输入新词到响应返回之间沿用上一查询的命中集"(search-as-you-type)契约对「空集→首词」转换失效 —— 首词的待响应窗(防抖 400ms + 请求往返)里 searchHits 还是空集, 命中门照常生效把整个列表塌成 0 行: 文档高塌掉 → 滚动位置被钳回 0(列表中部搜一次整页跳顶), 底部停靠面板失去 sticky 锚点跟着弹。修法 = searchPending 门(待响应且命中集未落袋时不许命中门接管列表, 落袋后一次性换真结果); 配套 .layout min-height 撑满首屏治 sticky 脱锚(见 dock-panel)。
> 触发: 改搜索/筛选派生, 改 searchHits 消费, 新增走命中门的列表视图, 搜索时列表闪空, 搜索整页跳顶, 搜索时面板跳动, 待响应窗, search-as-you-type, filteredTorrents, filteredGroups, searchPending, _searchGateActive

### 空集是「还没有裁决」, 不是「0 命中」—— 契约在空集→首词转换处断裂

- **触发**: `filteredTorrents`/`filteredGroups` 命中门 `if (q && !hits.has(r.hash)) continue`; 渐进输入
  ("G"→"GR")时上一词已落袋、命中集非空, 契约成立; 但**首词**(或 clearSearch/resetSearch 后)没有
  "上一查询", searchHits 是空集 —— 用户看到的输入前列表在防抖武装那一刻起整体消失, 直到响应落袋
  (实测: docH 18582→800(恰视口高)→1141, 每轮搜索两次跳)。
- **判别**: 「空命中集」有三种来源: ①待响应未落袋(该显示输入前列表) ②服务端真判 0 命中(该显示
  空态) ③构建中轮间(building 自动重查窗口, 既有行为)。凡"命中集为空就过滤"的派生, 先问空集
  属于哪一种 —— 与 qb_traffic 「有无落袋结果」判据(2026-10-05)同型: 判据的取值域要穷举。
- **处置**: `searchPending` 状态(view.js: onSearchInput 武装防抖即置位 / doSearch 直达入口补武装 /
  resetSearch 清除 / 落袋且过代际守卫后清除)+ `_searchGateActive(q)` 单点(filters.js): 待响应且
  命中集未落袋 → 命中门不生效, 显示输入前列表(命中集非空仍按旧集过滤, 渐进输入不跳)。
  **单点纪律**: 任何新的搜索命中消费视图必须走 `_searchGateActive`, 绕开单点现写命中门 = 复发。
- **守阵**: `test_web.py::test_frontend_search_pending_no_collapse`(searchPending 生命周期四锚 +
  两派生走门 + 旧门 `if (!q) return base` 不得回潮)+ `e2e/drawer-dock-stability.spec.mjs`
  (行为: 逐帧采样, 面板 top 全程偏差 ≤2px、docH 不塌到视口高+150 以内 —— 静态守阵探不到
  「几何/时机错」形态, 必须真浏览器采样)。
- **取证(2026-10-07, prism 1280x800, 修复前)**: 逐字输入 GROUP7, docH 18582→800→1141、
  面板 top 430↔416 反复横跳; 滚到 scrollY=8000 再搜 → 钳回 0。

**Refs:** memory-bank/tasks/26-10-07-webui-drawer-search-jump.md
