# Active Context — 当前焦点

> Memory Bank 核心文件之一: 回答"现在正在做什么 / 上次做到哪 / 下一步从哪继续"。**每次会话开始先读本文件。**
> 稳定事实在 projectbrief / productContext / systemPatterns / techContext 与各主题文档; 计划与完成状态在 [progress.md](progress.md); 本文件只放**易变的会话级状态**。
> 维护纪律 (完整规程见 [memory-bank skill](../.agents/skills/memory-bank/SKILL.md)): ①每次会话收尾更新本文件, 已完成条目沉淀到 [progress.md](progress.md) 或主题文档后**删除** — 本文件只放易变状态; ②命中立档阈值的任务在 [tasks/](tasks/_index.md) 立档并同步索引; ③**禁止**在本文件追加长流水账纪要 (会淹没真正的当前焦点)。

**最后更新**: 2026-09-19 (**上轮复核的第 1、2 批缺陷修复 + 续查的热路径优化均已实施未提交** ——
  第 1 批: 行窗口间距改运行时实测(棱镜占位总高 +2973 → **0**)、冒烟改同帧「窗口化 vs 全量」对照、
  两条写序号接线断言、回执/失效顺序调换、`sync_interval` 钳制、文档漂移、harness 限回环、`cmdStats` 接消费者;
  第 2 批: 组/集行乐观(BUG-3) + 修复过程中新发现的 **BUG-8 追剧页刷新后永久空白(高)** /
  **BUG-9 复制磁力恒失败(中)** / **BUG-7 两页状态色不一致(低)**;
  续查: 报表 §08 第 6 项(响应体裁剪)**经实测否决**, 真正的开销是 FastAPI 对裸 dict 返回值先跑一遍
  `jsonable_encoder`(占端点耗时 85%), 改 `return JSONResponse(...)` 后服务端 `view=torrent`
  189 → **23.5 ms**、**前端整轮 refresh ~240 → ~85 ms**。
  **基线 1049 → 1053 passed / cov 92%; 冒烟 34 → 46 项(ok) / 44 项(error) 0 失败**。
  只剩报表 §08 第 7 项(节拍对齐, 需先拍板方向) —— 见下「正在进行」第 ① 条与
  [progress.md](progress.md) 三波次总条目 — 详见 [testing.md](testing.md))

## 正在进行

- **① 上轮计划复核的收尾(只剩第 7 项) (2026-09-19)**: 复核报表
  [docs/plans/26-09-19-1745-webui-responsiveness-review.html](../docs/plans/26-09-19-1745-webui-responsiveness-review.html)
  (评级 计划 A− / 实施 A− / BUG B / 安全 A− / 性能 B+ / 测试 B−), 报表已追加 **§10 复核修订与修复回执** +
  **§11 热路径白跑 85%**(FastAPI `jsonable_encoder`)。**第 1、2 批与 §11 均已实施未提交**
  (明细见 [progress.md](progress.md) 三波次总条目末段 + 档案进度日志)。
  **剩余两项已入池为 issue(见 [issues/_index.md](issues/_index.md)), 未开工**:
  1. **[webui-poll-cadence-mismatch](issues/26-09-19-1900-webui-poll-cadence-mismatch.html)** ——
     `sync_interval`(1.5s)与前端分档轮询(1.5/2/3s)在 >3000 种子时错配, 约一半 `rebuild_views` 无人消费。
     **需先拍板方向**: 让轮询跟上快档(降 `basePollMs` 下界) vs 给快照刷新加 Web 活跃门控(无人看就不刷)。
     ⚠ 这条是**频率类**改动, 拍板前先按 pitfalls 「主循环分层节拍」与「把 main_tick 缩短来换响应速度」两条判据过一遍。
     ⚠ 另注: 第 1 批给 `sync_interval` 加的钳制(`min(sync_interval, main_tick)`)只兜住了"快照新鲜度
     掉到心跳之下", **没有**解决"重建了没人消费"这一半 —— 两件事别混。
  2. **[webui-hot-endpoints-jsonable-encoder](issues/26-09-19-1900-webui-hot-endpoints-jsonable-encoder.html)** ——
     同类端点的同样改法(低优先): `/api/search`(实测 1.46MB / 服务端 82.6ms, **第二大载荷**)与
     `/api/torrents/{hash}` 详情族(`/files`、`/trackers`、`/peers`)仍返回裸 dict, 改法与 `/api/state`
     一致(`return JSONResponse(content=…)`)。收益取决于响应体大小; 这些是用户触发型、不在 1.5~3s
     轮询路径上, 故未纳入本批。改完必须逐个真请求一次(防 fail-fast)。
