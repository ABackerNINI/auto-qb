# 前后端数据契约

> 摘要: 前端不只是后端的镜像 —— 判"字段不一致"前必须沿派生链追到消费点; 跨视图裁剪与真值时序是两条反复出事的线。
> 触发: 字段不一致, 前后端契约, 视图回传, rid, 真值, 乐观 UI, 状态色, 占位符, HR 标签, 空值转有值, 上游修复后的展示回归

### 不能只看后端载荷, 前端还有一层派生

- **触发**: 判"前后端字段不一致"(想下"必失效 / 必崩"这类强断言)。
- **判别**: **必须沿前端 computed 派生链追到实际消费点**(如 `save_path` 由 `decoratedGroups` 派生),
  只看后端对象与某一行的 `g.xxx` 会**误报**。反向也成立: 后端补字段前先确认前端是不是**已经算了**。
- **处置**: 详细步骤与实测证据见 [attachments/contract-api-details.md](attachments/contract-api-details.md)

### 追剧视图 `members` 是**双形态**(后端 hash 数组 / 前端成员对象)

- **触发**: 把成员写进 URL / 命令载荷 / `memberByHash` 查找(前端由 `decoratedShows` 把 hash 数组装饰成成员对象)。
- **判别**: 不归一就字符串化成 `[object Object]` ⇒ 后端 404「种子不存在」(不报错, 只有一条 toast)。
  ⇒ **"同一动作单种子正常、聚合行失败"基本就是这个形状**。
- **处置**: 详细步骤与实测证据见 [attachments/contract-api-details.md](attachments/contract-api-details.md)

### P1-1 按视图回传: 前端赋值必须"**键不存在则保留原引用**"

- **触发**: 改 `/api/state` 的视图分片 / 前端赋值。
- **判别**: 写成无条件赋值 ⇒ 每次轮询把其它两个视图**抹成空**。
- **处置**: 详细步骤与实测证据见 [attachments/contract-api-details.md](attachments/contract-api-details.md)

### 每条视图的数组集必须覆盖"该视图渲染所需的**全部**数据源"

- **触发**: 改 `VIEW_ARRAYS`。
- **判别**: 追剧页的 `shows[].members` 只是 hash, 前端要靠 `memberByHash`(groups + singles 拼)还原成员 ⇒
  只回 shows 会让整页**永久空白且不自愈**(lastRid 已记住, 之后每轮都是"版本未变不回传")。
- **处置**: 详细步骤与实测证据见 [attachments/contract-api-details.md](attachments/contract-api-details.md)

### 跨视图的派生聚合(状态分布 / chip / 状态条)必须按 `viewMode` **自取数**

- **触发**: 写跨视图呈现的派生值(2026-09-21, issue 26-09-21-0247)。
- **判别**: 后端按视图裁剪(`VIEW_ARRAYS` 的设计本意), 旧版 `distSegments` 只数 `this.groups[].members[].kind` ⇒
  两种场景 chips **全空**: ①localStorage 持久化 `autoqb.ui.view=torrents` 后首进种子页(`groups=[]` 首轮即空);
  ②在种子页停得久(轮询只刷 torrents, groups 永远空或冻结旧值)。
  表现「做种10 错误1」整行消失 —— 用户只会觉得"统计没了", 排查方向跑偏。
- **处置**: 详细步骤与实测证据见 [attachments/contract-api-details.md](attachments/contract-api-details.md)

### 上游从「空/未接入」变「有值」会点亮下游**从未跑过**的展示分支 (2026-09-29)

- **触发**: 上游修好让某字段**从空变有值**(本仓 `hr_safety` 曾恒空: 芯片/弹窗从未上线)。
- **判别**: 那些分支**从没渲染过**, 口径问题只在点亮那刻暴露 —— 本轮实报: 未核/在线行只剩孤立芯片(`hr_triggered` 门连要求时长一起藏), 弹窗把「未核实」与真放行同类收起成「无时长要求」。
- **处置**: 详细步骤与实测证据见 [attachments/contract-api-details.md](attachments/contract-api-details.md)

### ⚠️ 跨视图的常驻消费者**不能**依赖按视图裁剪的阵列 (同类**已第四次**)

- **触发**: 增删 `VIEW_ARRAYS` 键 / 新增常显 UI 元素(2026-09-21)。
- **判别**: 四次同一形状 —— ①**状态栏速度**对 `groups` 求和(issue 26-09-20-1646)②**追剧页成员索引**(BUG-8)
  ③**筛选器选项**(标签/分类/站点/路径 + H&R)一律遍历 `groups` ⇒ 种子页四个弹层恒空、只剩"暂无数据"
  (H&R 是固定两档, 表现为 0/0, **更隐蔽**)④**添加种子三候选「最近使用」排序**(2026-10-09)直读
  `state.torrents` ⇒ 默认辅种页(`VIEW_ARRAYS["group"]` 只回 groups + singles)拿到**空表**, 排序
  **静默退化**成纯字母序(不报错、不白屏, 只是"排序没生效")。
- **处置**: 详细步骤与实测证据见 [attachments/contract-api-details.md](attachments/contract-api-details.md)

### "真值到达" ≠ "值覆盖结束"

