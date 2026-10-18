# 26-10-18-backend-traffic-snapshot-merge — 流量快照解耦与「流量与限速」合并卡 (Phase 2)

**Status:** Done
**Added:** 2026-10-18
**Updated:** 2026-10-18
**Summary:** 把流量快照的所有权从限速曲线任务移交独立模块 `traffic_snapshot`（`source`/`limit` 段级 API + 派生 `state` + 自有节奏键 `traffic_source.refresh_interval`），修掉「没配曲线就永远没有历史图」「两条刷新路径语义不一」「轮询背整份 history」三个结构性死角；设置页把「数据来源 / 限速曲线 / 流量图」三张卡合并为一张「流量与限速」（schema 合组 `traffic_limit` + 独立组件 `aq-traffic-card` + 卡内三区），顺带补通用层两笔欠账（`show_if` 下移到 object 段、排除表单点化）。17 条拍板见计划 D1–D17；批次 P0（收口 Phase 1 的 S8）→ P2-A → P2-B。
**Topics:** backend-traffic-snapshot-merge, webui-traffic-limit-card
**Refs:** memory-bank/plans/26-10-18-0813-plan-global-traffic-source-phase2.html, memory-bank/testing/baselines/26-10-18-1058-traffic-limit-card-p2b.md

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
| P0 | 收口 1737-S8「切源即刷新」+ 守阵 | Done |
| A1 | `traffic_snapshot` 模块骨架 + 自注册任务（装配在 `speed_curve` 之前） | Done |
| A2 | 快照契约拆段 + `derive_state` + `publish_source/publish_limit/publish_off` | Done |
| A3 | `traffic_source.refresh_interval` 四层契约（默认 10M / 校验 10S–1H） | Done |
| A4 | 曲线模块降为只写 limit 段，删 `refresh_traffic_view` | Done |
| A5 | `refresh_traffic` 改指新模块 + 轮询载荷摘 history | Done |
| B1 | schema 合组 `traffic_limit` + 首页卡/面包屑/LED/读数 + 旧 key 映射 | Done |
| B2 | 通用层两修：`show_if` 下移到 object 段 + `HUB_SKIP_PATHS` 单点化 | Done |
| B3 | `aq-traffic-card` + `shared/tpl/traffic-card.html` + 三皮肤清单 + 额度回落 | Done |
| B4 | 卡内三区 + 折叠头 + 依赖提示条 + 「打开历史图表」入口 | Done |
| B5 | 守阵与 e2e 跟随改造 + 四条变异验证 | Done |

## 进度日志

### R0 · 立档 (2026-10-18)

三轮 grilling 收敛并落盘 Phase 2 计划（17 条拍板 D1–D17），本档同建立；代码零改动。待开工起点＝ P0（Phase 1 的 S8 收口）。

### R1 · P0 完成 — 收口 1737-S8「切源即刷新」(2026-10-18)

按 D4 先把 Phase 1 的尾巴收干净再动快照所有权。落地三处：① `core/traffic_source/paths.py` 新增 `source_signature(config)`（来源指纹 = `enabled` / `provider` / 文件来源路径三位，**只取配置事实**，不含指针解析结果）；② `webui/commands.py::_cmd_reload_config` 热重载前后比对指纹，变了就投递现成的 `refresh_traffic`（`trigger="config"`），该命令在**同一轮 drain** 内执行；③ `_cmd_refresh_traffic` 加 `trigger` 参数只分流日志口径，执行路径仍是一条。前端**零新增取数点**：`dialogs.js` 既有 `status.traffic.ts` 监听已覆盖「弹层开着时快照一变就重拉」，顶栏 pill 走主轮询 —— 另加显式重拉只会在 PUT 回执（早于热重载落地）时先拉一次旧快照。

守阵 4 条 + 变异红验（放宽判定 ⇒ 2 条立即红）。**给 P2-A 留下的接口契约**：A4 删 `refresh_traffic_view`、A5 把命令改指 `traffic_snapshot.refresh()` 时，**判定方（`_cmd_reload_config`）一行都不用改** —— 它只认命令名。**边界**：曲线未启用时刷新仍跳过不发布（计划 §02 #1 的结构性死角），P0 保持行为等价，由 A1/A4 的独立发布修掉。全量回归绿除一条既存红（`test_docs_forms::test_doc_map_live_rotation`，净树同样红，与本轮无关）；数字见基线切片。

