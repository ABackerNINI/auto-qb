# 轮询重渲染把派生候选塞回选中集 (筛选器"自己重置")

> 摘要: 数据是轮询/增量刷新、某一组筛选的**候选值从数据派生**(不是定长常量数组)时, 若在每次数据到达的派生函数里直接 `选中集.add(候选)`, 每轮刷新都会把用户刚取消的勾选加回来 —— 表现是「这一组筛选器每隔 N 秒自动重置」; 而候选是定长常量的那几组(形态 / issue 类型)完全正常, 因为它们的候选压根不进派生。**只中一组、且按刷新节奏复发**就是本坑的指纹。修复 = 给自动入选加「只补一次」的记账(statusSeeded): 派生仍补数据里新冒出来的候选(否则带新值的条目会静默消失), 但已入选过的值不再碰。**同族坑 (本文末节)**: 给筛选器加 localStorage 持久化后, 还原时若不同时把已知候选计入该台账, 刷新后首轮派生又把用户取舍盖回 —— 症状与不落盘时一样, 看着像"持久化没生效"。
> 触发: 筛选器自动重置, 过滤器自己复位, 每隔一会儿又全选, 勾选取消了又回来, 轮询后筛选失效, 派生候选 vs 常量候选, 只有某一组筛选出问题, 状态筛选器重置, poll reseed, auto-reselect, 筛选器刷新重置, 筛选器不保存, 刷新后筛选丢失, 筛选持久化, localStorage 筛选, 持久化后又被重播种, 还原后筛选失效, 取消的筛选刷新又回来
**Refs:** memory-bank/activeContext/26-10-04-0952-kb-nav-page.md · memory-bank/testing/baselines/26-10-04-1730-kb-nav-status-filter.md

### 只有一组筛选器"每隔一会儿自己重置" (2026-10-04 kb.nav 台账实测)

- **触发**: 用户报「`kb.nav` 台账的**状态**筛选器每隔一段时间自动重置, **形态 / issue 类型**筛选器正常」; 页面每 30s 静默重拉 `/api/data` 并重渲染当前视图。
- **判别**: 先看**候选值从哪来** —— 形态 `FORM_ORD`、issue 类型 `TYPES` 是写死的字面量常量数组, 派生函数不碰它们, 所以不受影响; 状态是从 `DATA.items` 现算的 `new Set(items.map(stOf))`(还会有「(无状态)」这类只有数据里才出现的值), 派生每轮都要扫一遍补新值。**落在同一个 `derive()` 循环里的那句 `S.aStatuses.add(s)` 就是全部根因**: 本意是「新出现的状态要自动入选, 否则带该状态的条目会静默消失」, 副作用是每轮无条件盖一次用户的选择。判别要点 = 报障只命中**候选从数据派生**的那一组; 若所有筛选器一起重置, 那是另一类问题(整个状态对象被重建 / 持久化被置换, 见 `columns-persist.md`)。
- **处置**: 派生里加**自动入选记账** `statusSeeded`(已自动入选过的候选值记一笔, 下轮 skip) —— 新值补一次、老值永不回填。别用「只在首次加载时派生」或「重渲染时不重算候选」来绕: 数据里新出现的候选值会漏掉, 代价变成「某类条目莫名消失」这条更难查的路。最小修法:

  ```js
  let statusSeeded = new Set();   // 已自动入选过的候选值台账
  function derive() {
    /* ... */
    const seen = new Set(DATA.items.map(i => stOf(i)));
    for (const s of seen) {
      if (!statusList.includes(s)) statusList.push(s);   // 候选列表照旧随数据长
      if (statusSeeded.has(s)) continue;                 // 关键: 已入选过的不再回填
      statusSeeded.add(s);
      S.aStatuses.add(s);
      S.cStatuses.add(s);                                // 卡片墙共用同一份选中集, 一起修
    }
  }
  ```
- **守阵**: `tests/test_kb_nav.py::test_status_filter_not_reseeded_every_poll`(钉住 `statusSeeded.has(s)` 的 continue 闸门排在 `S.aStatuses.add(s)` 之前、且记账 `statusSeeded.add(s)` 全文件只有一处)。静态守阵只守得住形态; 运行时行为本次用 Node 回放验证 —— 页面脚本套最小 DOM 桩后依次 `applyData(...)` → `toggleSet(S.aStatuses, "Done")` → 再 `applyData(...)` 模拟轮询, 直接读 `S.aStatuses`(比肉眼审 diff 快且不会漏分支)。
- **附带教训 · 表列位置也算"看不见"**: 同一轮用户还报「台账表没有状态」—— 状态列其实在第 6 列(专题右侧), 宽屏不横向拖也能看见, 但**紧贴右边界 + 低对比 chip** 让它被当成不存在。窄且用于判断的列(状态 / 标签)放标题左侧, 别跟「链 / 计数」一类辅助列挤在行尾; 改表格必须**表头与行模板同步改** —— 只改一头 = 整行数据错位一列且表格不报错(守阵 `test_ledger_status_column_between_form_and_title` 同时钉两头)。

### 持久化还原与「只补一次」台账的交互 (2026-10-05 kb.nav 筛选器落盘实测)

- **触发**: 用户报「筛选器没保存, 每次刷新重置」, 于是给筛选器加 localStorage 持久化 (`mb-nav-filters`)。
- **判别**: 落盘本身不难, 难在**还原后与派生重播种的时序**。若某组候选从数据派生、且靠 `statusSeeded`「只补一次」防重播种 (见上一节), 而 `statusSeeded` 只是**运行期内存态** —— 刷新后它归零, 首轮 `derive()` 会把数据里存在的候选**全部** `add` 回选中集, 把刚从 localStorage 还原的用户取舍又盖掉。表现极具迷惑性: 持久化代码逐字看着没错, 但「取消的已知状态刷新后又回来了」, 与**完全不落盘时症状一模一样** —— 容易误判成"localStorage 没写进去"。
- **处置**: 还原时**先把已知候选 (定长常量那部分, 如 `KNOWN_ST`) 计入 `statusSeeded`**, 再把持久化的选中集覆盖进 `S`; 并把 `statusSeeded` 本身一并落盘 / 还原, 让「已入选过」的记账**跨会话延续** —— 这样数据里新冒出的候选仍会补一次, 已入选的永不回填。还原值还须对 schema 校验 (非法值丢弃 / 空集回落默认), 详见 [ui-location-persist.md](ui-location-persist.md)。
- **守阵**: `tests/test_kb_nav.py::test_restore_filters_seeds_known_statuses`(还原体必须含 `statusSeeded` + `KNOWN_ST`) 与 `test_filter_state_not_reseeded_on_poll`(derive 不得读写持久化)。运行时用 Node 最小桩回放验证: 还原 → `derive()` 后, 取消的已知状态不被加回 (静态守阵只守得住形状, 时序靠回放)。
