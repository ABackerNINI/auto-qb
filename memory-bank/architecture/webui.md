# WEB UI 运行时

> 摘要: FastAPI 装配单点与启动 fail-fast、皮肤目录即 URL 与静态契约、线程边界(读快照 + 投命令)、视图发布与版本门控、组行 hash 引用式(聚合 + members hash 数组)、truth 通道、前端 ingestion 物化缝、version-reload 自愈、响应性设计要点、表格几何单点(dt_table)、排序引擎单点(sort.js 三态 / 默认升序键修复)、列风格引擎(colstyle.v1 五维 / data-cs-* 属性派生 / 判定纯函数家族)、部分组操作预警、键位现场提示(按需显影/键帽/页签徽标/角标)、图形化配置编辑器骨架、配置备份 bundle 导出/导入(掩码不出机 + 勾选段应用 + 偏好键双清单)。
> 触发: WEB UI, webui, FastAPI, create_app, 路由, 皮肤, 静态, 线程边界, 视图发布, group_view_ver, hash 引用式, members hash 数组, memberByHash, VIEW_ARRAYS, 物化, _materializeGroupRows, _rematQueue, version-reload, _versionSelfHeal, truth, 回执, 乐观 UI, 响应性, 窗口化, 表格几何, dt_table, DT_TABLE, columns_grid, gridTemplate, 排序, setSort, 三态排序, defKey, defDir, dtSortCell, dtSortState, IP 点分数值序, HR 三表, hrDetail, hrWave, hrKv, hr-full-modal, 列风格, colstyle, colStyle, data-cs-, csb-, csp-, cst-, csu-, cs-v, cs-u, --cs-fill, 进度条样式, LED 方块条, 色阶谱, 单位色组, progBand, speedBand, numScale, fmtSizeParts, fmtSpeedParts, 部分组, 部分组预警, partialGroups, 将缺文件, 整组迁移, 键位, 键帽, 键位现场提示, 显影, 常驻, kbd-reveal, kbd-persist, Backquote, kbShortcutDisplay, kbKeycapOf, kbKeysRev, aq-kbd, 配置编辑器, schema, writer, 配置备份, bundle, 导出配置, 导入配置, backup, 掩码, ui_prefs, PREF_KEYS

## 装配单点与启动 (webui/server/factory.py, webui/module.py)

`create_app` 是纯组装壳, 装配顺序固定: 鉴权依赖(全局 dependencies 单点, 所有 `/api/*` 经 Bearer 密钥) → FastAPI 实例(docs/openapi 关) → 按域 Router(`routes/ROUTE_BUILDERS` 固定顺序) → 静态挂载(最后 —— mount "/" 是兜底路由)。端点定义一律在 `routes/` 各模块, 工厂禁内联路由(守阵钉住)。**启动期监听失败 = fail-fast**(plans/26-11-03-0930-plan-webui-bind-fail-fast.html): 模块 start 拉起服务后检查 handle.started, 失败先落 INFO 诊断块(原因/占用者/处置, **只进日志** —— 绝不进异常消息/stderr), 再抛 `WebUIBindError` → CLI 单行 stderr、退出码 1、无堆栈; 低层 `start_web_server` 保持「返回 handle」契约(热重载复用, 不在那里抛)。热重载 apply: 有差异即置脏, **仅「监听身份」(enabled/host/port)变化才重启服务器**; 主循环每轮钩子(消费命令/刷新视图/落回执)经宿主按装配序调用。

## 皮肤目录即 URL 与静态契约 (webui/server/static_ui.py)

`webui/static/<名>/` 一个目录 = 一套皮肤(atlas 星图 / prism 棱镜 / console 控制台 / flux), `shared/` 是公共逻辑层、`fx/` 是动效库 —— **新增 UI = 新增目录, 零后端改动**。根路径按 cookie(`shared/boot.js` 写入)307 直达「上次使用的 UI」(服务端只认形状合法且 index.html 真实存在的值, 挡路径逃逸), 失效回落默认; 旧 `/newui` 书签 307 到 prism。**静态契约**: 默认非 /api 响应 `Cache-Control: no-cache` —— 浏览器仍缓存但每次带 ETag 协商(未变更 304), 否则升级后浏览器自缓存数小时, 界面「改了没变」; P2-b 起(plans/26-11-20-0727) 分流例外: 仅「v == 当前静态树哈希 V + 非 HTML + 2xx」的静态响应发 `public, max-age=31536000, immutable`, 裸路径/无 v/过期 v/3xx/4xx/5xx/HTML 仍 no-cache(升级后旧 v 落 no-cache + HTML 永 no-cache 保新 V 下发)。/api 响应不受本中间件影响（保持原样，非 no-cache）。

