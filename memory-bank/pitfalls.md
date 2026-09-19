# Pitfalls — 陷阱、风险点与文档漂移 (改代码前必读)

> **如何读本文件**: "判别标准/规则"类条目是**常青约束**, 始终遵守; 带日期的条目是**历史事故记录** — 结论已沉淀为规则与测试 (括注的测试名为证), 叙事用于理解"为什么"。压缩本文件时只压叙事, 不删规则与判别标准。

## 🔴 生产文件, 禁止改动/提交

- **`config.yml`**: 用户真实生产配置 — 含真实 PT 站点域名、tracker 规则、qB 凭据引用。不是示例! 改示例用 `minimal.yml`/`test_yamls/`。
- **`auto-qb-data/state.json`** (2026-09-09 改: 运行时文件集中到 auto-qb-data/ 数据目录): 运行中程序的状态文件, 程序退出时覆写。改它毫无意义且可能破坏运行。锁文件 `<state_file 去扩展名>.lock` (`auto-qb-data/state.lock`) 与伴生 `.meta.json` 也在同目录; 日志在 `auto-qb-data/logs/auto-qb.log`, 跳检备份在 `auto-qb-data/skip-check-backup/`, 均落在此数据目录下。
- 两者均已 gitignore, 但在工作区可见 — 不要"顺手"格式化/重排它们。

## ⚠️ 高风险业务操作 (代码中已有防护, 改动时不得削弱)

1. **跳检 (skip-checking)**: 删除种子→重加, 丢失统计 (下载量/上传量/做种时长/分享率); 内容错误会传垃圾数据 (PT 站严令禁止)。防护 (2026-09-05 审计加固后): ①部分下载 (0<progress<1) 拒绝跳检 (预分配零块会被标记有效上传, fail 提示改 full-checking) ②同规则同日去重 + **跨规则**同日去重 (`skip_check_day`, 统计只丢一次) ③强制 filelist 前置检查 ④重加前轮询确认种子已从客户端消失 (qB 删除异步, ≤5s; 未消失放弃, 种子还在无损失) ⑤重加属性**直传** (0/负值有语义, 不得 `or None` 吞掉) + contentLayout 由 content_path/save_path/文件列表推断 (布局错位不自愈) ⑥无参考 warning ⑦重加失败 .torrent 落盘备份且**元数据立即落盘**。跳检过程中种子会从 store 消失 (`remove_torrent`) — 该种子同 tick 内的后续动作必须容错 (历史 bug: commit e5ea9e7, 测试 test_checking.py 覆盖)。
2. **reannounce 动作**: 已加运行时保护 (2026-09-05): 同种子最小间隔 10M(state `reannounce_ts`) + 暂停种子跳过 + 加载期未配去重 WARNING —— 但高频汇报本质上仍是高风险操作, 规则应配 execute_once。
3. **qB 版本兼容**: `_refresh_torrents` 首次拉到种子信息时校验 `REQUIRED_TORRENT_FIELDS`(24 个 = 快照 18 + 跳检重加 6, 见 torrents.py `_SNAPSHOT_FIELDS`/`RE_ADD_FIELDS`), 缺失抛 `QbCompatError(AutoQbError)` → CLI 干净退出 —— 快照字段缺失会**静默零值**(规则基于假数据决策), 比崩溃更危险 (qB 5.0 preferences 键漂移前科)。
4. **`or 默认值` 掩盖数值字段** (2026-09-06 清理): `progress or 0.0`/`ratio or 0` 类写法把上游 bug 静默转为合法语义且方向可能朝危险侧 (progress=None → 视为全新辅种 → 放行跳检)。已清理: 闸门 0/_skip_gates/HR 判定 4 处。**保留的合法 `or`**: 空串/空容器归一化 (category/tags/API 边界) 与除零防护 (`total_size or 1`)。判别标准见 conventions.md。
5. **死防御清理** (2026-09-06): 同型问题扩展至 `is None`/`getattr` 默认 —— 已删: client setter 的 store/api 守卫、`_execute_full_checking` 的 task_queue None 退化分支、`getattr(task, "resume_index", None)`/`getattr(prev, "is_uploading", False)` 冗余默认(含 2026-09-06 二次复查补删的 grouping 上传转暂停判定)、`_valid_for_representative` 中恒真的 MOVING 显式排除(MOVING 本就不在 is_complete/is_uploading 集合)、QbApi 的 `store=None` 可选形态与 15 处 `if self.store is not None` 守卫 (store 改必传, 见 06 可测试性原则)。**合法 None 保留**: 惰性缓存、运行时状态 (种子被删/外部入口)、功能开关。判别标准: 守卫的条件在正确上游流程下**不可能发生** → 删; 是真实可选语义 → 留。
6. **自有动作污染状态观测** (2026-09-06): 自家整组停种 (大小一致性/下载冲突) 经 QbApi 快照同步**当场改写 `by_hash` 的 state**, `_handle_state_transitions` 若在自有动作之后运行, 会把自家停种误判为外部"上传转暂停" → 多余的缺文件扫描 (曾靠代表种 is_uploading 过滤掩盖, 代表种放宽为 is_complete 后暴露)。修复: refresh 中状态转移观测移到新增归组等自有动作**之前** (轮次开始的干净观测点), 顺序约束见 systemPatterns.md。
7. **删除种子** (`QbApi.torrents_delete`, qbapi.py): 仅跳检流程使用, `delete_files=False` 固定。
8. **限速不覆盖手动值**: 奇数 KiB 视为用户手动设置则跳过 — 判定统一走 `utils.is_manual_speed_limit`, 三个调用点 (`mixins/tracker.py` 单种限速 / `rules/actions/transfer.py` 限速动作 / `mixins/speed_curve.py` 全局曲线) 逻辑必须保持一致。

## ⚠️ 平台/API 兼容陷阱

- **锁文件残留随平台不同** (2026-09-10): `locking.py` 的 `release()` 只无条件删除伴生 `meta.json`, 锁文件 `state.lock` 的删除交给 `filelock` 底层 — Windows(msvcrt) 释放时删, POSIX(flock) **不删**(flock 标准语义, 删锁文件反而不安全)。因此 Linux CI 上 `release()` 后锁文件残留是正常行为, 测试按 `os.name == "nt"` 分平台断言, 不是代码 bug。
- **qB 5.0+ 全局限速**: 必须走 `transfer_upload_limit`/`transfer_set_upload_limit` 端点 (bytes/s, 0=不限)。旧 `app.preferences` 的 `upload_limit/download_limit` 键**已静默失效** (历史 bug, commit f402eaf)。qbittorrent-api 新版 `app.preferences` 是 property 不是方法 (commit be0911b)。
- **qB 状态枚举**: 用 `qbittorrentapi.TorrentState` 枚举属性 (`is_stopped` 等) 判定, 不要比较 state 字符串 (pausedUP vs stoppedUP 跨版本差异)。
- **`/api/v2/sync/maindata` 是增量接口, 响应不是全量** (2026-09-13): rid 与上次一致时只回**变化种子的变化字段**(qB 端 `processMap` 逐字段 diff), **未变化种子完全不出现在响应中**; 删除的种子列在 `torrents_removed`(哈希列表); 新增种子(基线缺失)回全量字段; rid 不匹配/为 0 时 `full_update=true`(自愈信号, 漏 tick/qB 重启都只退化成一次全量)。**因此绝不能把单次响应当成种子全集** —— `TorrentStore._apply` 必须区分 full(以响应为全集)与 delta(只改 `patches` 中的记录, 删除以 `torrents_removed` 为准)。❗ **全量轮不可早退**: `full=True` 时即使 `patches` 为空也必须走完(需检测删除), 只有增量轮才能因无变化提前返回。
- **sync 响应的 hash 是 `torrents` 字典的键, 值内不含 hash** (2026-09-13 生产崩溃实锤): 与 `torrents/info` 的**数组元素**(每个含 `hash` 字段)不同 —— 直接把 `torrents[h]` 当校验样本会报 "缺少字段: ['hash']" 并抛 `QbCompatError`(启动即退出)。校验前必须补齐 `{**patch, "hash": h}`(`TorrentStore.apply_sync` 已做)。**测试替身同样不能在值里塞 hash**, 否则会掩盖该 bug(`helpers._torrent_fields` 已排除 hash 以对齐真机)。
- **sync 与 `torrents/info` 字段齐平**(同一 C++ 序列化器 `serialize/serialize_torrent.{h,cpp}`, sync 仅额外移除 `"id"` 键): 所以 `REQUIRED_TORRENT_FIELDS` 可直接用于 sync 响应; 但**只能在全量轮校验** —— 增量响应只含变化字段, 做字段存在性校验必误报缺失(已由 `store.need_validate` 闸门隔离)。校验样本是 **qB 原始字段映射(dict)** 而非记录对象, 故 `missing_torrent_fields` 必须同时支持映射(按键判定)与对象(`hasattr`); 否则 dict 样本会被全部字段报“缺失”。
- **sync 端点不可降级为“少几个字段”**: 旧版 qB 无该端点时抛 `NotFound404Error`(qbittorrent-api 对未知 API 方法), 测试替身缺方法时抛 `AttributeError` —— `TorrentStore.apply_sync` 只捕获这两类并降级 `torrents_info()`(一次性 WARNING), **其它异常(网络等)rid 归零后原样上抛**, 否则会掩盖断连/鉴权失败。
- **`TorrentRecord` 是唯一数据所有者, 不要再引入投影视图** (2026-09-13 性能修复): 曾用 `SyncTorrent(Mapping)` 做一层"基线字段视图"给 `update_from` 读, 结果把热路径从 ~21 次 C 级调用放大到 ~80 次 Python 调用(py-spy: `_collections_abc.get` 占 26% total, `update_from` 14%)。现改为: 快照字段直接存 `TorrentRecord` slots, 非快照字段(RE_ADD_FIELDS)存 `_raw` + `__getattr__` 兜底, `apply_delta(patch)` **只遍历 patch 的键**。新增字段时: 快照字段加进 `_SNAPSHOT_FIELDS`, 其余进 `_raw` 自动生效。
- **`apply_delta` 返回变化字段集而非 bool**: 下游靠它把 O(N) 扫描降为 O(变化数)(`delta_fields`/`state_changed`/`dirty_groups`)。注意变化集对**视图字段按 `_VIEW_QUANTUM` 量化后比较** —— 故 `seeding_time` 秒级递增不会出现在变化集里(它仍会写入 slot); 而非视图字段(如 `downloaded`)值不同即计入。
- **`dirty_groups` 跨轮累积, 不能用 `_apply` 清空**: 轮次外的写操作(Web 命令/任务队列/自有停种)发生在 `_check_download_conflicts` 之后, 登记必须保留到下次检查。`_check_download_conflicts` 取出并复位; `store.rounds_applied == 0`(直接驱动该方法的白盒测试/外部调用, 无变化集)时**退回全量扫描**以保证正确 —— 改这个方法时不要去掉该兼容分支, 否则 `test_checking`/`test_grouping` 的直接调用测试会静默不再暂停。
- **主循环节流不得依赖 `stop_event` 是否存在** (2026-09-14 实锤回归): `run()` 的每轮节流必须经模块级 `_throttle(stop_event, main_tick)` —— 非托管(CLI 默认 `stop_event=None`)`time.sleep`, 托管(`--tray`)`Event.wait`。曾写成 `if stop_event is not None and stop_event.wait(main_tick)`: 非托管模式被 `and` 短路 -> **完全不阻塞 -> 主循环空转**(由 `begin_round` + `update_state_snapshot` 的每 tick 固定成本反推约 **2800 tick/s**, 为 `main_tick=2s` 的约 5500 倍; 实测假服务下 0.9s 内 1600 次 tick vs 修复后 6 次)。后果: CPU 打满一个核 + `sync/maindata` 请求量放大数千倍(连带 requests 每次请求的 netrc/代理/注册表解析一并放大; py-spy: `get_netrc_auth` 13%、`proxy_bypass_registry` 2%、`begin_round`/`update_state_snapshot` 各若干)。**托管模式反而会掩盖该 bug**(`wait` 真实阻塞), 故回归测试必须用**非托管模式**(`test_qbmanager.test_run_loop_throttles_without_stop_event` 断言 `time.sleep(main_tick)`, `test_local_qb_service.test_main_loop_throttled_by_main_tick` 用真实 HTTP 计 tick 数)。另: 首连失败重试循环的 `stop_event is None or stop_event.wait(main_tick)`(非托管直接返回)是**有意语义**, 与主循环节流不是一回事, 不要一并改。
- **本地 qB 关闭 requests `trust_env`** (2026-09-14 修为真正生效): 本地地址经 `qbmanager._new_client()` 构造 **`LocalQbClient`**(`Client` 子类, 覆盖 `_session` property, 在返回前强制 `trust_env = False`), 跳过每请求 `get_environ_proxies`/`get_netrc_auth`(实测 0.276ms -> 0.043ms/请求); 远程域名用原生 `Client` 保留默认(企业代理/netrc 需求)。
  - ❗ 旧实现 `client._session.trust_env = False` **从未生效过**: 库的 `Request._session` 是**只读 property**, 且 `build_base_url()`(首次请求)与 `_initialize_context()`(登录过期/qB 重启)都会调 `_trigger_session_initialization()` **丢弃并重建 Session** —— 设置在下一次访问时就被一个默认 Session 取代(实测: 赋值 -> 触发重建 -> 回 `True` 且对象已换)。改造后 `super()._session` 每次返回前重新赋 False, 故对任何时刻新建的 Session 均生效。
  - 验证方式(不回退): `test_qbmanager.test_new_client_local_disables_trust_env`(显式 `_trigger_session_initialization()` 后仍为 False)与 `test_local_qb_service.test_local_request_skips_env_and_netrc_lookup`(真实请求期间 patch 两个解析函数断言 0 次调用; 另有原生 Client 对照组确保测试有区分力)。
  - 本地判定取 `config.qbittorrent.base_url` 解析后的 **hostname**(`_is_local_qb`), 所以 `localhost`/`[::1]`/带端口写法都认得。
