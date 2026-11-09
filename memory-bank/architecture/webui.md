# WEB UI 运行时

> 摘要: FastAPI 装配单点与启动 fail-fast、皮肤目录即 URL 与静态契约、线程边界(读快照 + 投命令)、视图发布与版本门控、truth 通道、响应性设计要点、表格几何单点(dt_table)、图形化配置编辑器骨架。
> 触发: WEB UI, webui, FastAPI, create_app, 路由, 皮肤, 静态, 线程边界, 视图发布, group_view_ver, truth, 回执, 乐观 UI, 响应性, 窗口化, 表格几何, dt_table, DT_TABLE, columns_grid, gridTemplate, 配置编辑器, schema, writer

## 装配单点与启动 (webui/server/factory.py, webui/module.py)

`create_app` 是纯组装壳, 装配顺序固定: 鉴权依赖(全局 dependencies 单点, 所有 `/api/*` 经 Bearer 密钥) → FastAPI 实例(docs/openapi 关) → 按域 Router(`routes/ROUTE_BUILDERS` 固定顺序) → 静态挂载(最后 —— mount "/" 是兜底路由)。端点定义一律在 `routes/` 各模块, 工厂禁内联路由(守阵钉住)。**启动期监听失败 = fail-fast**(plans/26-11-03-0930-plan-webui-bind-fail-fast.html): 模块 start 拉起服务后检查 handle.started, 失败先落 INFO 诊断块(原因/占用者/处置, **只进日志** —— 绝不进异常消息/stderr), 再抛 `WebUIBindError` → CLI 单行 stderr、退出码 1、无堆栈; 低层 `start_web_server` 保持「返回 handle」契约(热重载复用, 不在那里抛)。热重载 apply: 有差异即置脏, **仅「监听身份」(enabled/host/port)变化才重启服务器**; 主循环每轮钩子(消费命令/刷新视图/落回执)经宿主按装配序调用。

## 皮肤目录即 URL 与静态契约 (webui/server/static_ui.py)

`webui/static/<名>/` 一个目录 = 一套皮肤(atlas 星图 / prism 棱镜 / console 控制台 / flux), `shared/` 是公共逻辑层、`fx/` 是动效库 —— **新增 UI = 新增目录, 零后端改动**。根路径按 cookie(`shared/boot.js` 写入)307 直达「上次使用的 UI」(服务端只认形状合法且 index.html 真实存在的值, 挡路径逃逸), 失效回落默认; 旧 `/newui` 书签 307 到 prism。**静态契约**: 非 /api 响应一律 `Cache-Control: no-cache` —— 浏览器仍缓存但每次带 ETag 协商(未变更 304), 否则升级后浏览器自缓存数小时, 界面「改了没变」。

## 线程边界 (webui/runtime.py, WebUIRuntime 门面)

- **Web 线程(uvicorn)只做两件事**: 读只读快照 + 经 `post_command()` 投递命令; 暂停/开始/删除/热重载等写操作全由主循环命令线消费 —— 单一写线程约束不变, Web 线程不碰 store/队列/state_file。
- 表现层状态(视图快照/版本号/脏标记/回执/搜索索引/命令队列)全部在 `manager.web`; 核心域 → 表现层单向通知(`mark_dirty`), 表现层 → 核心域只有一条回调(写能力 + 视图构建器)。
- **视图快照主循环发布**(持 view_lock 一次性替换全部视图 + 版本号), Web 线程只读; **「同轮发布」是硬约束**: 各视图共用一个版本号, 任何一份漏建或跨轮混拼, 前端都会把陈旧数组当新数据换上去。

## 视图发布与 truth 通道

- **版本门控**(等价 qB 的 rid): `group_view_ver` 每次重建自增; `ensure_state(rid, view)` 版本一致**不回传任何数组**(响应趋近零, 恒回 status 标量与 traffic/server 快照); **按视图回传**(指定视图只回该视图数组, 单点 `views_common.py`); 切视图前端置空 rid 强制取一次全量。
- **命令回执**: 每个 `_cmd_*` 是一次 qB 写操作, 由门面在主循环线程分发执行; 回执(cmd_id → status/wait/exec/truth)暂存, **每轮收尾 `flush_truths()` 无条件落**(异常路径兜底)。
- **命令唤醒**: `wake()` 只触发消费命令**不触发 tick** —— 否则每 tick 任务数上限的速率语义失效, 且自投递命令会自激循环(自投递走白名单)。

## 响应性设计 (plans/26-09-19-1241-webui-responsiveness-plan.html)

总原则: **感知延迟与真实延迟分开治** —— 「不跟手」主因是沉默(点击后无反馈), 收益最大的是乐观 UI, 后端加速只负责把真值对齐压到百毫秒级。

