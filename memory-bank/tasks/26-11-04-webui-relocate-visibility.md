# 26-11-04-webui-relocate-visibility — 待收尾迁移种子的 WebUI 可见性与路径链(P0-P3)+真机验收

**Status:** Done
**Added:** 2026-11-04
**Updated:** 2026-11-04
**Summary:** P0–P3 已实现并评审修复，七项真机验收全过(RM04-15..18 + RM04-14 回归)，全量数字见基线 26-11-04-1519
**Topics:** webui-relocate-visibility
**Refs:** memory-bank/plans/26-11-04-1042-plan-webui-relocate-visibility.html, memory-bank/testing/baselines/26-11-04-1519-webui-relocate-visibility-r5.md

## 原始请求

1. 为「待收尾迁移」种子补齐 WebUI 可见性(成员/组标注、行内徽标、详情段、迁移筛选)与路径链展示(A→B→C 浮窗), 先出可评审计划。
2. 按计划落地 P0–P3, 并完成 code review 修复。
3. 对功能分支 `feat/webui-relocate-visibility`(HEAD `3dd603f9`)做真机测试: 四皮肤行高/浮窗定位/真实路径链/qB 标签/UNC 不可达/组行入口/迁移主流程回归; 只用 real-fake 与副实例; 能固化的断言补进 `tests-real`; 按 DoD 回写并本地提交(不 push、不配 upstream、不跑同步)。

## 思考过程与决策

- 计划单点: `memory-bank/plans/26-11-04-1042-plan-webui-relocate-visibility.html`(P0–P3 分期, 待拍板 D 编号见其 §05/§06)。
- 真机取证路径: 新增 `tests-real/rm04_relocate/test_rm04_relocate_visibility.py` 的 RM04-15..18, 复用 RM04 造种/清场助手; 浏览器侧用 Playwright(`tests-real/lib/relocate_visibility_ui.mjs`)取四皮肤几何与浮窗行为; qB 标签写请求用 `TcpProxy` 计数证明。
- 符号链接: 本机无 `SeCreateSymbolicLinkPrivilege`, symlink 造段失败(WinError 1314)时降级 junction 并如实记录原因, 不伪报 symlink 通过。
- UNC 起点: 链端点设计为「远端不做 syscall」, 实测 15.8ms 返回单节点 `unknown/unknown` + 原因; `path_normalize` 会把 `\\server\share` 折叠为 `/server/share`, 断言只钉主机+共享名保留。
- armed 后组行为: 别名作用域重归组(`regroup_scope`)把 mover 与非 mover 并回同一组, 不存在独立「源组」行; RM04-15 以并组断言固化。

## 实现计划

1. P0: job 快照发布、成员/组标注、origin 落账、前端指纹。
2. P1: 路径列徽标、详情「迁移」段、独立迁移筛选、浮窗骨架。
3. P2: `GET /api/relocate/chain`、逐跳类型/归属章、TTL 缓存、四皮肤浮窗链展示。
4. P3: opt-in `relocate.pending_tag` 标签镜像(armed 加/终态摘/重启补写)。
5. code review 修复(head `3dd603f9`)。
6. 真机验收 RM04-15..18 + RM04-14 回归, 断言固化进 `tests-real`。
7. 全量测试与基线、DoD 回写、本地提交。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | P0 快照/标注/聚合/origin/指纹 | Done(2026-11-04) |
| 2 | P1 徽标/详情/筛选/浮窗 | Done(2026-11-04) |
| 3 | P2 链端点/归属/缓存/浮窗展示 | Done(2026-11-04) |
| 4 | P3 pending_tag 镜像 | Done(2026-11-04) |
| 5 | code review 修复 | Done(2026-11-04) |
| 6 | 真机验收 RM04-15..18 + RM04-14 回归 | Done(2026-11-04) |
| 7 | 全量测试/基线/回写/提交 | Done(2026-11-04) |

## 进度日志

### R0 · 立档 (2026-11-04)

P0–P3 实现与评审修复已完成(详见计划 §10 与 activeContext R1–R4)。本轮补充真机验收:

- RM04-15 通过(51.1s): prism 种子/组行高 44/44/44/44, atlas/flux/console 43; 徽标数 A=1/B=0 且都在路径格内; 浮窗底色 alpha=1(flux `rgb(28,42,63)` 不透底); 底部锚点上翻(anchorTop=960 → popTop=596); 左右夹取 8/468 与 1212/1672(vw=1680); 表格滚动(694→574)与页面滚动(0→160)均关闭浮窗; 长链浮窗内部可滚(clientH=558/scrollH=877), 外层滚动即关; Esc 逐层退栈且焦点回 `rel-badge`; 组行 drawer 入口基准 == `drawer.hash` == mover; armed 后并组 count=1/memberCount=2/state=pending_finalize。
- RM04-16 通过(30.2s): A→B→C 三跳 `junction→junction(降级)→dir` 全 ok、target 正确、归属章 `auto=false`(36.0ms); UNC 起点 `env=remote`、单节点 unknown + 「远程路径需在 qB 主机查看」, 15.1ms(本地 15.7ms), 且该种子不进 `/api/groups`(unc_in_groups=false); 10 级 junction 长链 9 跳 ok + 末跳 limit(17.2ms)。symlink 失败原因 WinError 1314 已入证据。
- RM04-17 通过(70.0s): armed 期间 1 次 addTags, 两成员均带 `zRelocatePending`; 用户手删后 addTags 计数不增且相位仍 armed; 重启后 reconcile 再发一次(1→2); 撤销(confirm 两步)到 cancelled 后 1 次 removeTags 且标签摘净。
- RM04-18 通过(38.2s): pending_tag 关闭时 armed 相位内 add/removeTags 写请求 0 次。
- RM04-14 回归通过(34.3s): 迁移 confirm 回路(浏览器点击 → 7 要素 → 确认)仍正常。

- 2026-11-04 15:24 真机验收完成: 新增 tests-real RM04-15..18 并全过(四皮肤行高/浮窗翻转夹取与滚动关闭/Esc 退栈回焦/组行入口基准/A->B->C 与 UNC 15.1ms 未确认/pending_tag 加-手删不重加-重启补写-终态摘/关闭零写), RM04-14 confirm 回路回归通过; test.full 5185 passed + 10 skipped, 新基线 26-11-04-1519
