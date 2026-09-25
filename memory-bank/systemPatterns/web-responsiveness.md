# WEB UI 前端渲染与响应性

> 摘要: 按视图回传、窗口化、节拍对齐、命令唤醒 —— 响应性那一整波的设计。
> ⚠ **2026-09-22 方案 C 目录迁移已落地**: 文内单文件路径为迁移前快照 —— 旧根平铺 8 文件+mixins/ → `core(/mixins)/`, 6 个基础设施 → `infra/`, web_runtime/web/web_ui/ui → `webui/{runtime,server,static}`/`tray/`; 映射总表见 [overview.md](overview.md)。
> 触发: 响应性, 跟手性, 按视图回传, 窗口化, 节拍, 命令唤醒, P0, P1

## WEB UI 前端渲染与响应性 (2026-09-19, P0/P1 波次)

**总原则: 感知延迟与真实延迟分开治。** 用户说"不跟手"时第一反应常是"后端慢", 但剖面显示
**主因是"沉默"**(点击后 0.5~6.5s 无任何反馈), 所以收益最大的一项是**乐观 UI**, 后端加速
(命令唤醒 / 命令后立即刷新)只负责把真值对齐时间压到百毫秒级。

- **命令线 / tick 线解耦**: `wake()` + `_wake_event` 只触发"消费命令", **不触发 tick** ——
  否则 `max_tasks_per_tick` 的速率语义失效, 且自投递命令(`build_search_index`)会形成自激循环
  ⇒ `SELF_POSTED_COMMANDS` 白名单里的命令不唤醒。
- **命令后补刷新走完整 `_refresh_torrents()`**: 绝不单独调 `store.apply_sync()`(只更 `by_hash`
  与 `server_state`, 分组/任务/事件/索引全不管 ⇒ 留下半刷新态); 整批命令 drain 完**只补一次**。
- **乐观 UI 只做白名单(pause/resume)**: `pendingOps[hash] = {patch, prev, ts}`, 真值匹配即清,
  3s 兜底回落, **失败立即回滚**。
  - ✅ **3s 兜底会显式回滚到 `op.prev`**(2026-09-19,
    [issue 26-09-19-2141](../issues/26-09-19-2141-bug-webui-pending-timeout-stale-patch.html)):
    `_expirePending()` 在每轮 `refresh()` 里先回滚超时的补丁再 `delete`, 与失败回滚同一写法。
    - ❗**光 `delete` 不叫"回落真值"**: 旧写法只删 pendingOps、注释称"下轮以服务端为准", 而 rid
      未变时服务端**不回传数组**、行对象不被替换 ⇒ 补丁值永久留在行上(命令没执行却一直显示已暂停,
      hang 模式实测 3.66s 后行仍是 `s-paused`)。**要回到真值就必须显式写回 `op.prev`。**
    - ❗`isPending()` 超时**只返回 false、不 delete**: 模板每帧都调它, 在渲染函数里改响应式数据有
      递归更新风险; 回滚统一交给 `_expirePending()`(代价: 过期条目最多多活一个轮询周期)。
  - ✅ **「真值匹配即清」已落地**(2026-09-19, [issue 26-09-19-2024](../issues/26-09-19-2024-bug-webui-truth-convergence.html)):
    `refresh()` 拿到新数据时先 `_snapshotTruth()` 记下 pending hash 的**服务端原始值**,
    `reapplyPending()` 比它 ⇒ 对齐就 `delete`。回执后 `_pullTruthAfterCmd()` 立刻 refresh
    (不等轮询), 短退避 200→400ms 重试, 总窗口 1.5s, 超时仍由 3s 兜底收尾。
    - ❗**必须比服务端快照, 不能比行上的当前值**: 行在上一轮已被贴过补丁, 拿它跟补丁比 = 跟自己比
      ⇒ 首轮必"匹配"、pending 立刻消失(实测 22ms); 且 `updated === false`(rid 未变)时行对象
      根本没被换掉, 这个假匹配更容易发生。快照**拷值不拷引用**(赋值后与 payload 是同一批对象)。
    - ❗只认本轮 payload **真的带了**的 hash: 追剧视图 `view=show` 回 shows+groups+singles,
      成员真值走 groups 取到; 若某 hash 不在本轮 payload 里 ⇒ 不算对齐, 继续贴、交给 3s 兜底。
  - ❗**补丁必须先于 POST 贴上**(4 条入口: `act` / `actTorrent` / `actEpisode` / bulk 一律如此)。
    放在 `await POST` 之后 = 把"点击即变"押在网络往返上 —— 受控测量(注入 2000ms POST 延迟):
    修前补丁 2012ms 才贴, 修后 0ms(issue 26-09-19-1939, 用户真机报"点了 2-4s 才变")。
    POST 失败走 `resolveOptimistic(hashes, false)` 回滚, 不留假状态。
  - ❗**3s 兜底从「回执到达」起算**(成功时刷 `op.ts`), 不是从点击起算: 补丁提前后若按点击算,
    慢 POST 会在命令刚完成时就烧光窗口 ⇒ 弹回陈旧真值。**无回执(hang)不刷新 ts**, 3s 后照旧回落。
  - 埋点: `cmdStats` 含点击侧两段(`patchMs` / `postMs`)与回执段(`waitMs` / `execMs` / `totalMs`),
    阈值 补丁>50 / POST>400 / 排队>100 / 端到端>400 打 `[perf]` —— **「点击 → 投递」曾经是盲区**。