- **Windows 长路径**: 磁盘文件检查过 `add_long_path_prefix_for_win` (`\\?\` 前缀), 新文件访问要走同一工具。
- **`yaml.BaseLoader`**: 配置全是字符串; 写解析时不要假设 YAML 已给原生类型; 空 `trackers:` 段会解析成 None/str, 已有 `isinstance` 防御, 新增类似段同样要防。

## ⚠️ 行为细节 (易误判为 bug)

- **奇数限速保护**: `(current_limit / 1024) % 2 == 1` → 跳过。这是特性不是 bug; 相关测试断言"奇数不覆盖"。
- **interval 归一化**: `Task.interval <= 0` → 1s (每 tick 级别); 规则 interval 为 0 表示每轮执行。
- **`handled` 返回值**: `Rule.process` 返回 `not result.is_skipped` — 最后一个动作 skip 时 handled=False, 但**执行历史已记录** (只要前面动作成功过)。设计如此, 勿"修复"。
- **上传增量下限 0**: `upload_delta = max(0, uploaded - baseline)` — 种子重加/客户端重启后 uploaded 归零不会产生负增量。
- **缺文件扫描/参考种子的代表种已分化** (2026-09-12): 缺文件扫描代表种 (`_valid_for_representative`) 从 `is_complete 且非 checking/errored` 放宽为 **`is_complete or is_errored 且非 checking`** — 代表种只提供 save_path(组内共享)与缓存文件映射, errored(missingFiles)成员两者有效且恰是缺文件第一现场, 排除它会导致全组同轮 errored 时无法扫描; 参考种子候选 (`_group_reference_candidates`, 供跳检参考) 仍只从 `is_complete 且非 checking` 选, 两者别混。
- **MISSING 组豁免 mixed 冲突是有意设计** (2026-09-12): `_check_download_conflicts` 的 n_done 不计带 `missing_tag` 标签的完成成员 — 缺文件组被标记后用户重新下载是合法补救, 不应被"已完成与下载中并存"拦停; multi-dl(两个同时下载写同一物理文件)不豁免。健康组(成员无 MISSING 标签)行为不变。另: 重校验发现文件缺失(stalledUP→missingFiles)现与"上传转暂停"同为缺文件扫描触发路径, 修复了"校验发现缺失不触发、组继续假健康做种、用户重下又被 mixed 拦"的链式问题; MISSING 标签无自动清除逻辑, 文件补齐后需手动摘标签。
- **tracker 匹配是"第一个命中"且已统一为 hostname 精确匹配**: `_match_tracker_conf` 复用 `utils.match_tracker_confs` (精确/子域名匹配, 与规则绑定同语义), 取第一个匹配配置, **命中多个配置时打 ERROR 日志**(仍用第一个, 不跳过种子); 导出模板 `find_missing_domains` 仍用包含关系匹配 (有意宽松, 用于找未配置域名)。
- **`RuleContext.torrent` 的 snapshot 回退是合法语义, 非死防御**: `ctx.torrent` 实时 `store.get(hash)` 优先, 种子已从客户端删除 (`on_torrent_deleted`, store 已移除) 时回退 `RuleContext.snapshot` 删除前快照副本。这是真实可选语义 (种子被删的合法现场), 与 死防御清理 (点5) 中"条件在正确上游流程下不可能发生 → 删"的判别不冲突。供 `print_torrent_details` 只读留档用; 需活种子的动作在 config 白名单阶段已被 `on_torrent_deleted` 拒绝。
- **WEB UI 搜索结果是真实辅种组的筛选, 不是另建虚拟分组** (2026-09-13): 前端用后端返回的命中 hash 集合过滤 `sortedGroups` —— 任一组员命中即保留**整组**(组行沿用真实组 key → 组级操作可用), 仅命中成员 `search-hit` 高亮。**未归组**的命中种子(分组未启用/文件列表不可读)以单种子虚拟行(前端 key `u-<hash>`)兜底展示, **虚拟行不是真实组 key**, 前端右键必须退化为单种子菜单 —— 否则 `/api/groups/u-xxx/action` 走 `decode_group_key` 解析失败直接 500。**初版 bug 教训(必修)**: 搜索结果容器曾被写成 `v-if="!searchQuery"`(误以为搜索时该隐藏), 结果输入关键字后整个结果区连同"无匹配种子"提示一起被隐藏, 表现为"搜索无结果/明显词无匹配"但后端逻辑完全正常 —— 搜索结果必须渲染在**始终存在**的容器内。判别法: 搜索类 bug 先分清"后端无匹配"还是"前端未渲染"(后者看容器 `v-if` 与空态提示是否也被藏)。
- **搜索索引的脏标记与构建语义** (2026-09-13): `_search_index_dirty` 仅在种子集变化(added/removed)时置脏, **不在每 tick 重建**; 构建单次限流 `SEARCH_INDEX_BUILD_BUDGET` 条, 因此 `building=True` 可能跨多轮, 前端据 `building` 每 1s 自动重查直至消除。qB 断开(`self.client is None`)时必须中止构建**并保持脏** —— 不得把空文件列表当成“已建完”, 否则文件搜索会长期空结果直到下次种子增删(该分支已单测覆盖)。
- **同一份视图脏标记被两条重建路径共享时, 两条路径的**重建范围**必须完全一致** (2026-09-18, 症状"WEBUI 种子速度刷新慢但状态栏正常"): `_group_view_dirty` 由主循环 `_tick` 与 Web 线程 `ensure_group_view` 共享, 但主循环曾**只** `_build_group_view()` 就把标记清掉 ⇒ 会重建 `singles`/`shows`/`flat` 的 Web 线程兜底分支永不触发 ⇒ 这三份视图长期停在旧快照, 而 `_group_view_ver` 照常自增 ⇒ 前端判 `updated=true` 把**陈旧数组整表换上去**。状态栏"速度合计" = `Σ groups[].dlspeed`, 恰恰是主循环唯一在重建的那份 ⇒ 永远新鲜 —— **同一屏"新鲜的速度合计 + 陈旧的种子行速度"就是这个机制的指纹**。**修法**: 视图重建收敛为唯一入口 `WebviewMixin.rebuild_views()`(四视图 + 版本号 + 清标记一次完成), 两条路径都只调它, 新增视图也只能挂在这里(在调用点各建一部分必然再漏)。**同源第二坑**: 置脏语句写在 `if grouping.enabled` 块内而 `consume_view_changed()` 在块外 ⇒ 分组关闭时标记被吞、版本号不再变化 ⇒ 前端 `updated=false` 并退避轮询; 脏标记是**全部** Web 视图的共享状态, 与"辅种分组是否启用"无关(种子页平铺视图 / 未归组单种子 / 追剧视图都不依赖分组)。**判别法**: 版本号在自增但回传数组没变 ⇒ 该视图被饿死; 只 spy 某一个 `_build_*` 的用例会把缺陷**固化成预期行为**(原 `test_tick_rebuilds_group_view_only_when_changed` 就是), 断言必须写成"四份同次重建"。
- **前端不要用"视图版本号未变"当"数据没变"** (2026-09-18): `currentPollMs()` 曾按 `idlePolls`(连续 `updated=false`)把轮询退避到 5s/10s, 而状态栏全局速度走 `/api/stats`(`server_state`)**恒回传、不受 rid 门控** ⇒ 两个速度来源的刷新频率被解耦, 观感变成"状态栏正常、种子行滞后"。现改为**只保留失败退避**(`pollFails` 翻倍至 15s 上限), 间隔恒定: 版本未变时响应体本就趋近于零(不回传 groups), 退避省不下什么却直接牺牲行数据新鲜度。同时把 `server_state` 作为 `status.server` 并入 `/api/state`, 状态栏与行数据**同源同轮**, 每轮仍是 1 条请求(`/api/stats` 保留给统计面板手动刷新)。
- **分组视图"惰性组装"的脏标记必须精确, 否则惰性名存实亡** (2026-09-13): `_refresh_torrents` 曾**无条件** `_group_view_dirty = True`, 导致只要网页开着就每 2s 全量重建 group view + 全量 JSON 序列化 + 前端整表重渲染(种子库静止时也一样)。现改为 `store.view_changed` 仅在 `_VIEW_FIELDS`(name/save_path/state/dlspeed/upspeed/uploaded/size/progress/seeding_time/ratio)或组成员变化时置真, 由 `_tick` 消费判定。
- **`seeding_time` 必须按分钟量化, 否则惰性重建对做种库形同虚设** (2026-09-13): 该字段每秒递增, 而 PT 库里绝大多数种子都在做种 → 不量化时几乎每轮都置脏。现由 `torrents._VIEW_QUANTUM = {"seeding_time": 60}` + `view_field_value()` 统一向下取整(**重建判定与 `_build_group_view` 展示值共用**, 不能只改一处 —— 只改判定不改展示会让 UI 显示的秒数停留在上次重建时刻; 只改展示不改判定则永远重建)。前端 `fmtDuration` 同步去掉 <1h 的秒位。剩余每轮置脏的情形是**真在上传**的种子(uploaded/upspeed 增长), 这是真实数据变化, 属于预期行为。
- **WEB `/api/state?rid=` 的版本门控** (2026-09-13): `_group_view_ver` 每次重建自增, `ensure_group_state(rid)` 在 rid 一致时**不回传 groups**(只回 status)。前端靠 `updated` 字段决定是否整表替换 —— 若以后把其他会变的数据也塞进 groups 之外的字段, 要记得它们不受版本门控(status 是故意恒回传的 4 个标量)。前端适配: 换密钥/重新鉴权时须把 `lastRid` 置 null, 否则可能因版本碰巧一致而拿不到 groups 导致列表残留。
- **WEB 鉴权的空 Bearer 误报与日志分级** (2026-09-14): 前端 `api()` 无 token 守卫时会发出 `Authorization: Bearer `(尾随空格), 服务端 h11/httptools 按 RFC 裁剪字段值首尾 OWS 后收到的是裸 `"Bearer"`(len=6) —— 日志里"收到 'Bearer'(len=6) 期望 'Bearer xxx'(len=71)"就是这么来的, **与密钥正确、正常进入 WebUI 并存**(触发点: 登录框空提交; 以及 401 登出后 searchTimer/visibilitychange 的无守卫请求)。教训三条: ①前端**空凭证请求不出网**(`api()` 首行无 token 直接抛 auth 错, 调用方复用 401 处理路径), 空提交在 `saveToken()` 与表单(`required`/`:disabled`)双层拦截, 登出清理必须连同 searchTimer 一起停; ②后端缺省/畸形头(无头/裸 Bearer/错 scheme/空白 token)静默 401 —— 这类请求是常态, 记 WARNING 会经 notify.py 推系统 toast 扰民; 仅"携带了但错误"的密钥记一条不含密钥内容的 WARNING; ③Bearer 比较先解析 scheme 再用 `secrets.compare_digest`, 不要整串 `!=`。回归: `test_web.test_api_requires_token` 对 4 种畸形头断言无 WARNING、错密钥恰好一条 WARNING。
- **WEB 登录遮罩只能由"验证成功"放行, 不能由 token 赋值驱动** (2026-09-14): 错误密钥点"进入"会闪现主界面 —— 旧实现 `saveToken()` 同步 `this.token = 候选值`, 而遮罩门控是 `v-if="authRequired && !token"`: 候选值一赋值遮罩立即消失、主界面(含**上一会话残留**的 groups/status/settingsText)渲染一帧, 等 `/api/state` 401 回来 token 清空遮罩才恢复。修复后的鉴权状态机(安全为上): ①`this.token` 语义收窄为**已验证通过的身份**, 候选密钥只存 `pendingToken`; ②遮罩 `v-if="authRequired"` 单一门控, `authRequired=false` 是**唯一放行点且只在验证成功后**——成功前主界面 DOM 根本不创建(MutationObserver 实测错误密钥全程零渲染); ③401 收口于唯一 `_logout(msg)`: 遮罩 + 凭证 + localStorage + 轮询/searchTimer + **全部受保护数据**(groups/status/settingsText/搜索态/展开态)一并清空, 防内存视图残留; ④区分 401 与网络失败: 服务不可达不清凭证、给"重试连接", 401 才清; ⑤页面加载时 localStorage 密钥必须**重新验证**才放行(不再 token 非空即渲染)。教训一般化: 认证 UI 的渲染门控绑定"凭证变量"而非"认证结论", 任何异步验证窗口都会泄露受保护界面。
- **ruamel round-trip 写盘: 值未变必须跳过赋值, 否则标量会被加引号** (2026-09-14): 前端持有 BaseLoader 语义的字符串树, 若把每个键都重新赋值, ruamel 为"保持字符串类型"会把磁盘上原本无引号的 `port: 16585`/`enabled: true` 写成 `'16585'`/`'true'` —— 语义等价但文件可读性大跌。`writer._sync_mapping` 因此对**值未变化的键跳过赋值**(保留 CommentedScalar 原形态), 并对新增/修改的标量走 `_plain_scalar`(数字/布尔样式写为原生标量, BaseLoader 下语义等价)。比较必须按 BaseLoader 语义: round-trip loader 把 `true` 读成 bool `True`, 直接 `str()` 得 `"True"` 与树里的 `"true"` 不等 → 会误判"值已变"而重写整个标量(症状: 预览里所有布尔都变成 `'true'`), 故 `_as_builtin` 对 bool 统一小写化。**列表整体替换、项级注释不保留**是已记录的取舍, 不要为此改成逐项合并(会引入项级 diff 语义)。
- **图形化配置编辑器: UI 元数据与"配置键/插件"的漂移由守卫测试兜底** (2026-09-14): `config/schema.py` 是设置页表单的唯一描述来源(控件类型/分组/枚举/帮助/插件 spec 形态), 它**不承载正确性规则** —— 合法性唯一入口仍是 `validate_config`(保存时把树落临时文件跑 `load_config`, 与启动同路径; 失败 400 且不碰磁盘)。新增配置键必须同时登记 schema, 否则界面缺失该项; 忘记时 `tests/test_config_schema.py` 直接失败(顶层键集合 vs `KNOWN_CONFIG_KEYS`、各段子键 vs `KNOWN_*_KEYS`、插件表 vs `registry.CONDITIONS/ACTIONS`)。另两个易踩点: ①可选整段(站点 `hr`、checking 的 `with_reference`)靠 `Field.optional` **显式声明**, 不能用 `default=None` 判定 —— 普通段(`log`/`web`)也无默认值, 会被误渲染成一个开关; ②前端登出必须调用 `cfgReset()` 清空配置树(与 groups/status 同为受保护内容), 否则错误密钥窗口期可能闪现上一会话的配置。前端结构约定: 字段渲染由 `ce-field` 组件统一承担, 嵌套 object 在 `cfgFlatten` 阶段**扁平化为带缩进的渲染项**(故组件无需递归), 插件 spec 也映射为同一套字段项 —— 新增字段类型只需扩 `KINDS` 与组件的一个分支, 不要在每个专段里重复写控件。
- **每个动作的 dry-run 返回 success** — dry-run 日志里看到的都是"成功", 别据此判断真实执行结果。
- **配置保存热重载后 WEB UI 报 `Errno 10048` 并失联** (2026-09-14, 已修): `apply_new_config` 的 L1 分支曾写 `handle.stop(); start_web_server()` —— `stop()` 只是**请求退出**(uvicorn 主循环每 0.1s 才读一次 `should_exit`, 之后才关闭监听套接字), 1ms 内重新 bind 同端口必失败。症状很有迷惑性: 日志里 `WEB UI 已启动`(无条件打印)与 `配置热重载完成` 时间戳只差 1ms, 之后的 uvicorn `ERROR:` 行不带时间戳、也没有我们自己的堆栈 —— 因为 `sys.exit(STARTUP_FAILURE)`(=3)的 `SystemExit` 在非主线程被 `threading` **静默吞掉**, 而 `_web_handle` 指向的已是个死 server。修复: ①`WebServerHandle`(`stop()`/`wait(timeout)`/`started`) + `stop_web_server()`(停并 join, 超时记 WARNING 后照常重启——监听套接字毫秒级就释放); ②`_apply_web_config` 只在 `(enabled, host, port)` 变化时重启, 否则只刷新 `_web_token`, 顺带修好 `web.enabled` 热开关(原先 `_web_handle is None` 时整段跳过, 关->开 完全不生效); ③`_run_server` 包一层把失败退出记进日志, `start_web_server` 改为就绪(`server.started`)后才打"已启动", 失败记 ERROR。回归: `test_web.test_stop_web_server_releases_port_for_restart`(**真实 uvicorn** 起->停->同端口再起) + `test_start_web_server_reports_failure_when_port_taken` + `_apply_web_config` 三个单测。**判别法**: 任何"重启监听同一端口"的逻辑, 先确认旧监听器已 `close()`, 不要相信"请求退出"类 API 的返回值。
- **配置热重载分级的两处"看着像 bug"的现状** (2026-09-13, 补 `test_impact.py` 时发现, 未改动):
  1. `impact.py` 注释说 L0 段"字段级 diff, 仅变更字段计入", 但 `_diff_flat` 的分支条件是**两侧值都是纯 dict** —— 真实 `Config` 的 L0 段(`grouping`/`add_episode_tags`)是 dataclass 实例, 故实际产出**整段单条 L0** 变更(path 只到段名)。级别判定仍正确(热重载行为没问题), 差异仅在变更条目粒度与"变更 N 项"日志计数。已有测试固化该现状。
  2. `max_level` / `restart_required_paths` 是模块公共工具但**当前无生产调用**(`web.py` 与 `qbmanager.py` 各自内联 `[c.path for c in changes if c.level == "R"]`)。属清理候选, 未擅自删除(测试已覆盖其契约)。
- **`state_file` 仅退出时落盘**: 运行中 kill -9 会丢执行历史 → 去重可能重放, 已知取舍 (想法.md 明文)。
- **qB 断连期间错误日志静默**: tick 内 `APIConnectionError` 经 `_last_conn_ok` 状态机节流 (2026-09-12) — 仅"连接态→断开"转换时记一次 ERROR, 恢复时记一次 INFO("已重新连接 qBittorrent", `connect()` 内), 断开期间每 tick 重试失败不打日志。是有意节流 (防 qB 宕机刷屏), 不是丢日志; 非 `APIConnectionError` 异常照常记 "主循环异常"(exc_info=True)。

- **WEB UI 前端类名/DOM 与 JS 行为耦合** (2026-09-14 视觉重做后确认): 改样式可以随便改, 但以下结构**不得改名/增删**: ①`.group-head`/`.detail-head` 是列宽拖拽的锚点(`startResize`/`autoFitColumn` 从中读**渲染列宽**与列索引), 而列索引与`_visibleCols(page)` 严格对应 —— 两者派生于同一份列定义(`TABLE_COLUMNS[page]`, 见下条), 所以**不会再出现"列数不一致 → gridStyle 静默回退"**(旧实现把顺序分散在表头/行/模板三处, 改列数就得同步 `COLS_STORE_KEY` 版本); ②`.search-hit`/`.ctx-menu`/`.detail-*`/`.pop-menu`/`.col-menu` 为逻辑挂钩; ③成员行的"进度"单元格是"细进度条 + 数字"的**同一列**。样式层已令牌化(单一 `:root`), 调色/圆角/阴影改令牌即可, 不要在各组件里散写色值。
- **列宽模型 = 列定义单一来源 + "只改被拖列"** (2026-09-14 按用户要求重做): `GROUP_COLUMNS`/`DETAIL_COLUMNS`(app.js 顶部)是列头/单元格/grid 模板/列选择器的**唯一来源**; 列宽按**列 key**(不是索引! 索引在支持隐藏列后会漂移)存在 `autoqb_cols_v3`(`{widths,hidden,manual}`)。行为: (a) 未手动调过列宽时, `materializeColumns()` 在挂载/窗口 resize/切页时把默认弹性模板**实体化**为当前渲染 px(保留"填满容器 + 自适应"的观感); (b) `startResize` 起始时把**全部可见列**固化为 px —— 这是"拖一列不动其它列"的前提(不固化则被拖列会从邻居的 fr 余量里抢空间); (c) 双击分隔线 = 按内容自适应(`autoFitColumn`, 取表头+已渲染单元格的 `scrollWidth`, 夹在 `[56, 520]`); (d) Shift+拖 = 与相邻列互挤(总宽不变)。**注意上一版文档曾把"稀疏覆盖 + 其余列弹性"当成正确设计, 那是与本需求相反的取舍, 已反转**。
- **`.h-cell .resizer` 必须完全落在单元格内** (2026-09-14 实测拖拽失效): `.h-cell` 有 `overflow: hidden`, 拖拽把手原写 `right: -5px`(宽 10px) → **右半被裁掉, 既不可见也无法命中**, 实际可点区只剩 5px。改为 `right: 0`(落在 `padding-right: 10px` 内)。判别: 拖拽/悬停类交互"没反应"时先量 `getBoundingClientRect()` 与祖先的 `overflow`。
- **过滤/筛选类 UI 的弹层要能被"空白处点击"关闭, 且自身按钮 `@click.stop`** (2026-09-14): `colMenuOpen`/`filterMenu` 都是单例字符串状态; 根组件 `window` click 监听统一置空(右键菜单同时关)。踩点: 测试/操作时**先点表格行再点开弹层** —— 点行会冒泡到 window 把弹层关掉(本次浏览器验证时因此报 `undefined.click()`)。
- **视图字段扩容必须同时检查"写侧置脏"** (2026-09-14): 把 `tags`/`category` 加进 `_VIEW_FIELDS` 后, 除了 `apply_delta` 会置脏, 还必须在 `TorrentStore.update_torrent_fields`(tags_add/tags_remove/category 分支)与 `apply_tag_removal` 里置 `view_changed` —— 旧代码注释明确写着"tags/category 不影响视图展示", 一旦视图开始展示它们而这些写操作不置脏, **本程序自己打的标签/分类要等下一轮增量响应才可见**(而 qB 增量轮不会重报未变化字段, 可能长期不刷新)。同 PR 已把 `test_store_update_fields_marks_view_changed` 的期望改为 tags/category 也置脏。
- **`cfgFlatten` 的 `group_of` 分组判定不能递归复用** (2026-09-14 实测): 子卡内字段是"已归属父字段"的, 若仍参与分组判定, 它们会被再次收进 `children` 而 `roots` 为空 → 子卡渲染成空壳(`ce-subcard-body` 里什么都没有, 且**不报错**)。修法是递归时传 `allowGrouping=false`。同理, 排查这类"渲染出来但是空的"问题走浏览器控制台 + 在模板里临时打一行 `{{ item.items.length }}` 最快(本次即如此定位)。
- **Vue 计算属性被写成方法后, 模板里 `this.x[...]` 会静默得 undefined** (2026-09-14): 曲线图 `cfgCurveCharts` 起初写在 `methods` 里, 而 `cfgCurveChartOf` 按计算属性那样 `this.cfgCurveCharts[key]` 取值 → 取函数对象上的属性得 `undefined`, 图表恒不渲染且**无任何报错**。改计算属性(或改成 `this.cfgCurveCharts()[key]`)即可。判别: 模板里 `v-if` 守护 + 内部多处取值 → 用计算属性(只算一次), 且别混用两种访问方式。
- **静态资源不加 `Cache-Control` 会被浏览器启发式缓存** (2026-09-14 实际踩到): FastAPI `StaticFiles` 只给 ETag/Last-Modified, 浏览器按启发式规则自行缓存(app.js 能缓存数小时) → **升级程序后仍加载旧前端**, 表现为"界面改了但没变", 开发时甚至误导排查方向(以为是代码 bug)。现由 `web.py` 的 middleware 给所有**非 `/api`** 响应加 `Cache-Control: no-cache`(允许存储但每次必须带 ETag 重新校验: 未变更走 304, 变更为新内容)。回归: `test_web.test_static_assets_disable_heuristic_cache`。
- **`FakeQbServer` 只做 HTTP 适配, 出口数据必须可 JSON 序列化** (2026-09-14 实际踩到): `_fake_file()` 返回 `SimpleNamespace`, 而 `/torrents/files` 路由直接 `json.dumps` 它 → TypeError 在 handler 内抛出 → 连接被**无响应关闭** → 客户端报 `APIConnectionError`。后果极隐蔽: 辅种分组(`_assign_new_torrent` → `torrent.files()`)在真实 HTTP 栈下整体中断, 表现为"辅种分组永远为空", 而主循环把它当作 qB 断连静默吞掉(只记一条连接失败)。**替身出口统一转真机语义**: 现 `_file_to_dict()` 把文件项转 dict; 新增替身端点时务必照此处理。回归: `test_local_qb_service.test_fake_server_files_endpoint_serializes_objects`。
- **前端交互原语是单例, 且迁移到 Promise 后必须 await** (2026-09-14): `toast()`(替代 alert)与 `confirmDialog()`/`promptDialog()`(替代 confirm/prompt, 返回 Promise)在根组件 mixin 上; 模态为**单例**(重复打开会先把上一个结算为"取消", 防 Promise 悬空)。踩点: 迁移 `confirm` 的方法必须改 `async` 并 `await`, 否则**弹窗还没确认代码就继续往下跑**(等价于"永远确认", 删除类操作会直接执行); 取消/遮罩/Esc 一律结算 false/null 且**不发出任何请求**。`_logout()` 必须一并清空 `toasts`/`modal`(与 groups/settings 同属受保护数据, 防错误密钥窗口期残留)。
- **图标一律走 index.html 的 sprite**(`<svg class="icon-sprite">` + `<use href="#i-*">`): 无外部图标库/网络依赖(离线 localhost 环境), 新增图标只在 sprite 里加一个 `<symbol>`; `.ico` 靠 `stroke: currentColor` 继承语义色, 需实心图标(如播放三角)时在该 symbol 内显式 `fill="currentColor" stroke="none"`。

## 📝 文档与代码的一致性 (2026-09-05 已同步)

README.md 曾有的客观漂移已于 2026-09-05 修正: 任务队列描述 (双队列→单队列)、集数标签格式 (`E1-5`→`zE1-5`)、mixins 组合列表补 SpeedCurveMixin、目录树补 qbapi/curves/speed_curve、checking.py 职责描述。

**🚧 标注的语义 (作者澄清, 重要)**: 🚧 = "未实现 **或** 已实现但未严格测试(实盘验证)"。规则系统一节的 🚧 (trigger/execute_once/cooldown、size/trackers/state/hr/date_time/seedtime/upload_*/freespace 条件、checking/move_to/reannounce 动作、stop_following_rules_if) 属于后者 — 代码已有单测, 但作者认定未经严格验证, **必须保留, 勿因"已实现"而移除** (2026-09-05 曾误删, 已按作者要求恢复)。

其余 🚧 属未实现: `on_torrent_added` / `on_torrent_deleted` / `on_torrent_state_enum_changed` 三个事件触发时机 (README 功能矩阵同样标 🚧 规划中)。**2026-09-12 全部落地** (trigger 解析/白名单/`print_torrent_details` 动作/事件分派引擎/测试), 已从 🚧 转正式特性。单实例锁 (`locking.py`) 与 fail-fast 全量配置校验 (`config.validate_config` 聚合校验, 见 config-reference.md) 均已于 2026-09-05 实现, README 中列为正式特性 (无 🚧 标注)。

> 想法.md 是设计草稿, 不随实现同步; 改 README 时以代码为准, 但 🚧 标注的取舍听作者。

## 🎨 WEB UI 视觉/交互 (2026-09-14 打磨)

- **分组视图里"由配置派生的展示值"必须自己找置脏源头**: 成员视图的 `hr_tag`/`hr_tag_done`(已触发 HR 未达标 / 已达标时应有的标签, 供前端把 HR 标签着成鲜亮/镇静两色)不是快照字段, `_VIEW_FIELDS` 完全不覆盖它 —— 只靠 `store.view_changed` 会出现"改了 HR 标签模板 → 界面仍显示旧标签色"的静默错误。凡此类值(标签模板、名称/分类格式等由配置生成者)都要在 `apply_new_config` 里显式 `_group_view_dirty = True`; 相反, 纯由种子状态驱动的部分(seeding_time/ratio/progress)已在 `_VIEW_FIELDS` 内, 无需额外处理。**判别法: 该值是否可能在种子数据一字未变时变化 —— 会, 就必须显式置脏。**
- **HR 标签着色靠"文本逐字相等", 绝不能在前后端各写一遍模板逻辑**: 后端 `qbmanager._hr_view_tags` 用 `utils.replace_vars` 展开 `${required_seeding_time}` 后透出字符串, 前端 `app.js tagClass()` 只做 `tag === member.hr_tag` 比较; 判定复用 `check_hr_condition`/`check_hr_satisfied`(与打标签流程同一语义)。若前端改用"图案猜测"(如匹配 `!!HR..!!`)或在 JS 里再拼一次模板, 自定义标签格式会立即失效或误判。新增需要判定的标签类型时, 同样由后端算好文本再透出。
- **同一语义不要用两种视觉重复表达** (用户明确反馈): 组级状态原本既有 `.g-status` 图标徽标(图标 + `.k-*` 语义色), 左侧又有一条 `.group-row::before` 色条承载同一信息 —— 判定为冗余并已移除。新增标记前先确认是否与现有徽标/chip 重复; 组状态的唯一载体现在是 `.g-status`(`.s-*` 类名仍在 DOM 上, 但已无样式绑定)。
- **`diff-mark`(± / 多分类)必须保持低调**: "组内不一致"是**提示性**信息而非风险, 原本用 `--warn`(黄)与真正的风险信号抢视觉权重, 已改为与 `.zero` 同族(`--surface-2` 底 + `--fg-dim` 字)。对比色资源留给需要立刻行动的信号(HR 未达标 `hr-pending` / 错误 `--error`)。
- **图标 sprite 的 viewBox 可以彼此不同**: 新增图标一律画在 `0 0 16 16`; 例外是"齿轮"(`#i-settings`, 用 `0 0 24 24` 的常见齿轮轮廓 + `stroke-width="1.9"` 补偿缩放变细)。使用处仍写 `viewBox="0 0 16 16"` —— `use` 引用 `symbol` 时按 symbol 自身的 viewBox 映射进 use 视口, 无需改动使用处。
- **Vue 模板里 computed 是属性, 不能当函数调用** (2026-09-14 实际踩到, 页面整块空掉): 新增 `hasUnit`/`unitParts`/`unitOptions` 三个 computed 后, 模板误写成 `v-else-if="hasUnit()"` / `unitParts().num` —— 生产版 Vue 下该分支抛 `hasUnit is not a function`, 导致每个 `ce-field` 渲染为空, **设置页字段全部消失(仅剩分组标题), 但侧栏与控制台无醒目提示**, 极易误判为"配置没加载"。规则: computed 在模板中用**属性访问**(无括号, 也不必写 `.value`); 只有 `methods` 才可 `xxx()` 调用(如 `ce.ceRefOptions()`)。新增模板表达式后当面打开页面确认字段在渲染, 不要仅靠测试通过。
- **computed 区段里不能放"看似方法的辅助函数"** (2026-09-14 同类重现, 后果更重): 把 `_limitDefaultTip()` 写在 computed 块内(跟在另一个 computed 后面), 它在 computed 里被 `this._limitDefaultTip()` 调用时抛 `is not a function` —— 因为 Vue 把它当**属性**而非方法。这次报错发生在顶栏 pill 的渲染中, 结果是**整个顶栏(含统计/限速/今日流量)渲染失败**, 表格也不刷新。判别法: 写完一个 `xxx()` 先看它在 `methods` 还是 `computed` 里 —— 只要在 computed 里, 就不能写成 `this.xxx()`, 也不能在模板里加括号调用。需多处复用的小计算直接在 computed 内**内联为局部常量**最安全。
- **前端表达式错误只有浏览器能发现, 单测与后端用例都盖不住** (2026-09-14 两次实测): 上述两个 bug 都是 `pytest` 全绿(866 passed)而页面崩掉的形态 —— 后端字段/接口均正确, 错在模板/JS。**改任何前端渲染逻辑后必须做一次浏览器冒烟**(假 qB + 临时配置, 见 testing.md), 并在页面里主动触发对应的渲染分支(例: pill 只在 `limitRows` 非空时才渲染 —— 未启用限速曲线时看不到该分支, 必须先启用再验)。
- **改 `config/schema.py` 后必须重启进程才看得到变化** (2026-09-14): schema 是**模块级常量**(`GROUPS`/`TRACKER_FIELDS` 在 import 时构建), `/api/config/schema` 只是把它序列化出去 —— 运行中的实例仍持有旧对象。症状: 前端刷新后字段属性(如新的 `kind`/help 文本)不生效, 看起来像前端问题。同样适用于 `UNIT_OPTIONS` 之外的其它模块级表。
- **静态写的 `viewBox` 会被模板编译器小写成 `viewbox`, 浏览器直接忽略** (2026-09-14 实际踩到, 图表内容溢出容器): 写成 `:viewBox="ch.viewBox"` 时, Vue 的**静态**属性名被小写化, DOM 里出现 `viewbox` —— SVG 属性**大小写敏感**, 浏览器不认 → 坐标系不缩放, 内容按用户单位 1:1 绘制并溢出。修法: 用**动态绑定对象** `v-bind="{ viewBox: ch.viewBox }"`(运行时 key 保留大小写)。判别: 内联 SVG 里元素位置“明显跑到容器外”/标签被截断时, 先查 `svg.attributes` 里 viewBox 的**大小写**。
- **内联 SVG 只有 `width:100%; height:auto` 时高度会退化成 150px** (2026-09-14): 没有固有尺寸的替换元素在 `height:auto` 下取默认高度, 于是 `aspect-ratio` 缺失时图表被压扁(与 viewBox 无关)。修法: CSS 显式 `aspect-ratio: <viewBox 宽高比>`。本次同时踩了上面两条, 两个都修才正常。
- **普通 object 段的子字段不要再缩进** (2026-09-14 用户反馈\"输入框左右未对齐\"): `cfgFlatten` 曾对**所有** object 子字段 `depth+1`(缩进 16px), 而段标题一行已经界定了范围 —— 结果是同一页里两组输入框左缘相差 16px。现在只有**可选段 section 内部**缩进(那里确实需要表达从属)。验证手段: 在浏览器里取所有 `.ce-field .ce-ctl` 的 `getBoundingClientRect().left` 去重, 应为**单一值**。
- **`ce-field` 里 computed 与 methods 不能同名** (2026-09-14): 给可选段加 `sectionExists` 时一次放进了 computed, 而 methods 里本就有同名方法(组件模板调用 `sectionExists()`) → 冲突。computed 一律按属性用(`sectionOpen`/`sectionSummary`), methods 才可 `xxx()`。

### 视觉/交互打磨补充 (2026-09-14 第二轮)

- **CSS `background` 简写会静默抹掉 `background-image`(自绘 caret 消失)**: 给所有 `<select>` 加 `appearance:none` + data-URI chevron 后, 单位下拉(`.ce-unit-select`)的 caret 没出现 —— 因为另一条 `.ce-unit-group .ce-unit-select { background: var(--bg-sunken) }`(specificity 0,2,0)`的**简写**把 image 重置了, 而我的规则只有 `select.ce-input`(0,1,1)。同理, 我规则里的 `border-radius` 又把原有“拼接方角”(`.ce-unit-group` 左倒角置 0)盖掉了。修法: 把选择器提升到同等强度(`.ce-unit-group .ce-unit-select` 进列表)并在末尾重新声明方角。**验证手段: `getComputedStyle(select).backgroundImage.includes("svg")` 与 `borderRadius` —— 不要只看“样式写了”。**
- **筛选器“位置固定”需要三件事同时成立**(用户明确抱怨过位置漂移): ①按钮定宽(`min-width` + `justify-content:center`, 否则标签文字长短会改宽); ②选中计数徐标 `position:absolute`(在流内就参与布局, 数字从 1 到 2 位就会推挤后继按钮); ③“清除筛选”按钮 **常驻占位**(用 `visibility:hidden` 而非 `v-if` —— 后在筛选激活时才出现, 会把整行筛选器左推一个按钮宽)。弹层另用 `left:0` + 固定 `width`, 不用 `right:0`(它也随按钮宽度漂)。验证手段: 选中不同数量后取各按钮 `getBoundingClientRect().left` 序列, 应**完全不变**。
- **既有窄屏媒体查询会把新加的信息一起吞掉**: `@media (max-width:1180px) { .stat-pills { display:none } }` 是旧规则 —— 一旦顶栏新增“今日流量/限速对照” pill, 它们同样会在 1180px 以下全部消失(作者本地窗口 1159px 就看不见)。修法: 把“整槽隐藏”改为**逐级收敛**(1320 缩搜索框 → 1180 隐刷新间隔 → 1000 隐速度/今日 → 900 才整槽让位), 并明确保留优先级(限速对照是“程序正在干预 qB”的唯一信号)。**加 pill 前先搜一遍 `@media` 块。**
- **加深快照字段(`_SNAPSHOT_FIELDS`)必须同步测试替身**: `added_on` 加入后, `REQUIRED_TORRENT_FIELDS` 随之变长, 而 `tests/helpers.py` 的 `FakeTorrent._SNAPSHOT_FIELDS` 与 `_torrent_fields()` 是靠该常量驱动的 —— 不同步就会在 sync 版本校验时报“缺少字段: ['added_on']”而**启动即退**(fail-fast 是有意的, 不要把校验改成宽容)。
- **加/减列不再升列状态存储版本** (R10-09 反转, 2026-09-17 起; **本条旧结论"加/减列必须升版本"已作废**, 现行口径见第十轮小节同名条目): 列宽记忆按**列 key** 存(`autoqb_cols_v4` = `{widths,hidden,manual,order}`), 新增列在旧缓存里只是“没有记录”(回退 `tpl` 默认宽), 已删列的残留 px 由 `loadColState()` 按当前列 key 求交集**洗净** —— 都不会错配。**升版本反而会清空用户手调的宽/隐/序**, 这正是“列宽时不时被重置”的机制性来源; v3→v4(新增 “H&R”/“分享率”)是唯一一次因列集变更升版本, 已判定为错误决策。**判据: 只有“旧缓存的结构已无法被 loadColState 正确解释”才升版本**(如 v2 按列索引存 —— 支持隐藏列后索引漂移), 且升版本必须把旧键挂进 `LEGACY_COLS_KEYS` 迁移(命中即按列 key 洗净并回写当前键; v2 索引式不可迁移, 刻意不挂)。09-15 新增 show 页 / 09-16 明细表补 8 列 / 09-16 加 `order` / 09-17 保存路径列迁移, 均**未升版本**。

### 第十轮修复 (2026-09-17): 取数口径 / 偏好持久化 / 生成式样式 / 鉴权判据

- **qB `server_state` 的全局限速键是 `dl_rate_limit` / `up_rate_limit`, 不是 `dl_limit` / `up_limit`**:
  后者是**单种子**级字段(`TorrentRecord`, 见 `mixins/web_view.py` 的种子限速列), 两者语义不同。
  前端曾读 `s.dl_limit/s.up_limit` ⇒ 恒 `undefined` ⇒ 状态栏"限制速度"永远显示 "—"; **同一字段还兼作
  速度染色分母**(`numTone(value, denom)` 分母缺失即返回空串) ⇒ 色阶**从未生效过**。判别法: "某列/某值
  恒为占位符"且**同一取数点被多处复用**时, 先核字段名(全仓 grep 该键名命中 0 处 = 后端根本没这个键),
  再改口径 —— 并且必须收成**单一取数点**(现 `speedLimitBytes`), 否则修了显示、染色还是死的。
- **`localStorage` 两种"重置"必须分清, 且不要用"升版本"应对列集变更** (R10-09):
  ① **按 origin 隔离**(`scheme://host:port`): `localhost` 与 `127.0.0.1`、换端口都算不同站点, 各有各的偏好
  —— 客户端**无法**消除(用户已明确要求只存浏览器, 不接受服务端化), 只能记录;
  ② **存储键升版本 = 用户偏好清零**: 历史 v2→v3→v4 每次为"新列错配"而升键, 结果是用户手调的列宽/隐藏列/
  列序全丢 —— 这才是"时不时被重置"的机制性来源。**正确做法**: 宽/隐/序一律按**列 key** 存(新增列只是
  "没有记录", 会回退 `tpl` 默认宽, 不会错配) ⇒ 新增列**不升版本**; 旧键靠 `readColStateRaw()` 迁移
  (`LEGACY_COLS_KEYS`, 按列 key 洗净后回写当前键)。换密钥/登出只清 `autoqb_token`, 全仓无
  `localStorage.clear()` —— 这是"不重置"的可验证保证。
- **生成式列对齐的两个坑** (R10-08, `colAlignCss` 注入 `<head>` 的 `:nth-child` 规则):
  ① **left 列也必须生成规则**: 数值列的**值**单元格带 `.g-stat/.m-stat`(0,1,0, `text-align: right`),
  若因"left 是 CSS 默认值"跳过生成, 左对齐口径会被这两条盖掉(实测现象 = 表头左、值右);
  ② 选择器必须用 `:where()` 把特异性压到 0,1,0 —— 高于 `.g-stat` 才能覆盖, 又必须**低于**
  `.g-stat.zero`(0,2,0) 才能保留既有"0 值居中"口径; 同时写 `text-align` 与 `justify-content`
  (值单元格有的是 flex: 进度条/分享率对/芯片组, 只写前者会漏)。
  配套纪律: **行/表头容器必须带 `data-table="<page>"`**(新增行别忘), 否则该行不归对齐口径管辖。
- **鉴权判据不能用"凭证串非空"** (R10-01): 本机免鉴权模式(`web.skip_local_verify`)下后端**不看**
  Authorization 头, 前端却把"有身份"绑死"token 非空" ⇒ 进主界面首个请求就自判无凭证 → 登出回密钥页
  (表现为"必须先随便输一次密钥才进得去")。正确做法: 引入显式 `authMode`(`local|token`)+ `authOk` 单点判据,
  `api()`/轮询续排/标签页可见性三处守卫全读它; **空凭证不出网**(`token` 为空时不发 `Authorization` 头)。
  注意后端那侧: 免鉴权分支的提示 WARNING 必须**每进程只记一次** —— 免鉴权下前端按设计不带凭证, 每请求都记
  会把轮询日志刷满(实测 2 条/轮)。
- **两套 UI 的"同一个东西"必须成对改, 并加静态断言兜底**: 第九轮给限速加"就近浮层"时只删了棱镜的旧模态,
  星图残留 —— 两个容器由**同一个 `speedOpen`** 控制 ⇒ 点一次开两窗(用户: "会弹出两个窗口")。
  判别法: 同一个状态开关(`v-if="xxxOpen"`)在模板里出现**两次以上**时, 基本可断定是遗漏的旧实现;
  重构后应加静态计数断言(如"全站 `.speed-dialog` 模态引用计数 = 0")而不是只靠肉眼走查。

### 第十轮真机走查修正 (2026-09-17): flex 行里的输入框与按钮

- **flex 行里"输入框缩成一截 + 按钮文字竖排"= 父容器缺增长因子**: `input` 的 `flex-basis` 是 `auto`,
  而 `.add-dialog-input { width: 100% }` 在**自动宽度的父级**里会回退成 input 的内容宽(实测 ≈ 180px);
  即使外层行有 700px 空余, 输入框也不会自己长大(实测: 保存路径独占整行后仍只有 181px)。
  修法: 给**直接父级**(如 `.add-dialog-pathrow > .add-input-row`)加 `flex: 1 1 auto`;
  同时把同行按钮锁住(`flex: 0 0 auto; white-space: nowrap`) —— 否则 input 的 100% basis 会把按钮
  挤到只剩十几像素, 中文按钮变成竖排两行(实测现象: "新建" 边成 "新/建")。
  判别法: 量三个数 —— 容器宽 / 输入框宽 / 按钮宽; 三者加起来远小于容器宽 = 父级没涨;
  按钮高 > 行高 = 按钮被压。

### 视觉/交互打磨补充 (2026-09-14 第三轮: 左栏信息栏 / 图标着色 / 滚动背景)

- **两个吸顶条各自 `backdrop-filter` → 各自建立层叠上下文, 子元素的 z-index 跨不出去** (用户反馈"列选择器下拉被二级导航栏遮挡"): `.topbar` 与 `.status-strip` 都有 `backdrop-filter`, 互为同级兄弟且状态条 DOM 在后 → 状态条整块盖住顶栏子树, 顶栏内 `.col-menu` 的 `z-index:40` 只在顶栏**内部**有意义。修法: 在"吸顶兄弟层"里把两者都设 `position:relative` 并拉开次序(`.topbar z-index:31` / `.status-strip z-index:30`)—— **只加之一无效**。判别: 浮层被"另一个 sticky 条"遮挡(而非被页面内容遮挡)时, 先查该条是否也有 `backdrop-filter`/`transform`/`filter`, 不要一味加大数值。验证: `document.elementFromPoint()` 在两者重叠区取样, 应命中浮层。
- **`:focus-within` 用在带 `tabindex` 的行上, 鼠标点击也会画出 outline** (用户反馈"筛选器下拉框点击选中时的边框"): `.pop-item` 是 `role=button` + `tabindex=0`, 点击会聚焦自身 → `:focus-within`/`:focus` 立即命中并出现 2px 描边。改用 `:focus-visible`(仅键盘操作命中, 键盘可达性不丢)。**判别: "点一下就多出一个框"而不是"hover 才出现" → 先查 `:focus*` 伪类。**
- **表头无法按列单独对齐**: `.h-cell` 原先没有任何列区分信息, 而数值单元格(如 `.g-count`)右对齐 → 表头左对齐、数字右对齐, 观感错位。修法: 模板统一挂 `:class="'hc-' + col.key"`, CSS 加 `.hc-count { text-align:right }`; 需要对齐别的列照此加规则(不动 `.group-head`/`.detail-head` 这两个拖拽锚点)。
- **横向滚动时"行右侧没有底色"**: `.group-table` 是 `flex-column` 容器, 行/列头作为 flex 子项默认 `align-items:stretch` → **盒宽 = 容器宽**, 而 grid 内容可以更宽; 滚动到右侧那一段落在盒外, 露出页面背景(用户反馈"调整列宽出现横向滚动条时背景没有同步调整")。修法: `.group-head/.group-row/.detail/.detail-head/.member-row { width:fit-content; min-width:100% }`(可用宽不足时 fit-content 取 min-content, 正好等于列最小宽之和; `min-width:100%` 保证列少时仍铺满)。顺带让明细与外层共用**同一条**横向滚动(原先 `.detail` 自己 `overflow-x:auto`, 两边位置会错开)。验证: 断言 `row.getBoundingClientRect().width === groupTable.scrollWidth`。
- **sticky 侧栏的偏移与最大高度不能写死**: 顶栏高度随媒体查询、状态条是否渲染、窄屏折行而变化。修法: `--head-h` 由 app.js `_syncHeadHeight()`(mounted/resize/updated 读 `.sticky-head` 的 `getBoundingClientRect().height`, **值未变直接返回**)写入 `:root`, `.rail` 用 `top: calc(var(--head-h) + 12px)` 与 `max-height: calc(100vh - var(--head-h) - 24px)`。验证: 临时撑高内容列后 `window.scrollTo`, `.rail` 的 `rect.top` 应恒定。
- **`min-width` 固定 px 的窄屏规则会与新布局打架**: 900px 以下原写 `.group-head, .group-row { min-width: 1180px }`, 与新的 `min-width:100%` 并存时后者被覆盖 —— 实测无害(1180 小于列最小宽之和 1333, 最终取 fit-content), 但**改窄屏规则时要重新算"哪个约束更大"**。
- **`.ico-*` 语义色可能被更具体的选择器吃掉**: `.search-box > .ico { color: var(--fg-dim) }`(0,2,0)会盖住 `.ico-find`(0,1,0) —— 加图标色类后要逐个用 `getComputedStyle` 核对实际色值, 必要时直接改那条更具体规则的 color。
- **删除顶栏统计槽时, 指向它的媒体查询与 CSS 会静默变成死代码**: `.stat-pills`/`.stat-pill`/`.pill-today`/`.pill-speed`/`.pill-refresh` 的规则与三个 `@media` 块(1320/1180/1000)在统计槽迁到左栏后全部失效。收尾务必 `grep` 一遍类名, 否则下一轮改样式会被这些"看着还在生效"的规则误导(本轮还清出 `.table-tools` 与 `.col-mark` 两条同类残留)。

### 视觉/交互打磨补充 (2026-09-14 第四轮: 弹层视口翻转 / 站点专属色 / 标签展示口径)

- **弹层"左对齐 + 固定宽度"在靠右锚点上会伸出视口并拖出横向滚动条**: 筛选弹层(最右的"路径")与列选择器都是 `left:0` 定位, 锚点靠右时菜单整体超宽。修法: 打开弹层的**同一同步调用栈**里测 `anchor.getBoundingClientRect().left + 菜单宽 > innerWidth - 8`, 超出则加 `flip-x`(`left:auto; right:0`)。注意 `ev.currentTarget` **只在 handler 同步代码内有效**(Vue 事件处理结束后被置 null), 必须当场取值; `toggleFilterMenu(kind, $event)` 要在模板里显式传 `$event`。
- **站点 chip 换"专属配色"时, 状态信息要搬走而不是删掉**: `sc-0..7`(按站点名确定性哈希)取代了原本染在 chip 本体上的状态色, 若只删旧规则, 错误红就从分组行消失。修法: 状态色移到 chip 内的圆点(`.site-chip.seeding .dot` 等, 圆点元素原本在 CSS 里定义但模板没渲染, 顺手补上)。另注意文件尾的 `.site-chip.search-hit` 覆盖(搜索命中色)靠**声明顺序**赢过 `.sc-*` 同特异性规则, 新增同特异性规则时留意相对位置。
- **"展示口径"与"筛选口径"要分离**: 与站点名一致的标签(忽略大小写)只在**展示层**过滤(`_commonTags` 组级交集后过滤 / `mTags` 明细行过滤 / 搜索虚拟行同口径), 标签筛选下拉(`tagOptions`)仍列出全部标签 —— 若筛选也滤掉, 用户将无法按站点名标签筛选。组级 `diff`(± 标记)仍按**原始**标签集合比较, 不受展示过滤影响。
- **入场动效(`page-in`)给带 sticky 子元素的容器加时不要用 fill-mode**: `.layout` 含 `position:sticky` 的 `.rail`, `animation` 结束后不保留 transform(无 `forwards`), sticky 不受影响; 若加 `fill-mode: forwards` 会让 transform 常驻(创建层叠上下文, 影响内部 fixed/浮层定位)。页面切换靠 `v-if` 重建元素触发动画, 不需要 JS 配合。
- **明细行模板里调方法(`mTags(m)`)每帧都会重算**: Vue 模板表达式不走缓存, 同一行调了 4 次(`title`/列表/计数/空判断)。标签数组很小可接受; 若未来对大数组做同样的事, 应改为 computed 预计算或装饰成员对象, 不要在方法里做重活。

### 视觉/交互打磨补充 (2026-09-14 第五轮: 列宽误触排序 / 时间单位中文化 / 关联配置折叠 / 表头吸顶 / 站点配色重做)

- **拖列宽时浏览器仍会派发 click 到 `.h-cell` 触发 `setSort`** (用户反馈"调列宽顺手把排序也变了"): resizer 与 `.h-cell` 共父级, `mouseup` 后浏览器仍会把按下→移动→释放序列合成 `click` 冒泡到 `.h-cell`。修法在 `startResize` 的 `move` 里累计位移(`RESIZE_DRAG_THRESHOLD=3px`), `up` 时若 `dragged=true` 在 `document` 注册**一次性 capture 阶段** `click` 拦截器(`stopPropagation+preventDefault`), 拦完即注销 —— 不影响纯点击 resizer 的原行为。`detail-head` 共用同一方法, 顺手修复。
- **时间单位下拉只改显示, value 不变**: 用户要求时间下拉显"秒/分/时/天" 但后端解析仍按 `S/M/H/D`(配置值不能漂移)。修法: `UNIT_LABELS = { time: {S:'秒', M:'分', H:'时', D:'天'} }`, ce-field 的 **method** `unitLabel(u)`, 模板 `{{ unitLabel(u) }}` 显示而 `:value="u"` 仍是原始单位。size/speed 不映射(用户只要求时间)。❗ **带参的 `unitLabel(u)` 必须放 `methods` 不能放 `computed`**: 模板在 `v-for="u in unitOptions"` 里调 `unitLabel(u)`,Vue 3 computed getter 被框架以"组件代理"为参数绑定/调用,收到的 `u` 是 Proxy 而非遍历项,`String(proxy)` 抛 "Cannot convert object to primitive value"(本轮冒烟实测);computed 只用于无参响应式派生,带参渲染辅助一律 method。
- **`type='group'`(普通 object 段)由"扁平兄弟序列"改为"嵌套子项 + v-show"**: 设置页字段太多, 默认折叠让用户先看概览再决定展开哪段。`cfgFlatten` 把子字段塞进 `item.items` 而不再 push 到外层兄弟序列, 渲染层用 `v-show` 控制 —— 与 `type='section'` 同构。`pattern_list` 字段(delete_tags 等)同样默认折叠 list 区, 用 `.is-pattern` class 与 `str_list` 区分; 限速曲线卡(`ce-curve-card`)也默认折叠。所有折叠态复用 `caret` SVG + `--ease-spring` 旋转过渡, 不引入新 sprite。❗ 模板里 `groupOpen`/`listOpen` 这类**无参 computed 不能加 `()`**(`groupOpen()` 会对布尔值再求函数调用,抛 "groupOpen is not a function",与现有 `sectionOpen` 用法保持一致);带参辅助(如 `unitLabel(u)`、`sectionExists()`)才走 methods。
- **同组多段循环色(`.ceg-0..5`)只染**色条**不染文字**: 6 种 token(`blue/violet/teal/pink/indigo/cyan`)轮转给 `.ce-group` 的左侧 3px 色条; 文字色保持 `--fg` 高对比(色条只做识别, 不损可读性) —— 与"对比色留给 HR/错误"既定原则一致。可选段(section)用紫、相关设置子卡(subcard)用青、普通段(group)用 6 色轮转, 三种段一眼可辨。
- **表头吸顶需把 `.group-head` 移出 `.group-table`**: spec 规定 `overflow-x:auto + overflow-y:visible -> overflow-y:auto`,使 `.group-table` 成为双轴滚动容器;`.group-head` 的 sticky 上下文变成 `.group-table`(它自身不纵向滚动)→ 失效。修法: DOM 把 `.group-head` 移到 `.content` 下做兄弟元素 + `position:sticky; top: var(--head-h, 100px);`,横向滚动靠 JS `syncGroupHeadScroll` 用 `transform: translateX` 跟随(不用 `scrollLeft` 避免反向触发自身 scroll 回环, 不带 transition 跟手不滞后)。`detail-head` 仍在 `.detail` 内(用户主动展开, 不需吸顶)。
- **站点配色方案重做(底色=状态色, 文字色=站点专属)**: 用户反馈"底色随站导致无法一眼分辨状态"。修法: `.sc-0..7` 只设 `color`(文字色, 站点专属), 不设 `background`; `.site-chip.seeding`/`.downloading`/`.error`/... 设 `background`(状态色), 声明顺序在 `.sc-*` 之后保证底色覆盖。移除站点 chip 后缀 `<i class="dot">`(底色已表状态, 圆点冗余); 明细行的 `m-site`/`m-state` 圆点是**前缀**而非后缀, 保留不动。
- **站点配色方案重做(底色=状态色, 文字色=站点专属)** —— ⚠️ **已被 2026-09-15 反转**: 用户最终要求改回"字体与背景都用状态色", `siteHue()`/djb2/`.sc-0..7`/`.stalled*` 死规则已全部删除, 现状 = `.site-chip.<kind>` 同时设语义 `color`+`background`, 站点身份由 chip 文字表达。此条目保留作历史脉络; 明细行 `m-site`/`m-state` 圆点前缀保留不动。加同特异性规则时仍需留意文件尾 `.site-chip.search-hit` 的声明顺序覆盖。
- **H&R/站数列居中**: `.hc-count`/`.hc-hr` 表头 + `.g-count`/`.g-hr` 单元格改 `text-align:center` / `justify-content:center`(grid cell 内 inline-flex 元素不靠 text-align, 必须给 flex 加 `justify-content`)。`detail-head` 同列不动(用户只要求分组表)。

### 视觉/交互打磨补充 (2026-09-15 第六轮: 回执确认 / 多选 / 历史流量 / 删除确认框)

- **强制汇报的"成功"回执是 tracker 确认而非 API 返回**: WEB 汇报命令(`_cmd_reannounce_*`)只发指令并登记 `_reannounce_pending`, 回执由 `_check_reannounce_pending` 每 tick 确认(读 `torrents/trackers`): status==3(updating) / next_announce 比 baseline 提前>60 / status 从非 2 变 2 = 成功; status==4 且带 msg = 失败; 超时 `REANNOUNCE_CONFIRM_TIMEOUT=30s` 判失败。**判定的前提是替身 trackers 数据带 status/next_announce 字段**(FakeClient 默认只返回 url → 永远无结论 → 测试需配 `trackers_map`); DHT/PeX/LSD 虚拟 tracker(`**` 开头)已排除。FakeQbServer 写端点只回 "Ok." 不改替身状态 → 端到端冒烟需外部动态改 `trackers_map`(冒烟钩子线程)。
- **命令回执机制**: 所有 WEB 命令端点入队时生成 `cmd_id`, 主循环执行完写 `_web_results[cmd_id]`(reannounce 例外: 由确认跟踪器在确认/超时后写); Web 线程经 `GET /api/cmd/{id}` 只读。`_drain_web_commands` 把 `cmd_id` 从 args 剔除后才分发 handler(否则 handler 收到未知参数 TypeError); reannounce handler 特殊传参 `cmd_id=`。无 cmd_id 的旧调用路径(直接 put 队列)完全兼容。
- **删除编排在前端而非后端**: "删除前强制汇报"由前端串行编排(汇报→等回执→成功才投递删除), 后端不做复合命令 —— 失败保留种子的语义由前端保证, 后端 `torrents_delete` 调用点不变。modal 通用化扩展了 `checks`(多选项)/`details`(信息区)/`icon`(标题图标覆盖), `resolveModal` 对 checks 返回 `{checked, checks:{key:bool}}`(向后兼容单 checkbox 的 checked)。
- **多选保留策略**: 增量刷新(groups 整表替换)后按 key/hash 交集保留选中; 虚拟行 key(`u-<hash>`)不做存在性校验(搜索视图重建); 批量目标拆解时已消失的 key 跳过 —— 否则 `/api/groups/u-xxx` 解析失败 500。
- **成员视图补 `name` 字段**(2026-09-15): `_build_group_view` 的 members_view 原本没有种子名, 删除确认框需要它。`name` 已在 `_VIEW_FIELDS` 置脏集合内, 无需额外置脏; 但新增**展示字段**时仍要按判别法确认置脏源头。
- **前端冒烟的具体做法已验证**: FakeQbServer(假 qB) + 真实 QbManager(临时 config/data_dir, web.enabled)后台进程 + Edge headless(`--remote-debugging-port`) + Node CDP 脚本(Runtime.evaluate 逐项断言 + captureScreenshot)。踩点: ①programmatic `btn.click()` 不触发 form submit, 要 `form.dispatchEvent(new Event("submit"))`; ②headless profile 持久 localStorage → 第二次启动直接进主界面(登录表单不出现, 属正确行为); ③断言即时色值可能取到 transition 中间值, 用语义断言(非默认灰/无 sc- 类)更稳; ④破坏性操作后的 UI 更新有轮询延迟(≈2s), 断言要轮询等待而非固定延时; ⑤PowerShell 管道读写 UTF-8 脚本会把中文写坏(GBK 转码), 批量改文件用 Python 或专用工具。

### 视觉/交互打磨补充 (2026-09-15 第七轮: 折线图 / 吸顶批量条 / 状态分家 / 平铺段 / 冒烟运维)

- **`cfgGroupToggle` 三态 bug (用户报告"有折叠但不能点击折叠")**: 旧实现是"记录存在→删除(回 schema 缺省) / 不存在→写 true"的二态切换, 对缺省展开(open=True)的段**永远写不出显式 false** → 点击无效果。修法: `next[key] = !cfgGroupOpen(path, field)` 写"当前有效态取反"。平铺段(open=True, 如 日志/WEB UI/通知)在 `cfgFlatten` 直接透明展开(splice 子项、同级 depth、无段头无缩进), 折叠头不再渲染; schema.py 的 `Field.open` 仍是唯一声明来源, 前端只改渲染方式。
- **`_attachGrey` 只在本层命中才覆写 greyBy**: 透明展开把内层子项 splice 进外层 items 后, 外层 `_attachGrey(items, 外层 byKey)` 会把内层已算好的 greyBy 清成 null —— grey_if 引用的是同段字段, 内层字段表才是正确上下文。修法: `byKey.has(key)` 命中才赋值。判别: 动 grey 逻辑先想清楚"这段字段属于哪一层字段表"。
- **历史流量图悬停闪烁根因与修法**: 命中区 `hist-hit` 宽度只等于**单根柱宽** + enter/leave 挂在逐桶 `<g>` 上 → 指针扫过桶间空隙时 hoverIdx 反复归 -1, tooltip 显隐交替。修法: mousemove 挂图表容器, 指针 x 按 getBoundingClientRect 折算 viewBox 坐标再换算桶索引(连续无空隙), 图形元素一律 `pointer-events:none`; tooltip 本就 pointer-events:none 不抢事件。
- **SVG `pathLength` 与 viewBox 同属大小写敏感属性**: 折线 draw-in 用 `pathLength="1000"` 归一化 + CSS dasharray 动画; 静态写法会被模板编译器小写, 必须 `v-bind="{ pathLength: 1000 }"`(与 viewBox 同款坑, 同款修法)。
- **吸顶批量条与表头联动**: sticky 元素出现会与既有吸顶表头重叠, 偏移量用 CSS 变量接力 —— `--bulk-h` 由 app.js `_syncBulkHeight()` 量测写入(无选中/切页归 0, 值未变跳过), 表头 `top: calc(var(--head-h) + var(--bulk-h))`; 与 `--head-h` 同款模式。层叠次序: topbar(31)/status-strip(30)/bulk-bar(6)/group-head(5)。
- **冒烟运维两坑(实测)**: ①Edge 同 user-data-dir 会**单例移交** —— 新 spawn 的进程立即退出, `/json/list` 拿到的是旧实例的**旧页面**; 冒烟必须每轮独立 profile 目录(带时间戳)。②被杀脚本的残留页面轮询会在新服务起来后自动重连, 页面里悬空的交互序列可能继续执行"幽灵操作"(实测把新环境里的同名组删了, 导致后续断言全歪)——起服务前先按命令行清 smoke edge(`CommandLine -match "edge-smoke"`; **不能全杀 msedge**, 用户自己开着浏览器)并确认端口无监听; kill 后端口释放有延迟, 立即重启必 10048。

### 棱镜 UI (prism, 曾名 newui) 主题系统与冒烟补充 (2026-09-15)

- **企业策略强装扩展会污染 headless 冒烟**: 本机 Edge 被策略强装 Dark Reader(chrome-extension, `kbijh...`), 即使 `--disable-extensions` + 全新 user-data-dir 也照样注入 —— 它改写 CSSOM(注入 `--darkreader-bg--*` 变量与自建样式表), 元素 computed 背景色不再等于应用令牌值(实测 .topbar background 与 `--glass` 完全脱钩, 改根变量也不变)。**颜色类断言必须读 `:root` 的自定义属性**(getComputedStyle(root).getPropertyValue), 而非元素 computed 背景; 控制台错误过滤 chrome-extension 来源; 截图可能被改色, 视觉验收以令牌 + 结构断言为准。
- **CDP 颜色解析坑**: 自定义属性 getPropertyValue 返回**原始书写值(hex)**, 不是 rgb() —— 对比度计算要先解析 hex(天真的 `\d+` 抓数字会把 `#3d6aa3` 拆成 [3,6,3]); 另 JSON 序列化 NaN 变 null, 冒烟断言里出现 null 先怀疑 NaN。
- **CSSStyleRule.cssRules 在 Chromium 已存在**(空 CSSRuleList, 真值): 递归遍历样式表不能用"有 cssRules 就是容器规则"判断, 必须按 rule.type 判定(MEDIA=4/SUPPORTS=12), 否则全部样式规则被当容器跳过(实测踩坑)。
- **主题系统约定(prism)**: 组件样式只允许引用令牌, 颜色一律出自 themes/*.css(tokens.css 只放结构令牌); 加主题 = themes/ 加一个文件 + theme.js THEMES 注册表加一行, 组件零改动; theme.js 必须在 `<head>` 同步执行(首帧前定 data-theme 防 FOUC); 顶栏切换器用**事件委托**(登录验证前顶栏未渲染, 不能假设元素存在), 不进 Vue 状态(共享 app.js 零改动); 契约之外的新 UI 专属类(ui-tools/theme-pop/theme-menu/ui-link)不与 JS 耦合, 可自由改名。

### 诊断定案与实施第八轮 (2026-09-15: 吸顶贴合 / 幽灵空位 / 确认框路径 / H&R 筛选 / 单种子视图 / 信息栏双模式)

- **"改了但没生效"类反馈必须先运行时诊断再改**(第八轮方法论): 三个"上轮未成功"项实测后两个根因与样式无关(占位策略/取数 bug), 一个实测已生效; 盲改样式永远修不到。诊断手段: FakeQbServer + Edge headless CDP 量 getComputedStyle + Range 字形留白 + getBoundingClientRect 几何(脚本 .openclaw/tmp/diag_ui.mjs → 冒烟 smoke8.mjs)。
- **前端派生字段不在原始组字典: `_findGroup` 必须优先查 `decoratedGroups`**(R03 根因): 后端组字典没有 `save_path`(它是前端 decorated 层派生), `delGroup` 从 `this.groups` 取数 → 保存路径恒 "—"。判别法: 弹层里"后端明明有值前端显示 —"时, 先查取数来源是原始数据还是派生层。
- **`visibility: hidden` 占位的幽灵空位**(R02 根因): "清除筛选"chip 未激活时 hidden 仍占位 85px —— 防按钮组推动的初衷是对的, 但右缘留下一个隐形块, 用户看成"路径筛选器右边有空位"。修法: 常驻可见 + 降透明禁用(宽度不变 → 位置稳定 + 空位消失)。
- **`--bulk-h` 语义 = 吸顶条自身高度, 流内 margin 不计入**(R01 根因): 表头吸顶偏移 = head-h + bulk-h, 把 margin-bottom 算进 --bulk-h 会让吸顶态恒定多让一条缝(实测 10px)。修后吸顶态两根条零缝堆叠(冒烟断言 gap===0)。
- **诊断/断言"吸顶"必须让页面真的滚得动**(冒烟环境坑, 两轮才定位): 冒烟假数据只有 2-3 行, 长视口下内容不满屏 → 两根条根本没进入 sticky 态, 量到的是流内 margin(误判成吸顶 bug); 且 `.rail` 的 `max-height: calc(100vh - ...)` 会把页面高度跟 viewport 一起抬走 —— 缩矮视口时滚动余量不增反减, 必须 press 到 rail 被 max-height 压得小于内容列(280px)滚动余量才够吸顶阈值(26px)。
- **冒烟假数据的 HD 种子无文件列表 = 永久未归组 single**(设计行为, 别当 bug 查): files_map 只配了 HA/HB/HC → 分组表 2 组、单种子视图 4 行(3 成员 + 1 single)是正确状态; 第八轮首跑误判为"组消失"排查半天, 实为分组规则(文件列表不可读不归组)的正常表现。
- **单种子视图数据面: singles 与 groups 同脏窗口同快照同版本门控**: `_build_singles_view` 与 `_build_group_view` 在 `ensure_group_view` 同一重建窗口产出, ensure_group_state 仅在 updated 时随 groups 一并回传; `store.view_changed` 对任意种子的 _VIEW_FIELDS 变化置真已覆盖未归组种子, 无需额外置脏。未归组种子此前只有搜索兕底路径, 单种子视图是第二个消费者。
- **H&R 筛选只消费后端算好的组级计数/成员布尔**(hr_triggered/hr_pending/hr_satisfied), 前端只做 `_hrBucket` 比较 —— 与 tagClass 同一纪律, 前端重算模板/阈值会让自定义 HR 标签立即失效。
- **新增列 page(torrent) 不升 COLS_STORE_KEY**: loadColState 对缺失 page 返回空属向后兼容; 该结论在 R10-09(2026-09-17)后扩大为**任何列集变更(加列/减列/重排)都不升版本** —— 只有存储结构本身无法被 loadColState 解释时才升(详见上文"加/减列不再升列状态存储版本")。

### 横向滚动条三项根因 / fr 列取整 / 明细排序 (2026-09-17 第十一轮 TASK013)

- **"两个横向滚动条"是两条独立真因**(实测复现, 不是同一条的两个症状):
  1. **`.group-head` 脱离滚动容器**(为做纵向 sticky 而挂在 `.content` 下): 表头比 `.content` 宽时把**整页**撑宽 → 表格内一条 + 页面级一条。实测判据: 把表头 inline `width` 写 3000px, `documentElement.scrollWidth` 1872 → 3012(页面级横滚条), 而表体内的行不会(在 `.group-table` 滚动容器内)。修法: `.content { overflow-x: clip }` —— **clip 不创建滚动容器**, 所以 `.group-head` 的 sticky 顶贴与 JS `syncGroupHeadScroll` 的 transform 跟随都不受影响(用 `overflow-x: hidden` 会把 `.content` 变成滚动容器, sticky 立刻失效)。
  2. **`.detail` 自带 `overflow-x: auto`**: 与外层 `.group-table` 各滚各的, 展开明细时出现第二条(老注释写着"共用同一条滚动"但属性一直没删)。修法: 去掉 inner 滚动, 溢出交由外层滚动容器承载。
- **行宽口径 = `fit-content + min-width: 100%`, 且行内单元格必须 `min-width: 0`**(2026-09-17 第十一轮, 两轮才定位):
  - 症状 A「**列没溢出却常驻一条横滚动条**」: 行**不是**被栅格轨道放大的, 而是被单元格的**自动最小尺寸**顶宽的 —— 表格层有 `white-space: nowrap`, 而单元格 `min-width: auto` ⇒ 自动最小宽 = **文本全长**; 13 列文本累加把行的 `min-content` 顶到容器之上 ⇒ `fit-content` 恒比容器宽 2~6px ⇒ 滚动容器常驻一条横滚条(实测: 轨道是 260.88px/108.71px 小数, 行却是 1850.28 vs 容器 1848)。修法 = `.group-row/.group-head/.detail-head/.member-row > * { min-width: 0 }`(文本排不下由各格自己的 overflow/ellipsis 收尾), 行最小宽回到 `minmax(Xpx,·)` 之和, 轨道回到**小数**铺满 → `scrollWidth == clientWidth`。
  - 症状 B「**横向滚动到右侧没有行底色/边框**」(用户实测): 上一轮曾用「行定宽 `width: 100%`」治症状 A —— 那是**改错位置**: 定宽后行盒永远等于容器宽, 一旦内容真正宽于容器(存有旧列宽 / 拖宽列 / 窄窗口)溢出段就没有行底色。已回退为 `fit-content`, 靠上面的 `min-width: 0` 治 A。
  - 判别口诀: **底色跟内容、滚动条看容器** —— 两者同时满足才算对。回归验证: 注入宽模板(如 `.group-row { grid-template-columns: 420px 300px … !important }`)后断言 `行盒宽 == 最后一格右边界` 且 `scrollWidth > clientWidth`(合法滚动), 再去掉注入断言 `scrollWidth == clientWidth`(无假滚动)。
  - 另两处同时保留: `.content { overflow-x: clip }`(表头脱离滚动容器做 sticky, 不裁切会把整页撑出第二条横滚条) 与 `.detail` **不得**再写 `overflow-x: auto`(否则明细与外层各滚各的)。
- **明细表排序与三视图正交**(三视图都有明细): 不要复用 `sortKey`/`torrentSortKey`/`showSortKey`, 新增 `detailSortKey/detailSortDir` 并让 `setSort(key, scope)`/`_sortKeys(scope)`/`_resetSort(scope)`/`headMenuSort` 都走 scope 分支(表头右键菜单从 `m.page === "detail"` 推 scope)。三点易漏: ①明细列模型的 `sortable` 标记要补齐(当年"暂未接排序"的遗留); ②**数组字段(标签)先 `join(",")` 再比**, 否则相减得 NaN、比较器语义失义; ③空键 = 后端原序, 第三态要能回到原序。
- **芯片状态色改口径时 HR 标签必须排除**: `.tag-chip` 的 hr-pending/hr-done 是唯一真带信息的 chip 配色, 行状态色规则要用 `.tag-chip:not(.hr-pending):not(.hr-done)` 才盖不住它们(用裸 `.tag-chip` 会因特异性更高把 HR 色一并覆盖)。
- **集成浏览器(页面 hidden)会让 `page.evaluate` 里的"等两帧"永久挂起**(本次再次踩到): `document.hidden === true` 时 rAF 不触发 → `new Promise(r => requestAnimationFrame(...))` 永不 resolve → 工具报 deferred 且轮询不完; 同一页面的 `getComputedStyle`/`getBoundingClientRect` 读数也可能停在旧布局。对策: 先 `page.bringToFront()` 让页面可见, 等待改用 Playwright 侧 `page.waitForTimeout`(不依赖 rAF), 交互一律 `dispatchEvent`(Playwright click 会因过渡停在 enter-from 而超时)。

## ⚠️ 代码内 TODO (改动相关区域时顺带了解)

- ~~`qbmanager.py` `_get_torrent` 兼容方法标记"TODO: 删除"~~ — 已删除, 代码统一用 `self.store.get(hash)`。
- ~~HR 判定单点化(原 `rules/base.py` "移动到 actions.py" TODO)~~ — 已完成 (2026-09-12, commit d987015): `check_hr_condition`/`check_hr_satisfied` 单点判定在 `TorrentRecord` (torrents.py), hr 条件 (conditions.py) 与 `mixins/tags.py` 的 `_add_hr_tag_or_category` 均已委托复用 (移除 tracker_conf 参数), 改 HR 判定语义只动 torrents.py 一处。**2026-09-12 语义变更**: 触发条件增加"完全下载即触发"边界 (`is_fully_downloaded`: `progress>=1.0` 或 `amount_left==0` 且 `total_size>0`) — 小于触发量/比例的种子下载完成也视为触发(修复想法.md 已知问题), 生产 `torrents.py` 与测试 `helpers.py` 两处已同步实现(注意 FakeTorrent `amount_left` 默认按 `total_size-downloaded` 推导, 显式传值优先)。
- ~~`rules/conditions.py` tags/category/trackers 三个条件不支持 `:ignore_case`~~ — 已完成 (2026-09-12): 三条件统一改走 `utils.match_value`(语法解析唯一入口 `utils.MatchPattern`), `:ignore_case` 对精确与 regex: 均生效; 同时 config 阶段对这些条件与 remove_tags 动作补 `regex:` 可编译 fail-fast 校验, 运行时的静默跳过仅为兜底。
- ~~`actions/checking.py` "recheck 后仍未完成防重复校验"~~ — 已处理 (2026-09-05): 连续失败 3 次当日冷却(`recheck_fails` state 键, 次日重置, 成功清零); 但 `CheckAction.execute` 闸门 0 上方仍留一条 TODO: "未完成且暂停的种子 recheck 后仍未完成, 下一轮会再次校验"(冷却兜底, 未彻底处理)。
- ~~`episodes.py` 集数标签格式不可自定义~~ — 已实现 (2026-09-05): `add_episode_tags` 段支持 `add_tag_single`/`add_tag_multi` 模板, `${episode_first}`/`${episode_last}` 占位; 仅集数连续时生成。
- `config/loaders.py` `load_global_hr`/`load_tracker_hr` 上方仍留 `# TODO: optimize`。

### ⚠️ 本仓是多 worktree + 多 agent 并行, 提交可能被别的会话顶掉 (2026-09-19 实测)

- **拓扑**: `D:/Projects/auto-qb-backend` 是 **worktree**(`.git` 是文件, 指向 `D:/Projects/auto-qb/.git/worktrees/auto-qb-backend`); 同仓还有 `auto-qb`(主仓, develop)、`-autoclaw`、`-trae`、`-zcode`、`-other`(含 be/fe 子 worktree)、`-frontend` 共 9 个 worktree, 共享同一个 `.git`。
- **事故**: `git commit` 打印 `[backend/develop 6e572af]` 看似成功, 几秒后 `git log -1` 却退回 `ed4cdd0`, `git status` 冒出 2133 个 staged。真相是**分支 ref 被别的会话回退/钉住**, 不是提交失败也不是有人动了文件:
  - `git update-ref refs/heads/backend/develop <sha>` → rc=0、reflog 有 "reset: moving to ..." 条目, 但 loose ref 文件随即消失, `for-each-ref` 仍读到旧值。
  - `git branch -f` → `fatal: cannot force update the branch 'backend/develop' used by worktree at 'D:/Projects/auto-qb-backend'`。
  - 不在 packed-refs 里的新 ref(如 `refs/heads/tmp-sync-agent-skills`)能正常写入 → 说明只针对这个被争用的分支 ref。
- **判别法**: 提交后若 `git status` 突然冒出成百上千个 "staged", **先别急着 stage/commit**, 用 `git write-tree` 对比 `git rev-parse <刚才的提交>^{tree}` —— 两者一致的话, 说明工作区/索引完好, 只是分支指针被回退了, 改动一个字都没丢。
- **处置**: ①确认没有别的会话正在操作同一个 `.git`; ②改动用 `git format-patch -1 <sha> --stdout > 备份.patch` 留底 + `git update-ref refs/heads/tmp-xxx <sha>` 建锚点防 GC; ③等对方结束后再 `git reset --soft <sha>` 恢复指针(工作区/索引无需变动)。**不要**用 `git add -A` / 全量提交去"解决"那批 staged —— 那是别人的在途改动(含 `想法.md` 这类高危文件)。
- **复核动作**: 提交后必须跑 `git log --oneline -1` 确认 HEAD 真的是刚建的提交, 只看 commit 的输出会被骗。

## ⚠️ 并发/状态机约束回顾 (违反即引入难以复现的 bug)

1. 主循环线程是唯一修改队列/state_file/store 分组索引的线程 — 不要在校验回调、信号处理器、新线程里改这些。
2. 校验登记与 recheck 的顺序 (`actions/full_checking.py`): **先 `add_task(轮询子任务)` 登记在途(已在途则 skip), 再发 `torrents_recheck`** — 发送失败返回 `fail`(不返回 pending, 规则任务不留断点); 成功才返回 pending(规则断点, origin 的恢复完全由轮询子任务负责, 队列对"暂停/恢复"无感知)。
3. 断点续跑语义 (taskqueue.py `add_task`): `keep_progress=True` 保留 `resume_index`(校验成功后续跑后续动作), 默认(重置)清空 `resume_index` 重走完整决策链 — 二者不可混用。
4. 种子删除**没有**队列级清理入口: 轮询/等待子任务靠 handler 首行 `store.get(hash) is None` 删除守卫判死(FINISHED 前 `add_task(origin)` 默认重置, origin 由 `_handle_rule`/`_handle_event_rule` 的删除守卫判死); store 侧清理走 `TorrentStore.remove_torrent`(快照/分组索引)。任何在途任务都必须自带删除守卫。**事件规则的 rule-event 任务**作 origin 被轮询子任务重新入队续跑后, 下 tick `_handle_event_rule` 首行同样用 `store.get(hash) is None` 判死 (删除时 FINISHED 消亡); 但 `print_torrent_details` 只读动作经 `ctx.torrent` 回退删除前快照副本 (`RuleContext.snapshot`) 仍可打印留档, 其余需活种子的动作则在 config 白名单阶段已被拒绝。
5. QbApi 写方法必须同步 store (`update_torrent_fields`/`invalidate_*`), 否则同 tick 读旧值 (test_snapshot_sync.py 防回归)。

### venv 半截残留让 uvicorn "auto" 误选 httptools + venv 删除的进程占用坑 (2026-09-15 实测)

- **症状与根因**: WEB UI 每个连接抛 `AttributeError: module 'httptools' has no attribute 'HttpRequestParser'`。venv 里的 httptools 残留是**半截包**(目录在但 `__init__.py` 丢失、dist-info 只剩 licenses/, 疑似杀软误杀或安装/清理中断), Python 把它当**命名空间包**导入成功 → uvicorn `http="auto"` 探测到"httptools 可导入"就选它, 每个连接建协议时炸。判别法: `import httptools` 成功但 `httptools.__file__ is None` 且 dir 为空 = 命名空间残留; `pip show` 报 "invalid metadata entry 'name'" = dist-info 损坏。
- **修法是删不是补装**: 项目锁文件不含 httptools(pyproject 的 uvicorn 不带 [standard], 锁定态就是 h11 协议), 补装锁外包反而偏离 uv.lock; 直接删除残留目录即可。web.py 若将来想用 httptools, 应走 pyproject 显式加依赖再锁版本。

### 导出 .torrent 报 500: HTTP 头只能 latin-1, 文件名必须走 filename* (2026-09-17 实测)

- **症状**: 日志 `UnicodeEncodeError: 'latin-1' codec can't encode characters in position 22-24`, 栈底是 `starlette/responses.py init_headers -> v.encode("latin-1")`, 触发端点是 `/api/torrents/{hash}/export`(右键"导出 .torrent")。
- **根因**: 头值由 `Content-Disposition: attachment; filename="{种子名}.torrent"` **直拼种子名**; 种子名含中文(PT 站常态)时 Starlette 按 latin-1 编码整条头 → 抛错。这是 HTTP 头字符集约束(RFC 7230 头字段值 = latin-1 字节流), 与 qB / 种子内容无关。
- **修法**: 统一走 `web.content_disposition(filename, fallback, ext)` — 双段头 `filename="<ASCII 回退>"` + `filename*=UTF-8''<百分号编码原名>`(RFC 6266); ASCII 回退名剔除非 ASCII 后**若不含字母数字**(纯中文名清洗后只剩 `_`)则改用 hash, 否则下载名不可辨识; 同时剔除 CR/LF 等控制字符(防头注入)。
- **判别**: 凡"把用户数据拼进响应头"(下载文件名、自定义头)的位置都要过这类编码层。**测试盲区提醒**: 前端是 `fetch` + blob 自取 `a.download` 命名, 该头只是兜底 → 浏览器冒烟也看不出问题; 只有"非 ASCII 名 + 直连该端点"才会炸, 所以必须补一个中文名用例(TestClient 会把 UnicodeEncodeError 上抛)。
- **删 venv 的进程占用坑**: VS Code 的 ms-python isort 等格式化辅助进程会用 venv 的 python.exe 起子进程, 且被杀后**自动重生** —— 删除前按 `ExecutablePath -like '*<venv路径>*'` 过滤 Win32_Process 杀掉, 然后**同一条命令内**立刻删(分两步会被重生的进程抢锁); 删除中途失败会留下"只剩 Scripts\python.exe"的残壳, 需补删。

### WEB UI 波次三 · 双 UI 镜像与批量替换的坑 (2026-09-17 实测)

1. **车道分支会停在旧基线, 开工前必须先 ff**: 派工协议要求"合并后把车道分支快进回主线 HEAD", 实操漏掉后车道落后主线 **1689 行**。在落后基线上改代码不会报错, 但会产出"看起来对、实际落错位置"的补丁(本次实测: 替换成功却因上下文不同而错位)。**开工第一件事: `git merge --ff-only agentAutoClaw/develop`**, 并核对 `git log --oneline -1` 与主线一致。
2. **多行文本替换在"多处同型块"上会错位吞行**: 同一文件里有多个结构相同的 `<p ...>` + `<svg>` + `<span>` 块时, 一次替换可能把 newString 插到偏移位置, 产生 `</p>note warn">`、`{{ x }}leGroupKey, rn, ...` 这类语法垃圾(工具仍返回成功)。**防法**: ①oldString 扩到含前后**不重复**的上下文; ②改完立刻做**标签配对计数**——统计 `div/template/main/aside/section/header/footer/p/span/svg/button/label/table/tr/td` 的开闭标签数, 不平衡即可疑(本次的检查脚本 `.openclaw/tmp/tpl_check.py` 留在车道工作区, 未入库, 方法可照抄); ③已损坏就直接 `git checkout -- <file>` 回滚重做, 不要"就地缝补"。
3. **`core.autocrlf=true` 下编辑会归一整文件行尾**: `atlas/index.html` 的 blob 历史上混入过 CRLF(非 autocrlf 提交所致), 一次编辑后 `git add` 会把**整文件归一为 LF**, 单文件 diff 从 23 行变成 1431 行。**这不是损坏**(归一后与仓库其余文件一致), 但提交信息里要写明"行尾归一", 否则后人会误判为整文件重写。
4. **双 UI 镜像首选"以一方模板为基线重建", 不要逐块手抄**: 实测 prism 与 atlas 模板 **86% 同构**(2210 行里只有约 310 行差异)。逐块移植 13 项极易漏; 更稳的是 `Copy-Item atlas/index.html prism/index.html -Force`, 然后**只回填对方专有部分**(此处 = head 的主题链 + 主题切换器 + 界面互切链接), 再补 CSS。重建后必须做**静态 class 覆盖检查**(模板静态 `class="..."` 的每个 token 是否在 CSS 里有定义): 本次 prism 410 个类仅 6 个未定义, 且与 atlas 的未定义集合一致 → 说明没有漏样式。
5. **共用逻辑层决定"改一处还是两处"**: 逻辑在 `shared/app.js` 的(如 CTX-02 用 DOM 标记 + watch 清理) → 模板零改动即双 UI 生效; 需要**模板事件绑定或样式**的(如 TBL-05 表头拖动、状态栏布局) → 必须两边都改。移植前先按这条分类, 能把工作量砍掉一半。
6. **"CSS 已入库但模板从未切换"这类两不管缺口**: 波次二/三的多次交接出现过 `.ce-note` 样式已落盘、模板却仍用旧类名(渲染成无样式默认元素)。**判别法**: 静态 class 覆盖检查里"模板用到但 CSS 未定义"的集合, 与"CSS 定义了但模板从不使用"的集合, 两边都查一遍。
7. **`keep/*` 孤儿标签 = 留档, 不是待合并分支**: `keep/agentZCode-old-line-f396972` 与 `keep/agentZCode-old-line-48836d7` 是**同一条被放弃的线**(后者是前者的后代), 都 fork 自 `beb8642`。放弃原因是该线**不含 `ada3d77`(W5-RFB-01 详情抽屉重构)**, 其 W4 改动建立在"抽屉仍有 9 个操作按钮"的旧模板上; 主线先合了 `ada3d77`(index.html 大改 4398 行), 所以选择**在新基线上重放**而非 merge。判别这类线要不要合: `git merge-base --is-ancestor <关键重构提交> <旧线>` —— 不包含关键重构就应重放。**教训**: 当年"按字节核验挑文件重放"时只搬了 `config_editor.js` + `config/schema/*.py`, 把同一提交里 `index.html`/`style.css` 的部分判为"已被新基线取代"而跳过 → 直接造成上面第 6 条的两不管缺口(风险标识整整一轮无样式)。**重放一个提交时必须逐文件核验, 判定"跳过"的要写明理由并留缺口登记**。

### WEB UI 整页白屏: 一条注释续行落在已闭合的 `*/` 之后 (2026-09-17 实测)

- **症状**: 打开 `/atlas/`(与 `/prism/`)只看到页面背景色, 登录框/顶栏/表格全部没有; `getComputedStyle(document.getElementById('app')).display === 'none'` —— `#app` 带 `v-cloak`(Vue 未 mount 前隐藏), **Vue 一旦不 mount 它就永远隐藏, 于是"只剩背景"**。任何"整包 JS 语法/加载失败"都长这个样子, 见到"只剩背景"先按这条查。
- **根因**: `shared/app.js` 里 `* 列宽重实体化契约由 watch(page) 与 …` 这行**被留在已经用 `*/` 闭合的注释块之后**(波次三"以星图模板为基线重建 + 批量替换"引入) → 整文件 `SyntaxError: Unexpected identifier 'watch'` → app.js 一行都不执行。
- **定位手法(无需 node, 也不用搭冒烟基建)**: ①起静态服务即可复现: `.venv\Scripts\python.exe -m http.server <port> --directory src\auto_qb\web_ui\static`, 浏览器开 `/atlas/`; ②在 `page.addInitScript` 里挂 `window.addEventListener('error', e => push({msg:e.message, file:e.filename, line:e.lineno, col:e.colno}), true)` 然后 reload —— 直接拿到 `shared/app.js:1997:18`。**只靠后端日志/curl/pytest 都看不到这个错误**(静态文件 200、pytest 全绿)。
- **防回归**: `tests/test_web.py::test_frontend_static_bundle_health` 静态扫 `web_ui/static`(冲突标记残留 / JS 注释孤儿续行 / 模板引用的静态资源是否存在), 已做红绿验证 —— 对修复前的 app.js 精确报出 `shared/app.js:1997`, 对修复后的工作区 0 问题。
- **判别法**: 改完前端"页面整块没内容"时分两类查 —— ①**整页连骨架都没有**(含 v-cloak 未摘)= 包级失败(语法错误/404/文件被改名), 用上面手法看 `window.onerror`; ②**骨架在但某块区域空**(如设置页只剩分组标题)= 模板表达式错误(computed 当函数, 见上文 2026-09-14 两条), 只能真机看页面。

### 波次三复查: 三类"pytest 全绿但界面废掉"的结构性损坏 + 集成浏览器冒烟的坑 (2026-09-17)

> 用户反馈"统计/限速点不开、添加窗口/删除确认框弹不出、页面只剩背景"等一批问题, 逐一复现后**根因只有两个**(弹窗全灭 / 棱镜丢样式), 其余是需求口径偏差。三类损坏都靠静态扫描守阵(`test_frontend_static_bundle_health`)兜住。

1. **未闭合的 `<transition>` 会静默吞掉其后所有弹窗(本次最狠的一例)**: 详情抽屉外层多了一个 `<transition name="pop">`(波次一加内层 `name="drawer"` 时忘了先关它), 于是统计/限速/添加/分类标签管理/全局确认框**全部**被浏览器解析成它的子节点。Vue 的 `<Transition>` 只渲染**第一个**子节点 → 6 个弹窗全被丢弃: **点击毫无反应、控制台零报错、DOM 里连元素都没有**。判别法: 弹窗"点了没反应且无报错" → 先查它在模板里是否落在某个 `<transition>` 内(逐行数 `<transition>`/`</transition>` 的配对, 看弹窗所在行深度); 修完必须核对 `document.querySelectorAll('.modal-mask')` 的**父节点**不是 `TRANSITION`。
2. **CSS 规则漏 `; }` + 选择器头被吞 → 浏览器把其后规则整段丢弃**(棱镜 statics 大半丢失的真凶): `prism/css/views.css` 里 `.ce-subcard .ce-field { … padding: 7px 0`(漏 `; }`)与 `.ce-subcard { margin: …`(选择器头被吞, 只剩孤立声明 + 多余 `}`)是同一次批量编辑的两处残留。全文件花括号**是配平的**(两处互相抵消), 所以"数括号"查不出来; 但浏览器解析到第一条未闭合块后, 后续约 200 条规则全被当声明丢弃 → 棱镜页面的"选中底色/状态色/详情字段行/设置页栅格"等样式静默消失。定位法: 把 CSS 文本塞进 `<style>` 后比 `sheet.cssRules.length` 与顶层块数, 再用二分找第一处"解析数 < 应得数"的行。守阵已按"顶层规则未闭合而下一非空行又开新规则"判定(注释里不要写 `{`/`}` 字面量, 会干扰该判定)。
3. **不可见的全屏遮罩会拦掉整页点击**: `.drawer-mask` 关闭后若过渡未走完(见下条环境坑), Vue 不移除元素, 于是留着一个 `opacity:0` 的 `position:fixed` 全屏层吃掉所有点击/右键。加固: 模板 `<transition :duration="200">`(不依赖 `transitionend` 也能清理) + CSS `.drawer-mask.drawer-leave-active { pointer-events: none }`。
4. **集成浏览器(VS Code 内置页)里页面是 `hidden` 态**: `document.visibilityState === 'hidden'` 且 **rAF 完全不触发** → ①Vue 的 `<Transition>` 永远停在 `enter-from`(元素在 DOM 里但 `opacity:0`, 看上去"没渲染"); ②Playwright 的 `click()` 因拿不到两帧稳定盒模型而**全部超时**(报 "waiting for element to be visible, enabled and stable")。冒烟对策: 交互一律用 `page.evaluate` + `dispatchEvent(new MouseEvent('click', {bubbles:true, view:window}))`(JS 事件), 判定一律看 **DOM/状态**而不是 opacity; 视觉确认靠截图时要先注入 `*[class*="-enter-from"]{opacity:1 !important; transform:none !important}` 中和过渡类, 且截图可视区域小于 CSS 视口(固定定位元素可能落在截图之外, 用 `getBoundingClientRect` 判断而不是"截图里没看到")。
5. **状态栏/表头菜单等本轮口径修订(用户 2026-09-17 明确)**: ①底部状态栏 = 左统计摘要(本次/累计/连接/DHT/剩余)+完整统计入口, 右速度合计+限速入口, 删掉全局状态徽标(顶栏已有连接状态); ②页内第二套"分组/种子/追剧"切换器退役(顶栏一级导航已覆盖); ③已选批量条位置 = "做种数量统计(dist-legend)之后、筛选器之前"; ④TBL-03 是**文字颜色**不是背景色(状态语义色染名称/数值列文字, 0 值占位不染); ⑤明文"点击种子即选中"取消 —— 明细行/种子行普通点击不再选择, 只保留 Ctrl/⌘ 与 Shift; ⑥TBL-05 的表头右键菜单要的是「隐藏**该列**」(单列)而非笼统打开列选择器(列选择器仍作为菜单末项保留)。

### 知识库纪律: "立档规则"写在只对 `memory-bank/**` 生效的 instruction 里 → 3 天只立 1 档 (2026-09-17 诊断)

- **症状**: `memory-bank/tasks/` 在 09-14~09-17 三天里只有 **1 条**登记, 而同期 25 条跨会话大任务 (WEB UI 波次一~三 / 大文件拆分 / 依赖现代化 / tracker 分组 / 追剧视图…) 全部堆在 `activeContext.md` 的"会话纪要"里, 把"易变层"泡成了流水账。
- **根因 4 条** (按因果排序, 均有文件证据):
  1. **载体不存在**: `.github/skills/` 是空目录 — 大家口中的 "memory bank skill" 只是概念, 仓库里只有 `.github/instructions/memory-bank.instructions.md`。instruction 靠 `applyTo` 文件 glob 生效, skill 靠 `description` 语义触发, **两者发现机制不同**。
  2. **决策点与规则暴露点错位**(本次最机械的一条): 该 instruction 的 `applyTo: 'memory-bank/**'` 只在**编辑 `memory-bank/` 下文件时**注入上下文; 而"这个任务该不该立档"的决策发生在编辑 `src/`、`tests/` 的时刻 → 那一刻规则**不在上下文里**。规则必须写在决策点能看见的地方 (always-on 的 `AGENTS.md` / `.github/copilot-instructions.md`, 或 skill)。
  3. **规则不可判定**: 原文只写"跨会话的**大**任务要立档" — 无阈值 ⇒ 无法判定 ⇒ 默认不立档。改成硬阈值 (跨 ≥2 会话 / ≥5 轮指令或 ≥3 个源文件 / 出现"计划·波次·后续阶段" / 需产出交付文档) 后才可执行。
  4. **零机械后果**: 项目对代码约定有守卫测试, 知识库当时零校验 — 登记了没文件、纪要回流都不会被发现。现由 `tests/test_memory_bank.py` 双向校验索引↔文件/命名/状态分区/必备章节, 并禁止 `activeContext.md` 出现 `^- 2026-` 纪要行 (已做红绿验证)。
- **通用判别法 (给未来)**: 若某条纪律"反复强调但从不执行", 按顺序查 ①载体 (skill/instruction 文件真在吗) ②规则暴露点是否落在决策点 ③阈值是否可判定 ④有没有机械后果。四条缺任何一条, 纪律都会衰减。

### WEB UI 第九轮 (FX-01~FX-25) 的坑 (2026-09-17 实测)

- **Vue 模板解析不了下划线前缀标识符** (浏览器实测, `pytest` 全绿): 批量条改为直接渲染计数方法后写成 `{{ _bulkCountText() }}`, 运行期抛 `ReferenceError: _bulkCountText is not defined` 且**整块区域渲染失败**(控制台只有这一行, 页面其余部分照常, 极易漏看)。Vue 的模板编译器把 `_` 前缀视为自己的内部变量保留域。**规则: 凡是模板要调用的方法/属性一律不得以 `_` 开头** —— 内部的 `_bulkTargets` 可以留私有, 对外派生值叫 `bulkCountText`。判别: 界面"某个区域整体不渲染"而控制台只有一行 ReferenceError 时先看名字前缀。
- **浮层"点了没反应"= 缺定位祖先, 而不是事件没绑上** (FX-18 根因): `.pop-menu` 是 `position:absolute` + `top: calc(100% + 4px)`, 容器必须有 `position: relative`。包着路径输入框与按钮的 `.add-dialog-pathrow` 没有 → 最近定位祖先是 `.modal-mask`(`position: fixed; inset: 0`)→ `top: 100%` 换算到视口下沿之外, 面板被渲染到屏幕外。**同类坑第二次出现**(与 `.ctx-item.has-sub` 必须 relative 同源)。排查法: 打 `getBoundingClientRect()` 看坐标(本次实测 `pop.x` 为 0、`pop.y` 远超视口高)。
- **另一个"点了没反应": 全局点击关闭把刚开的面板当场关掉**: `document` 上的 window click 监听统一关闭各类浮层(设计如此), 而聚焦输入框用的是 `@focus` —— 聚焦由**点击**触发, 点击继续冒泡到 window → 面板开了又立刻关。修法: 触发行同时 `@click.stop`(项目内既有写法: 分类/标签输入框就是这么做的)。**规律: "聚焦即展开" 的输入框必须同时 `@click.stop`, 否则永远看不到面板。**
- **`min-height` 是含边框的**: 全局 `* { box-sizing: border-box }` 下, 想让"有/无某段内容"时行高完全一致, `min-height` 必须把 `border-bottom` 的 1px 算进去 —— 只写 `40px`(7px×2 内边距 + 26px 内容)在内容出现时会被撑到 41px(实测差 1px)。断言前先在浏览器里量, 别按 CSS 数值推算。
- **"模板里重复三份的口径"必须收成函数后再改**: 做种时长/分享率/用户·做种三列的口径原先在模板里各写三份(明细表 / 种子页 / 追剧集明细), 两套 UI 共六份 —— 本轮同时要改其中三条口径, 先抽 `cellSeedingTime`/`cellRatio`/`cellPeers` 再改模板是**唯一**不遗漏的顺序。**顺带**: 隐藏单元格用**空串**而不是 `v-if` 摘节点(单元格仍在 grid 里, 列宽与表头不错位)。
- **HR 条件必须进隐藏判据**: "0 分钟做种时长不显示"若只判 `seeding_time <= 0`, 会把"HR 已触发但还没开始做种"的种子一起隐藏 —— 而那正是最需要被看见的一类。隐藏判据 = `t <= 0 && !(hr_triggered && hr_req_time)`。
- **限速浮层必须是状态栏的兄弟节点**: `.statusbar` 有 `overflow: hidden`, 子元素溢出会被裁掉(表现为"点了没反应")。浮层用 `position: fixed` 挂到 `#app` 层, 只由 JS 写 `left`(并夹取到视口内), 纵向交给 CSS `bottom: calc(var(--statusbar-h) + 8px)`。
- **无遮罩浮层的"点空白关闭"要靠根节点 `@click.stop`**: 把 `.speed-pop` 的根加 `@click.stop`, window 监听才能只在真正点外部时关闭; `@click.stop` 缺失时点输入框也会关掉浮层。
- **mousedown 只在 `mousedown.prevent` 下才保得住输入焦点**: 自绘候选面板的选项若用 `@click` 选值, 浏览器会先把焦点从输入框移走(触发 blur 链); 用 `@mousedown.prevent` 才既不丢焦点又不丢选中。
- **原生 `<datalist>` 必须整体退役而不是"驯服"**: 它的建议浮层样式不受主题控制、会自行超时消失(用户报的"下拉 2 秒后消失"), 还与自绘面板抢同一次交互。删 `list=` 属性 + `<datalist>` 节点即可; 不要试图用 CSS 接管它。
- **复选框在"浮层/选项"语汇里被替换为切换胶囊**: `.opt-pill`(左色块 + 柔底 + 亮字 = 已选, 与筛选弹层 `.pop-item.on` 同构)。危险项用 `.opt-pill.danger.on`(错误色)。添加窗口 5 项与删除确认框 2 项共用同一份 —— 新增选项不要退回 `input[type=checkbox]`。
- **内容出现/消失导致的"高度跳动"用常驻占位解决**: 勾选后才出现的警告行用 `visibility: hidden`(保留真实占位高)而不是 `v-if`/`opacity`(前者不占位、后者仍参与布局但透明度不可见时可能被误判为不可交互)。实测勾选前后窗口高度差 0。
- **调试/演示时页面每 2s 整表重渲染会让 Playwright 动作失败**: 断言工具报 "another element intercepts pointer events" 且反复重试失败, 往往是轮询把行元素换掉了(不是产品 bug)。对策: 用 `force: true` 或在两轮轮询之间完成动作; 断言优先取值(`allInnerTexts`/`count`)而非连续点击。
- **跑冒烟前必须重启服务**: 上一轮被杀掉的页面脚本残留的轮询会在新服务起来后自动重连并继续执行"幽灵操作"(实测把新环境里的同名组删了), 导致后续断言全歪。

### 组件变体用 CSS 变量承载时, 后写的直接属性会让变体静默失效 (2026-09-17 实测, TASK014)

- **症状**: 基础层用 `.btn{background:var(--btn-bg,var(--primary))}` + `.btn-secondary{--btn-bg:#fff}` 这套"变量承载变体"的写法, 在**某些主题里变体全部退化成主色**(实测: 6 个按钮渲染成一模一样的黑底; 另一个主题里次级按钮的指定文字色丢失, 但边框色生效 —— 半对半错最迷惑人)。
- **根因**: 该主题的 CSS 里又写了一条 `.btn{background:#000}`, 同特异性下后写者胜 —— 它把 `background` 直接写死, **变量声明就成了死代码**; 而变体规则只声明变量、不写属性, 于是"看起来写对了, 实际全被压掉"。反过来若变体里既写变量又写死属性, 就出现"边框生效、底色不生效"的半生效态。
- **判别法**: 变体视觉不生效时, 先 grep 主题 CSS 里有没有同选择器的**直接属性**覆写(`.btn{background|color}`), 而不是去查权重/拼写。修法二选一并**全库统一**: ①主题只用 `--btn-bg/--btn-ink/--btn-hover/--btn-hover-ink` 变量覆写; ②变体直接写属性(不走变量)。混用必踩。
- **附带**: 悬停态也需要独立的文字色变量 —— 只改 `--btn-hover` 背景、文字色继承原 `--btn-ink`, 会在"悬停背景=墨色"的主题里造出白底白字(不可见但静态截图查不出来, 必须逐主题过一遍 hover)。

### 无头浏览器(Edge/Chrome headless)做渲染自检的三个坑 (2026-09-17 实测, TASK014)

- **`--window-size` 在 Windows 上被最小窗口宽度钳制**: 传 `--window-size=390,1250` 实际布局视口是 **481px** —— 截出来的图右侧内容被裁, 看起来像"移动端布局溢出", 实为假象。要验真窄屏: 用 `--force-device-scale-factor` 无效(它只放大渲染), 正确做法是**外层包一个 390px 宽的 iframe** 截图, 让被检页面自己按 390px 布局。判别: 截图里所有元素都在同一处被切断(而非个别元素溢出) 时先怀疑视口被钳制。
- **`file://...#anchor` 想截"滚动到某区块"会得到空白图**: 无头截图只绘制首屏, 滚动位置对应的区域未绘制 → 输出纯背景色(文件大小会突然掉到几 KB, 是很好的信号)。要截中间区块: 注入 `<style>` 把前面的区块 `display:none` 掉, 让目标区块落到首屏。
- **整页截图 + PIL 自动裁剪在"有平铺底纹/渐变背景"的页面上失效**: 裁剪靠"与右下角像素比对找内容边界", 而 22px 点阵、33px 网格、径向渐变让空区也不均匀 → 内容高度被算成整张图高(实测把 6.6k px 的页面读成 14k px)。对策: 裁剪后再按最大内容高**硬截**(如 8400px), 或按背景类型跳过自动裁剪。

### 并行 worktree 同时立档会造成重复档案与重复索引条目 (2026-09-18 实测, 多分支合并后)

- **症状**: `tests/test_memory_bank.py` 双向一致守卫报 `仅有文件=['TASK015']`、状态分区守卫 `KeyError: 'TASK015'`; 但磁盘上 `TASK015-ui-component-libraries.md` 与 `26-09-17-webui-component-libraries.md` **逐字节相同**(md5 一致), 索引里同一条 UI 组件库条目还被登记了两次(一次 `[TASK014]`、一次误写 `[TASK012]`, 与真实 TASK012「第十轮修复」撞号)。
- **根因**: 同一专题在两条分支上各自立档 → 编号各自递增(14 / 15), 合并后两边文件与索引条目**双双入库**。`_indexed_sections()` 是 dict, 同一 TASKID 重复登记会**静默覆盖** —— 所以"重复条目"这一半故障比"多余文件"更隐蔽, 双向一致守卫也查不出来。
- **修法**: 保留被索引登记且内容完整的那份(`TASK014`), 删除重复档案, 删掉索引重复条目, 并把档案内标题的错号(`# TASK012 —`)改正为与文件名一致的编号; 顺手修掉指向旧编号的失效相对链接(`tasks/TASK012-ui-component-libraries.md` → `TASK014-...`)。
- **守卫**: 新增 `test_task_ids_and_slugs_are_unique`(档案 slug 唯一 + 索引同 ID 只登记一次), 把这类重复拦在"合并后第一次跑测试"。立档前先查 `tasks/_index.md` 是否已有同专题档案, 能直接避免。

### qB API 没有"错误原因"字段 + WebUI 错误原因预取的设计约束 (2026-09-18 实测, TASK015)

- **核实结论(别再翻第二遍)**: qB Web API 的 **`torrents/info` 不含任何错误文本/原因字段** —— 只有粗粒度的
  `state` 字符串(`missingFiles` / `error`, 见 `serialize_torrent.h` / `torrentscontroller.cpp`)。错误文本
  **只**存在于 **`/torrents/trackers`** 的每条记录里(`msg` 文本 + 数值 `status`)。因此"界面显示具体错误原因"
  **不存在直接透出这条路**, 只能①由状态派生(`missingFiles` 自明)或②额外调 API 取 `trackers.msg`。
  `qbittorrentapi` 侧对应 `TorrentState.is_errored`(={MISSING_FILES, ERROR})与 `TrackerStatus`
  (4=NOT_WORKING / 5=TRACKER_ERROR / 6=UNREACHABLE 是"报错"三态)。
- **视图组装里绝对不能发 qB API**(这是本项目的硬约束, 不是优化): 视图可能**每 tick 重建**
  (`ensure_group_view` 脏窗口), 在里面发 API = 主循环被 N 次网络往返拖死。取数一律**主循环预取 + 视图只读缓存**。
- **预取必须 TTL + 单轮预算双限额**: ①错误种子会**成片**(整站挂掉 / 批量文件丢失), 全量拉会把主循环卡住
  → 单轮预算(本项目 `ERROR_REASON_BUDGET = 5`), 余下按轮次摊开; ②`msg` 随站点状态变化, 不能永久缓存
  → TTL(本项目 300s)。**先写时间戳再拉取** —— 拉取失败也不在 TTL 内反复重试。
- **`missingFiles` 必须排除在拉取分支外**: 原因自明("文件丢失"), 再花预算去拉 tracker 是浪费; 而"文件成片丢失"
  恰恰是最需要保住预算的场景(实测该分支会吃掉预算并产生多余 tracker 调用)。
- **非快照字段的脏判定必须显式置**: 缓存槽若**不进** `_SNAPSHOT_FIELDS`/`_raw`(本项目刻意如此, 免得污染
  `apply_delta` 与快照槽守卫), 则 `store.view_changed` **覆盖不到它** ⇒ "种子数据一字未变、原因却变了"时视图
  不会重建。判别法同"配置派生的展示值": **值能在数据不变时变化 ⇒ 变化方负责 `_group_view_dirty = True`**。
- **取数单点放后端, 前端只展示**: 原因文本由后端 `_error_reason()` 一个出口算好透出(`error_reason`), 前端
  `stateText(m)` 仅在 `kind === "error"` 且有值时采用, 其余回落 `kindText`。**前端不得按 state 猜原因**
  (与 HR 标签/悬浮提示同纪律); `kindText` 继续服务状态图例 / 筛选器 / 组级与集级聚合文案(那里没有"某一种子的原因")。

### flex 子元素里的**裸文本节点**不可省略 —— 长文本要包一层 span (2026-09-18 实测, TASK015)

- **症状**: 状态列(tracker 报错原文可能很长)在窄列里**不省略、把行顶宽**; 给容器加 `min-width: 0` +
  `overflow: hidden` + `text-overflow: ellipsis` 也无效。
- **根因**: 该格是 flex 子元素, 里面是**匿名文本节点**(直接 `{{ text }}`)。`min-width: 0` 只对**盒**生效,
  匿名文本节点不可压缩 → 省略规则无处落脚。修法: 文本包一层 `<span class="state-text">`(它才是可压缩的盒,
  再对 span 写 `min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap`), 容器给 `title` 看全文。
- **判别**: "加了 ellipsis 却不生效" 且该处是 flex/grid 子元素时, 先看被省略的是**盒**还是**裸文本节点**。

### 无头 Chrome 冒烟本轮踩到的四个环境坑 (2026-09-18 实测, TASK015)

- **`--headless=new` 在本次环境挂起/无输出**(首个 dump 尝试直接收到 SIGTERM), 回落 **legacy `--headless`**
  可用(会打印无害的 net/disk-cache stderr 噪音, 可忽略)。
- **临时注入的路由会被 `StaticFiles` 挂载(`/`)遮蔽**: `create_app` 最后把静态目录挂到 `/`, 之后新增的路由
  永远匹配不到(表现: 注入的 `/smoke-seed` 返回 **404**)。修法: 把注入路由**插到 `app.router.routes` 最前**。
- **注入脚本必须放 `<head>`(在 `app.js` 之前)**: 放在 `</body>` 时 `app.js` 已执行完(已读过 `localStorage`
  的视图偏好), 注入无效; 想让页面按指定视图启动, 只能在 `app.js` 读偏好**之前**写 `localStorage`。
- **`--dump-dom` 里顶层 `id="app"` 的 DOM 是整整一行**: 按行 grep 渲染出的单元格会**全部落空**(只剩 `x-template`
  片段能命中), 容易误判成"页面没渲染"。要判渲染结果请对整串做正则/子串匹配, 或用截图。

### 合并冲突处理把 UTF-8 当 GBK 写入 → 文档乱码且不可逆, 藏了 3 天 (2026-09-18 实测修复)

- **症状**: `memory-bank/progress.md` 有一行是 `- TorrentRecord 鍏ㄥ瓧娈电紦瀛?(2026-09-15): …`, 且**行内两条目之间的换行丢失**(被粘成一行, 长度 1100 字符); 文件其余部分完全正常 → 扫过去像"某条老记录", 肉眼极易漏过(实测存在 3 天, 期间多次提交都没人发现)。
- **成因**: 合并 `beef5bb`(merge backend/develop) 时冲突处理把 UTF-8 字节按 GBK 解码后写回。含**私用区字符**(`\ue0a4` 等)与 `?` 替换符 ⇒ **不可逆** —— `s.encode("gbk").decode("utf-8")` 这类"反解"救不回来。
- **检测**: 统计每行"GBK 误解码高频字"密度(`鈥 鍏 锛 涓 鐨 娴 鍩 缂 瀛 娈 缂 撳 …`)即可定位; 或直接 `grep -c "鍏ㄥ瓧娈电紦瀛"`。
- **恢复(别反解, 从 git 取原文)**: 关键是**取哪一侧的版本** —— 先 `git cat-file -p <merge>` 列出父提交, 再逐父 `git show <parent>:<file>` 比对, 确认该条目只来自哪一侧(本次 `998136f` 是唯一来源, 另一父根本没有该条目)。整行替换后三项核对: ①无乱码字符 ②相对链接全部存在 ③**行尾风格不变**(本仓库工作区是 CRLF, 用 `\r\n` 写回, 否则整文件 diff 炸开)。被粘连进来的重复条目若在别处已有正确副本, 直接丢弃即可。
- **顺带(两类缺陷要分开查)**: 同一文件另有 4 处 `docs/*.html` 相对链接, 在 `docs/` 迁入 `docs/plans/<日期-时间>-*` 后未同步 → **失效链接**。修乱码时顺手做一次全文件链接存在性扫描(把 `](target)` 逐个 resolve), 别只修乱码就收工。
- **验证编码一律用 Python 显式按 UTF-8 读, 别信 Git Bash 的管道输出**(本次差点误判): `sed -n '11,17p' file | cut -c1-260` 对**完好的** UTF-8 文件会打印出 `WEB UI 绗�涔濊疆淇�澶�` 这种"乱码", 而 `git diff | cat` 同一批行却是正常的 —— 这是**控制台/管道解码层**的问题(Windows 控制台代码页), 不是文件坏了。判据: `open(p,"rb").read().decode("utf-8")` 不抛错 且 `"\ufffd" not in text` ⇒ 文件没问题(真乱码文件的特征正是含 U+FFFD 替换符)。**同一环境里 `sed` 有的文件正常有的"乱码"**, 所以不能靠"换个命令试试"下结论。

### "两套 UI 同口径"必须逐 UI 核对 —— 第九轮 FX-06 只落了棱镜, 星图漏改藏了两轮 (2026-09-18 实测, R12)

- **症状**: 用户反馈"暂停的种子状态色**还是**太白"。第九轮 FX-06 的诉求原文就是"暂停中的种子状态色'太白'(无颜色)",
  且计划文档里写明了修法(五主题补 `--paused/--paused-soft/--paused-line` + 补 `.g-status.k-paused` 等修饰符),
  验收时也确实"过了" —— 但**只改了棱镜**(`prism/css/components.css` + `themes/*.css`)。
- **真因**: 星图 `atlas/style.css` 是**独立的一套主题**(只有 `:root` 一组暗色令牌, 不共享 `tokens.css`),
  FX-06 的令牌与修饰符在星图**完全缺失** ⇒ `.g-status.k-paused` 落回基类 `.g-status` 的 `background: var(--surface-2)`,
  暗底上 = **白 6% 的"白底灰字"** —— 这正是"太白"的观感来源。
- **判据(自查手法)**: 凡"状态色/令牌族/修饰符"类改动, **按选择器在两套 CSS 各 grep 一遍**(`.k-paused`/`.site-chip.paused`/
  `.member-row.paused`/`--paused`), 数量对不上就是漏改。仅改 `shared/app.js`(逻辑层)才天然两套生效。
- **口径落点**: 星图 `:root` 与棱镜 `themes/*.css` 的 `--paused` 三值**必须逐字同值**; 星图 `--paused` 指向 `--fg-muted`
  (即"已暂停"状态文字那支色), 棱镜同。**不要**给暂停铺任何底(包括 `--surface-2`): 暂停是"无色相"那一支,
  表达方式是"不铺底 + 中性描边", 与四个有色底(绿/蓝/红/琥珀)并列时层次反而更清楚。

### 视觉类改动的核对手法: 桩 `/api/state` + 系统 Edge + 主题注入 (2026-09-18 实测, R12)

纯 CSS 改动"pytest 全绿但观感不对"是常态, 且本项目有 **2 套 UI × 6 套主题**(星图 1 + 棱镜 5), 靠推理不可靠。
可复用的最小手法(不必起真 qB, 不必 `uvicorn`):

1. **造真 state**: 用项目自带 `tests/helpers.py`(`make_manager` + `FakeTorrent` + `seed_store`)灌入覆盖**全部 6 种 kind**
   的种子(seeding/paused/downloading/checking/error/other), 设好 `store.groups`/`member_to_key` 分组, 再
   `mgr.ensure_group_state(-1)` + `mgr.status_snapshot()` 拼成 `/api/state` 的响应体落 JSON。
   **必须用 `uv run python` 跑**(裸解释器缺 `qbittorrentapi`); 脚本放临时目录, 别进仓库。
   **追剧视图(`shows`)要另外合成**: 后端 `_shows_view` 依赖 `tvshows` 配置, 临时 manager 造不出来 ——
   直接按前端消费的形状手写 `{list:[{key,name,episode_count,latest,seasons:[{season,gaps,episodes:[{key,state,members,count,progress,size,...}]}]}],unrecognized:[]}`
   塞进响应体即可(`ep.key` 取 `["ep", N]` 三形态之一; `members` 里的 hash 复用**已灌进 `torrents` 平铺视图**的种子,
   前端 `memberByHash` 才能解析出成员)。集行是 `group-row ep-row s-<state>`, 与种子页行同一套状态色规则。
   另外**状态分布条/图例(`.status-strip`)**在**吸顶条**里, 不在 `.content` 内 —— 截 `.content` 拍不到, 要单独截该元素。
2. **桩 + 静态服务**: 一个几十行的 node 脚本起 `http` 服务指向 `src/auto_qb/web_ui/static`, 再用 Playwright 的
   `page.route("**/api/**")` 把 `/api/config/public`(回 `{web:{skip_local_verify:true}}` 免鉴权)、`/api/state`(回上面的 JSON)、
   `/api/stats`/`/api/log` 全部 stub 掉 —— **不用起后端**。
3. **主题**: 棱镜主题由 `localStorage["autoqb.ui.theme"]` 决定, 用 `context.addInitScript` 在页面脚本前写入即可逐主题出图
   (星图无主题切换, 只有一套暗色)。
4. **浏览器**: 本机 `ms-playwright` 里的 chromium 版本常与 `npm i playwright` 装到的版本**对不上**
   (`Executable doesn't exist at ... chromium_headless_shell-1243`), 不必下载 —— 直接用系统浏览器:
   `chromium.launch({ channel: "msedge" })`(Windows 自带 Edge; `channel: "chrome"` 亦可)。设 `deviceScaleFactor: 2` 再裁剪放大,
   才能肉眼分辨 `--fg-muted` 与 `--fg-dim` 这种一档灰差。
5. **对照出图**: 改动前后各跑一轮(文件名带 `before`/`after`), 逐张比对; 关注 `暂停` 行是否还"发白"、进度/状态两列文字是否
   随状态变色、以及**亮色主题**(frost/golden)下中性描边是否够可见 —— 亮色主题是这类"无色相"改动最容易翻车的一侧。

### 测试真的会弹系统通知: MagicMock 配置绕过 notify_fatal 守卫 + "换后端 ≠ 不发" (2026-09-18 实测)

**现象**: 跑 `uv run pytest tests` 时弹出系统通知框(本机实测标题 `auto-qb 已停止`)。

**主犯**: `test_cli.py::test_main_qb_compat_error_clean_exit` 把 `manager` 设成 `mock.MagicMock()`, 于是
`cli.py` 致命退出路径的 `notify_fatal(msg, manager.config.notify)` 拿到的是**恒真的 MagicMock** ——
`notify_fatal` 的守卫 `if not config or not config.enabled` **放行**, 真的构造 `PlatformChannel()` 并
`send("auto-qb 已停止", ..., urgent=True)` ⇒ **真发一条 Windows toast**。修法: 该测试 mock 掉
`auto_qb.cli.notify_fatal` 并断言调用(顺带把"致命退出要补发通知"这条也测了)。
**通用教训**: 给被测代码传 `MagicMock` 当配置对象时, **任何 `if not cfg.xxx` 形式的守卫都会放行** ——
凡是守卫后面接着"真实系统副作用"的路径, 测试里必须显式 mock 那个副作用入口。

**从犯**: 测试里写 `PlatformChannel("linux")`(`test_ui.py::test_notify_handler_enabled_toggle`、
`test_notify.py::test_notify_emit_exception_swallowed` / `test_notify_close_twice_safe`)只是**换了个后端**,
`NotifyHandler` 的后台 daemon 线程照样真实执行 `notify-send` —— 在**装了通知器的机器**(Linux 开发机 /
带 libnotify 的 CI)上就是真的弹通知。

**处置**: `tests/conftest.py` 会话级夹具把通知器命令名(`notify-send`/`osascript`/`powershell`/`pwsh`)拦在
`subprocess.run` 之前(抛 `OSError`, 等价于"机器上没装通知器")。要点三条:
① **只拦命令名**, 不拦 `_build_*` 的命令**构造**(结构断言照常)与 `node --check` 等非通知器子进程;
② 需要真实 `subprocess.run` 的用例(如 `test_notify_channel_send_failure`)自行 monkeypatch 即可自然覆盖夹具;
③ 夹具让 `send()` 走"发送失败"分支(返回 False, 只记 DEBUG), **调用方语义不变**。

**排查方法论坑(差点误判成"没问题")**: 诊断插件的输出**不能写 `sys.stderr`** —— pytest 会按用例捕获 stdout/stderr,
**通过的用例直接丢弃**, 于是"真实发送"的横幅全被吞掉, 统计出来是 0(假阴性)。必须写**文件**。
另一个同源坑: 日志/输出里的中文会被写坏, **统计一律用 ASCII 标记**(本次先按中文串 grep 得到 0, 改用 `CMD:`/`REAL SEND` 才看到真相)。
正确姿势: 探针挂 `subprocess.Popen.__init__` + `PlatformChannel.send` + `NotifyHandler.emit`, 三者都往同一个**文件**追加,
并用 `-p <plugin>` 注入。

**教训**: 想"测试里不产生系统副作用", 不能靠"换一个后端/换一个平台"绕过 —— 要么拦在**真实执行点**, 要么让被测代码
**可注入**(本项目 `NotifyHandler` 已支持传任意 channel)。同理适用于 `_register_appid_registry`(真写注册表 +
清理开始菜单 `.lnk`)与 `autostart`(真写 HKCU Run) —— 这些已有逐用例的 monkeypatch, 新增测试务必照做。

### FakeClient.torrents_add 总会登记种子: "重加后确认不到"不能靠"不预置"构造 (2026-09-19 实测)

写 `test_checking_skip_readd_unconfirmed_backs_up`(跳检"重加已发出但轮询确认不到"分支)时踩到:
以为"不预置 `client.torrents["HASH123"]`"就能让 `_poll_until(torrents_info)` 失败, 实测**走的是成功分支**
(还写了 `skip_check_day`)。原因: `tests/helpers.py:223` 的 `FakeClient.torrents_add` **无条件**把
`self.torrents["HASH123"]` 登记进去(这是它的正确语义: add 成功则种子存在)。

**正确构造**: 子类化客户端, 在 `super().torrents_add(**kw)` 之后 `self.torrents.pop(hash, None)`,
精确模拟"add 返回成功、但客户端里迟迟查不到该种子"。

**通用教训**: 测试替身的"成功路径"往往**顺手把状态补全了**, 想测"成功之后的下一步失败",
不能靠"不准备前置状态"(替身自己会补), 必须在**替身动作之后**动手脚。

### 本机测试速度画像: 按文件差两个数量级, 别盲跑全量等 (2026-09-19 实测)

**2026-09-19 二次实测修正 —— 下面第一段数字作废**: 那是**并发跑着多个 pytest 时**测的(CPU 争用),
严重失真。空载单机实测: **全量 1036 条 ≈ 32 秒**(带 `--cov-branch`), `--no-cov` ≈ 25 秒;
`test_web.py` 3 条 39s 的那次同样是并发污染 —— 全量里它根本不是瓶颈。**结论: 直接跑全量即可, 不必挑子集。**

(已作废的旧数字, 留作对照: `test_rule_engine + test_qbmanager + test_state_matrix` 159 条 0.93s、
`test_checking` 24 条 1.7s、`test_utils` 45 条 **156s**、`test_web` 9 条 **312s** —— 与空载实测差一个数量级,
唯一解释就是并发争用。)

**做法**: 改代码后跑**受影响文件 + `-k` 子集**做快速迭代(几秒出结果), 提交前跑一次全量(约 30 秒,
完全等得起)。**绝对不要同时起两个 pytest** —— 见下一条。另: 别用 `| tail -N` 接 pytest ——
会**缓冲到进程结束**才出任何输出, 期间完全看不到进度, 容易误判成"卡死"(曾据此白等 27 分钟并误杀进程)。

### 环境能力缺失 ≠ 代码缺陷: APPDATA 未设 / 沙箱把 symlink 落成真目录 (2026-09-18 实测)

全量测试在本机(沙箱化 shell)曾有 **2 个稳定失败**, 排查后都是**环境能力**差异, 不是代码错 —— 记录判据与修法:

1. **`test_notify.py::test_notify_legacy_shortcut_cleanup`**: 该用例 monkeypatch 了 `os.path.exists` / `os.remove`
   来"删旧 `.lnk`", 但 `PlatformChannel._legacy_shortcut_paths()` 在 **`APPDATA` 未设时直接返回 `[]`** ⇒
   路径清单为空、`os.path.exists` 根本不会被问到 ⇒ `removed` 恒空、断言必失败。
   修法: 用例显式 `monkeypatch.setenv("APPDATA", ...)`, 顺带真正覆盖了路径拼接分支(此前在无 APPDATA 环境等于空跑)。
2. **`test_web.py::test_api_fs_dirs_endpoint`** 第 ⑤ 条"符号链接逃逸"断言: 本机
   `os.symlink(dir, link, target_is_directory=True)` **返回成功但落成真实目录**(实测 `islink=False`,
   `lstat mode=0o40777`) ⇒ `realpath` 仍在根内 ⇒ 逃逸链接被**正常列出** ⇒ 断言失败。
   **生产代码没问题**(`_within_roots` 走 `normcase(realpath())`, 真链接会被挡掉), 是**沙箱/文件系统重定向层**
   表达不了"逃逸链接"这个场景。修法: 建链后补一道 `os.path.islink(link)` 判定, 不是真链接就跳过该断言
   (与用例原有的"Windows 无权限建链 -> 跳过"同一口径; 真机上能建真链接时照常断言, 覆盖率不减)。

**通用教训**: 断言"环境相关能力"的测试必须**显式给定前提**(setenv / 明确的跳过条件), 不能依赖宿主环境。
判据: 该用例 **单跑通过、全量失败**, 或 **本机失败但从逻辑上看不出问题** ⇒ 先怀疑环境能力(环境变量、
符号链接权限、注册表 / 文件系统重定向), 再怀疑代码。**排除环境之前不要动 `src/`**。

**顺带修的一处噪声**: `.gitignore` 原本只忽略 `.coverage`(**精确名**, 不带通配), 而覆盖率并行数据文件名是
`.coverage.<host>.<pid>.<随机>` ⇒ 会漏进 `git status` 变成未跟踪噪声(易被误当"该提交的东西")。已补 `.coverage.*`。

### 测试期"真实系统副作用"普查: 手法 + AUMID 注册表键 (2026-09-18 实测)

**为什么要普查**: 修完通知弹框后, "测试会不会碰真实系统"只答了一半 —— 通知只是**已知的一种**。
把**所有**真实副作用都记下来再逐类判定, 比逐个猜可靠。

**探针手法(可复用)**: 一个 pytest 插件, 在 `pytest_configure` 里 patch 五类入口, 输出**一律写文件**:
① `subprocess.Popen.__init__`(外部进程) ② `winreg.CreateKeyEx`/`SetValueEx`/`DeleteKey`/`DeleteValue`(注册表)
③ `os.remove`/`unlink`/`rmdir` + `shutil.rmtree`(文件删除) ④ `os.symlink`(建链) ⑤ `socket.socket.bind`(网络监听)。
`-p <插件名>` 注入 → 跑全量 → 按类别 `sort | uniq -c` 归类判定。
**过滤临时目录的坑**: 用 `tempfile.gettempdir()` 做 `abspath` 前缀过滤会被 Windows 长路径前缀 `\\?\`
绕过(`abspath` 不剥它) —— 本次 157 条"仓库外删除"**全是这个假阳性**; 改用"路径里是否含 TEMP"复核,
才发现全部落在 `C:\TEMP\pytest-of-*`。**别只信 abspath 前缀**。

**普查结论(2026-09-18, 全量 1007 项)**:

| 类别 | 实测 | 判定 |
|---|---|---|
| 外部进程 | **0** | 通知拦截夹具生效 |
| 注册表 · **AUMID 键** | **真写 2 值, 写完不清理** | ⚠️ **唯一真问题** —— 已加会话级守卫 |
| 注册表 · HKCU Run 键 | 写 + 删(自清理) | 既有明文约定(`test_autostart_windows_registry`, [testing.md](testing.md) 已记) |
| 文件删除 | 157 条, **全部**在 `C:\TEMP\pytest-of-11059\` | 仓库内 0、仓库外 0 |
| 建符号链接 | 117 条: pytest 自己的 `pytest-current` + 逃逸用例 | 全在临时目录 |
| 网络监听 | 161 条回环随机端口(`FakeQbServer`)+ 2 条同端口重启复现 + 1 条随机端口 | 全是 `127.0.0.1`, 自清理 |

**AUMID 键为什么值得修**: `PlatformChannel("win32")` 构造时会调 `_ensure_appid_registered()` **真写**
`HKCU\Software\Classes\AppUserModelId\AutoQB.UI`。与 autostart 的 Run 键的**关键区别是它不清理** ——
每跑一次测试就在用户注册表里留一个持久键。触发用例是 `test_notify_legacy_shortcut_cleanup`
(它只想测 `.lnk` 清理, 注册表写入是顺带发生的; 另两个构造 win32 渠道的用例都显式 patch 了注册环节 ——
**同一个类里两种写法并存, 正是"逐用例 patch 容易漏"的实证**)。
**修法(conftest 第二道会话级守卫)**: 只把**属于 AUMID 前缀**的 `CreateKeyEx`/`SetValueEx` 变成空操作,
其余注册表写入放行 ⇒ autostart 的 Run 键测试行为完全不变。
**两个关键细节**: ①让写入**静默成功而不是抛异常** —— `_ensure_appid_registered()` 只 catch `OSError`,
抛异常会让 `channel._appid` 回退成 `WINDOWS_TOAST_APPID_FALLBACK`、打乱既有断言;
②`CreateKeyEx` 的替身**必须支持 `with` 语句**(源码是 `with winreg.CreateKeyEx(...) as key:`)。

**后续: 普查能力已固化** (2026-09-18): 那次用的临时探针在 `%TEMP%` 里、会随会话消失,
同类问题下次还得靠人肉发现。已固化为 `tests/sidefx.py`(记账器 + 放行清单 + `is_violation` 判定)
+ `tests/conftest.py` 会话级 autouse 夹具(收尾有越界项即让本次 pytest 失败)
+ `tests/test_sidefx.py` 策略单测(8 项)。两个实施细节值得记:
①`StubRegKey` 放在 `sidefx.py` 而不是 conftest —— 记账器据此识别"被 AUMID 守卫拦下的调用";
**否则两个夹具谁先安装会让 AUMID 键一会儿被记成越界、一会儿不被记**(顺序依赖是隐藏 bug 的温床,
这次用"替身类型识别"把它变成顺序无关); ②`SetValueEx` 只记值名不记键路径 —— 本仓两处调用都紧跟
`CreateKeyEx`, 键路径由 `REG` 那条记录覆盖(已在模块 docstring 写明这一局限)。

**补 `LAUNCH` 类 + 端到端验证** (2026-09-18): 记完五类后发现还有口子 —— `os.startfile`(开资源管理器) /
`webbrowser.open`(开浏览器)/ `os.system` **不走 `subprocess`**, `POPEN` 抓不到; 而 `utils.open_path()`
在 Windows 上就走 `os.startfile`, `/api/open-path` 能触达它 —— 与用户最初报的"测试时弹出系统通知框"同一族。
新增 `LAUNCH` 类, **放行清单为空**(`subprocess.call/check_output/run` 内部都走 `Popen`, 由 `POPEN` 覆盖, 不重复)。
单测里**不真调用**这些入口(那本身就是越界副作用、会让会话夹具报错), 只验证"入口已被包装"。
**端到端验证(重要)**: 用独立脚本跑(不经 pytest ⇒ AUMID 守卫不生效)构造 `PlatformChannel("win32")`,
记账器确实抓到 `REG: ...AppUserModelId\AutoQB.UI` + `REGVAL: DisplayName/IconUri` 三条越界,
并正确放行了临时目录删除与回环监听 —— 证明"守卫一旦失效就会被记账器抓到", 而不是靠"检测不到"蒙混过关。
**以后动这类守卫都要做一次这种"撤掉守卫看它报不报"的验证, 否则可能只是装了个永远不触发的空壳。**

**再补 `CONNECT`** (2026-09-18): 原本只记 `BIND`(监听), **出站连接是盲区** —— 测试若真连了外网
(慢、不稳定、还可能泄露数据)看不出来。新增 `CONNECT` 类覆盖 `socket.socket.connect` 与
`socket.create_connection`, 放行条件同 `BIND`(回环)。**全量实测零越界 ⇒ 本项目测试确实全部走回环、零外网连接**,
这条也顺带成了"测试不依赖外网"的守阵(以后谁在测试里引了真外网请求会立刻失败)。
自此记账器共 **七类**: `POPEN` / `LAUNCH` / `REG` / `REGVAL` / `FSDEL` / `SYMLINK` / `BIND` / `CONNECT`
(前两个算"启动类", 后两个算"网络类")。**仍未覆盖**: 文件**写入**(`open(...,'w')`)与 `os.rename/mkdir` 等 ——
`coverage`/`pytest` 自身会在仓库根写 `.coverage`、`.pytest_cache`, 要放开它们就得开白名单, 收益不抵噪音,
暂不做; 真要防"测试写脏仓库", 靠 `git status` 更直接。

### 改文件名 / 移动文档后不查全仓引用 → 留下坏链, 且没有任何测试会报错 (2026-09-18 实测)

- **症状**: 文档改完名, 引用方仍指向旧路径 —— 页面点开是 404、本地文件打不开。最坏的是**坏链不会让 pytest 失败**: `tests/test_memory_bank.py` 只查索引↔文件双向一致与必备章节, **不校验链接有效性**, 所以坏链可以长期静默存在, 直到有人点开才发现。
- **根因**: ①只扫 markdown 链接语法 `[x](y)` 会漏掉两类引用 —— HTML 里的 `href="..."`、以及表格与正文里的**裸路径**(不带链接语法的 `docs/plans/xxx.md`); ②`git mv` 只搬内容, **不会改写任何文本引用**; ③其余 8 个 worktree 各有一份 `memory-bank/` 副本, 改名不同步。
- **实测**: 2026-09-18 把 `docs/plans/26-09-17-0346-webui-qb-replace-wave3-handover.md` 转 HTML 时全仓 grep, 发现 `26-09-16-1128-webui-qb-replace-wave3-plan.html` 里写的是 `href="webui-qb-replace-wave3-handover.md"` —— **缺 `26-09-17-0346-` 日期前缀, 是个早就存在的坏链**; 本次改名若跳过查引用, 还会新造 8 处(`progress.md` 2 + `TASK002` 5 + 该 plan 1)。同源的上一批: `04d928b` 修掉 `modules.md` 与 TASK001~011 中 **34 处** `docs/*.html` 旧路径(当时"只扫 markdown 链接, 纯文本引用一直漏着"), 另修 `tasks/` 下 5 处 `../docs` 应为 `../../docs`; 那次靠人工复扫 170 条链接 + 107 条路径才收口。
- **修法(改名三步, 缺一不可)**: ①改之前先全仓 grep 旧文件名统计引用数(含 `.html` / `.md` / `.py` / `.yml`, 排除 `uv.lock`); ②用 **Python 显式 UTF-8** 批量替换(不要 PowerShell 重定向, 见本文件编码坑); ③替换后再 grep 一次确认为 0。
- **判别法**: 只要动 `docs/` 或 `memory-bank/` 下的文件名, 必须走这三步 —— **不要凭"我记得没人引用它"跳过**, 上面那个既有坏链就是这么来的。
- **已知守卫缺口(建议, 未做)**: 加一个链接守卫测试, 扫描 `*.md` / `*.html` 里的相对链接指向的文件是否存在。2026-09-17 那 34 处是人工扫出来的, 机器化之后不会再漏。

### 在 pytest 里用 subprocess 跑脚本会被副作用记账器判为越界 (2026-09-18 实测)

- **症状**: 给 `tests/test_memory_bank.py` 加"索引是否为生成结果"的守卫时, 用 `subprocess.run([sys.executable, "scripts/gen_tasks_index.py", "--check"])` 实现 —— **单独跑该测试通过, 跑整个文件时却是 `ERROR` 而不是失败**(`8 passed, 1 error`)。
- **根因**: 本项目禁止测试启动外部进程(`tests/sidefx.py` 七类副作用记账, `POPEN` 放行清单为空, 见 TASK016 收口)。`subprocess` 起的 Python 子进程被记入台账并判为越界, 由**会话级守卫在收尾时报错** —— 所以报错出现在收尾而不是断言处, 单独运行时看不出来。
- **修法**: 守卫改为在**进程内**加载脚本模块并比对字符串, 零子进程(也更快):
  `spec = importlib.util.spec_from_file_location("gen_tasks_index", GEN)` → `module.render(module.collect())` 与磁盘 `_index.md` 逐字节比对; 语义与 `--check` 等价。
- **判别法**: 测试代码里一旦出现 `subprocess` / `os.system` / `os.startfile` / `webbrowser.open`, 先怀疑会被 sidefx 拦下 —— 尤其"单独跑绿、全量跑 ERROR"这种症状, 基本就是它。

### WorkBuddy 项目级 skills 挂在 `.codebuddy/skills`, 不是 `.workbuddy-ai/skills` (2026-09-18 实测)

- **症状**: 把 `.agents/skills` 链接到 `.workbuddy-ai/skills` 之后, 会话的技能列表里一个项目级 skill 都没出现。
- **根因**: 内置 CLI 运行时 `cli/dist/codebuddy.js` 的 `SkillLoader.loadSkills()` 只扫三类根 —— `PathUtils.getProjectSkillsDir()` = `<workspace>/.codebuddy/skills`、`getHomeSkillsDir()` = `$CODEBUDDY_CONFIG_DIR/skills`、`$CODEBUDDY_SESSION_SKILL_DIRS`(path.delimiter 分隔, 仅当次会话有效)。产品文档里写的 `.workbuddy-ai/skills` **这个 CLI 根本不读**(对该 bundle 全量 grep `workbuddy-ai`: 0 命中)。
- **递归坑**: `scanSkillsDirectory()` 会**递归最深 5 层**收集每一个 `SKILL.md`, 不是只读顶层。整棵 `.agents/skills` 挂上去 = 213 条技能, 其中 193 条来自 `autoclaw-design-capability`(12MB 设计预设库)及其完整副本 `autoclaw-design-capability_noqa`; 按 name 去重后仍会全部注入系统提示, 严重挤占上下文。
- **现状**: `scripts/sync_agent_skills.py` 只把 21 个顶层 skill 以目录联接(junction, 免管理员权限)挂到 **`.codebuddy/skills` 这一处**, 排除上述两个预设包; 幂等, `--prune` 清失效链接, `--dry-run` 预演。源目录 `.agents/skills` 仍是唯一事实源(已入库), 链接两边读写同一份文件。
- **不要再给 `.workbuddy-ai/skills` 留兼容链接** (2026-09-18 已移除): 该路径 CLI 不读, 留着只会多一处需要同步、且容易让人误判"链接在、为什么没生效"。`.workbuddy-ai/` 下现在只剩会话记忆目录 `memory/`。
- **维护约束**: junction 不会自动跟随源目录增删 —— **在 `.agents/skills` 里增删 skill 后必须重跑该脚本**, 否则新 skill 不会出现在列表里。
- **判别法**: 技能没出现, 先查两件事 —— ①链接是否建在 `.codebuddy/skills` 下(不是 `.workbuddy-ai/`); ②是否重启了会话(技能列表在会话启动时加载一次)。
- **完整挂载清单 (2026-09-18 实测枚举, 按加载优先级从高到低, 同名先到先得)**:
  1. **project** `<workspace>/.codebuddy/skills` —— 21 条(本仓库 junction 挂载)
  2. **user** `$CODEBUDDY_CONFIG_DIR/skills` = `C:\Users\11059\.workbuddy-ai\skills` —— 14 个 SKILL.md / 13 条生效(`skill-vetter` 被项目级同名覆盖)
  3. **connector** `~/.workbuddy-ai/connectors/skills` —— 不存在
  4. **session** `$CODEBUDDY_SESSION_SKILL_DIRS` —— 未设置
  5. **bundled** `$CODEBUDDY_BUILTIN_SKILLS_DIR` —— 未设置
  6. **plugin**(`SkillExtensionLoader`, 每个已装插件的 `skills/`): `~/.workbuddy-ai/plugins/cache/workbuddy-builtin/*`(weixinpay 3 / tencent-docx 8 / tencent-docs-plugin 2 / sheetagent 2 / tencent-pptx 1)、`cache/codebuddy-plugins-official/*`(playwright-cli 1、find-skills 1 被项目级覆盖、document-skills 2)、`cache/cb_teams_marketplace/document-skills`(pdf、pdfkit-py)、以及应用内置 `H:\Programs\WorkBuddyAI\resources\app.asar.unpacked\resources\plugins\workbuddy-builtin\skills`(27 个 / 26 生效)。
  - 去重后共 **79** 条。注意应用内置 `builtin-plugins/*/skills` 与 `plugins/cache/` 下的同名副本重复, 后者先加载、前者全部落空 —— 排查"改了内置 skill 没生效"时先看是不是被 cache 副本挡了。
- **Windows 操作坑**: 在本会话的 Git Bash 里 `cmd //c ...` 会被路径转换坑掉(参数里的 `\` 变 `/`, cmd 把 `/Projects` 当成命令行开关报"无效开关"), 且可能退化成交互式 cmd 而**静默不执行**。删 junction 用 Python `os.rmdir()`(等价于 RemoveDirectory, 只摘链接不碰目标), 别用 `cmd /c rmdir`。

### 前后端契约不能只看后端载荷: 前端还有一层派生 (2026-09-19 实测, 架构审查 F1 误报)

- **症状**: 审查时看到"前端按 `g.save_path` 过滤分组, 但后端组对象没有 `save_path` 字段", 判定"路径筛选必失效、列表变空"并列为 P1 待修 —— **实施阶段逐行复核才发现是误报**。
- **根因**: 前端在 `decoratedGroups`(`shared/app.js:454`)里已经派生了 `save_path: (g.members[0] && g.members[0].save_path) || ""`, 而筛选的 `base` 来自 `sortedGroups` = `[...decoratedGroups].sort()`(`:429-431`), 筛选选项 `pathOptions`(`:468`)也取自同一派生集, 口径自洽。`app.js:2686` 的注释"原始组字典没有 save_path"正是这个设计的自述。
- **判别法**: 判"前后端字段不一致"前, **必须沿前端的 computed 派生链追到实际消费点** —— 只看后端产出的对象与前端某一行的 `g.xxx` 就下结论, 会漏掉中间那层派生。反向也成立: 后端补字段前先确认前端是不是已经算了(否则就是重复计算)。
- **教训**: 审查结论里凡是"必失效/必崩"这种强断言, 动手前先写一条能复现的用例或最小验证 —— 本条如果真按原方案改, 会在组对象上多一个前端已经算过的冗余字段。

### 写"修复前必失败"的用例时, 先确认它真的会失败 (2026-09-19 实测)

- **症状**: 给 Wave 1 的视图并发修复写回归用例, 直觉写法是"给四份视图打 build 号, 断言四份同号"。**有锁时绿、无锁时也绿** —— 因为无锁时若两个线程各自完整发布一轮, 最后发布者胜出, 四份数组仍自洽。跑红验实测输出 `NO_MISMATCH`, 这条用例是安慰剂。
- **修法**: 改成**确定性**断言 —— 让重建卡在 builder 里不放行, 再把脏标记置 False, 于是"读取能否返回"只取决于有没有锁; 有锁被阻塞、把锁换成 `nullcontext()` 后立即返回。
- **判别法**: 并发/时序类用例**必须做红验**(把修复临时还原, 确认用例失败)。红验做法: 优先用运行时 monkeypatch 还原旧实现(不碰工作区文件), 再跑同一断言; `lru_cache` 装饰的函数记得先 `cache_clear()`。
- **另一半经验**: 纯语义类修复(如 `_bare_ok` 加 `n >= 1`、`max_tasks_per_tick` 加 `>= 1`)的红验可以直接打脚本验证"旧实现下断言不成立", 不必真的回滚文件 —— 但**必须做**, 否则无法区分"用例有效"与"用例恒真"。

### 不要并发跑多个 pytest 进程 (2026-09-19 实测)

- **症状**: 全量跑着的同时又起几个 pytest 子进程跑子集, 结果全量里多出 2 条失败、且覆盖率阶段 `INTERNALERROR`。单独重跑那 2 条全绿。
- **根因**: ①`helpers.FakeQbServer` 会绑定本地端口, 并发抢端口/时序; ②`tests/sidefx.py` 的越界判定是**会话级**的 —— 任何进程删了越界文件都算到当前会话头上。
- **同样的症状还有第二种触发 (2026-09-19 实测): 不并发也会偶发** —— 工具环境的文件删除拦截层清理**其它进程遗留**的临时文件(`D:\Projects\*.tmp`)时, 那次删除同样被记进当前会话台账, 于是 `test_sidefx.py::test_sidefx_recorder_installed_and_records` 与 `test_web.py::test_api_stats_endpoint` 各挂一次; 之后两次复跑全量均 **1041 全绿**, 期间并无第二个 pytest 进程。
- **判别法**: ①全量跑完前不要开第二个 pytest; ②全量里只多出 1~2 条失败、失败信息指向**副作用台账/越界**、且**单独复跑即通过** ⇒ 判为环境干扰, **不要去改测试或代码**, 复跑一次确认即可(本次: 首跑 2 条失败 → 单跑 2 条全绿 → 复跑全量 1041 全绿)。另: 带 `--cov-branch` 的全量在本机约 **32 秒**(空载), `--no-cov` 约 **25 秒**(实测 22.7 / 23.7 秒) —— 文档里"约 12 秒"已过时(可能是早期用例更少时的数字)。

### 在工具 shell 里「非快进合并 + 工作区脏」会删掉整个 .git 对象库 (2026-09-19 实测, 重大事故)

- **症状**: `git merge <分支>` 报 `fatal: <oid> is not a valid object` / `fatal: stash failed` 或 `fatal: unable to read tree (<oid>)`; 之后 `git status` 报 `bad tree object HEAD`、`git fsck` 大面积 broken link、多个分支尖端断链、`.git/logs/**`(reflog)全空。
- **根因**: git 2.55 在**非快进合并**时**无条件**调用 `git stash create`(`GIT_TRACE=1` 可见, 干净工作区时也会调, 只是无内容可存)。工作区脏时它要真写 stash 对象, 而本工具环境的文件删除拦截层(`[safe-delete]`, 注意 `rm` 是 **bash 函数**而非 PATH 里的可执行文件)会顺着这次写入把 `.git/objects/**` **批量删除**。铁证: 被删文件**全部进了 Windows 回收站**(`D:\$Recycle.Bin` 的 `$I*` 元数据里能查到原始路径) —— git 原生 `unlink()` 绝不会走回收站, 说明删除者不是 git。
- **实测矩阵 (2026-09-19, 一次性临时仓库, 已清理)**:

  | 场景 | 结果 |
  |---|---|
  | 非快进合并 + 干净工作区 | **安全**: 对象 9→11, 合并成功 |
  | 非快进合并 + 脏工作区 | **必炸**: 对象 →0, `.git/objects` 全毁 |
  | 同上 + `merge.autoStash=false`(全局配置与 `-c` 均试) | 照样全毁 |
  | 同上 + 关沙箱 / 换系统 `D:/Program Files/Git`(同为 2.55.0) / 剔除 safe-bin 的 PATH / 清 `CODEBUDDY_SAFE_DELETE_*` | 照样全毁 |
  | 快进合并 + 脏工作区 | **安全**: git 不调用 stash create |

- **事故实例**: 2026-09-19 把 `backend/develop` 合进 `develop`(非快进)时工作区有 3 个脏文件 → 02:05:54~58 两秒内删掉 **319 个对象 + 全部 reflog + `hooks/*.sample` + `info/`**, 4 个分支尖端断链(`develop`/`other/develop`/`backend/develop`/`agentAutoClaw/develop`/`agentZCode/develop`)。同批的快进合并(`other/develop`)安然无恙。
- **修法(唯一可靠)**: **合并前先把工作区弄干净** —— 先提交, 或把改动移出仓库再合并; 高风险 git 操作前整份备份 `.git`。
- **事故后补救(已走通)**: ①被删对象基本都在 **Windows 回收站**, 按 `$I*` 里的原始路径还原即可。解析要点: `$I` 文件偏移 **16-24** 是删除时间(FILETIME, **UTC, 换算本地要 +8h**), 偏移 **28** 起是 UTF-16LE 的原始路径; 内容在同名 `$R*` 文件里。②**还原后必须先删掉被一起还原的陈旧 `*.lock`**(`index.lock` / `HEAD.lock` / `AUTO_MERGE.lock` / `packed-refs.lock` / `objects/maintenance.lock`), 否则任何 git 命令都报 `Unable to create '.git/index.lock': File exists`。③工作区文件若成片消失但在 `HEAD` 里仍在 → `git checkout -- <file>` 直接还原。④收尾 `git fsck --no-progress` 确认 **0 broken link**(dangling 无害)。
- **判别法**: 准备在工具 shell 里跑 `merge` / `rebase` / `checkout` / `stash` 之前, 先看 `git status --short` —— **非空就先弄干净**。记不住细节就记这句: **非快进 + 脏 = 必炸**。另外本 worktree 每次 `git commit` 的 ref 更新也可能被同一层拦截静默丢弃(lock+rename 失效, git 拿到 0 返回码), 提交后必须核对 `HEAD` == 松散 ref == `packed-refs`。

### GitHub Actions: `astral-sh/setup-uv` 没有浮动大版本标签, `@v10` 解析不了 (2026-09-19 实测)

- **症状**: CI 的 `Test (Python 3.12)` 直接报错 `Unable to resolve action astral-sh/setup-uv@v10, unable to find version v10`, 作业在第一步就死, 一行测试都没跑。
- **根因**: 该 action 从 v8 起只发**固定标签**(v8.0.0…v8.3.2 / v9.0.0 / v10.0.0 / v10.0.1 / v10.1.0), 仓库里**没有** `refs/tags/v10` 这种随大版本移动的浮动标签(对比 `actions/checkout`、`setup-python`、`upload-artifact` 都有 v1…v7 浮动标签, 所以同文件里写 `@v6` / `@v7` 是没问题的)。写 `@v10` 就是引用了一个不存在的 ref。
- **修法**: 按上游 v10.1.0 README 的推荐写法**固定到 commit SHA** 并在行尾加版本注释 —— `uses: astral-sh/setup-uv@bec219d24cd3e171d82865faccec33120bb574f4 # v10.1.0`(次选是直接写 `@v10.1.0`)。
- **判别法**: 给第三方 action 升大版本前, 先 `curl -s https://api.github.com/repos/<owner>/<repo>/git/refs/tags | grep -o '"ref": "refs/tags/[^"]*"'` 确认目标 ref 真的存在, 别照着上一个大版本的写法顺推 —— "上一个大版本有浮动标签" 不代表下一个也有。

### `git status -sb` 的 ahead/behind 会拿陈旧的远端 ref 骗你 (2026-09-19 实测)

- **症状**: 推 CI 修复提交前看 `git status -sb` 是 `## develop...origin/develop`, **没有 ahead/behind**, 以为和主线同步; 结果 `git push origin develop` 被拒 —— `Updates were rejected because the remote contains work that you do not have locally`。
- **根因**: `-sb` 的 ahead/behind 是拿**本地缓存的远端跟踪 ref**(`refs/remotes/origin/develop`)比出来的, 不会实时问服务器。本次这个 ref 停在 `d3b5d4c`, 而 Gitee 实际已到 `d4d2326`(领先 3 个提交), 差值只有 `git fetch` 之后(或者 push 被拒时)才暴露。
- **判别法**: **要回答"我有没有落后", 必须先 `git fetch`**, 再看 `git status -sb` 或 `git log --oneline HEAD..origin/develop`。裸 `git status` 只能回答"工作区干不干净", 回答不了"主线到哪了"。反向同样成立: 显示 `[ahead N]` 也不代表推得上去 —— 那是相对**当前上游**的, 上游若指向 GitHub 镜像就毫无意义(见 AGENTS.md「提交 / PR」节)。
- **修法**: 推之前按 AGENTS.md 走 `git pull --rebase origin develop` 即可 —— `pull` 自带 fetch, 所以"先 fetch 看差集"与"直接 pull"只差在要不要先瞄一眼对方改了什么。
- **与上面那条坑连起来看**: 一旦发现自己落后, **别在脏工作区上直接合并** —— 先提交弄干净, 再 pull/rebase(「非快进 + 脏 = 必炸」)。

### 提交信息里的反引号会被 bash 当成命令替换 (2026-09-19 实测)

- **症状**: `git commit -m "…已入库 `044908d..c888fba`…"` 提交成功, 但 `git log -1 --format=%B` 里那一段**变成空字符串**(同时 shell 报 `044908d..c888fba: command not found`)—— 提交内容没错, **只有信息被吃掉一段**。
- **根因**: `-m` 的双引号内, 反引号仍是 bash 的**命令替换**, 会被执行并替换为其输出(空)。本仓提交习惯用反引号包提交号/路径, 正中这个坑。
- **判别法**: 提交信息里凡是出现反引号, `git log -1 --format=%B` 复核一遍; 或者直接**改用单引号包整条 `-m`**(单引号内不做替换), 或干脆不用反引号(写 `044908d..c888fba` 裸文本即可)。
- **事后补救**: 已推送的提交**不要 amend + 强推**(develop 是协作主线, 多 worktree/多 agent 共用); 信息缺一段但可读就留着, 下次注意。教训也适用于其它"在 shell 里写中文长文本"的场合: 反引号、`$`、双引号都要先转义或换引号。

### 「Windows 全绿 / Linux 全红」: 本机跑通不等于 CI 跑通 (2026-09-19 Linux CI 实测, 三条同源)

- **症状**: 本地(Windows)全量 1038 passed 越界 0, 推上去 GitHub Actions 的 `Test (Python 3.12/3.13)` 一次红 4 项:
  ①`test_api_stats_endpoint` teardown 报 **78 条越界 FSDEL**(含 `'state.json'` / `'config.yml'` / `'raw.yml'` / `'movie.mkv'` 这类**裸文件名**);
  ②`test_sidefx_recorder_installed_and_records` 断言"临时目录内删除不应判越界"失败;
  ③`test_notify_legacy_shortcut_cleanup` `ModuleNotFoundError: No module named 'winreg'`;
  ④`test_connect_recovery_logged` `assert mgr.connect() is True` → False。
  ②是①的下游(它断言的是**会话累计**越界数, 不是自己那一条), 所以真根因只有三个。
- **根因一(76/78 条)**: POSIX 的 `shutil.rmtree` 走 fd 版实现(`_rmtree_safe_fd`), 删目录内条目时传的是
  **纯文件名 + `dir_fd`**; Windows 不支持 `dir_fd`, 走的是拼接好绝对路径的另一支。副作用记账器只记 `path`,
  于是同一份 `TemporaryDirectory` 清理在 Windows 记成 `<temp>\xxx\state.json`(判临时目录内), 在 Linux 只记成
  `'state.json'` → realpath 落到 CWD(仓库根) → 判越界。**修法**: 记账前用 `_with_dir_fd()` 把 `dir_fd` 补成
  绝对路径(Linux 读 `/proc/self/fd/<fd>`, macOS 用 `fcntl.F_GETPATH`), 见 `tests/sidefx.py`。
- **根因二(2/78 条)**: `utils.atomic_write("")` —— `abspath("")` 是 CWD, `dirname` 再取一级就成了 **CWD 的父目录**,
  于是空路径不是"什么都不写", 而是往**仓库外面**丢 `.xxxxxxxx.tmp`, 随后 `os.replace(tmp, "")` 失败再删掉。
  **这一条同时纠正了长期误判**: 之前本机偶尔出现的越界项 `D:\Projects\.brafjf1b.tmp` 一直被当成"IDE 临时文件
  被工具删除"的环境噪声, 实际就是它(仓库在 `D:\Projects\auto-qb-clone1`, 父目录正好是 `D:\Projects`)。
  **修法**: `atomic_write` 对空路径直接 `raise ValueError`(配置层已校验 `state_file` 非空, 走到这里就是调用方漏传);
  两个 `test_checking.py` 用例补上临时目录里的 `cfg.state_file`。
- **根因三/四(两条用例)**: ①`PlatformChannel("win32")` 内的 `import winreg` 在 Linux 抛 `ModuleNotFoundError`,
  而 `_ensure_appid_registered` 只 catch `OSError` ⇒ 直接外抛; 用例改为 `monkeypatch.setitem(sys.modules, "winreg", 替身)`,
  任何平台都跑得到真实分支。②`test_connect_recovery_logged` patch 的是 `qbmanager.Client`, 但 `connect()` 走的是
  `qbclient._new_client` ⇒ patch 根本不生效, 真的去连 `127.0.0.1:16585`, **是否抛异常取决于机器环境**(CI 红、本地绿);
  改成 patch 真正被调用的那个名字 `_new_client`, 与网络彻底解耦。
- **判别法**: 凡是"记账器判越界 / 平台专属模块导入 / 真实 socket 连接"这三类, **本机绿不算绿**。要验 Linux 行为,
  本机就能做: WSL(`wsl -- bash -c '...'`)里 `cp -r` 一份仓库(排除 `.venv`/`.git`)、`uv sync`、`uv run pytest tests -q`
  即可复现 CI 的全部平台差异(本次 15 秒出结果, 比推上去等 CI 快得多)。加 `-p 3.12`/`-p 3.13` 还能对上 CI 的矩阵版本。
- **顺带**: 记账器里"断言会话累计越界数为 0"的写法(`test_sidefx_recorder_installed_and_records`)是**哨兵**而非
  单点用例 —— 别的用例污染了台账它就会红, 排查时先看它列出的越界项归属哪个用例, 别在它身上找原因。

### 追剧视图 `members` 是**双形态**: hash 数组(后端) vs 成员对象(前端装饰后) (2026-09-19 实测)

- **症状**: 追剧页**剧右键 / 集右键** → "打开目标文件夹" 弹 `打开目标文件夹失败: 种子不存在`; 而**种子右键**的同一项正常。同一菜单里的 开始/暂停/强制汇报/删除 其实也一起哑火(前三项报 `Not Found`, 删除因 `memberByHash.get(对象)` 全落空而**静默返回**), 只是用户先注意到文件夹那一项。
- **根因**: `web_view._build_shows_view` 的集节点 `members` 是 **hash 字符串数组**, 而前端 `decoratedShows`(`shared/app.js:822`)会把它**换成成员对象**(`{...m, hit}`)供行内渲染/筛选。菜单里 `openShowEpMenu` 写的是 `hashes: ep.members.slice()`、`openShowMenu` 写的是 `for (const h of e.members)` —— **把对象当 hash 用**, 拼进 URL/JSON 时字符串化成 `[object Object]`, 后端 `_require_torrent` 查不到 ⇒ 404「种子不存在」。
- **修法**: 新增 `memberHashesOf(list)`(`typeof m === "string" ? m : m.hash`, 过滤空值)统一取 hash, 菜单与选中态(`_showHashes` / `_epUnits` / `epSelState`)一律走它 —— 两形态都收, 该类误用不再可能。
- **判别法**: 凡是"后端产出 hash 数组、前端 computed 再装饰成对象"的集合(当前只有追剧视图的 `ep.members`), **任何写进 URL / 命令载荷 / `memberByHash` 查找的地方都必须先归一成 hash**; 行内渲染(`v-for="m in e.members"`)才用对象形态。"同一动作在单种子上正常、在聚合行上失败"基本就是这个形状 —— 单种子菜单传的是 `member.hash`, 天然对。
- **顺带**: `[object Object]` 不会在控制台报错, 后端只回 404, 前端只出一条 toast —— 这类"类型错位"故障**没有 JS 单测兜底**(本仓无 JS 测试运行器, `test_frontend_static_bundle_health` 只做语法/结构守阵), 只能靠真机走查; 改到前端派生链时优先做**逐层级**的手动走查(剧 → 集 → 种子)。
- **验证手法(可复用)**: 本仓没有 JS 测试运行器, 但**能用 node 直接加载 `shared/app.js` 做真行为验证** —— 桩掉 `Vue.createApp`(把 options 接出来)/ `window` / `document` / `localStorage` 后 `eval(src)`, 再从 `opts.methods` + `opts.data()` 拼出一个 `this`(方法逐个 `bind`), 就能直接调 `openShowEpMenu`/`openShowMenu` 断言 `menu.episode.hashes`。**红验**用 `git show HEAD:<path>` 取旧版跑同一脚本(本次: 旧版 9 项挂 5 项, 含"载荷 hash = 对象"那一条; 新版 9/9 通过)。注意方法在 `opts.methods` 下, **不在** options 顶层。
- **端到端冒烟(可复用)**: 桩一个最小 HTTP 服务就能让**真页面在真浏览器里跑起来** —— ①静态托管 `web_ui/static`(注意 `.js` 必须回 `text/javascript`, 否则 ES 模块/脚本被拒); ②只需桩三个端点: `/api/config/public` 回 `{"web":{"skip_local_verify":true}}`(免鉴权直入, 不用走密钥表单)、`/api/state`(含 `shows`/`torrents`, `torrents` 里的 SEED_ITEM 供 `memberByHash` 解析 —— 缺了剧行渲染不出来)、目标端点(如 `/api/open-path` 把请求体落盘, 事后直接看载荷); ③`/atlas/` 顶栏第三个按钮 = 追剧。浏览器用 **node playwright**(在 `~/.workbuddy-ai/binaries/node/workspace/node_modules`, 配 `NODE_PATH`) + `chromium.launch({ channel: "msedge" })` —— 缓存里的 chromium 版本号与 playwright 期望的经常对不上(本次 1234 vs 1243), **系统 Edge 永远可用**。本次红验: 修复前 `/api/open-path` 收到的是 `hash: {整个成员对象}`(含 `hit:false`), 修复后是 `hash: "aaaa…"` —— 这就是用户看到的「种子不存在」。
  - 两个小坑: 桩服务**不要用 `os.remove` 清空记录文件**(会触发工具环境的批量删除拦截, 进程直接死; 用 `open(path,"w").close()`); 无头页里 Vue 实例**不在 window 上**(`const app = createApp(...)` 是模块作用域), 要操作只能点 DOM。
- **已固化**: `tests/test_web.py::test_frontend_static_bundle_health` 新增第 7 项 —— app.js 里凡是"集成员取 hash"的行(`e.members`/`ep.members` + `hashes`/`.hash`/`for (const h of`)必须含 `memberHashesOf(`, 否则报问题(对 HEAD 旧版实测报出全部 5 处)。
### 主循环「命令即时唤醒」不能连带唤醒 tick: max_tasks_per_tick 与两个每 tick 预算会一起失效 (2026-09-19 设计评审)

- **背景**: 为修「WEB UI 操作不跟手」提出「Web 投递命令即唤醒主循环」。初版设想是投递后立刻跑下一轮
  （把 `_throttle(main_tick)` 换成 `wake.wait(main_tick)`）—— 听起来只是让命令少等 0~2s, 实际连坐三处。
- **连坐一（速率语义）**: `max_tasks_per_tick` 的字面语义是**每次 `run_due` 最多弹 N 个**（taskqueue.py 的
  `_pop_due`, `max_tasks<=0` 才不限量）—— 唤醒后每次仍 ≤ N, 字面不失效。但它实际承载的是**速率语义**:
  默认 `max_tasks_per_tick=20` × `main_tick=2s` ⇒ 吞吐上限 10 任务/秒。tick 频率一旦改由命令决定, 上限就没了。
- **连坐二（自激循环, 最严重）**: `web_view.py` 的 `_build_shows_view` 与 `search_torrents` 在索引脏时会**自己投递**
  `build_search_index`, 而 `_build_search_index` 单轮可拉 `SEARCH_INDEX_BUILD_BUDGET=500` 条文件 API。
  「投递即唤醒」⇒ 唤醒 → drain(500 次 API) → tick → 重建视图 → 又投递 → 立刻再唤醒 …… 中间没有 main_tick 兜底,
  直到索引建完。这不是变慢, 是打满 CPU 并冲垮 qB（前端搜索在 `building` 期间还按 1s 重查, 每次补一刀）。
- **连坐三（每 tick 预算被摊薄）**: `_refresh_torrents`（每 tick 一次 qB sync）与 `refresh_error_reasons`
  （Web 活跃时每 tick `ERROR_REASON_BUDGET=5` 次 tracker 请求）—— tick 变密, qB 请求同比变密。
- **修法（设计 v2）**: 把**命令线**与 **tick 线**解耦 —— 唤醒只触发 `_drain_web_commands()`（汇报确认检查自带
  ≥1s 最小间隔, 不随唤醒放大）; `_tick()` 严格按 `next_tick_at` 走, 跑完推到 `now + main_tick`。
  两道保险: 自投递类命令（`build_search_index`）**不唤醒**; 验收加不变量用例 —— 2s 内连投 100 条命令,
  `_tick` 次数与无命令时**相同**。
- **判别法**: 任何「让主循环提前醒来」的改动, 先问一句 —— **提前跑的是消费, 还是整轮 tick?** 只要答案是整轮,
  就得重新确认 `max_tasks_per_tick` / 每 tick API 预算 / 自投递命令这三条是否还成立。

### 「把 main_tick 缩短来换响应速度」是 40× 成本买 0 收益 (2026-09-19 实测否决, 含单轮成本基线)

- **提议**: 主循环 50ms / 任务仍按 2s(=50ms×40) / 种子状态刷新 50ms。**结论: 不可行。**
- **实测单轮成本**(helpers 的 FakeClient + make_manager, 纯 CPU **不含** qB 网络往返 ⇒ 下界;
  浏览器打开时速度字段恒脏 ⇒ `rebuild_views` 是常态而非最坏):
  | 种子数 | `_refresh_torrents` | `rebuild_views` | 单轮合计 | 20Hz 占用 |
  |---|---|---|---|---|
  | 200 | 0.87ms | 2.98ms | 3.85ms | ≈8% 核 |
  | 1000 | 4.86ms | 13.79ms | 18.65ms | ≈37% 核 |
  | 3000 | 14.52ms | 46.91ms | **61.43ms** | **>100% 核** |
- **三条硬否决**: ①3000 种子单轮 61.43ms **已超 50ms 预算** ⇒ 循环追不上节拍、剩余休眠恒为 0,
  退化成无间隔连续跑(**越忙越慢、越慢越忙的正反馈**; 现在的 2s 正是这条正反馈的隔离带);
  ②空闲成本 ×40(0.7% → 29% 核)且永久; ③每 tick 预算 ×40(qB sync 0.5→20/s、tracker 2.5→100/s、
  搜索索引 250→10000 文件 API/s、任务吞吐 10→400/s ⇒ `max_tasks_per_tick` 限流被架空)。
- **收益侧为 0(关键)**: 命令延迟 —— wake 事件已经给 ≈0ms 且零成本; 状态可见延迟 ——
  **前端 `pollSec=2s` 才是端到端下限**, 后端再快用户也是 ≤2s 才看到(要把前端也提到 50ms,
  每轮 MB 级响应体 ×20/s, 传输与渲染先崩)。**提频只是把瓶颈从后端节拍搬到前端轮询。**
- **便宜的替代**: 命令执行完**补一次完整刷新**(单次 14.52ms @3000, **按操作次数计费**而非按时间计费)
  + 乐观 UI; 彻底去掉 2s 下限走 SSE 推送。
- **⚠ 补充红线**: 补刷新**必须调完整的 `_refresh_torrents()`**, **绝不能只调 `store.apply_sync()`** ——
  `apply_sync`(store.py:81)只更新 `by_hash` + `server_state`, 分组索引/任务/事件/搜索索引一概不碰。
  单调它的后果(半刷新态): ①`added` 未处理 → 新种子不 match tracker、不建任务、不归组、`on_torrent_added` 不触发;
  ②`removed` 被丢弃 → `on_torrent_deleted` 不触发、`_handle_removed_torrents` 不跑、**`store.groups` 残留已删 hash**、
  `_search_index_dirty` 不置位; ③`update_state_snapshot()` 未推进 → 命令造成的暂停在下轮被当成"外部状态变化"再触发一次事件;
  ④分组侧的上传转暂停扫描/路径重归组/下载冲突检查全部推迟。
  反之 `_refresh_torrents` 本来每轮都跑, 转换与事件由快照 diff 消费一次, 天然幂等
  (`_dispatch_events` 的 `state_changed` 参数就是为"同轮多处调用只有一处负责状态分派"准备的)。
  另: 补刷新要放在 `_drain_web_commands()` **整批结束后一次**, 不是每条命令后各一次(否则 N 条 = N × 14.5ms)。

### 主循环分层节拍: 拆分时必须把 `_tick` 的**五项**都归档, 只分三项会漏掉最贵的两个 (2026-09-19 设计评审)

- **提议**: 刷新 50ms / 视图重建 1s / 任务 2s。**技术可行**(与"整轮 50ms"不同: 单轮只剩刷新 14.52ms@3000,
  占 50ms 预算 29%, 节拍站得住; 3000 种子合计 ≈33.7% 核)。
- **⚠ 漏项警告**: `_tick` 里是**五项**不是三项。用户只点名三项时, 剩下两项若仍按 50ms 跑:
  `_build_search_index` = 单轮 500 条文件 API × 20 = **10000 次/秒**(qB 直接被打爆);
  `refresh_error_reasons` = 5 次 tracker × 20 = **100 次/秒**。
  ⇒ **归档清单**: `_refresh_torrents`(快档) / `rebuild_views`(1s) / `run_due`(2s) /
  **`_build_search_index`(2s 或更慢)** / **`refresh_error_reasons`(2s)**。
  (`_check_download_conflicts` 每轮跑但**增量 + 带去重**, 静止库零成本; 活跃下载时 amount_left 每轮变 ⇒ 0.5Hz 变 20Hz, 需实测。)
- **两个隐藏成本(不在我方 CPU 预算里)**: ①**打在 qB 进程上** —— `sync/maindata` 20/s, qB 每请求要做 O(N) diff,
  3000 种子 ≈ 6 万次字段比较/秒(qB 官方 WebUI 默认 1500ms, 20/s 极激进) ⇒ **快档建议 250~500ms, 别给 50ms**;
  ②**GIL 争用** —— 主循环 33.7% + Web 线程重建 47ms/次 + MB 级 JSON 序列化都持 GIL,
  可能出现"后台更快、前台更卡"。
- **落地形态建议**: 挂到已有的 **Web 活跃门控**(`_web_last_seen` / `WEB_VIEW_TTL=10s`)上做成**快档** ——
  浏览器开着才快, 关掉网页自动回落到 main_tick ⇒ 29% 只发生在用户正在看时, 空闲回到 0.7%。
  配置键 `web.fast_sync_ms`(默认 0 = 关闭, 跟随 main_tick; 取值 250~500, **不提供 50**), 必须进 validate_config + schema。
- **判别法**: 主循环任何"拆档/提频"改动, 先列全 `_tick` 的**全部动作**再逐个归档 —— 只对自己熟悉的三项归档,
  漏掉的往往是最贵的那两项(批量 API 型)。

### 定档: 刷新 1s / WEB UI 1.5s / 任务 2s —— 后端免费, 风险全在前端 (2026-09-19 评估, 含"别给视图重建单独配节拍")

- **后端成本(实测折算)**: 刷新 @1Hz + 重建 @1.5Hz ⇒ 200 种子 0.29% / 1000 种子 1.4% / **3000 种子 ≈4.6% 核**
  (现状 2s/2s 是 3.1%, 只多 1.5 个点)。qB 请求 0.5 → 1 次/秒, 与 qB 自带 WebUI 的 1500ms(0.67/s)**同量级**。
  ⇒ **刷新快于 qB 自身数据粒度没有意义**(速度类按滑动窗口更新), 1s/1.5s 是"刚好够快"的档位。
- **⚠ 别给 `rebuild_views` 单独配节拍**: `ensure_group_state()` 已是「**请求驱动 + 脏门控**」——
  Web 请求到达时脏才重建, 不脏直接返回当前引用 ⇒ **视图重建频率天然 = 前端轮询频率**。
  另外给它配定时器只会在"前端没来取"时白建。要改就只改前端 `pollSec`, 后端自动跟随。
- **⚠ 真正的风险在前端**: WEB UI 2s → 1.5s 会把「每轮全量回传 + 整树重渲染」频率**提高 33%**,
  而那正是"不跟手"的主因 ⇒ **未做 P1-1/P1-2 前降 pollSec 会加剧症状**。
  顺序必须是: P0 → P0-0 埋点测出单次渲染耗时 → P1-1(响应体 ≈1/4) / P1-2(行窗口化) → 最后才动 pollSec。
- **取值建议(让两个节拍成整数倍)**: ①刷新 1.5s / 轮询 1.5s(与 qB 对齐, 零浪费, 推荐);
  ②刷新 1s / 轮询 2s(两次刷新配一次拉取, 后端只 1.45%); 1s/1.5s 可行但不整齐(1/3 的刷新没人取)。
- **落地**: 新增 `sync_interval`(默认 1s 或 1.5s, **必须进 validate_config + schema**), `main_tick` 语义收窄为
  "任务节拍 + 兜底节流"; `_build_search_index` / `refresh_error_reasons` 仍跟 main_tick(2s), **不跟随快档**;
  前端 `pollSec`(app.js 硬编码 2)改可配, **默认仍 2s**, P1 落地后再按种子量放宽(≤1000 → 1.5s)。
- **判别法**: 谈"响应慢"时先分清 **轮询频率** 与 **响应延迟** —— 延迟该用**事件**解(唤醒/单次同步/推送),
  不是把轮询周期调小; 调小周期同时放大"每轮固定成本 × 频率", 而这份成本在空闲时也照付。

### 波次一落地踩到的四个坑 (2026-09-19 实施)

- **⚠ 多事件等待的顺序不能反**: 主循环要同时响应「命令唤醒」与「停止信号」, 而 Python 没有
  WaitForMultipleObjects。第一版写成「分段阻塞等 `stop_event` + 段间看 `wake_event`」, 结果唤醒要等满
  一个 0.5s 分段才被看见 —— 命令延迟从 ≈0 退化到 ≤0.5s, 恰好抵消了 P0-1 的全部收益。
  **正确顺序**: 阻塞在 `wake_event` 上(命令到达即返回), 分段只是为了让**非阻塞**的 `stop_event.is_set()`
  有机会被检查。判据: 单元测试里连投 3 条命令, `drain` 次数必须 = 3(实测反序时只有 1)。
- **⚠ 分层节拍不能退化成"单一 cadence + 内部门控"**: 若循环按 `sync_interval` 单一节拍跑、任务线在
  `_tick` 内部按 `next_tick_at` 判断是否执行, 任务实际间隔会被**循环粒度量化** —— 1.5s 循环粒 + 2s 任务
  间隔 ⇒ 实测 3s 一次(0→3→6), `max_tasks_per_tick` 的速率语义从 10 任务/秒 悄悄变成 6.7。
  **等待必须是 `min(两条线的到期时间)`**, 两条线各自精确推进(实测 0→2→4→6)。
- **⚠ 改主循环会静默废掉既有的节流守卫**: `test_run_loop_throttles_without_stop_event` 断言
  `time.sleep` 被调用、`test_local_qb_service.py::test_main_loop_throttled_by_main_tick` 假设"每轮一次 sync"。
  分层后 `_tick` **只在两条线同时到期时**才走到 ⇒ 该用例的 `_tick` 包装层(靠它抛 KeyboardInterrupt 退出)
  再也触发不了, 表现是**挂死**而不是失败。**改写这类用例时判据要用真实经过时间, 不能用 mocked sleep** ——
  时间不前进会让"两条线都不到期"的循环永远跑下去。
- **⚠ `yapf -i` 会顺手重排文件里**本来就超宽**的旧行**: 对 `config/schema/groups.py` 跑格式化, 除了新增的
  `sync_interval` 还多出 48 行无关重排(host/port/state_file 等原本就超 120 列)。
  **改配置 schema 这类文件时只格式化自己加的那段**, 或改完先 `git diff --stat` 看行数是否异常(11 行 vs 59 行一眼可辨)。

### 命令回执埋点: 下划线前缀键的约定 (2026-09-19)

- 投递时随命令带上 `_queued_ts`(P0-0 埋点用), 但**不能**直接塞进 payload —— drain 侧
  `args = payload - cmd_id` 会被 `**args` 原样传给 handler, 多一个键就是 `TypeError: unexpected keyword argument`。
  约定: **下划线前缀的键是元数据**, drain 里 `not k.startswith("_")` 过滤掉, 不传 handler; 前端/测试断言
  入队参数时也要先 pop 掉(已在 `test_api_torrent_write_endpoints_enqueue` / `test_api_t_bulk_group_keys_enqueue`
  里补)。回执回传 `wait_ms`(排队等主循环)与 `exec_ms`(执行), 前端再补"投递→回执"总时长 ⇒
  "感觉慢"变成可归因的三段。

### 波次二落地踩到的三个坑 (2026-09-19 实施)

- **⚠ 短缓存不能盖过"断连"信号**: 给 `/api/torrents/{hash}/files|trackers|peers` 加 TTL 缓存后,
  第一版把 `_require_client()` 留在 lambda 里(只有未命中才执行)⇒ qB 断开时**仍返回缓存的 200**,
  把"qB 已断开"藏起来了(测试用 503 断言抓到)。**连接检查必须在查缓存之前** —— 断连优先于缓存。
- **⚠ 短缓存必须有"写后失效"**: 只按 TTL 失效会出现"刚改完文件优先级、重取还拿到缓存旧值",
  用户看到的是**改了没生效**。解法是把写序号 `manager._web_write_seq`(任何非自投递命令执行成功
  即自增, 在 `_drain_web_commands` 里)并进缓存键 —— 写命令一执行, 键就换了, 缓存自然失效,
  不需要在每个写端点里手动清。自投递命令(build_search_index)不计数, 否则建索引期间缓存全废。
- **⚠ Vue Options API 里 data 字段与 methods 同名会互相覆盖**: 顶栏观察器的元素引用想叫 `_headEl`,
  但下方已有**方法** `_headEl(page)`(取表头元素) —— 两者共命名空间。改名为 `_headObsEl`。
  同类约束在模板侧更严: 模板里**不能**引用下划线前缀的标识符(会报 "_xxx is not defined" 且整块渲染失败)。

### P1-1 按视图回传: 前端赋值必须"键不存在则保留原引用" (2026-09-19)

- 服务端改成只回当前视图的数组后, 前端原来那套 `this.groups = state.groups || []` 会在每次轮询
  把**另外两个视图抹成空**(切回去要等一轮全量)。必须改成 `if (state.groups !== undefined) ...`。
- 切视图时把 `lastRid` 置空强制取一次全量(否则本地 rid 与新视图数据不对应); 顺手在 `setViewMode`
  里直接 `refresh()` 一次, 免得首次切到某视图要空/旧 ≤2s(`scheduleNext` 内部先 `stopPolling`
  再排下一次, 所以不会造成双份轮询)。
- 服务端 `view` 参数取**保守默认**: 未知值 / 缺省 ⇒ 四份全回。老客户端与非视图调用方不受影响。