### R2 · P2-A 完成 — 快照所有权移交 + 四层契约 + 载荷瘦身 (2026-10-18)

按计划 §04 的 A1–A5 一次走完，后端改动收口；P2-B（前端合并卡）未开工。

**A1 新模块**：`core/modules/traffic_snapshot_mod.py` —— `sections()` 只返回 `("traffic_source",)`（**不声明曲线段**，这就是解耦判据，也是「没配曲线也能看历史图」的落点：`start()` 无配置门槛，任务 `traffic_snapshot_refresh` 照注册）；装配点排在 `SpeedCurveModule` **之前**，曲线 `start()` 首行 `_require_snapshot()` 缺失即 fail-fast。模块名与任务名刻意不同名（沿用 `speed_curve` -> `speed_limit_curve` 的既有做法）。`apply()` 段不变则短路，变则**就地**改已入队任务的 `interval`（新增 `TaskQueue.named()` 取引用），另订阅 `queue_rebuilt` 相位兜底 L2 重建。

**A2 段级契约**：`publish_source(rows, state, reasons)` / `publish_limit(target, actual, reasons, state)` / `publish_off(reason)` 三个入口，内部同一个 `_publish(**segments)`：读旧快照 -> 只改自有键 -> `derive_state` 算顶层 `state` -> **一次** `set_traffic_view`。顶层 `state` 不接受外部入参（防第二真相源）；`periods` 固定 `day`/`month` 两行，不再是「各曲线 period 的并集」，曲线增删不再改变快照形状。

**A3 四层契约**：`TrafficSourceConfig.refresh_interval: float = 600.0`（models）/ `Field("refresh_interval", "刷新间隔", "time", "10M")`（schema/groups）/ 已知键集 + `_try_time(..., min_s=10, max_s=3600)`（validation）/ `parse_time`（loaders）；键面基线 169 -> 170。前端同批落两行（`config_hub.js::tmSourceRows()`），曲线 `interval` 的 help 补「只管写限速」——与本键划清语义。

**A4 曲线降级**：删 `_history_rows` / `_period_rows` / `_read_source_rows` / `refresh_traffic_view`；handler 里来源关时**直接 REQUEUE 不发布**（off 态由快照模块 own 自己的节拍 + S8 切源即刷新保证），dry_run/ok 走 `_publish_limit`。读档逻辑下沉到 `core/traffic_source/reader.py::read_source_rows` —— 两模块读同一份 dat，失败判据必须同源，否则两段 state 会各说各话（计划原写「留在曲线模块内」，这是实施偏差①，见 §10 R1）。

**A5 单一路径 + 载荷瘦身**：`refresh_traffic` 命令改调 `host.get("traffic_snapshot").refresh()`；`webui/runtime.py` 新增 `public_traffic_view(view)` 摘 `history`，`routes/state.py` 的 `_status_payload` 走它，`/api/traffic/history` 成为 history 唯一出口。**S8 的接口契约兑现**：`_cmd_reload_config` 一行没改（它只认命令名）。

**守阵**：新增 `tests/test_traffic_snapshot.py` 14 条（段认领 / 装配序 / 无曲线配置照发历史 / `derive_state` 表 / state 恒派生 / 两向段隔离 / off 清双段 / stale 原因码 / 关源不读盘 / 曲线跑完不动来源段 / `set_traffic_view` 调用点源码检索 / interval 就地生效 / 轮询载荷无 history）；改造 8 个既有文件里依赖「曲线独家发布」的断言，并给 `refresh_interval` 补了配置校验边界守阵。全量回归与覆盖率见基线切片（数字只写那一处）。

**边界（留给 P2-B）**：前端仍按旧形状消费（`status.traffic.state` 三态分流 + 弹层读 `/api/traffic/history` 已可用），但 `source`/`limit` 段尚无 UI 读点；schema 仍是三组独立段（`traffic_limit` 合组属 B1）；`settings.html` 额度未回落。

### R3 · P2-B 完成 — 合并卡 / schema 合组 / 通用层两修 (2026-10-18)

按计划 §04 的 B1–B5 一次走完，Phase 2 两批全部收口。

