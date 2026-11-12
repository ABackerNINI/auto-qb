# WEB UI 运行时

> 摘要: FastAPI 装配单点与启动 fail-fast、皮肤目录即 URL 与静态契约、线程边界(读快照 + 投命令)、视图发布与版本门控、组行 hash 引用式(聚合 + members hash 数组)、truth 通道、前端 ingestion 物化缝、version-reload 自愈、响应性设计要点、表格几何单点(dt_table)、部分组操作预警、图形化配置编辑器骨架。
> 触发: WEB UI, webui, FastAPI, create_app, 路由, 皮肤, 静态, 线程边界, 视图发布, group_view_ver, hash 引用式, members hash 数组, memberByHash, VIEW_ARRAYS, 物化, _materializeGroupRows, _rematQueue, version-reload, _versionSelfHeal, truth, 回执, 乐观 UI, 响应性, 窗口化, 表格几何, dt_table, DT_TABLE, columns_grid, gridTemplate, 部分组, 部分组预警, partialGroups, 将缺文件, 整组迁移, 配置编辑器, schema, writer

## 装配单点与启动 (webui/server/factory.py, webui/module.py)

`create_app` 是纯组装壳, 装配顺序固定: 鉴权依赖(全局 dependencies 单点, 所有 `/api/*` 经 Bearer 密钥) → FastAPI 实例(docs/openapi 关) → 按域 Router(`routes/ROUTE_BUILDERS` 固定顺序) → 静态挂载(最后 —— mount "/" 是兜底路由)。端点定义一律在 `routes/` 各模块, 工厂禁内联路由(守阵钉住)。**启动期监听失败 = fail-fast**(plans/26-11-03-0930-plan-webui-bind-fail-fast.html): 模块 start 拉起服务后检查 handle.started, 失败先落 INFO 诊断块(原因/占用者/处置, **只进日志** —— 绝不进异常消息/stderr), 再抛 `WebUIBindError` → CLI 单行 stderr、退出码 1、无堆栈; 低层 `start_web_server` 保持「返回 handle」契约(热重载复用, 不在那里抛)。热重载 apply: 有差异即置脏, **仅「监听身份」(enabled/host/port)变化才重启服务器**; 主循环每轮钩子(消费命令/刷新视图/落回执)经宿主按装配序调用。

## 皮肤目录即 URL 与静态契约 (webui/server/static_ui.py)

`webui/static/<名>/` 一个目录 = 一套皮肤(atlas 星图 / prism 棱镜 / console 控制台 / flux), `shared/` 是公共逻辑层、`fx/` 是动效库 —— **新增 UI = 新增目录, 零后端改动**。根路径按 cookie(`shared/boot.js` 写入)307 直达「上次使用的 UI」(服务端只认形状合法且 index.html 真实存在的值, 挡路径逃逸), 失效回落默认; 旧 `/newui` 书签 307 到 prism。**静态契约**: 非 /api 响应一律 `Cache-Control: no-cache` —— 浏览器仍缓存但每次带 ETag 协商(未变更 304), 否则升级后浏览器自缓存数小时, 界面「改了没变」。

- **version-reload 自愈**(plans/26-11-11-0630 §04 S3, 2026-11-12 接线): no-cache+ETag 只保证**新开页面**拿到新 JS —— 同仓同进程发布下**已开的旧标签页**仍跑旧 JS, 每轮轮询把新形状载荷喂给旧消费位(静默渲染破损, 用户无感)。机制: 后端 status 载荷恒带 `version`(app_version), 前端 `_versionSelfHeal`(polling.js, 轮询数据入口)每轮比对: 变更沿 → `location.reload()` 自愈一跳(**中止本轮载荷应用**, 不把跨版本载荷喂进旧 JS)且照常续排下一拍; **30s 防抖**(sessionStorage per-tab, 不可用退内存层)把 reload 速率封顶 1 次/30s, 部署稳定后归零; 配置编辑器脏态守卫(cfgGuardActive)活跃 = 让拍不让位(不 reload、基线不动, 守卫释放后下一轮变更沿自然再触发); version 缺失/非字符串**保守不动基线**(无从判定变更方向, 宁可不自愈)。

## 线程边界 (webui/runtime.py, WebUIRuntime 门面)

