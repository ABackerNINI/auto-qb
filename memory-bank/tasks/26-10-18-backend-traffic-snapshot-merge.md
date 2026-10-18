# 26-10-18-backend-traffic-snapshot-merge — 流量快照解耦与「流量与限速」合并卡 (Phase 2)

**Status:** Open
**Added:** 2026-10-18
**Updated:** 2026-10-18
**Summary:** 把流量快照的所有权从限速曲线任务移交独立模块 `traffic_snapshot`（`source`/`limit` 段级 API + 派生 `state` + 自有节奏键 `traffic_source.refresh_interval`），修掉「没配曲线就永远没有历史图」「两条刷新路径语义不一」「轮询背整份 history」三个结构性死角；设置页把「数据来源 / 限速曲线 / 流量图」三张卡合并为一张「流量与限速」（schema 合组 `traffic_limit` + 独立组件 `aq-traffic-card` + 卡内三区），顺带补通用层两笔欠账（`show_if` 下移到 object 段、排除表单点化）。17 条拍板见计划 D1–D17；批次 P0（收口 Phase 1 的 S8）→ P2-A → P2-B。
**Topics:** backend-traffic-snapshot-merge
**Refs:** memory-bank/plans/26-10-18-0813-plan-global-traffic-source-phase2.html

## 原始请求

1. 「计划 Phase 2 立项，grilling: <1737 Phase 1 计划>」—— 以 Phase 1 计划里的 P1–P3 方向为起点，用 grilling 三轮把 Phase 2 的方案钉死，再落盘立项。
2. Q12 订正：合并范围要**把「流量图」（qB 口径上传/下载流量历史曲线）也合并进来**，视图命名「流量与限速」。
3. 其余问题一律「按推荐」。

## 思考过程与决策

三轮 grilling 共 17 问，全部拍板，逐条见计划 §06（D1–D17）。几个改变了原方向的判断：

- **原 P2「三卡合一」的前提不成立**：设置页里根本没有「历史流量图」卡 —— 它是顶栏 pill 打开的全局弹层（`popovers.html:197-271`）。用户订正后合并对象改为「数据来源 + 限速曲线 + 流量图（qB 采样）」三组，历史图仍留弹层，卡头只加入口（D2）。
- **解耦的真实收益是「没配曲线也能看历史图」**：现状快照只由曲线任务发布，`global_speed_limit_curve is None` 时任务不注册（`speed_curve_mod.py:173-174`），历史图结构性为空。只有独立任务能修（D3）。
- **节奏必须新增**：`refresh_traffic` 的唯一触发是工具事件，曲线 `interval` 又兼作快照节奏；解耦后来源侧要自带节拍 → 新键 `traffic_source.refresh_interval`（D9）。
- **先收 S8 再动所有权**：S8 改的是同一段刷新路径，合并做会让失败归因失效（D4）。
- **顶层 `state` 保留但降级为派生值**：单一枚举混着来源态与曲线态，拆 `source.state`/`limit.state` 后仍需兼容三个前端消费点；用单点纯函数 + 守阵锁住（D8）。
- **合组比 UI 层合并省得多**：首页卡、面包屑、块组装三处都按 `group.key` 直查 schema，合组后全部原生工作，只改三处硬编码 case（D13/D17）。

## 实现计划

计划：`memory-bank/plans/26-10-18-0813-plan-global-traffic-source-phase2.html`（D1–D17、§04 A1–A5 / B1–B5 各有验收判据）。

- **P0** 收口 Phase 1 的 S8（切源即刷新）+ 行为守阵 —— 前置，属 1737 计划。
- **P2-A（后端）** A1 新模块骨架 → A2 契约拆段/派生 state/段级 API → A3 新键四层 → A4 曲线模块只写 limit 段、删 `refresh_traffic_view` → A5 命令改指 + 轮询载荷摘 history。
- **P2-B（前端）** B1 schema 合组 + 首页卡/LED/读数改键 + 旧 key 映射 → B2 通用层两修 → B3 组件抽片（三皮肤清单同步、`settings.html` 额度 440→400）→ B4 卡内三区 + 折叠 + 依赖提示 + 历史图入口 → B5 守阵/e2e 跟随 + 四条变异验证。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| P0 | 收口 1737-S8「切源即刷新」+ 守阵 | Open |
| A1 | `traffic_snapshot` 模块骨架 + 自注册任务（装配在 `speed_curve` 之前） | Open |
| A2 | 快照契约拆段 + `derive_state` + `publish_source/publish_limit/publish_off` | Open |
| A3 | `traffic_source.refresh_interval` 四层契约（默认 10M / 校验 10S–1H） | Open |
| A4 | 曲线模块降为只写 limit 段，删 `refresh_traffic_view` | Open |
| A5 | `refresh_traffic` 改指新模块 + 轮询载荷摘 history | Open |
| B1 | schema 合组 `traffic_limit` + 首页卡/面包屑/LED/读数 + 旧 key 映射 | Open |
| B2 | 通用层两修：`show_if` 下移到 object 段 + `HUB_SKIP_PATHS` 单点化 | Open |
| B3 | `aq-traffic-card` + `shared/tpl/traffic-card.html` + 三皮肤清单 + 额度回落 | Open |
| B4 | 卡内三区 + 折叠头 + 依赖提示条 + 「打开历史图表」入口 | Open |
| B5 | 守阵与 e2e 跟随改造 + 四条变异验证 | Open |

## 进度日志

### R0 · 立档 (2026-10-18)

三轮 grilling 收敛并落盘 Phase 2 计划（17 条拍板 D1–D17），本档同建立；代码零改动。待开工起点＝ P0（Phase 1 的 S8 收口）。