**B1 合组**：`groups.py` 里「流量图」「全局流量来源」「限速曲线」三组并成一组 `traffic_limit`（label「流量与限速」，8 -> 6 组；字段序 = 卡内区序 `traffic_source` -> `global_speed_limit_curve` -> `qb_traffic`）。选合组而不是「UI 层合并」的理由兑现了：`hubCards` / `hubNow` / `hubBlocks` 三处按 `group.key` 直查 schema，合组后原生工作 —— 前端只改三处硬编码 case（LED / 读数 / 徽标）与视图分支。旧 `hub.view` 存量值用 `HUB_VIEW_ALIAS`（`traffic_source` / `speed` / `traffic` -> `traffic_limit`）在**取值处**（`initialHubView`）映射，不清 localStorage；`__logs -> basic` 仍留在 `hubRestore`（那是"分区已删除"的另一类，改的是恢复路径）。

**B2 通用层两修**：① `config_editor.js::visible()` 删掉 `type !== "field" -> true` 短路，group/section 项改走 `cfgVisible(field, owner)` —— 段上的 `show_if` 从此真的生效；② `config_hub.js` 的硬编码 `if (hubKey === "config.hr_check.sites")` 提成 `HUB_SKIP_PATHS` 常量表（三条：hr_check.sites / traffic_source / global_speed_limit_curve），`walk` 只查表。顺手把 `tmProviderItems(key)` 的「手工挑 provider」换成按 `cfgVisible` 过滤 —— 手工那份与 schema 的 `show_if` 是两套真相，漏改一边就会出现「选 A 也显示 B 的参数」。

**B3 抽组件**：新增 `shared/traffic_card.js`（`inject: ["ce"]` + 同样透传 `provide`，理由与 `CE_FIELD_BASE` 同：全局 mixin 给每个组件都 provide 了 `ce: this`，不透传的话卡内 `hub-field` 注入到的是组件实例，字段只显默认值）+ `shared/tpl/traffic-card.html`（`into: body` 的 x-template，三皮肤清单同步）。`settings.html` 的来源分支缩成三行挂载（418 -> 318 行），`settings-detail.html` 的 `speed` 分支删除（543 -> 420 行）；`test_webui_static_skins` 里 `settings.html` 的 440 例外额度随之删除，回落默认 400。

**B4 卡内三区**：外壳一张 `.hb-blk`，三个 `.hb-blk.hb-sub` 子区（数据来源 -> 限速曲线 -> 流量图采样），区头 `hb-blk-hd hb-sub-toggle` 可折叠、折叠态存 `hub.sub`（**不持久化**）。来源关闭时卡头下方常驻提示条（文案经 `tmAffectLabels()`，与「关闭工具」确认框同源），限速曲线区与流量图区各给一句"关源后这一区会怎样"的说明 —— 原来只剩一个「启用限速曲线」按钮会让人误判成"本功能没开"。卡头右侧「打开历史图表」-> `openHistory()`，历史图仍留在全局弹层（D2）。另把 `popovers.html` 关源空态与 `core/traffic_source/paths.py` 两处指路文案改到新卡名。

**B5 守阵**：新增 `tests/test_web_traffic_limit_card.py` 9 条（组并合 / 组件接线含 ce 透传 / 三区与折叠 / 历史图入口 / 提示条同源 / 旧视图映射 / `show_if` 下移 / 排除表单点 / 分片体量回落）；`test_web_traffic_monitor.py` 的模板取数改成经 `_tm_tpl()` 单点（下次搬分片只改一行）；`test_web_backend_misc.py` 组清单、`test_webui_static_skins.py` 额度表同步。e2e：卡名改「流量与限速」、工具参数块改取最内层（卡内 `.hb-blk.hb-sub` 嵌套，`hasText` 会同时命中三层祖先）、新增合并卡三区 + 折叠 + 历史图入口用例（prism/atlas 各 1）。**四条变异逐条红验**：去掉子区 / 去掉折叠头 / 恢复 `visible()` 非叶子短路 / 排除表改回硬编码 —— 各让对应守阵变红，还原后文件字节一致（SHA256）。

**计划偏差**：无实质偏差；B1 的旧值映射落在 `initialHubView` 而非 `hubRestore`（计划 §B1 写的是前者，`__logs` 那条先例在后者 —— 两者语义不同，前者是"分区改名"，后者是"分区删除"，按计划落点执行）。**遗留（本批不做）**：`source.state` / `limit.state` 两个细分字段尚无 UI 读点（D8 明说"前端逐批迁到细分字段，不在本计划一次性改完"）。