- **boot.js 装载已并发化 + `?v=` 版本化**(plans/26-11-20-0727): 分片 `Promise.all` 并发 fetch + index 归位拼接, 脚本 `link rel=preload as=script` 并发预取 + 全部成功后按清单序批量插入 `async=false`(四皮肤共用 boot.js, 一处改动四套受益); `withV()` 单点给分片 fetch / preload href / script src 三处统一追加 `?v=V`(已有 query 用 `&v=`, window.AQB_V 缺失优雅退化), fail-fast/保序/10s 超时不变量不变。

- **version-reload 自愈**(plans/26-11-11-0630 §04 S3, 2026-11-12 接线): no-cache+ETag 只保证**新开页面**拿到新 JS —— 同仓同进程发布下**已开的旧标签页**仍跑旧 JS, 每轮轮询把新形状载荷喂给旧消费位(静默渲染破损, 用户无感)。机制: 后端 status 载荷恒带 `version`(app_version), 前端 `_versionSelfHeal`(polling.js, 轮询数据入口)每轮比对: 变更沿 → `location.reload()` 自愈一跳(**中止本轮载荷应用**, 不把跨版本载荷喂进旧 JS)且照常续排下一拍; **30s 防抖**(sessionStorage per-tab, 不可用退内存层)把 reload 速率封顶 1 次/30s, 部署稳定后归零; 配置编辑器脏态守卫(cfgGuardActive)活跃 = 让拍不让位(不 reload、基线不动, 守卫释放后下一轮变更沿自然再触发); version 缺失/非字符串**保守不动基线**(无从判定变更方向, 宁可不自愈)。

## 线程边界 (webui/runtime.py, WebUIRuntime 门面)

- **Web 线程(uvicorn)只做两件事**: 读只读快照 + 经 `post_command()` 投递命令; 暂停/开始/删除/热重载等写操作全由主循环命令线消费 —— 单一写线程约束不变, Web 线程不碰 store/队列/state_file。
- 表现层状态(视图快照/版本号/脏标记/回执/搜索索引/命令队列)全部在 `manager.web`; 核心域 → 表现层单向通知(`mark_dirty`), 表现层 → 核心域只有一条回调(写能力 + 视图构建器)。
- **视图快照主循环发布**(持 view_lock 一次性替换全部视图 + 版本号), Web 线程只读; **「同轮发布」是硬约束**: 各视图共用一个版本号, 任何一份漏建或跨轮混拼, 前端都会把陈旧数组当新数据换上去。

## 视图发布与 truth 通道

