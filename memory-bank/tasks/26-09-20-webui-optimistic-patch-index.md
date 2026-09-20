# 26-09-20-webui-optimistic-patch-index — 乐观补丁改为 hash 索引查找（消除 O(目标数 × 数据集规模)）

**Status:** In Progress（已认领 issue 26-09-20-1033，计划已出，**未动代码**）
**Started:** 2026-09-20
**Owner:** 主线（单会话连续实施）
**Plan doc:** [docs/plans/26-09-20-1039-webui-optimistic-patch-index-plan.html](../../docs/plans/26-09-20-1039-webui-optimistic-patch-index-plan.html)
**Issue:** [26-09-20-1033-perf-webui-optimistic-patch-quadratic](../issues/26-09-20-1033-perf-webui-optimistic-patch-quadratic.html)
**Summary:** 冒烟里恒现的 `[perf] 补丁 2033ms` 经受控探针定性为 `applyOptimistic` 的 O(目标数 × 数据集规模)（逐 hash 调 `_forEachRow` 线性扫三张全表），不是抖动；同样的代价在 `reapplyPending` 里每轮 refresh 都要付一次（单轮 1588ms）。方案 A：入口一次建成 `hash -> rows[]` 索引，四个调用点共用；实测预估 1810ms → 9.5ms（190×）。已出计划并认领 issue，**代码未改**（等用户拍板开工）。

## 原始请求

> （承接上一轮「WEB UI 解耦」的冒烟复核）冒烟打出 3 条 `[perf]`，其中「补丁 2033/2407ms」此前被记为「大库主线程抖动，未做 A/B，未入池」。用户要求继续 —— 先定性，再决定是否认领并出修改计划。

> 用户追加：「要我认领它、按方案 A 出一份修改计划？」

## 思考过程与决策

1. **先别急着信"抖动"这个结论**：`[perf]` 只报一个数字（补丁 2033ms），看不出是算法复杂度还是偶发卡顿。要定性就得把变量分开 —— 于是写探针在页面内**直接调同步函数**（不发请求、不触发重排），分别固定「目标数」和「数据集规模」两个轴。
2. **两个轴都要量**：只量「目标数」会得到一条直线，既符合 O(目标数) 也符合 O(目标数 × 数据集)。必须再固定目标数、变数据集规模，才能区分。实测单目标成本 0.079 ms（300 条库）→ 0.715 ms（3000 条库），库大 10×、成本约 9× ⇒ 二次关系实锤。
3. **顺藤摸瓜发现更严重的一处**：`_forEachRow` 有四个调用点，其中 `reapplyPending` 是**每轮 refresh** 都跑（单轮 1588ms）—— 比点击那一次的 1810ms 更值得修，因为它重复付。原 issue 只写了点击路径，计划里补上了。
4. **成本拆分决定方案**：建索引 2.1ms、用索引打补丁 7.4ms ⇒ 不需要缓存、不需要批量合并写入，最小改动就够。因此否决了「跨轮缓存索引」和「合并 pendingOps 写入」两个听起来更"高级"的做法（缓存失效漏一处就是贴到旧行上，比慢更危险）。
5. **红线是语义不是性能**：一个 hash 可能命中多行（平铺 / singles / 组成员，甚至同一对象被两个数组引用），改造必须逐行执行且顺序不变。这点写进计划，并安排 W4 红绿双验（故意改成只取第一行 ⇒ 冒烟必须变红）。
6. **按范围守恒不就地改**：定性 + 入池 + 出计划，代码一行没动；issue 由 Open 转 In Progress 只改状态，不改"实际修法"（那栏留给修完填）。

## 实现计划

见 [计划文档](../../docs/plans/26-09-20-1039-webui-optimistic-patch-index-plan.html)。要点：

- **W1** 新增 `_buildRowIndex()`（`Map<hash, row[]>`，扫 torrents → singles → groups[].members 一次），改 `applyOptimistic`
- **W2** 改 `reapplyPending`（收益最大）/ `_expirePending` / `resolveOptimistic` 失败分支
- **W3** `patchMs` 的 `[perf]` 阈值按目标数分档，与 `settleMs` 的 budget 同款（消除大库常驻噪音）
- **W4** 红绿双验：索引改成「只取第一行」⇒ 冒烟「整组 / 整集乐观」项必须变红
- **W5** 知识库回写 + issue 转 Fixed

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 定性：受控探针两轴实测 | ✅ Done | 数据集 300/3000 × 目标 100~3000，二次关系确认 |
| 成本拆分（建索引 / 打补丁 / reapplyPending） | ✅ Done | 1810 / 2.1 / 7.4 / 1588 ms |
| 入池 issue 26-09-20-1033 | ✅ Done | 已推送 `7de7a6f` |
| 出修改计划（delivery-artifact，单文件 HTML） | ✅ Done | `docs/plans/26-09-20-1039-...html` |
| issue 转 In Progress + 索引重建 | ✅ Done | 徽标与 meta 两处同改 |
| W1~W5 代码实施 | ⬜ 未做 | **等用户拍板开工**（计划外问题已认领，但未授权改码） |

## 进度日志

- **2026-09-20 10:20** — 冒烟复核撞见恒现的 `[perf] 补丁 2033/2407ms`，当时记为「大库抖动，未做 A/B，未入池」，写进解耦档案验收段。
- **10:33** — 写探针 `patch-probe.cjs` 定性：不是抖动，是 `applyOptimistic` 逐 hash 全表扫描，复杂度 O(目标数 × 数据集规模)。入池 issue（Open），解耦档案改为「已定性并指向 issue」；两笔推送 `7de7a6f` / `1723687`。
- **10:37** — 探针 v2 拆成本：建索引 2.1ms / 用索引打补丁 7.4ms / `reapplyPending` 单轮 1588ms ⇒ 预估 1810→9.5ms（190×）。发现 `reapplyPending` 每轮 refresh 都付一遍，写入计划。
- **10:39** — 出计划文档（Native HTML，冷峻技术方向），issue 转 In Progress，立本档案。**代码未动。**

## 坑与约束（供实施时回看）

- 探针三要素：① 必须先切到种子视图（读 `filteredTorrents`，`torrents` 在切过去前不回传，直接读会 waitForFunction 超时）；② Vue 实例走 `document.querySelector('#app')._vnode.component.proxy`（`_instance` 恒空）；③ 每轮测完 `resolveOptimistic(hashes,false)` 回滚，否则污染下一轮。
- `_forEachRow` 的四个调用点里，**只有 `applyOptimistic` 在原 issue 里写了**；`reapplyPending` 是每轮的，别漏。
- 语义红线：一个 hash 可能多行、迭代顺序不能变、取不到行即不做（追剧视图 payload 只回 shows）。