- **② WEB UI 操作跟手性优化 (2026-09-19)**: 三波次全部入库(`10e06a8` 分层节拍 + 命令唤醒 + 乐观 UI + 批量合单
  / `5d1e52c` 请求超时 + 视图分片回传 + 只读缓存 / `366092d` 行窗口化)。计划
  [docs/plans/26-09-19-1241-webui-responsiveness-plan.html](../docs/plans/26-09-19-1241-webui-responsiveness-plan.html); 档案 [tasks/26-09-19-webui-responsiveness.md](tasks/26-09-19-webui-responsiveness.md)。
  **剩**: 真机走查(真实 qB 数据下的观感)。
- **③ 前端轮询按种子量分档 (2026-09-19, 待提交)**: 计划里唯一排在 P1 之后的项 —— 降轮询间隔会**放大**全量回传 + 整树重渲染, 顺序错了会加剧不跟手。档位实测而定: 1000 种子单轮 143ms / 3000 种子 353ms / 5000 种子 ~550ms ⇒ **≤1000 → 1.5s / 1000~3000 → 2s / >3000 → 3s**(主线程占用率 10%/15%/17%); 下界 1.5s = 服务端 `sync_interval`(再快只是多拿空响应)。实现: `pollSec` 字段退役(不留死字段), 新增 `basePollMs()`; 冒烟新增分档断言 ⇒ 30 项 0 失败。
- **④ WEB UI 视图重建范围收口 · 种子速度刷新滞后修复 (2026-09-18, 未提交)**: 真因是两条重建路径**范围不一致**(主循环 `_tick` 只重建 `_group_view` 却清掉共享脏标记 ⇒ singles/shows/flat 被饿死, 版本号照常自增 ⇒ 前端换上陈旧数组)。已改为唯一入口 `rebuild_views()` + 置脏移出门控 + 前端取消 idle 退避并把 `server_state` 并入 `/api/state`。基线 1018 → **1021 passed**。剩用户真机走查 → [tasks/26-09-18-webui-view-rebuild-scope.md](tasks/26-09-18-webui-view-rebuild-scope.md)
- **⑤ 浏览器冒烟能力 (2026-09-19, dev-only, 长期有效)**: `scripts/ui_harness.py`(真 `create_app` + `FakeClient` + 合成种子 + 命令泵 `ok|error|hang`)+ `scripts/ui_smoke.cjs`(Playwright, 双 UI **46 项断言** + 内置 A/B 基准)。**Windows 上可跑**, 攻破了"单测测不到前端交互"这个长期卡点。⚠ `--host` 现在只接受回环(免鉴权服务不得暴露到局域网)。⚠ **两种模式都要跑**: `ok` 看正向、`--expect-cmd error` 看回滚 —— 后者此前必红所以没人跑, 已按模式分流断言。

## 待用户真机走查 (代码/测试均已完, 只差真实 qB 数据下的观感确认)

- **跟手性优化三波次** —— 右键菜单响应 / 切视图首帧 / 3000+ 种子滚动流畅度
- **本轮新修的 4 处(建议顺路走查)** —— ① 刷新页面时若上次停在**追剧页**, 现在应正常显示(修复前是永久空白);
  ② 右键**复制磁力**在辅种页/追剧页应真能复制(修复前 100% 提示"没有 magnet 链接");
  ③ 整组/整集暂停后**行本身**应立刻变灰(半透明 `is-pending`)且颜色即时切换;
  ④ 混合状态组的颜色可能与修复前不同(状态优先级已统一到后端口径, 只影响 2 种混合态)