- **版本门控**(等价 qB 的 rid): `group_view_ver` 每次重建自增; `ensure_state(rid, view)` 版本一致**不回传任何数组**(响应趋近零, 恒回 status 标量与 traffic/server 快照); **按视图回传**(指定视图只回该视图数组, 单点 `views_common.py`); 切视图前端置空 rid 强制取一次全量。
- **命令回执**: 每个 `_cmd_*` 是一次 qB 写操作, 由门面在主循环线程分发执行; 回执(cmd_id → status/wait/exec/truth)暂存, **每轮收尾 `flush_truths()` 无条件落**(异常路径兜底)。
- **命令唤醒**: `wake()` 只触发消费命令**不触发 tick** —— 否则每 tick 任务数上限的速率语义失效, 且自投递命令会自激循环(自投递走白名单)。
- **组行 hash 引用式(P-02 二期, plans/26-11-11-0630, 2026-11-12 落地)**: 组行 = **聚合字段 + `members` hash 数组**(`_build_group_row` views_group.py, `"members": [r.hash for r in recs]`; 先例 views_episodes.py 集节点), 成员明细不随组行回传, 前端经既有 `memberByHash()` 从 `singles ∪ torrents` 拼装 —— **VIEW_ARRAYS group 视图连带 torrents, show 视图同连带 torrents**(P-02 二期后索引生效源 = singles ∪ torrents; shows 视图当年「连带 groups+singles」同款 ride-along 先例, views_common.py:111)。聚合仍吃 `_member_view` 明细(组级聚合口径逐字段不变), 组行仍是完整行对象随整行走(R8 整行替换, 不做字段级 patch); delta 下组行整行 upsert(聚合 + hash 数组), 抖动成员明细改经 **delta.torrents 桶**回传(只抖那一条)。full 语义常驻回退与 `_reduce_delta` 三判据不动; 守阵 = 镜子测试 hash 形状 + `test_s6_partial_rows_equal_full_rebuild`「局部重算 == 全量重跑」单测。
- **载荷结论(S0/S5 实测对照, 单点 = 任务档案 tasks/26-11-11-webui-group-hash-ref.md)**: 全量回包 **-35%**(@3000 -35.3% / @5000 -35.5%, 与改造前投影命中 —— @5000 逐位、@3000 偏差 0.2pp); 抖动轮组行塌缩 **24.6×**@100 成员组(116 KB→4.7 KB) / **27.0×**@2000 成员组(2.33 MB→86 KB), 抖动轮响应整体 -93%(@3000 117 KB→8 KB)/ -96.2%(@2000 成员组 2.33 MB→90 KB); view=group 因连带 torrents 反而略大(计划「不预写承诺」被实测证实); G1(按需字段)/G2(分页)/G3(C2 二次演进)经 S5 实测三裁决点全部不立项(裁决记录在计划 §05)。

> 已外迁: 响应性设计(乐观 UI / ingestion 物化缝 / 行窗口化) → [attachments/webui-interaction-details.md](attachments/webui-interaction-details.md)(2026-11-22 cap 清零)

> 已外迁: 表格几何单点(dt_table.layout / assertLayout / HR 三表迁移) → [attachments/webui-rendering-details.md](attachments/webui-rendering-details.md)(2026-11-22 cap 清零)

> 已外迁: 排序引擎单点(AQB_SORT.setSort 三态 / 默认升序键修复) → [attachments/webui-rendering-details.md](attachments/webui-rendering-details.md)(2026-11-22 cap 清零)

> 已外迁: 列风格引擎(五维 / data-cs-* 派生 / 判定纯函数家族) → [attachments/webui-rendering-details.md](attachments/webui-rendering-details.md)(2026-11-22 cap 清零)

> 已外迁: 部分组操作预警(判定聚合双单点 / 三落点 / 后端纵深闸) → [attachments/webui-interaction-details.md](attachments/webui-interaction-details.md)(2026-11-22 cap 清零)

## 图形化配置编辑器 (webui/static/shared/ + config/writer.py)

- **前端持与磁盘同构的 YAML 树**(标量全为字符串, 与加载层 BaseLoader 语义一致): 编辑即就地增删改, 无格式往返转换零语义漂移; 脏检测用 JSON 快照对比。
- **保存管线(config/writer.py)**: 结构自检 → 落临时文件跑 `load_config`(**与启动同一校验路径**, 失败 400 不碰盘) → diff 判定 → R 级字段回退磁盘旧值 → 备份 → ruamel round-trip 写盘 → 投递 `reload_config` 命令(仍由主循环线程应用)。已存在键的注释保留; **值未变的键跳过赋值**(保留磁盘原标量形态); 列表整体替换。
- **保存后联动刷新只有一种做法: 投递命令, 不在端点里干活**(热重载后快照类数据要等下一轮 interval; 判定单点按配置指纹在 apply 前后各算一次, 不等即投刷新命令)。
- `config/schema/` 是纯声明的 UI 元数据(分组/字段/控件/单位/枚举/帮助), **不承载正确性** —— 合法性唯一入口仍是 `validate_config`。

> 已外迁: 键位现场提示(显影 / 键帽 / 页签徽标 / 角标) → [attachments/webui-interaction-details.md](attachments/webui-interaction-details.md)(2026-11-22 cap 清零)

> 已外迁: 配置备份 bundle 导出/导入(掩码不出机 / 勾选段应用 / 偏好键双清单) → [attachments/webui-config-backup-details.md](attachments/webui-config-backup-details.md)(2026-11-22 cap 清零)