- **乐观 UI 只做白名单(pause/resume)**: 补丁**先于 POST** 贴上(放 await 之后 = 押在网络往返上); **3s 兜底显式回滚到补丁前值**(光删补丁记录不叫回落 —— rid 未变时服务端不回传数组, 行对象不被替换, 补丁值会永久留在行上); **真值匹配即清必须比服务端快照**(比行上的当前值 = 跟自己比, 首轮必假匹配); 只认本轮 payload 真带了的 hash; 失败立即回滚。
- **命令后补刷新走完整同步**(只 apply 增量会留半刷新态), 整批命令 drain 完只补一次; qB 受理(HTTP 200)≠建好, 另有**有界追平**: 登记期望 hash, 同步线提前 +80ms 再问(≤3 次/TTL)。
- **行窗口化只减 DOM 行数不改布局模型**(上下占位撑高度, 列对齐与列宽协议保持有效); 行高逐行实测 + 前缀和 + 二分(行高不齐, 等高假设会漂); 展开的组在可见集合里时窗口退避全量。
- **搜索索引**: 种子名匹配即时扫 store, 文件列表匹配靠索引(文件 API 只在主循环线程); 按 hash 增量维护 + 单次限流预算, 未拉完下一 tick 续建。
- 前端纪律: 页面隐藏停轮询恢复即刷; setTimeout 链式续排不堆叠请求; **只做失败退避**, 不做「无变化退避」。

## 表格几何单点 (webui/static/shared/dt_table.js + columns_grid.js)

- **`DT_TABLE.layout()` 是全仓表格几何字符串(轨道串 / aligns)的单一生产者**(计划 plans/26-11-10-0027-plan-dt-table-wiring.html, 2026-11-10 接线): `columns_grid._gridTemplate` 与 `colAlignCss` **内部委托**该单点取轨道串与对齐, 旁路拼接已删; 调用方(主视图 computed + 抽屉桥)与 DOM 零改动, 全部表格面(含主列表、含 flux)同一链。新增/改表格几何逻辑只改 dt_table.layout 一处 —— **禁止再造平行计算**。
- **`assertLayout()` 常驻生产渲染自查**(拍板 D3): 三处 O(1) 计数(grid 轨道数 / 列头格数 / 首行子格数), 不一致 `console.error`(含 tableId 与三方计数)**不打断渲染**(保守默认); 未挂载豁免。
- **D4 例外清单(明文化)**: HR 三表(hrDetail / hrWave / hrKv, 无 tpl/align 字段)+ 04 卡片形态面不接几何单点; 守阵钉「清单之外零旁路」。HR 三表统一交互(拖宽/拖序/右键隐藏/持久化)为第二轮立项(拍板 D7, 方向迁 aq-table grid 链路), 届时补 tpl/align 字段后纳入同一单点。
- 守阵: node 电池等价性探针(`tests/test_webui_static_r4_node_batteries.py::test_r4_dt_table_layout_geometry_equivalence`, 13 表 136 列 + colWidths 五类场景, 断言现役拼轨 ≡ DT_TABLE.layout 输出) + e2e `dt-table-layout-parity.spec.mjs`(语义 = **钉住单点输出不变**)与 `dt-table-face-bg.spec.mjs`。

## 图形化配置编辑器 (webui/static/shared/ + config/writer.py)

- **前端持与磁盘同构的 YAML 树**(标量全为字符串, 与加载层 BaseLoader 语义一致): 编辑即就地增删改, 无格式往返转换零语义漂移; 脏检测用 JSON 快照对比。
- **保存管线(config/writer.py)**: 结构自检 → 落临时文件跑 `load_config`(**与启动同一校验路径**, 失败 400 不碰盘) → diff 判定 → R 级字段回退磁盘旧值 → 备份 → ruamel round-trip 写盘 → 投递 `reload_config` 命令(仍由主循环线程应用)。已存在键的注释保留; **值未变的键跳过赋值**(保留磁盘原标量形态); 列表整体替换。
- **保存后联动刷新只有一种做法: 投递命令, 不在端点里干活**(热重载后快照类数据要等下一轮 interval; 判定单点按配置指纹在 apply 前后各算一次, 不等即投刷新命令)。
- `config/schema/` 是纯声明的 UI 元数据(分组/字段/控件/单位/枚举/帮助), **不承载正确性** —— 合法性唯一入口仍是 `validate_config`。
- 字段渲染单点 `hub-field` 组件(嵌套 object 预先扁平化为带缩进的渲染项, 组件无需递归); 命名实体(站点/规则集/规则)增改删收敛为三个骨架 + 三份差异清单; **「不适用」整块隐藏 ≠「不可用」灰显**: 来源不支持 ⇒ 字段无意义整块不渲染; 功能开关关 ⇒ 灰显但仍可编辑(先把参数配好, 开回即生效)。
