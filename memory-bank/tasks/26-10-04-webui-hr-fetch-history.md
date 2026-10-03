# 26-10-04-webui-hr-fetch-history — WEBUI HR 在线核实拉取历史详情表

**Status:** Open
**Added:** 2026-10-04
**Updated:** 2026-10-04 03:20
**Topics:** webui-hr-fetch-history
**Summary:** HR在线核实新增「拉取历史详情表」：后端三类事件（波次/拦截/对账）环形留痕进站点文件 history 字段 + GET /api/hr/history + 全屏弹层表③(参照扩展选项页取数明细表并加细)。计划已落文待拍板, S1-S6 未开工。
**Refs:** memory-bank/plans/26-10-04-0312-plan-webui-hr-fetch-history.html

## 原始请求

> WEBUI HR在线核实需要添加拉取历史详情表, 什么时间拉取了什么站点, 解析结果等, 参照插件的表格, 且需更详细. 先写一个分步实施计划

（2026-10-04, 用户; 本轮只出计划, 实施待拍板后指派。）

## 思考过程与决策

- **「插件」的所指**（勘察结论）: 项目里带历史表格的「插件」= 浏览器扩展 hr-fetch-proxy, 其选项页有「站点现状表」与「最近取数明细表」（时间/站点/类型/结果/耗时/大小, 环形 50 条, 数据在 `chrome.storage` 的 events 环）。WebUI 读不到扩展侧存储, 且解析/放行语义只在后端 —— 历史必须由后端自记。
- **关键差距**（勘察结论）: 后端站点文件只存最新快照（`index`/`wave.lanes` 每档最近一波/累计账本）, **没有每次取数的历史流水** —— 「上周那波为什么失败」现在不可考。历史只散落在日志与 `.bak`（一版）。
- **存储决策**: 内嵌 `HrSiteData.history` 环（拍板项①推荐 A）。理由: 零新锁、零新版本注册（versioning.py:16-18「不为补字段造版本」）、随既有原子写/.bak/多实例共享; 独立文件方案要第二把锁 + 新版本链 + 双写点, 不值。
- **写盘纪律**（硬不变量）: 60s poll 被调度闸跳过时不记事件不写盘（否则每分钟全文件重写）; 写盘只发生在真实波次（本就有逐页 commit）、用户触发的 defer、对账动作。S2 用测试钉死。
- **粒度决策**: 波次级一行 + 行内展开各档明细（拍板项③推荐 A）; 每页平铺会刷屏且丢「波」语义。插件表「大小」列不搬（无排障价值, 页数/行数代替）。
- **UI 决策**: 表③ = `<details>` 折叠段, 放全屏弹层 `.hrs-list` 之后全局段（拍板项②推荐 A）; 页签化要动 26-10-02-1936 刚收口的弹层结构。并入 hr_status.js（免动三份 index.html 脚本清单）。
- **记录器安全**: 纯内存 append + 修剪、无 IO、try 包裹, 记录失败降级日志绝不影响取数主流程。
- **已知限制**: 新旧版本混跑时旧程序写盘会丢 history 键（业务字段无损, 升级窗口期现象, 不做双写兼容）。

五项拍板（①存储位置 ②UI 形态 ③记录粒度 ④defer 事件 ⑤容量/保留常量化）见计划 §04, 均带推荐, 待用户拍板。

## 实现计划

单点: [plans/26-10-04-0312-plan-webui-hr-fetch-history.html](../plans/26-10-04-0312-plan-webui-hr-fetch-history.html)（§03 方案设计 / §04 拍板项 / §05 分步实施, 锚点行号取证 2026-10-04 03:12）。

- **S1** 数据模型与序列化: model.py `HrHistoryEvent` + `HrSiteData.history` + cap/保留常量; 不抬 hr_site 版本。
- **S2** 记录写入点: service.py `_append_history` + `_do_wave` 六终态 + force-defer; report.py 对账事件; poll 零写盘断言。
- **S3** 只读口径与 API: status.py `history_rows()`（合并/降序/limit/人话/徽章映射）+ routes/hr.py `GET /api/hr/history`。
- **S4** 前端表③: hr_status.js `hrsHist*` + settings-detail.html 表③段（`aqb:hr-history` 锚）+ 三皮肤 CSS 成对。
- **S5** 桩走查: ui_harness.py 补 `/api/hr/history` 桩; 三皮肤 5 态截图自查。
- **S6** 收尾: test.full 基线切片 + docs/hr-online-verify-docs.md 登记 + 档案收口。

## 子任务状态表

| 步骤 | 内容 | 状态 |
|---|---|---|
| 拍板 | 计划 §04 五项 | Open |
| S1 | 数据模型与序列化 | Open |
| S2 | 记录写入点 | Open |
| S3 | 只读口径与 API | Open |
| S4 | 前端表③ | Open |
| S5 | 桩走查与三皮肤目检 | Open |
| S6 | 收尾回写 | Open |

## 进度日志

- **2026-10-04 03:20** 立档。计划编制轮完成: sync 成功(13e2646f) → 勘察（子智能体全库调研 + service/store/model/versioning/routes/settings-detail/hr_status 精读, 锚点快照 03:12）→ 计划落文 [plans/26-10-04-0312](../plans/26-10-04-0312-plan-webui-hr-fetch-history.html)（8 节: 现状差距/方案设计/五拍板/S1-S6/测试口径/风险/锚点附录, 含表③静态 mock）。本会话零代码改动, 实施待用户拍板后指派。