- **Web 线程(uvicorn)只做两件事**: 读只读快照 + 经 `post_command()` 投递命令; 暂停/开始/删除/热重载等写操作全由主循环命令线消费 —— 单一写线程约束不变, Web 线程不碰 store/队列/state_file。
- 表现层状态(视图快照/版本号/脏标记/回执/搜索索引/命令队列)全部在 `manager.web`; 核心域 → 表现层单向通知(`mark_dirty`), 表现层 → 核心域只有一条回调(写能力 + 视图构建器)。
- **视图快照主循环发布**(持 view_lock 一次性替换全部视图 + 版本号), Web 线程只读; **「同轮发布」是硬约束**: 各视图共用一个版本号, 任何一份漏建或跨轮混拼, 前端都会把陈旧数组当新数据换上去。

## 视图发布与 truth 通道

- **版本门控**(等价 qB 的 rid): `group_view_ver` 每次重建自增; `ensure_state(rid, view)` 版本一致**不回传任何数组**(响应趋近零, 恒回 status 标量与 traffic/server 快照); **按视图回传**(指定视图只回该视图数组, 单点 `views_common.py`); 切视图前端置空 rid 强制取一次全量。
- **命令回执**: 每个 `_cmd_*` 是一次 qB 写操作, 由门面在主循环线程分发执行; 回执(cmd_id → status/wait/exec/truth)暂存, **每轮收尾 `flush_truths()` 无条件落**(异常路径兜底)。
- **命令唤醒**: `wake()` 只触发消费命令**不触发 tick** —— 否则每 tick 任务数上限的速率语义失效, 且自投递命令会自激循环(自投递走白名单)。
- **组行 hash 引用式(P-02 二期, plans/26-11-11-0630, 2026-11-12 落地)**: 组行 = **聚合字段 + `members` hash 数组**(`_build_group_row` views_group.py, `"members": [r.hash for r in recs]`; 先例 views_episodes.py 集节点), 成员明细不随组行回传, 前端经既有 `memberByHash()` 从 `singles ∪ torrents` 拼装 —— **VIEW_ARRAYS group 视图连带 torrents**(shows 视图当年「连带 groups+singles」同款 ride-along 先例, views_common.py:111)。聚合仍吃 `_member_view` 明细(组级聚合口径逐字段不变), 组行仍是完整行对象随整行走(R8 整行替换, 不做字段级 patch); delta 下组行整行 upsert(聚合 + hash 数组), 抖动成员明细改经 **delta.torrents 桶**回传(只抖那一条)。full 语义常驻回退与 `_reduce_delta` 三判据不动; 守阵 = 镜子测试 hash 形状 + `test_s6_partial_rows_equal_full_rebuild`「局部重算 == 全量重跑」单测。
- **载荷结论(S0/S5 实测对照, 单点 = 任务档案 tasks/26-11-11-webui-group-hash-ref.md)**: 全量回包 **-35%**(@3000 -35.3% / @5000 -35.5%, 与改造前投影命中 —— @5000 逐位、@3000 偏差 0.2pp); 抖动轮组行塌缩 **24.6×**@100 成员组(116 KB→4.7 KB) / **27.0×**@2000 成员组(2.33 MB→86 KB), 抖动轮响应整体 -93%(@3000 117 KB→8 KB)/ -96.2%(@2000 成员组 2.33 MB→90 KB); view=group 因连带 torrents 反而略大(计划「不预写承诺」被实测证实); G1(按需字段)/G2(分页)/G3(C2 二次演进)经 S5 实测三裁决点全部不立项(裁决记录在计划 §05)。

## 响应性设计 (plans/26-09-19-1241-webui-responsiveness-plan.html)

总原则: **感知延迟与真实延迟分开治** —— 「不跟手」主因是沉默(点击后无反馈), 收益最大的是乐观 UI, 后端加速只负责把真值对齐压到百毫秒级。