- **触发**: 用户报「整组暂停后颜色 灰→绿→灰」(2026-09-21)。
- **判别**: 真值走 `torrents/info` **直查**, 比我们自己的 `/sync/maindata` **快照**新 ≤ `sync_interval`(1.5s);
  真值事件一到就把 `pendingOps[h]` 删掉 = 把"值覆盖"的寿命交给了一个**比快照快**的数据源 ⇒
  这 1.5s 内**任何一次视图发布**(任何种子任何字段变化都会让 rid 前进、整表重发)都会带着**命令前**的 `kind`
  覆盖行对象 ⇒ 行被打回命令前的颜色(暂停组闪回做种绿), 快照追上再变灰。
- **处置**: 详细步骤与实测证据见 [attachments/contract-api-details.md](attachments/contract-api-details.md)

### rid 门控下"下轮以服务端为准"是**不成立**的

- **触发**: 写乐观 UI 的兜底。
- **判别**: `updated === false` 时前端**不回传数组也不整表替换**, 行对象保持原引用 ⇒
  任何"我不再写它了"的写法都会把值**永久留在行上**。
- **处置**: 详细步骤与实测证据见 [attachments/contract-api-details.md](attachments/contract-api-details.md)

### "服务端的值"不等于"**已落地**的值"

- **触发**: 命令后立刻补刷新, 读到旧值, 想"是不是预测猜错了"。
- **判别**: `torrents/resume` 返回 200 时 **qB 还没翻状态**, 紧跟着的补刷新读到的是**命令前**的旧值 ⇒
  "权威值"其实是**滞后一拍的旧值**。判据: 与本地预测不一致的服务端值**绝大多数是还没落地**。
- **处置**: 详细步骤与实测证据见 [attachments/contract-api-details.md](attachments/contract-api-details.md)

### 同一概念两张表必须对齐(前端 `STATE_RANK` 与后端 `_SHOW_STATE_RANK`)

- **触发**: 改状态优先级。
- **判别**: 由 `tests/test_web_*.py` 静态守阵机械比对, 改一边不改另一边即红。
  ⚠ 且"一致"只管**两页同色**, 管不了"**同成哪个色**" —— 顺序语义本身也被钉住了:
  **`seeding` 必须严格排在 `paused` 之前**(组/集内"部分暂停部分做种中"取**做种色**, 2026-09-21 用户口径)。
  反例就在 2026-09-19 修 BUG-7 时: 把前端表整体对齐后端, 顺手把 `{paused,seeding}` 也翻成 paused ⇒
  辅种页做种中的组**整行变灰**, 用户报"以前是对的"(回归提交 `04cbc8e`)。
- **处置**: 详细步骤与实测证据见 [attachments/contract-api-details.md](attachments/contract-api-details.md)

### 取数单点放后端, 前端只展示

- **触发**: 前端想按 state 猜原因 / 想自己算阈值。
- **判别**: tracker 错误原因由 `_error_reason()` **一个出口**算好透出; HR 筛选只消费后端算好的组级计数 / 成员布尔。
- **处置**: 详细步骤与实测证据见 [attachments/contract-api-details.md](attachments/contract-api-details.md)

### 只在用户显式动作时才需要的字段不要塞进轮询载荷

- **触发**: 想让前端"随时能拿到"某字段(如 `magnet_uri`)。
- **判别**: 每轮响应体加字段在大库上是 **MB 级**。
- **处置**: 详细步骤与实测证据见 [attachments/contract-api-details.md](attachments/contract-api-details.md)

### HR 标签着色靠"**文本逐字相等**"

- **触发**: 改 HR 标签染色。
- **判别**: 后端用 `replace_vars` 展开模板透出字符串, 前端只做 `tag === member.hr_tag` 比较 ⇒
  前端改用图案猜测或**再拼一次模板**, 自定义标签格式会**立即失效**。
- **处置**: 详细步骤与实测证据见 [attachments/contract-api-details.md](attachments/contract-api-details.md)

### "某列 / 某值恒为占位符"且同一取数点被多处复用 ⇒ **先核字段名**

- **触发**: 某列恒显示 `—`, 且它兼任染色分母。
- **判别**: 实测过一次"恒 undefined ⇒ 显示恒为 — 且兼任染色分母 ⇒ **色阶从未生效**";
  全局限速的正确字段是 `server_state` 的 `dl_rate_limit` / `up_rate_limit`
  (`dl_limit` / `up_limit` 是**单种子级**字段)。
  **全仓 grep 该键名命中 0 处 = 后端根本没这个键。**
- **处置**: 详细步骤与实测证据见 [attachments/contract-api-details.md](attachments/contract-api-details.md)

### 候选集的"展示序"从另一数据源派生时, **键的口径必须与候选集同径** (2026-10-09)

- **触发**: 给"原本按字母序"的候选(下拉选项)加**由数据派生**的排序/分组 —— 本仓: 添加种子的保存路径/分类/标签按「最近使用」排序。
- **判别**: 候选集与排序基准若来自**两个来源**、口径不一致, 匹配**恒不命中**。本仓实例:
  `/api/paths` 回的是 `path_normalize` **已归一**的路径(反斜杠转正斜杠 + 压重复斜杠), 而
  `SEED_ITEM.save_path` 是 qB **原文**(如 `R:\Seeds\A`) ⇒ 拿原文当 Map 键去命中归一后的候选, 永远 miss。
  症状是**静默退化**: 不报错、不白屏、不 404, 只是排序悄悄退回纯字母序 —— 用户说不清、走查也看不出。
- **处置**: 详细步骤与实测证据见 [attachments/contract-api-details.md](attachments/contract-api-details.md)