- **热路径提速(§11, 建议重点体感)** —— 3000+ 种子库下切视图/滚动时数据到达更快(服务端 189 → 23.5 ms)。
  重点看: 种子页在**数据变化那几轮**是否还有"迟一拍"的观感; 若大库仍觉卡, 下一步就是报表 §08 第 7 项
- **追剧页剧/集右键「打开目标文件夹」** (`c888fba`) —— 剧 → 集 → 种子三级各点一次; 顺带确认整剧开始/暂停/删除已恢复
- **视图重建范围收口** (`1021 passed`, 未提交) —— 种子速度是否已随轮询刷新
- **TASK015 错误种子原因** (`9723a76`) —— 错误态状态列是否显示 tracker 原文
- **TASK013 / TASK012 / TASK011**(第九/十/十一轮修复) —— 逐轮走查反馈
- **TASK014 UI 组件库 20 式** (`fae019a`) —— 挑选与按需迭代

## 定案口径 (别改回去; 完整判据见 [pitfalls.md](pitfalls.md))

- **列偏好"升版本"**: 列集变更(加列/减列/重排)与存储结构扩展**一律不升版本**, 只有"旧缓存结构已无法被 `loadColState()` 正确解释"才升(如 v2 按列索引存), 且升版本必须同时挂 `LEGACY_COLS_KEYS` 迁移。当前键冻结在 `autoqb_cols_v4`, 无 v5 计划。历史计划 `docs/plans/26-09-15-1042-webui-optimization-plan-v3.html` 里"重排列集则升 v4→v5"是当时口径, 已被第十轮计划取代 —— 存档未改动, **别照抄**。
- **第十轮两处已知限制**(非待办): ① 列偏好受 localStorage **origin 隔离** 影响(`localhost` 与 `127.0.0.1`/换端口 = 不同站点各存一份) —— 用户明确要求只存浏览器, 不做服务端化; ② 目录浏览器只能浏览**已有保存路径及其子目录**(安全边界), 全新位置需在输入框手填。
- **第十一轮定案**: 行/表头一律 `fit-content; min-width: 100%`(**底色跟内容**), **行内单元格必须 `min-width: 0`**(否则 nowrap 文本把行顶宽 ⇒ 列没溢出却常驻横滚条); 曾用"行定宽 100%"治假滚动条, 会让**溢出段没有底色**(用户实测"滚动后右边无背景条"), 已回退。
- **`想法.md`**: 工作区**干净**(最后一次入库 `3bface9`)。它属于红线文件(与 `config.yml` / `auto-qb-data/` 同级), 提交前照例用 `git status --short` 确认一遍是否又有改动, 不进暂存区。

## 下一步候选 (来源: `想法.md` 待办 + progress.md 规划中)

- **上轮复核的收尾**(见「正在进行」第 ① 条) —— 只剩报表 §08 第 7 项(节拍对齐, **需先拍板方向**)
  与同类端点的同样改法(低优先); 第 1、2 批与 §11 已实施未提交
- WEB UI: WebSocket 推送; 多用户; **设置页全面重构**(`想法.md` 现存最大一条未做项)
- WEB UI: 窗口日志等级可选; 星图侧补齐第九轮的纯版式项(棱镜已做: FX-05/06/09/17~25)
- 规则系统: 条件取反 (`!`/非 logic); 重新梳理 ignore_next_action_error / stop_following_rules_if
- tracker 分组前端增强 (阶段 2/3, 2026-09-15 拍板后续): 设置页 groups 下拉快捷追加 (rules_ref 风格); 辅种管理页按组筛选 (web_view 透出 conf.groups + app.js filterDefs)
- 其它: 切分大文件; 种子未变动时不触发内置维护任务; 版本管理; 命中限速曲线强调显示; 插件系统
- 🚧 实机验证: README 标注 🚧 的功能 (alpha 阶段), 生产使用前先 `--dry-run` 观察

## 历史归档 (已迁出本文件)

2026-09-14 ~ 2026-09-19 的全部会话纪要已按专题迁移到 [tasks/](tasks/_index.md) 各档案的"历史会话纪要 (原文归档)"段 (原文未删改), 或已沉淀进 [progress.md](progress.md) 的「已实现」段。需要回查历史请走 `tasks/_index.md` 定位专题档案, 本文件只保留**当前焦点**。