- **乐观 UI 只做白名单(pause/resume)**: 补丁**先于 POST** 贴上(放 await 之后 = 押在网络往返上); **3s 兜底显式回滚到补丁前值**(光删补丁记录不叫回落 —— rid 未变时服务端不回传数组, 行对象不被替换, 补丁值会永久留在行上); **真值匹配即清必须比服务端快照**(比行上的当前值 = 跟自己比, 首轮必假匹配); 只认本轮 payload 真带了的 hash; 失败立即回滚。
- **命令后补刷新走完整同步**(只 apply 增量会留半刷新态), 整批命令 drain 完只补一次; qB 受理(HTTP 200)≠建好, 另有**有界追平**: 登记期望 hash, 同步线提前 +80ms 再问(≤3 次/TTL)。
- **ingestion 物化缝**(plans/26-11-11-0630 §04 S2, 2026-11-12 接线): 组行 `members` 改 hash 引用式后, 前端在**摄入侧**物化成员明细 —— polling.js 三入口(applyStateRows 全量/delta + auth.js bootstrap)经 `_materializeGroupRows` 产**成员行浅拷贝**而非 canonical 行引用(动因: 乐观链 prev 采集「同 hash 多命中各为独立对象」, 别名化下第二命中读到已打补丁值 → `op.prev` 被污染, 失败回滚静默失效; 浅拷贝与物化前服务端成员字典同构, g.members 消费位零波及)。delta 桶序 torrents/singles 先于 groups 合并 ⇒ 物化时索引恒新鲜; 缺项保留原 hash 字符串不产 undefined + `_rematQueue`/`_rematDrain` 后续轮补物化(后端「成员脏 ⇒ 同代组脏」不变式下常规不可达, 纯兜底)。**已知语义边界**: `_snapshotTruth` 组员源换本地物化拷贝后, 组脏(他员变化)+ 该组另有成员 pending 同窗会提前撤 hold 且 op.prev 同窗污染 —— 成功路径观感不变, 失败/停滞路径补丁值滞留至该成员下次变化或下一次全量轮。守阵单点: node 电池 `test_r4_truth_snapshot_materialized_members` + `test_r4_remat_drain_after_assign_two_beat`(tests/test_webui_static_r4_poll_auth_lifecycle.py)+ e2e `group-hash-ref.spec.mjs`。
- **行窗口化只减 DOM 行数不改布局模型**(上下占位撑高度, 列对齐与列宽协议保持有效); 行高逐行实测 + 前缀和 + 二分(行高不齐, 等高假设会漂); 展开的组在可见集合里时窗口退避全量。
- **搜索索引**: 种子名匹配即时扫 store, 文件列表匹配靠索引(文件 API 只在主循环线程); 按 hash 增量维护 + 单次限流预算, 未拉完下一 tick 续建。
- 前端纪律: 页面隐藏停轮询恢复即刷; setTimeout 链式续排不堆叠请求; **只做失败退避**, 不做「无变化退避」。

## 表格几何单点 (webui/static/shared/dt_table.js + columns_grid.js)

- **`DT_TABLE.layout()` 是全仓表格几何字符串(轨道串 / aligns)的单一生产者**(计划 plans/26-11-10-0027-plan-dt-table-wiring.html, 2026-11-10 接线): `columns_grid._gridTemplate` 与 `colAlignCss` **内部委托**该单点取轨道串与对齐, 旁路拼接已删; 调用方(主视图 computed + 抽屉桥)与 DOM 零改动, 全部表格面(含主列表、含 flux)同一链。新增/改表格几何逻辑只改 dt_table.layout 一处 —— **禁止再造平行计算**。
- **`assertLayout()` 常驻生产渲染自查**(拍板 D3): 三处 O(1) 计数(grid 轨道数 / 列头格数 / 首行子格数), 不一致 `console.error`(含 tableId 与三方计数)**不打断渲染**(保守默认); 未挂载豁免。
- **D4 例外清单(明文化)**: HR 三表(hrDetail / hrWave / hrKv, 无 tpl/align 字段)+ 04 卡片形态面不接几何单点; 守阵钉「清单之外零旁路」。HR 三表统一交互(拖宽/拖序/右键隐藏/持久化)为第二轮立项(拍板 D7, 方向迁 aq-table grid 链路), 届时补 tpl/align 字段后纳入同一单点。
- 守阵: node 电池等价性探针(`tests/test_webui_static_r4_node_batteries.py::test_r4_dt_table_layout_geometry_equivalence`, 13 表 136 列 + colWidths 五类场景, 断言现役拼轨 ≡ DT_TABLE.layout 输出) + e2e `dt-table-layout-parity.spec.mjs`(语义 = **钉住单点输出不变**)与 `dt-table-face-bg.spec.mjs`。

## 部分组操作预警 (webui/static/shared/selection.js + delete_flow.js + drawer.js)