- **按视图回传**: `/api/state?view=group|torrent|show` 只回该视图数组; 前端赋值必须
  "键不存在则保留原引用"(否则另外两个视图每轮被抹空)。
- **只读端点短缓存 key 含 `_web_write_seq`**: 写后自动失效; **断连检查必须在查缓存之前**
  (否则 qB 断开仍返回缓存 200, 把断连藏起来)。
- **行窗口化(P1-2)是渲染侧最大的一刀**: 核心约束是**只减 DOM 行数, 不改布局模型** ——
  行仍是 flex 列里"渲染完整单元格序列"的元素, 只靠上下两个 `.row-pad` 占位撑高度,
  这样 `:nth-child` 列对齐与 `[data-table]` 列宽协议全部保持有效。高度必须**逐行实测 + 前缀和 +
  二分**(真实数据行高不齐: H&R 行多一行 ⇒ 43.7px 与 65.4px 混排, 等高假设会漂上百像素);
  展开成员行会插队打断边界 ⇒ **展开的组当前确实在可见集合里**时 group 窗口**退避回全量**
  (判据是 `expandedKey && filteredGroups.some(k)`, 不是只判 `expandedKey` 非空 —— 展开态会跨视图
  带回(`app.js` 的 `stashExpandState`/`restoreExpandState`), 组可能已被删/被筛掉, 只判非空会让
  窗口为一个不存在的面板**永久**退避, 症状是"界面一切正常, 只是滚动变卡")。
  ⚠ 附带发现: **别在 computed 里对响应式大对象做展开复制** —— `filteredTorrents` 里的
  `{ ...r, hit }` 单项 74 字段 × 3000 条 = 22 万次 Proxy `get` 陷阱, **单这一句 68ms**,
  比整个窗口渲染还贵; 改成原引用出栈 + 模板现问 `isHit(m)` 后 115ms → 5ms。

**验证手段**: 单测覆盖不到前端渲染, 靠两道 —— ①静态守阵
`test_frontend_static_bundle_health`(JS 语法、`node --check`、CSS 闭合、`<transition>` 吞弹窗、
模板引用的资源存在); ②**真浏览器冒烟** `scripts/ui_harness.py`(真 `create_app` + `FakeClient`
+ 合成种子 + 命令泵)配 `scripts/ui_smoke.cjs`(Playwright, 双 UI 断言 + 内置 A/B 基准)。
改前端渲染/交互逻辑后应当跑第 ② 道。
