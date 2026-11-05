# WEB UI 线程模型

> 摘要: Web 线程与主循环的边界与协作 —— 线程模型 / 热重载重启 / 视图门控 / SSE 推送。热重载、惰性组装、rid 增量同步、SSE、前端筛选、HR 派生值、错误原因与流量快照细节已外迁到 `attachments/web-runtime-details.md`。
> 触发: WEB UI 线程, webui, 线程模型, 主循环解耦, SSE

## WEB UI 线程模型 (webui/runtime.py + webui/server/)

- **Web 线程(uvicorn 独立线程)只做两件事**: 读只读快照(`manager.web.*` 的视图/流量快照与 `status_snapshot`)与经 `manager.web.post_command()` 投递命令 —— 暂停/开始/汇报/删除/热重载等写操作全由主循环 `host.run_command_line()` 消费执行(单一写线程约束不变); Web 线程不得触碰 store/队列/state_file。**表现层状态归 `WebUIRuntime`**(2026-09-20 起): 视图快照/版本号/脏标记/活跃心跳/回执/搜索索引/命令队列都在 `manager.web`(`webui/runtime.py`); **旧字段名转发层已随别名层处置 W3 整体退役(2026-10-01)** —— 反复活守阵 `tests/test_qbmanager_alias_freeze.py`, 新旧代码一律写 `manager.web.<新名>`。
- **启动期监听失败 = fail-fast(plan 26-11-03-0930, 2026-11-03)**: `WebUIModule.start`(`webui/module.py:137-153`) 在 `web.start_server()` 返回后检查 `web.handle.started`; 失败即先落 INFO 诊断块 `WEB UI 启动失败诊断`(原因 / 占用者 / 处置 / 退出), 再抛 `WebUIBindError(AutoQbError)`。单行消息由 `_bind_message`(`webui/server/lifecycle.py:34`) 生成, 用配置原值给 `web.enabled`/`web.host`/`web.port` 键路径; `AutoQbError` 通道 ⇒ CLI 退出码 1 + 单行 stderr + 无堆栈。低层 `start_web_server` **保持「返回 handle」的原契约**(热重载 `apply` 复用, 不在那里抛)。占用者诊断来自 `infra/port_owner.describe_port_owner`(三态 found/absent/unavailable、总预算 1.5s、任何异常降级), **只进日志** —— 绝不进异常消息 / stderr / `notify_fatal`; 命令行截断 160 字符且换行压空格。`qbmanager.run` 的 `start_all` 在 try 内 + `lifecycle_ready` 闸门, 锁与 `state.lock.meta.json` 在任何路径都释放(见 [main-loop.md](main-loop.md))。
> 已外迁: 热重载重启 WEB 服务 → [attachments/web-runtime-details.md](attachments/web-runtime-details.md)
> 已外迁: 惰性组装 + 活跃窗口 → [attachments/web-runtime-details.md](attachments/web-runtime-details.md)
- **视图版本门控 (等价 qB 的 rid)**: `group_view_ver` 每次重建自增; `ensure_state(rid, view, delta)`(`webui/runtime_views.py:604`)在 rid 与服务端版本一致时**不回传任何数组**(响应体趋近于零), 仅回 status(标量 + `traffic` 与 `server` 快照, 与版本无关恒回传 —— `server` 即 `store.server_state`, 状态栏常显统计与"限制速度"的数据源)。**按视图回传**: `view` 指定当前视图时只回传该视图需要的数组(`VIEW_ARRAYS`, 单点 `webui/views_common.py:111`), 响应体降到约 1/4; 四视图共享同一版本号, 切视图时前端把 lastRid 置空强制取一次全量。`/api/state?rid=` 暴露该语义, 前端据此跳过整表替换与重渲染。前端另配: 页面隐藏(`document.hidden`)停轮询、恢复即刷; `setTimeout` 链式续排(不堆叠请求); **只做失败退避**(`pollFails` 翻倍至 15s 上限), 不做"无变化退避"。rid 之上叠加的增量载荷协议见下一节。
> 已外迁: rid 式增量同步 S1-S10 → [attachments/web-runtime-details.md](attachments/web-runtime-details.md)
> 已外迁: 事件推送 (SSE) → [attachments/web-runtime-details.md](attachments/web-runtime-details.md)
- **搜索索引 `search_index` (hash -> {name, files}, `webui/runtime.py:147`)**: 种子名匹配即时扫 `store.by_hash`(无 API 开销), 文件列表匹配依赖索引(文件 API 只在主循环线程, 种子记录 `_files` 缓存跨 tick 复用)。索引按 hash **增量**维护: 已建条目只刷新名称(不重拉文件), 新种子补拉, 已删种子淘汰; 单次限流 `SEARCH_INDEX_BUILD_BUDGET`(500, 常量 `webui/views_common.py:13`)条, 未拉完保持 `search_index_dirty=True` 由下一 tick 续建, 前端据 `building` 每 1s 自动重查。
> 已外迁: 搜索结果是辅种组的筛选 → [attachments/web-runtime-details.md](attachments/web-runtime-details.md)
> 已外迁: 前端筛选/列/右键 → [attachments/web-runtime-details.md](attachments/web-runtime-details.md)
- **视图含“由配置派生的展示值”(2026-09-14)**: 成员视图除原始快照值外, 还透出 HR 展示字段(**由 `webui/views.py` 的 `hr_view_fields` 在视图装配期统一计算**, `webui/views.py:293`; 宿主上的同名旧方法已随内核化重构 + 别名层处置退役):
  - `hr_tag`/`hr_tag_done`: 已触发 HR 未达标 / 已达标时应有的**标签文本**(供前端把 HR 标签分别着成鲜亮/镇静两色) —— 经 `utils.replace_vars` 展开(`${required_seeding_time}`), 与真正写入 qB 的标签逐字相等(前端只需文本匹配)。
  - `hr_triggered`/`hr_satisfied`: 本机下载条件满足(**纯本地展示辅助**, 26-09-30-0559 起只用于区分「本机下载 vs 疑似辅种」, 不再表达管束语义) / 是否已达成要求(前端 H&R 栏与对照列着色的依据)。字段全集另含 `hr_excluded`(排除表命中)与站点侧三态/安全档位/站点值(`hr_state*`/`hr_safety*`/`hr_site_*`), 单点见 `webui/views.py:293` docstring。
  - `hr_req_time`/`hr_req_ratio`: 要求做种时长(= required + extra)与要求分享率(0 = 不要求); 供明细表显示 `实际 / 要求` 并**按列各自的要求**决定是否着色(未配要求的列必须保持中性色)。
> 已外迁: HR 判定委托与派生值置脏来源 → [attachments/web-runtime-details.md](attachments/web-runtime-details.md)
> 已外迁: 错误原因派生展示值 → [attachments/web-runtime-details.md](attachments/web-runtime-details.md)
- **流量/限速只读快照 `traffic_view`(2026-09-14 立, 26-10-18 拆段)**: 快照**不是**某一个任务独占的 dict, 而是两个模块各写一段的**段级契约**(计划 26-10-18-0813 D3/D8/D10; 单一写入点仍是 `ctx.web.set_traffic_view`, `webui/runtime_stream.py:180`) ——
> 已外迁: 流量/限速快照来源段、限速段与结构 → [attachments/web-runtime-details.md](attachments/web-runtime-details.md)