- **判定/聚合双单点**(计划 plans/26-11-11-0820-plan-webui-partial-group-warning.html, 拍板 D2): 「辅种组只被选中一部分」的唯一判定点 `selection.js::_partialGroupsOf(keys, hashes)` → `[{key, name, sel, total}]`(真实组 `!virtual` 且 `total>1`: 有成员命中 ∧ 组键不在 groupKeys ∧ 未全选; hash→组反查走 decoratedGroups, 与 `_findGroup` 同源, 不得 filteredGroups 独走) + 展示聚合单点 `_partialGroupsSummary(partials)` → `{names, sel, total, gap}`(组名上限 3 个 +「等 K 个」)。消费方不得另写判定/聚合。
- **三落点**(删除链/移动链共用上述单点): ① 删除确认框 `_deleteDetails` 末尾恒显行(tone error, D5 —— 与「同时删除磁盘文件」勾选无关恒显, 文案钉住词「将缺文件」); ② 设定位置迁移关提交前确认框(`drawer.js::_partialMoveConfirmGate`, error + danger 钮, 确认才发, 拍板 D3); ③ 迁移开披露条(`move-dialog.html` 内嵌, tone warn, 开框即见不加分步, 拍板 D4 —— 选 1 搬 N 由后端 `_buckets` 级联全组, 行为安全, 提交前醒目披露)。
- **R6 降级口径(解析不出不误拦)**: 谓词对缺失组数据空返回; 迁移关闸门 `flags.relocate_enabled === false` 严判、迁移开披露条 `=== true` 严判(旗标取不到一律降级为无提示/直发) —— 绝不因开框到提交之间的快照竞态阻断正常操作。
- **守阵**: `tests/test_webui_static_r4_node_batteries.py`(谓词五形态 + 三落点电池 + 对称单点锚); 文案钉住词「将缺文件」「整组迁移」双向钉住(reannounce-inactive-gate 同款纪律)。
- **后端纵深闸门**(issue issues/26-11-11-0823, 2026-11-12): `/api/torrents/bulk` 直发可绕过全部前端预警 —— 分派前部分组闸(谓词 `commands_torrents.py::_partial_groups_of` 为前端 D2 口径的**后端镜像**, 成员取 groups∩在册; 文案单点 `_partial_group_reject_msg` 与前端聚合同形)。**混合形态**(用户拍板): delete×delete_files×部分组 fail-closed 硬拒(confirm 不释放); 迁移关 location 无 confirm 拒单、**confirm=true 放行**(声明位幂等, 与整组迁移 confirm 同范式但无服务端待确认状态; 前端 S3 确认框确认后 drawer.js `post(gated !== null)` 带上)。放行面: keys 覆盖全组/成员全选平铺/单成员组/未归组照常; 武装态在闸前分流(`_buckets` 级联全组无此洞)。后端守阵: `test_web_commands_bulk.py` 闸门电池 6 条 + dispatch 无 cmd_id 矩阵第 7 类。范围注记: rename-fs 端点防线不在本闸(issue 正文即范围), 仍待另案。

## 图形化配置编辑器 (webui/static/shared/ + config/writer.py)

- **前端持与磁盘同构的 YAML 树**(标量全为字符串, 与加载层 BaseLoader 语义一致): 编辑即就地增删改, 无格式往返转换零语义漂移; 脏检测用 JSON 快照对比。
- **保存管线(config/writer.py)**: 结构自检 → 落临时文件跑 `load_config`(**与启动同一校验路径**, 失败 400 不碰盘) → diff 判定 → R 级字段回退磁盘旧值 → 备份 → ruamel round-trip 写盘 → 投递 `reload_config` 命令(仍由主循环线程应用)。已存在键的注释保留; **值未变的键跳过赋值**(保留磁盘原标量形态); 列表整体替换。
- **保存后联动刷新只有一种做法: 投递命令, 不在端点里干活**(热重载后快照类数据要等下一轮 interval; 判定单点按配置指纹在 apply 前后各算一次, 不等即投刷新命令)。
- `config/schema/` 是纯声明的 UI 元数据(分组/字段/控件/单位/枚举/帮助), **不承载正确性** —— 合法性唯一入口仍是 `validate_config`。
- 字段渲染单点 `hub-field` 组件(嵌套 object 预先扁平化为带缩进的渲染项, 组件无需递归); 命名实体(站点/规则集/规则)增改删收敛为三个骨架 + 三份差异清单; **「不适用」整块隐藏 ≠「不可用」灰显**: 来源不支持 ⇒ 字段无意义整块不渲染; 功能开关关 ⇒ 灰显但仍可编辑(先把参数配好, 开回即生效)。
