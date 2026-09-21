# Pitfalls — 陷阱、风险点与文档漂移 (改代码前必读)

> **读法**: 条目以"规则 / 判别法"为主; 括注日期的是历史事故沉淀(结论已固化进代码与测试), 叙事只用于理解"为什么"。**精简本文件时只压叙事, 不删规则与判别法。**
> 2026-09-20 精简: 删掉重复条目、已废弃路径(worktree / 旧口径)的叙事、一次性事故的过程数字; 常青约束全部保留。

## 🔴 生产文件, 禁止改动/提交

- **`config.yml`**: 用户真实生产配置(真实 PT 域名 / tracker 规则 / qB 凭据引用)。改示例用 `minimal.yml` / `test_yamls/`。
- **`auto-qb-data/`**: 运行时数据 —— `state.json`、锁 `<state_file 去扩展名>.lock` + 伴生 `.meta.json`、`logs/auto-qb.log`、`skip-check-backup/`。state 只在程序退出时覆写。
- 两者均已 gitignore 但在工作区可见 —— 不要"顺手"格式化 / 重排。

## ⚠️ 高风险业务操作 (代码中已有防护, 改动时不得削弱)

1. **跳检 (skip-checking)**: 删种重加会丢统计, 内容错误会传垃圾数据(PT 严令禁止)。七道防护: 部分下载(0<progress<1)拒绝跳检; 同规则同日去重 + **跨规则**同日去重(`skip_check_day`); 强制 filelist 前置检查; 重加前轮询确认种子已从客户端消失(qB 删除异步 ≤5s, 未消失则放弃); 重加属性**直传**(0/负值有语义, 不得 `or None` 吞掉)+ contentLayout 由 content_path/save_path/文件列表推断; 无参考 warning; 重加失败 .torrent 落盘且元数据立即落盘。跳检过程中种子会从 store 消失 —— 同 tick 后续动作必须容错。
2. **reannounce**: 同种子最小间隔 10M(`reannounce_ts`)+ 暂停种子跳过 + 加载期未配去重 WARNING; 本质仍是高风险操作, 规则应配 `execute_once`。
3. **qB 版本兼容**: `_refresh_torrents` 首次拉全量时校验 `REQUIRED_TORRENT_FIELDS`(快照 18 + 跳检重加 6), 缺失抛 `QbCompatError` → CLI 干净退出。快照字段缺失会**静默零值**(规则基于假数据决策), 比崩溃更危险。**加深快照字段必须同步 `tests/helpers.py` 的 `FakeTorrent._SNAPSHOT_FIELDS`**, 否则 sync 版本校验报缺字段、启动即退(fail-fast 是有意的, 别改宽容)。
4. **`or 默认值` 掩盖数值字段**: `progress or 0.0` 类写法把上游 bug 静默转成合法语义, 且方向可能朝危险侧(progress=None → 视为全新辅种 → 放行跳检)。已清理闸门 / HR 判定 4 处。合法 `or` 仅限空串 / 空容器归一化与除零防护; 判别标准见 conventions.md。
5. **死防御清理**: 判别标准 —— 守卫条件在正确上游流程下**不可能发生** → 删; 是真实可选语义(惰性缓存、运行时状态、功能开关) → 留。已据此删掉 client setter 守卫、`store is None` 15 处等。
6. **自有动作污染状态观测**: 状态转移观测必须放在归组 / 自有停种**之前**(轮次开始的干净观测点), 否则自家停种被误判为外部"上传转暂停", 触发多余的缺文件扫描。顺序约束见 systemPatterns.md。
7. **删除种子** (`QbApi.torrents_delete`): 仅跳检流程使用, `delete_files=False` 固定。auto-qb **不存在任何自动删除路径**(规则系统无 delete 动作, 唯一删除入口是 WEB UI 命令)。
8. **限速不覆盖手动值**: 奇数 KiB 视为用户手动设置则跳过, 判定统一走 `utils.is_manual_speed_limit`(三个调用点逻辑必须一致)。断言"该保护生效"前先确认测试数据真的落在保护范围内 —— 造出偶数 KiB 会被程序正常覆盖, 测的是"保护没生效时的行为"。

## ⚠️ 平台 / API 兼容陷阱

- **锁文件残留随平台不同**: `locking.release()` 只删伴生 `meta.json`; `state.lock` 由 `filelock` 底层处理 —— Windows(msvcrt) 释放时删, POSIX(flock) **不删**(flock 标准语义, 删锁文件反而不安全)。Linux CI 上残留是正常行为, 测试按 `os.name == "nt"` 分平台断言。
- **qB 5.0+ 全局限速**: 必须走 `transfer_upload_limit` / `transfer_set_upload_limit`(bytes/s, 0=不限); `app.preferences` 的 `upload_limit/download_limit` **已静默失效**。qbittorrent-api 新版 `app.preferences` 是 property 不是方法。
- **qB 状态枚举**: 用 `qbittorrentapi.TorrentState` 的 `is_*` 属性判定, 不要比较 state 字符串(pausedUP / stoppedUP 跨版本漂移)。仿真数据里 `"errored"` **不是合法状态名**(解析成 UNKNOWN、缺文件扫描完全不触发), 合法名是 `"error"` / `"missingFiles"`。
- **`sync/maindata` 是增量接口, 单次响应不是种子全集**: rid 匹配时只回**变化种子的变化字段**; 删除列在 `torrents_removed`; 新增种子回全量; rid 不匹配 / 为 0 时 `full_update=true`(自愈信号, 漏 tick / qB 重启只退化成一次全量)。`TorrentStore._apply` 必须区分 full(以响应为全集)与 delta(只改 `patches`、删除以 `torrents_removed` 为准)。❗ **全量轮不可早退**: `full=True` 时即使 `patches` 为空也要走完(需检测删除)。❗ **rid 在 POST body**, 只解析 query 恒得 0 ⇒ 永远退化全量。
- **sync 响应的 hash 是 `torrents` 字典的键, 值内不含 hash**(与 `torrents/info` 的数组元素不同): 直接把 `torrents[h]` 当校验样本会报"缺少字段: ['hash']"并抛 `QbCompatError`(启动即退)。校验前必须补齐 `{**patch,"hash":h}`; **测试替身同样不能在值里塞 hash**, 否则掩盖该 bug。
- **sync 与 `torrents/info` 字段齐平**(同一 C++ 序列化器), 故 `REQUIRED_TORRENT_FIELDS` 可直接用于 sync, 但**只能在全量轮校验**(增量响应只含变化字段, 做存在性校验必误报), 由 `store.need_validate` 闸门隔离。`missing_torrent_fields` 必须同时支持 dict(按键)与对象(`hasattr`)。
- **sync 不可降级为"少几个字段"**: 旧 qB 无该端点抛 `NotFound404Error`, 替身缺方法抛 `AttributeError`, `apply_sync` **只**捕获这两类并降级 `torrents_info()`; 其它异常(网络 / 鉴权)rid 归零后原样上抛, 否则掩盖断连。
- **`TorrentRecord` 是唯一数据所有者, 不要再引入投影视图**: 快照字段存 slots, 非快照字段(RE_ADD_FIELDS)存 `_raw` + `__getattr__`, `apply_delta` **只遍历 patch 的键**。新增字段: 快照字段进 `_SNAPSHOT_FIELDS`, 其余进 `_raw` 自动生效。
- **`apply_delta` 返回变化字段集而非 bool**(下游据此把 O(N) 扫描降为 O(变化数))。变化集对视图字段按 `_VIEW_QUANTUM` 量化后比较 ⇒ `seeding_time` 秒级递增不进变化集(但仍写入 slot)。
- **`dirty_groups` 跨轮累积, 不能用 `_apply` 清空**(轮次外的写操作发生在 `_check_download_conflicts` 之后)。`store.rounds_applied == 0` 时退回全量扫描 —— 别删这个兼容分支, 否则直接调用该方法的测试会静默不再暂停。
- **主循环节流必须经模块级 `_throttle(stop_event, main_tick)`**: 非托管(CLI, `stop_event=None`)走 `time.sleep`, 托管(`--tray`)走 `Event.wait`。写成 `if stop_event is not None and stop_event.wait(...)` 会被 `and` 短路成**完全不阻塞** ⇒ 主循环空转(CPU 打满 + sync 请求放大数千倍)。**托管模式会掩盖该 bug**, 回归测试必须用非托管模式。首连失败重试循环里 `stop_event is None or stop_event.wait(...)` 是**有意语义**, 不要一并改。
- **本地 qB 关闭 requests `trust_env`**: 本地地址经 `qbmanager._new_client()` 构造 `LocalQbClient`(覆盖 `_session` property, 每次返回前强制 `trust_env=False`), 跳过每请求代理 / netrc 解析; 远程域名用原生 `Client`。❗ 旧写法 `client._session.trust_env = False` **从未生效** —— `_session` 是只读 property, 且 `build_base_url()` / `_initialize_context()` 会重建 Session。本地判定取 `base_url` 解析后的 hostname。
- **Windows 长路径**: 磁盘文件检查走 `add_long_path_prefix_for_win`(`\\?\` 前缀), 新文件访问走同一工具。
- **NTFS 稀疏文件: 只有 `FSCTL_SET_SPARSE` → `SetEndOfFile` 是稀疏的**(2026-09-21 实测, 100 文件 × 64 MiB 对照): 正确序列 `CreateFileW` → `DeviceIoControl(h, FSCTL_SET_SPARSE)` → `SetFilePointerEx` + `SetEndOfFile` ⇒ 实占 **0 字节/文件**(仅 MFT ≈205 B), **0.23 ms/文件**(6 万文件 ≈ 14 s)。❗**三种"看着对"的写法全部满额分配**: ①标记稀疏后再 `os.truncate` —— **truncate 会让稀疏标志失效**, 实占整个逻辑大小; ②朴素 `f.seek(n); f.write(b"\0")` —— 非稀疏文件向后扩展时 NTFS 必须让新区域读到 0 ⇒ 满额; ③`fsutil file createnew` 先建再 `sparse setflag` —— **setflag 不回收**已分配的簇(256 MiB 实测先占 166 MB 且不释放)。另: `fsutil` 是**进程派生**不是系统调用, 每文件一次 spawn 在数万文件规模上不可接受 ⇒ 走 `ctypes` + `DeviceIoControl`。⚠ **踩过的现场**: 按错误写法在 R 盘(70 GB 虚拟盘, 当时仅剩 7.2 GB)建树, 第一个 4 GiB 文件实占 4 GiB、第二个文件 `OSError: 112 (ERROR_DISK_FULL)` —— **把盘写满**。大文件稀疏建树前先建 1 个并校验分配量。
- **本机"删除拦截层"只在 D 盘生效, 且 R 盘无回收站**(2026-09-21 实测): 工具环境删除 D 盘大目录会**进回收站而不释放空间**(360sd 在跑) ⇒ `shutil.rmtree` 后 `df` 纹丝不动。要真释放必须按 `$I` 元数据定位自己的条目再删(`$I` 偏移 16-24 是 FILETIME **UTC**、偏移 28 起是 UTF-16LE 原始路径; 同名 `$R` 是载荷 —— ❗**`$R` 若是目录必须 `shutil.rmtree`, 用 `os.remove` 只会报 `WinError 5`**)。但 **R 盘 `$RECYCLE.BIN` 实测 0.00 MB、删除即释放**, **别套用同一条经验**去 R 盘找回收站。
- **判断"两套 API 读数矛盾"前先确认是同一时刻**(2026-09-21 教训): 我拿"写入前"的 `Get-PSDrive` 读数与"写满后"的 `shutil.disk_usage` 读数对比, 得出"三套空间 API 互相矛盾"的结论 —— **完全错误**, 同刻复核三口径逐字节相同(`GetDiskFreeSpaceExW` / `shutil` / `df`)。涉及"环境事实"的结论必须**同刻取样**, 否则会把两次状态差当成工具不一致。
- **`yaml.BaseLoader`**: 配置全是字符串, 不要假设已给原生类型; 空段(如空 `trackers:`)会解析成 None/str, 新增类似段同样要防。

## ⚠️ 行为细节 (易误判为 bug)

- **奇数限速保护** (`(limit/1024)%2==1` 跳过) 是特性不是 bug; 测试断言"奇数不覆盖"。
- **interval 归一化**: `Task.interval <= 0` → 1s; 规则 interval 为 0 = 每轮执行。
- **`handled` 返回值**: `Rule.process` 返回 `not result.is_skipped` —— 最后一个动作 skip 时 handled=False, 但执行历史已记录。设计如此。
- **上传增量下限 0**: `max(0, uploaded - baseline)`, 种子重加后 uploaded 归零不产生负增量。
- **代表种已分化**: 缺文件扫描代表种 `_valid_for_representative` = `is_complete or is_errored` 且非 checking(errored 恰是缺文件第一现场); 跳检参考候选 `_group_reference_candidates` 仍只从 `is_complete 且非 checking` 选。别混。
- **MISSING 组豁免 mixed 冲突是有意设计**: 缺文件组被标记后用户重新下载是合法补救, 不该被"已完成与下载中并存"拦停(multi-dl 不豁免)。重校验发现文件缺失(stalledUP→missingFiles)也是缺文件扫描触发路径。MISSING 标签无自动清除逻辑, 补齐后需手动摘。
- **tracker 匹配是"第一个命中"且统一为 hostname 精确匹配**: 命中多个配置打 ERROR 后仍用第一个(不跳过种子); 导出模板 `find_missing_domains` 仍用包含匹配(有意宽松)。
- **`RuleContext.torrent` 的快照回退是合法语义**: 种子已从客户端删除时回退删除前 `RuleContext.snapshot` 副本, 供只读留档。需活种子的动作在 config 白名单阶段已被拒绝。
- **WEB UI 搜索结果是真实辅种组的筛选, 不是另建虚拟分组**: 命中 hash 过滤 `sortedGroups`(任一组员命中保留**整组**), 未归组命中以单种子虚拟行 `u-<hash>` 兜底 —— **虚拟行不是真实组 key**, 右键必须退化为单种子菜单, 否则 `/api/groups/u-xxx/action` 解析失败 500。搜索结果必须渲染在**始终存在**的容器内(初版 `v-if="!searchQuery"` 把结果区连同空态一起藏了, 表现成"搜索无结果")。判别: 先分清"后端无匹配"还是"前端未渲染"。
- **搜索索引脏标记只在种子集增删时置脏, 不在每 tick 重建**; 构建受 `SEARCH_INDEX_BUILD_BUDGET` 限流故 `building` 可跨多轮。qB 断开时必须**中止构建并保持脏**, 不得把空文件列表当"已建完"。
- **同一份视图脏标记被多条重建路径共享时, 重建范围必须完全一致**: 曾出现主循环只重建 group view 就清标记 ⇒ singles/shows/flat 长期停在旧快照而版本号照常自增 ⇒ 前端判 `updated=true` 把陈旧数组整表换上。修法: 重建收敛为唯一入口 `WebviewMixin.rebuild_views()`; 断言必须写成"四份同次重建", 只 spy 某一个 `_build_*` 会把缺陷固化成预期行为。另: 脏标记是**全部** Web 视图的共享状态, 置脏语句不能写在 `if grouping.enabled` 块内。
- **前端不要用"视图版本号未变"当"数据没变"**: 轮询退避只保留**失败退避**, 间隔恒定。间隔分档只跟**种子总量**有关(≤1000→1.5s / 1000~3000→2s / >3000→3s), 与"本轮有无变化"无关 —— 按 rid 是否变化退避会让状态栏(`/api/stats` 不受门控)与种子行刷新频率解耦, 观感变成"状态栏正常、种子行滞后"。**下界是服务端 `sync_interval`, 不是 0**。
- **分组视图惰性组装的脏标记必须精确**: `store.view_changed` 只在 `_VIEW_FIELDS` 或组成员变化时置真;`seeding_time` 必须按分钟量化(`_VIEW_QUANTUM = {"seeding_time": 60}`, 重建判定与展示值**共用** `view_field_value()`, 只改一处必错)。
- **由配置派生的展示值必须自己找置脏源头**(HR 标签模板、名称 / 分类格式等): 它在种子数据一字未变时也会变 ⇒ 必须在 `apply_new_config` 里显式 `_group_view_dirty = True`。同一判别法适用于缓存的 tracker 错误原因(不进 `_SNAPSHOT_FIELDS` ⇒ `view_changed` 覆盖不到)。
- **WEB `/api/state?rid=` 版本门控**: 版本一致时只回 `status`(不回 groups), 前端靠 `updated` 决定是否整表替换; `status` 是故意恒回传的标量。换密钥 / 重新鉴权时须把 `lastRid` 置 null, 否则列表残留。
- **鉴权判据不能用"凭证串非空"**: 免鉴权模式(`web.skip_local_verify`)下后端不看 Authorization 头 ⇒ 必须引入显式 `authMode` + `authOk` 单点判据, 三处守卫(请求 / 轮询续排 / 标签页可见性)全读它, **空凭证不出网**。登录遮罩只能由"验证成功"放行(`v-if="authRequired"` 单一门控), 不能由 token 赋值驱动 —— 否则错误密钥会闪现主界面。401 收口于唯一 `_logout(msg)`: 遮罩 + 凭证 + localStorage + 轮询 + 全部受保护数据一并清空; 并区分 401(清凭证)与网络失败(不清)。后端: 缺省 / 畸形头静默 401 不记 WARNING(常态), 仅"携带了但错误"记一条不含密钥内容的 WARNING; Bearer 先解析 scheme 再用 `compare_digest`。
- **ruamel round-trip 写盘: 值未变必须跳过赋值**, 否则原本无引号的 `port: 16585` 会被写成 `'16585'`。比较必须按 BaseLoader 语义(round-trip loader 把 `true` 读成 bool, `str()` 得 `"True"` ≠ 树里的 `"true"` ⇒ 误判重写)。列表整体替换、项级注释不保留是已记录的取舍。
- **`config/schema.py` 是设置页表单的唯一描述来源, 不承载正确性规则**(合法性唯一入口仍是 `validate_config`: 把树落临时文件跑 `load_config`, 失败 400 且不碰磁盘)。新增配置键必须同时登记 schema, 否则 `tests/test_config_schema.py` 直接失败。易踩点: 可选整段靠 `Field.optional` **显式声明**(不能用 `default=None` 判定); 前端登出必须 `cfgReset()` 清空配置树。schema 是**模块级常量**, 改完必须重启进程才看得到。
- **每个动作的 dry-run 返回 success** —— 别据 dry-run 日志判断真实执行结果。
- **重启监听同一端口前必须确认旧监听器已 `close()`**: uvicorn 的 `stop()` 只是**请求退出**(主循环每 0.1s 才读 `should_exit`), 毫秒级内重新 bind 必 `Errno 10048`; 且非主线程的 `SystemExit` 会被 `threading` 静默吞掉, 日志里只看到一行不带时间戳的 uvicorn ERROR。现由 `WebServerHandle.stop()/wait()` + `_apply_web_config`(只在 enabled/host/port 变化时重启)处理。
- **`state_file` 仅退出时落盘**: 运行中 kill -9 会丢执行历史 → 去重可能重放, 已知取舍。
- **qB 断连期间错误日志静默是有意节流**(仅"连接态→断开"转换记一次 ERROR, 恢复记一次 INFO); 非 `APIConnectionError` 照常记"主循环异常"。
- **配置热重载的两处"看着像 bug"的现状(未改动)**: ①`_diff_flat` 的分支条件是"两侧都是纯 dict", 真实 Config 的 L0 段是 dataclass ⇒ 实际产出整段单条变更(级别判定仍正确, 只是粒度粗); ②`max_level` / `restart_required_paths` 当前无生产调用(Web 与 qbmanager 各自内联), 属清理候选。

## ⚠️ 并发 / 状态机约束回顾 (违反即引入难以复现的 bug)

1. 主循环线程是唯一修改队列 / state_file / store 分组索引的线程 —— 不要在校验回调、信号处理器、新线程里改。
2. **校验登记与 recheck 的顺序**: 先 `add_task(轮询子任务)` 登记在途(已在途则 skip), 再发 `torrents_recheck`; 发送失败返回 `fail`(不返回 pending), 成功才返回 pending。
3. **断点续跑语义**: `keep_progress=True` 保留 `resume_index`(续跑后续动作), 默认重置清空并重走完整决策链 —— 二者不可混用。
4. **种子删除没有队列级清理入口**: 在途任务必须自带 `store.get(hash) is None` 删除守卫; 事件规则任务作 origin 续跑后同样由首行守卫判死。`print_torrent_details` 走 `RuleContext.snapshot` 仍可打印留档。
5. **QbApi 写方法必须同步 store** (`update_torrent_fields` / `invalidate_*`), 否则同 tick 读到旧值。
6. **视图组装里绝对不能发 qB API**(硬约束, 不是优化): 视图可能每 tick 重建, 在里面发 API = 主循环被 N 次网络往返拖死。取数一律**主循环预取 + 视图只读缓存**, 且必须 **TTL + 单轮预算双限额**(成片错误种子会拖死主循环), **先写时间戳再拉取**(失败也不在 TTL 内反复重试)。

## ⚠️ 前端 / WEB UI 纪律

### 模板与组件

- **computed 在模板里是属性, 不能当函数调用**: `hasUnit()` / `unitParts().num` 在生产版 Vue 抛 `is not a function`, 结果是**整块区域不渲染**(设置页只剩分组标题 / 顶栏整条消失)而控制台常常无醒目提示。 ⚠ **这条坑在代码里真实存在过并被修掉(2026-09-21)**: `ce-field` 的 `setUnitNum` / `setUnitName` 长期写成 `this.unitParts().unit` / `this.unitParts().num`(而 `unitParts` 是 computed, 返回 `{num, unit}`) ⇒ 经典设置页**一改「数值+单位」字段的数字就整页白屏**; 没被发现是因为模板里的 `unitParts.num` 是对的, 只有真的去改主循环间隔/轮转大小这类值才触发。已改成属性访问 `this.unitParts.unit`。**守阵**: `tests/test_web.py::test_frontend_computed_not_invoked_as_function` —— 扫每个片段文件的 `computed: {` 块成员名, 一旦发现 `this.<名>(` 就红(注释行跳过, 否则守阵会逼人删文档); 已红验。带参渲染辅助(如 `unitLabel(u)`)必须放 `methods` —— Vue 3 的 computed getter 被框架以组件代理为参数调用, 收到的 `u` 是 Proxy 而非遍历项, `String(proxy)` 抛 "Cannot convert object to primitive value"。
- **带参数的 computed 是另一条更隐蔽的雷**(2026-09-21, issue 26-09-21-0247): 在 Options API `computed: {` 块里写 `memberWin(list) {…}`, Vue 仍把它当 getter 注册, 模板里 `memberPadTop(g.members)` 触发 `this.memberWin` 被当作属性访问 —— 框架**不会**把 `g.members` 传给 getter(只对 methods 传), 于是 getter 用未定义参数跑完返回一个对象 `{padTop:0,…}`, 然后 `(list)` 把它当函数调 → `this.memberWin is not a function` → 整表白屏(chips / 状态条 / 表头 / 行 全部消失)。坑在编译期不报、lint 阶段单控过、`pytest --passes` 也过 —— 只有能加载页面的脚本里才能复现。**带参的"计算"必须一律放 methods**(放 methods Vue 会把模板里的实参原样透传)。静态守阵见 `tests/test_web.py::test_frontend_member_window_functions_live_in_methods`(定位 `methods:` 与 `computed:` 块边界, 断言 `memberWin` / `memberPadTop` / `memberPadBottom` 定义行落在 methods 之内)。同坑曾因"没人走那条交互路径"长期潜伏, 真机一走就塌 —— 加新成员窗口函数时**先在两套 UI 都跑一遍展开/收起的冒烟**, 不能只看单测。
- **computed / methods / data 三者不能同名**(共命名空间): 同名后调用方拿到的是属性, 抛错形态同上。
- **模板里不允许下划线前缀标识符**: Vue 把 `_` 前缀当内部保留域, `{{ _bulkCountText() }}` 抛 `ReferenceError` 且整块渲染失败(控制台只有一行)。对外派生值去掉下划线前缀。
- **SVG 属性大小写敏感**: 静态写 `viewBox` / `pathLength` 会被模板编译器小写成 `viewbox` ⇒ 浏览器忽略、内容溢出容器。必须 `v-bind="{ viewBox: ... }"` / `v-bind="{ pathLength: 1000 }"`。
- **内联 SVG 只有 `width:100%; height:auto` 会退化成 150px**(无固有尺寸的替换元素) → CSS 显式 `aspect-ratio: <viewBox 宽高比>`。
- **图标一律走 index.html 的 sprite**(`<use href="#i-*">`, 无外部图标库 / 网络依赖): 新增图标只在 sprite 加一个 `<symbol>`; 各 symbol 的 viewBox 可以不同(按 symbol 自身映射, 使用处不必改)。
- **SVG `<use>` 图标想做双色: 外部 CSS 选择器进不去影子树**(2026-09-20 实测): 图标是 sprite `<symbol>` + `<use href="#i-*">`, `.ico-today .down { stroke: ... }` 这类选择器对 use 内部的 path **无效**; 能继承进去的只有 **CSS 自定义属性**。双色只能写成 symbol 内 path 的内联 `style="stroke: var(--token)"`, 靠 var() 在影子树里解析(令牌定义在 `:root`/主题上)。同理, 想按状态改图标局部颜色, 别指望加 class。
- **静态资源不加 `Cache-Control` 会被浏览器启发式缓存**(StaticFiles 只给 ETag)⇒ 升级后仍加载旧前端, 表现成"界面改了但没变"并误导排查。现由 `web.py` middleware 给所有非 `/api` 响应加 `no-cache`。
- **前端表达式错误只有浏览器能发现**: 后端字段 / 接口全对、pytest 全绿而页面崩是常态 ⇒ 改任何前端渲染逻辑后必须做浏览器冒烟, 并**主动触发对应渲染分支**(例: pill 只在限速曲线启用时才渲染)。
- **未闭合的 `<transition>` 会静默吞掉其后所有弹窗**: `<Transition>` 只渲染**第一个**子节点, 其余全部被丢弃 —— 点击毫无反应、控制台零报错、DOM 里连元素都没有。判别: 逐行数 `<transition>` 配对看弹窗所在深度; 修完核对 `.modal-mask` 的父节点不是 `TRANSITION`。
- **CSS 规则漏 `; }`(或选择器头被吞)会让其后规则整段被丢弃**, 而全文件花括号可能仍配平 ⇒ 数括号查不出来。定位: 把 CSS 文本塞进 `<style>` 比 `sheet.cssRules.length` 与顶层块数, 二分找第一处"解析数 < 应得数"的行。
- **组件变体用 CSS 变量承载时, 后写的直接属性会让变体静默失效**(`.btn{background:var(--btn-bg)}` + 主题里又写 `.btn{background:#000}` ⇒ 变量声明变死代码)。全库二选一并统一: 主题只覆写变量, 或变体直接写属性。悬停态也需要独立的文字色变量。
- **两套 UI(星图 atlas / 棱镜 prism)必须成对改**: 同一个状态开关(`v-if="xxxOpen"`)在模板里出现两次以上基本可断定是遗漏的旧实现(实测"点一次开两窗")。状态色 / 令牌族 / 修饰符类改动**按选择器在两套 CSS 各 grep 一遍**, 数量对不上就是漏改; 仅改 `shared/app.js`(逻辑层)才天然两套生效。改完加静态计数断言兜底, 不要只靠肉眼走查。
- **"CSS 已入库但模板从未切换"的两不管缺口**: 静态 class 覆盖检查要双向做 —— "模板用到但 CSS 未定义"与"CSS 定义了但模板从不使用"。
- **`cfgFlatten` 的 `group_of` 分组判定不能递归复用**(子卡内字段已归属父字段, 再参与分组会把它们收进 children 而 roots 为空 ⇒ 子卡渲染成空壳**且不报错**)。递归时传 `allowGrouping=false`。排查"渲染出来但是空的"最快的是浏览器控制台 + 模板里临时打一行 `{{ item.items.length }}`。

### 样式 / 布局 / 表格

- **列宽模型 = 列定义单一来源(`GROUP_COLUMNS`/`DETAIL_COLUMNS`) + 按列 key 存 + 拖动前先固化全部可见列为 px**。列宽按 **key** 存(索引在支持隐藏列后会漂移); drag 起始不固化全部列 ⇒ 被拖列会从邻居的 fr 余量里抢空间。
- **加 / 减列 / 重排一律不升列状态存储版本**(R10-09 反转, 旧结论"必须升版本"已作废): 新增列在旧缓存里只是"没有记录"(回退默认宽), 已删列由 `loadColState()` 按当前列 key 求交集洗净 —— 都不会错配, 而**升版本会清空用户手调的宽/隐/序**, 这才是"列宽时不时被重置"的机制性来源。**判据: 只有"旧缓存结构无法被 `loadColState()` 正确解释"才升版本**(如 v2 按列索引存), 且升版本必须把旧键挂进 `LEGACY_COLS_KEYS` 迁移(v2 索引式不可迁移, 刻意不挂)。当前键 `autoqb_cols_v4`。
- **localStorage 的两种"重置"要分清**: ①**origin 隔离**(`scheme://host:port`)—— `localhost` 与 `127.0.0.1`、换端口各存一份, 客户端无法消除(用户明确只存浏览器, 不做服务端化); ②**多标签页整份覆盖** —— 内存是页面加载时读一次的快照而 `saveColState()` 写整份 ⇒ last-writer-wins, 先改的那个标签的改动被静默吞掉。修法 = 写入改 **read-modify-write**(只覆盖本次涉及的 page)+ 监听 `storage` 事件跨标签 adopt + `visibilitychange` 补一次(只做 page 级合并不够, 两个标签通常改同一个表)。**报"偏好被重置"先问"几个标签页"**。换密钥 / 登出只清 `autoqb_token`, 全仓无 `localStorage.clear()`。
- **行宽口径 = `fit-content; min-width: 100%`, 且行内单元格必须 `min-width: 0`**: 缺后者时单元格的自动最小尺寸(= 文本全长)会把行的 min-content 顶到容器之上 ⇒ "列没溢出却常驻一条横滚动条"。**判别口诀: 底色跟内容、滚动条看容器**, 两者同时满足才算对(曾用"行定宽 100%"治假滚动条, 会让溢出段没有底色, 已回退)。
- **表头吸顶**: `.group-head` 必须移出 `.group-table` 挂到 `.content`(`overflow-x:auto` 会把 `.group-table` 变成双轴滚动容器, sticky 上下文失效), 横向靠 JS `transform: translateX` 跟随(不用 scrollLeft 避免回环、不加 transition); `.content { overflow-x: clip }` —— **clip 不创建滚动容器**(用 hidden 会让 sticky 立刻失效)且阻止表头把整页撑出第二条横滚条; `.detail` **不得**再写 `overflow-x: auto`。
- **生成式列对齐(`colAlignCss` 注入 `:nth-child`)**: ① **left 列也必须生成规则**(数值列的 `.g-stat/.m-stat` 会盖掉默认左对齐); ② 选择器必须用 `:where()` 压到 0,1,0 —— 高于 `.g-stat` 才能覆盖, 又必须低于 `.g-stat.zero` 以保留"0 值居中"; ③ 同时写 `text-align` 与 `justify-content`(值单元格有的是 flex)。行 / 表头容器必须带 `data-table="<page>"`。
- **sticky 偏移与最大高度不能写死**: `--head-h` / `--bulk-h` 由 JS 量测写入 `:root`(值未变直接返回), 元素用 `calc()` 引用; `--bulk-h` 只记吸顶条**自身高度**, 流内 margin 不计入(否则吸顶态恒定多一条缝)。
- **两个吸顶条各有 `backdrop-filter` ⇒ 各自建立层叠上下文**, 子元素的 z-index 跨不出去(浮层被另一个 sticky 条遮挡): 两者都设 `position:relative` 并拉开次序, **只加之一无效**。判别: 先看遮挡方是否也有 `backdrop-filter`/`transform`/`filter`, 不要一味加大 z-index。
- **`:focus-within` 在带 `tabindex` 的行上, 鼠标点击也会画 outline** → 改用 `:focus-visible`(保留键盘可达性)。
- **不可见的全屏遮罩会拦掉整页点击**: 过渡未走完时 Vue 不移除元素, `opacity:0` 的 `position:fixed` 层吃掉所有点击。加固: `<transition :duration="200">` + `.xx-leave-active { pointer-events: none }`。
- **flex 行里"输入框缩成一截 + 按钮文字竖排" = 父容器缺增长因子**: `input` 的 `flex-basis:auto` 在自动宽度父级里回退成内容宽; 给**直接父级**加 `flex:1 1 auto`, 并把同行按钮锁成 `flex:0 0 auto; white-space:nowrap`。判别: 容器宽 / 输入框宽 / 按钮宽三者加起来远小于容器宽 = 父级没涨。
- **flex / grid 子元素里 ellipsis 不生效** = 被省略的是**裸文本节点**(匿名文本节点不可压缩): 必须包一层 `<span>`(`min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap`), 容器给 `title` 看全文。
- **`min-height` 是含边框的**(`box-sizing: border-box`), 想让"有/无某段内容"行高一致必须把 `border-bottom` 算进去; 断言前先在浏览器里量, 别按 CSS 数值推算。
- **拖列宽会连带触发排序**: mouseup 后浏览器仍会把按下→移动→释放合成 click 冒泡到 `.h-cell`。修法 = 在 move 里累计位移(阈值 3px), up 时在 `document` 注册**一次性 capture 阶段** click 拦截器。
- **入场动效不要给含 sticky 子元素的容器加 `fill-mode: forwards`**(transform 常驻会创建层叠上下文, 影响内部 fixed / 浮层定位)。
- **「例外色」规则别靠书写顺序赢: 同特异性时后者压前者**(2026-09-20 实测): 状态栏今日流量的 `.sb-today .v-down` 与后面的 `.sb-item .val` 特异性同为 (0,2,0), 谁写在后面谁生效 —— 棱镜 views.css 里前者在前 ⇒ 数值与数值里的箭头图标掉回白色, 星图 style.css 里前者在后 ⇒ 碰巧正确(**同一份改动只坏一边**, 极易误判成“棱镜主题缺令牌”)。修法: 给例外规则**抬特异性**(`.sb-item.sb-today .v-down`, (0,3,0)), 与书写顺序解耦; 两套 UI 各写一份 CSS 时务必两边同步改。
- **既有窄屏媒体查询会吞掉新加的信息**(加 pill 前先搜一遍 `@media`), 删除某个槽位后其规则与媒体查询会变成死代码(收尾 grep 一遍类名)。
- **同一语义不要用两种视觉重复表达**; "组内不一致"是提示性信息, 对比色资源留给需要立刻行动的信号(HR 未达标 / 错误)。
- **HR 标签着色靠"文本逐字相等"**: 后端用 `replace_vars` 展开模板透出字符串, 前端只做 `tag === member.hr_tag` 比较。前端改用图案猜测或再拼一次模板, 自定义标签格式会立即失效。H&R 筛选同理 —— 只消费后端算好的组级计数 / 成员布尔, 前端不做阈值重算。
- **"某列 / 某值恒为占位符"且同一取数点被多处复用 ⇒ 先核字段名**: 全局限速读 `server_state` 的 `dl_rate_limit`/`up_rate_limit`(`dl_limit`/`up_limit` 是单种子级字段); 实测过一次"恒 undefined ⇒ 显示恒为 — 且兼任染色分母 ⇒ 色阶从未生效"。全仓 grep 该键名命中 0 处 = 后端根本没这个键; 修口径时收成**单一取数点**。

### 浮层与交互

- **浮层"点了没反应"首先查定位祖先**: `.pop-menu` 是 `position:absolute` + `top: calc(100% + 4px)`, 容器必须有 `position: relative`, 否则最近定位祖先变成 `.modal-mask`(`inset:0`)⇒ 面板被渲染到视口外。排查法: 打 `getBoundingClientRect()` 看坐标。**同类坑已出现两次。**
- **"聚焦即展开"的输入框必须同时 `@click.stop`**: 全局 window click 监听统一关闭浮层, 而 `@focus` 由点击触发 ⇒ 面板开了又被当场关掉。
- **弹层"左对齐 + 固定宽度"在靠右锚点上会伸出视口** → 打开弹层的**同一同步调用栈**里测 `anchor.left + 菜单宽 > innerWidth - 8` 并加 `flip-x`。注意 `ev.currentTarget` **只在 handler 同步代码内有效**。
- 无遮罩浮层: 根节点加 `@click.stop`(否则点输入框也关); 自绘候选面板的选项用 `@mousedown.prevent`(用 `@click` 会先移走焦点); 原生 `<datalist>` 必须整体退役(建议浮层不受主题控制、会自行超时消失)。
- **删除编排在前端而非后端**: "删除前强制汇报"由前端串行编排(汇报→等回执→成功才投递删除), 后端不做复合命令。
- **多选保留策略**: 增量刷新(整表替换)后按 key/hash 交集保留选中; 虚拟行 key(`u-<hash>`)不做存在性校验; 批量目标拆解时已消失的 key 跳过。
- **命令回执机制**: 入队生成 `cmd_id`, 主循环执行完写 `_web_results[cmd_id]`(reannounce 例外, 由确认跟踪器写), Web 线程经 `GET /api/cmd/{id}` 只读; `_drain_web_commands` 把 `cmd_id` 从 args 剔除后才分发(否则 handler TypeError)。**下划线前缀键是元数据**(如 `_queued_ts`), drain 里过滤掉不传 handler; 测试断言入队参数时也要先 pop。
- **强制汇报的"成功"回执是 tracker 确认而非 API 返回**: 判据 = status==3(updating)/ next_announce 比 baseline 提前 >60 / status 非 2 变 2, `REANNOUNCE_CONFIRM_TIMEOUT=30s` 超时判失败。前提是替身 trackers 带 `status`/`next_announce`(FakeClient 默认只返回 url ⇒ 永远无结论)。

### 前后端数据契约

- **不能只看后端载荷, 前端还有一层派生**: 判"前后端字段不一致"前**必须沿前端 computed 派生链追到实际消费点**(如 `save_path` 由 `decoratedGroups` 派生), 只看后端对象与某一行的 `g.xxx` 会误报。反向也成立: 后端补字段前先确认前端是不是已经算了。审查结论里"必失效 / 必崩"这类强断言, 动手前先做最小验证。
- **追剧视图 `members` 是双形态**(后端 hash 数组 / 前端 `decoratedShows` 装饰成成员对象): 任何写进 URL / 命令载荷 / `memberByHash` 查找的地方必须先 `memberHashesOf()` 归一成 hash, 否则字符串化成 `[object Object]` ⇒ 后端 404「种子不存在」(不报错, 只有一条 toast)。**"同一动作单种子正常、聚合行失败"基本就是这个形状**。守阵: `test_frontend_static_bundle_health` 第 7 项(集成员取 hash 的行必须含 `memberHashesOf(`)。
- **P1-1 按视图回传: 前端赋值必须"键不存在则保留原引用"**(`if (state.groups !== undefined)`), 否则每次轮询把其它两个视图抹成空; 切视图时把 `lastRid` 置空强制取一次全量; 服务端 `view` 取保守默认(未知 / 缺省 ⇒ 全回)。
- **每条视图的数组集必须覆盖"该视图渲染所需的全部数据源"**: 追剧页的 `shows[].members` 只是 hash, 前端要靠 `memberByHash`(groups + singles 拼)还原成员 ⇒ 只回 shows 会让整页**永久空白且不自愈**(lastRid 已记住, 之后每轮都是"版本未变不回传")。改 `VIEW_ARRAYS` 时逐个视图问"它渲染时还读哪些数组", 并**用刷新页面的方式验证**(切视图会掩盖问题)。
- **跨视图的派生聚合(状态分布 `distSegments` / 状态 chip / 状态条)必须按 `viewMode` 自取数**(2026-09-21, issue 26-09-21-0247): 后端按视图裁剪(`VIEW_ARRAYS` 的设计本意), 旧版 `distSegments` 只数 `this.groups[].members[].kind` ⇒ 两种场景 chips 全空: ①localStorage 持久化 `autoqb.ui.view=torrents` 后首进种子页(`groups=[]` 首轮即空); ②在种子页停得久(轮询只刷 torrents, groups 永远空或冻结旧值)。表现「做种10 错误1」整行消失 —— 用户只会觉得"统计没了", 排查方向跑偏。修法 = `distSegments` 按 viewMode 分支: groups 走 groups + singles / torrents 走 `torrents[].kind` / shows 走 `shows.list[].seasons[].episodes[].state`(`shows` 是 `{list, unrecognized}` 不是数组, 第一脚就踩过)。判定口诀"凡跨视图呈现的派生值, 都问一次'它在另两个视图下还成立吗'"; 守阵见 `tests/test_web.py::test_frontend_dist_segments_aggregates_per_view`。
- **⚠️ 跨视图的常驻消费者不能依赖按视图裁剪的阵列**(状态栏速度恒为 0, 同类第二次): 全局聚合一律**服务端算好放进 `status` 恒回传**(与 `traffic`/`server` 同口径), 不参与 `VIEW_ARRAYS` 分片、不参与 rid 门控。**不要**反过来把阵列加回 `VIEW_ARRAYS`(会废掉 P1-1 的体积优化)。每次增删 `VIEW_ARRAYS` 键、或新增常显 UI 元素时问一句"它的数据源会不会在某个视图下不回传"。
- **rid 门控下"下轮以服务端为准"是不成立的**: `updated === false` 时前端不回传数组也不整表替换, 行对象保持原引用 ⇒ 任何"我不再写它了"的写法都会把值永久留在行上。乐观 UI 的兜底必须**显式回滚 `op.prev`**; 且回滚放在每轮 `refresh()` 里, **不要在渲染函数里改响应式字段**(`isPending()` 每帧被调用, 有递归更新风险)。
- **"服务端的值"不等于"已落地的值"**: `torrents/resume` 返回 200 时 qB 还没翻状态, 紧跟着的补刷新读到的是**命令前**的旧值 ⇒ "权威值"其实是滞后一拍的旧值。判据: 与本地预测不一致的服务端值绝大多数是**还没落地**, 不是"预测猜错了"。修法 = 前端只在真值**匹配**时撤下(不一致保留乐观值继续等)+ 服务端发回执前等真值落地(上限 1200ms, 超时必须照发, 等待期间按 0.2s 快速补刷新)。**代价排序: 显示错误状态 >> 多等一会儿。**
- **同一概念两张表必须对齐**(前端 `STATE_RANK` 与后端 `_SHOW_STATE_RANK`): 由 `tests/test_web.py` 静态守阵机械比对, 改一边不改另一边即红。`distSegments` 里那张是**图例展示顺序**不是优先级, 别顺手统一。**⚠️ 且"一致"只管两页同色, 管不了"同成哪个色"** —— 顺序语义本身也被钉住了: **`seeding` 必须严格排在 `paused` 之前**(组/集内"部分暂停部分做种中"取**做种色**, 2026-09-21 用户口径)。反例就在 2026-09-19 修 BUG-7 时: 把前端表整体对齐后端, 顺手把 `{paused,seeding}` 也翻成 paused ⇒ 辅种页做种中的组**整行变灰**, 用户报"以前是对的"(回归提交 `04cbc8e`)。**教训: 统一两张表前, 逐项问一遍"这一项翻过去, 用户会看到什么变化"; 语义有争议的项(此处 `paused` vs `seeding` 谁更该被看到)不要夹在"消除漂移"里一起改。**
- **取数单点放后端, 前端只展示**: tracker 错误原因由 `_error_reason()` 一个出口算好透出, 前端不得按 state 猜原因。`missingFiles` 状态自明, 必须排除在 tracker 拉取分支外(省预算)。
- **只在用户显式动作时才需要的字段不要塞进轮询载荷**(如 `magnet_uri`): 按需取一次详情即可; 每轮响应体加字段在大库上是 MB 级。
- **验证手法(可复用, 比静态阅读快)**: 起 `uv run python scripts/ui_harness.py --torrents 300 --port <空闲端口>`(合成种子自带非零 dlspeed/upspeed), 再 `curl "…/api/state?view=<X>"` 逐视图比对响应键与合计 —— 一眼看出哪个键在某个视图下缺了。
- **在真浏览器里验"聚合行状态色"必须让注入的合成组落在渲染窗口内**(2026-09-21 实测): 组/集表是**窗口化 + 客户端排序**的(只渲染视口附近 ~26 行, 默认按 `added_on` 降序) ⇒ 把合成组 `prepend` 进 `vm.groups` 只会让它排在**窗口外**, `document.querySelector('[data-key=…]')` 拿到 `null`(第一轮就踩了, 差点把"没渲染"读成"没生效")。给注入组一个极大 `added_on`(如 4102444800)即可置顶。取色用 `getComputedStyle(el.querySelector('.g-name-text')).color` —— 组行没有 `.state-text` 列, 整行靠 `.group-row.s-<kind> .g-name-text` 那条规则着色(做种绿 `rgb(23,138,92)` / 暂停灰 `rgb(82,112,140)`)。
- **冒烟失败先做 A/B 归因, 不要默认"是我改坏的"**: 把改动临时改回旧值再跑一遍同样的冒烟, 失败项集合相同即为**既有失败**。2026-09-21 实测: 修辅种页状态色后冒烟 58 项失败 2 项(两 UI 各一条 `P0-3 乐观态及时落回真值`), 换回旧表重跑**同样那 2 项** ⇒ 与本改动无关。如实报"既有"即可, **别顺手去修不相关的断言**(那是范围守恒的反面)。

### 性能与刷新节奏

- **热路径返回裸 dict 会被 FastAPI 白跑一遍 `jsonable_encoder`**(递归遍历整个响应体做"可 JSON 化"转换, **全程占 GIL**): 端点里改成 `return JSONResponse(content=payload)` 走 `routing.py` 的短路(`isinstance(raw_response, Response)`)即可跳过。❗ **载荷里有非 JSON 原生类型(dataclass / datetime / set / Decimal / Enum)必须保留编码器**(如 `/api/config/schema` 的 dataclass), 否则直接 500 —— 那趟遍历对它不是白跑。守阵用**计数替身**包住 `jsonable_encoder` 断言调用次数为 0(刻意不用计时断言, CI 不可靠), 清单里明确排除 `/api/config/schema` 并写明原因。
- **"载荷大"不等于"要裁字段"**: 优化前先量四步, 每步都能独立否决一个方向 —— ①字节**构成**(最大字段占多少, 裁掉能省几成)②客户端**拆分**(parse / 赋值 / patch 各多少)③网络**对照**(同尺寸静态文件走同一栈要多久)④服务端**端点内耗时**(5 行计时中间件)。④与①②③对不上就是框架在收税。**排除法比猜测便宜。**
- **补刷新必须调完整的 `_refresh_torrents()`, 绝不能只调 `store.apply_sync()`**: 后者只更新 `by_hash` + `server_state`, 分组索引 / 任务 / 事件 / 搜索索引一概不碰 ⇒ 新种子不归组、`on_torrent_deleted` 不触发、删除不处理、`store.groups` 残留幽灵、状态快照不推进。补刷新放在 `_drain_web_commands()` **整批结束后一次**(不是每条命令后各一次)。
- **命令线与 tick 线必须解耦**: 命令唤醒只触发 `_drain_web_commands()`, `_tick()` 严格按 `next_tick_at` 推进; 自投递命令(`build_search_index`)**不唤醒**。任何"让主循环提前醒来"的改动先问一句 —— **提前跑的是消费, 还是整轮 tick?** 整轮会连坐三处: `max_tasks_per_tick` 的**速率语义**(默认 20 × 2s = 10 任务/秒)、两个每 tick API 预算(sync / tracker)、以及"唤醒→drain 拉 500 条文件 API→重建视图→又投递→立刻再唤醒"的**自激循环**。验收加不变量用例: 2s 内连投 100 条命令, `_tick` 次数与无命令时相同。
- **分层节拍的等待必须是 `min(两条线的到期时间)`**, 不能退化成"单一 cadence + 内部门控"(任务间隔会被循环粒度量化: 1.5s 粒 + 2s 间隔 ⇒ 实测 3s)。**多事件等待顺序不能反**: 阻塞在 `wake_event` 上、分段只是为了让 `stop_event.is_set()` 被检查; 反序时命令延迟退化到 ≤0.5s, 恰好抵消收益。
- **别给 `rebuild_views` 单独配节拍**: `ensure_group_state()` 已是"请求驱动 + 脏门控" ⇒ 视图重建频率天然 = 前端轮询频率, 另配定时器只会在"前端没来取"时白建。服务端快于客户端时用 **rid 消费情况反向门控**(`_web_pending_ver`): 两个边界 —— **脏标记必须保留**(只是不生产, 不是丢弃变化)与 **`force=True` 必须绕过**(本轮有命令改了状态时真值必须立刻可见)。
- **只读端点短缓存的四个边界**: ①写入点在 `_require_torrent()` 之后(否则不存在的 hash 以攻击者可控的键进缓存 = 投毒)②**断连判定必须在缓存之前**(否则缓存把 503 掩盖成 200)③失效键用**写序号** `_web_write_seq` 而不是主动失效(把"忘记调失效"换成"键空间增长", 有上限兜底)④残留: 锁外调 `fn()` 会惊群、超 128 项整表 clear。
- **埋点写完必须有人消费**: 立计划时给每条验收口径**指派交付物**(断言 / 报表字段 / 走查表), 没有承接方的口径等于没写; 前端埋点要覆盖**整条链路**(补丁 / POST / 排队 / 执行 / 端到端), 只量一段会在真机慢时无从下手。
- **改主循环会静默废掉既有的节流守卫**(靠"每轮一次 sync"假设的用例会在分层后挂死而不是失败), 改写这类用例时判据要用真实经过时间, 不能用 mocked sleep。
- **改 `_tick` / `_sync_line` / `_task_line` 签名时必须同步所有测试替身**: 替身签名不匹配 ⇒ 每轮调用抛 TypeError 被 `run()` 兜底吞掉 ⇒ 退出条件永不触发 ⇒ **全量测试挂死 10 分钟而不报错**。用 `grep -rn "_tick = \|_sync_line = \|_task_line = " tests/` 找齐(替身不一定叫 tick, 也可能是局部 `def boom(...)`)。新参数一律给默认值。
- **`yapf -i` 会顺手重排文件里本来就超宽的旧行**: 改配置 schema 这类文件时只格式化自己加的那段, 或改完先 `git diff --stat` 看行数是否异常。

- **相对时间("N分钟前")必须挂在响应式时基上, 否则会永久停在渲染那一刻** (2026-09-20 实测): 后端 `last_activity` **按分钟量化**且只在活动发生时才变, 加上 `rid` 未变时 `/api/state` 不回传数组(契约: 键不存在保留原引用) ⇒ 行对象不被替换、也没有响应式依赖变化 ⇒ Vue 不重渲染 ⇒ 单元格里现取 `Date.now()` 算出的相对值被冻结在渲染那一刻(暂停的种子"刚刚"挂一整天)。修法: 读响应式 `nowSec`(`data` + `mounted` 起 30s 的 `setInterval`, `unmounted` 清掉)而不是现取时间; **30s 一跳是刻意的** —— 展示粒度只到分钟, 更密只会白付整表 patch, 与 P1-2 窗口化的成果相抵。复验: 浏览器里把 `nowSec` 拨快 1 小时, 相对文案应整体加一档。纯**时长**(做种时长/ETA)不在此列 —— 它们的值本身是秒数差, 不随时钟走。
- **同一列里别混两种格式** (2026-09-20 用户反馈): "最近活动"改相对时间时留了"超 30 天回落绝对日期"的兜底, 结果同列里"有的 3天前、有的 08-11 21:06"被读成**没改干净**。做"把某列改成 X 口径"这类改动, **要么全列统一, 要么别改** —— 按阈值切换回落的"兜底"在读者眼里就是 bug; 长跨度的可核对性改用 `title`(悬停看绝对时间点)补回, 与列内格式解耦。

## ⚠️ 测试 / 冒烟 / 仿真纪律

### 副作用与测试环境

- **测试不得产生真实系统副作用, 由 `tests/sidefx.py` 记账 + 会话级守阵兜底**(收尾有越界项即让本次 pytest 失败)。七类: `POPEN` / `LAUNCH` / `REG` / `REGVAL` / `FSDEL` / `SYMLINK` / `BIND` / `CONNECT`, 回环与临时目录放行。要点:
  - **`POPEN`/`LAUNCH` 放行清单为空** ⇒ 测试里出现 `subprocess` / `os.system` / `os.startfile` / `webbrowser.open` 会被判越界。典型症状是"**单独跑绿、全量跑 ERROR**"(报错出现在收尾而非断言处)。守卫要改成**进程内**加载脚本模块, 零子进程。
  - **唯一曾被漏掉的真问题是 AUMID 注册表键**(构造 `PlatformChannel("win32")` 时真写 HKCU 且**不清理**; autostart 的 Run 键自清理)。conftest 的两道会话级守卫细节: 让写入**静默成功而不是抛异常**(源码只 catch OSError, 抛异常会让 appid 回退打乱断言), 且 `CreateKeyEx` 的替身**必须支持 `with` 语句**。`StubRegKey` 放在 `sidefx.py` 而不是 conftest —— 用"替身类型识别"避免两个夹具的安装顺序影响判定。
  - **通知器必须拦在真实执行点**: ①给被测代码传 `MagicMock` 当配置对象时, **任何 `if not cfg.xxx` 形式的守卫都会放行** ⇒ 守卫后面接真实副作用的路径必须显式 mock 该副作用入口; ②`PlatformChannel("linux")` 只是**换了个后端**, 后台线程照样真实执行 `notify-send` ⇒ **"换后端 ≠ 不发"**; ③conftest 只拦通知器**命令名**, 不拦命令构造与非通知器子进程, 需要真实 `subprocess.run` 的用例自行 monkeypatch 即可覆盖夹具。
  - **排查输出必须写文件, 不能写 `sys.stderr`** —— pytest 按用例捕获输出, **通过的用例直接丢弃** ⇒ 横幅全被吞掉, 统计成 0(假阴性)。统计一律用 **ASCII 标记**(中文在日志里会被写坏, 按中文串 grep 会得到假的 0)。
  - **记账器里"断言会话累计越界数为 0"是哨兵**而非单点用例 —— 别的用例污染台账它就会红, 排查时先看它列出的越界项归属哪个用例, 别在它身上找原因。
  - **过滤临时目录别只信 `abspath` 前缀** —— Windows 长路径前缀 `\\?\` 会绕过前缀过滤(`abspath` 不剥它), 曾把 157 条临时目录内删除全判成越界。
- **环境能力缺失 ≠ 代码缺陷**: 断言"环境相关能力"的测试必须**显式给定前提**(`monkeypatch.setenv("APPDATA", ...)`; 沙箱里 `os.symlink` 会**落成真实目录** ⇒ 建链后补 `os.path.islink()` 判定再断言)。判据: **单跑通过、全量失败**, 或"本机失败但从逻辑上看不出问题" ⇒ 先怀疑环境能力, **排除环境之前不要动 `src/`**。
- **不要并发跑多个 pytest 进程**(抢端口 + 越界判定是会话级 ⇒ 全量里多出 1~2 条失败而单独复跑全绿)。**不并发也会偶发**: 工具环境的文件删除拦截层清理**其它进程遗留**的临时文件时, 那次删除同样记进当前会话台账。判据同上 —— 复跑一次确认即可, **不要改测试或代码**。
- **测试基线的临时目录与覆盖率文件必须落在仓库外**, 且 basetemp 目录本身必须**不存在**:
  - `--basetemp` 指到仓库内 ⇒ 仓内删除被判越界(5 failed + 1 error, 是环境口径差异不是回归)。
  - 默认 basetemp 下收尾批量删 `%TEMP%\pytest-of-*` 会撞删除拦截层 ⇒ **点号全过却打不出 `N passed` 与覆盖率表**(退出码 1, 看起来像失败)。
  - `COVERAGE_FILE` 留在仓库根 ⇒ coverage 开跑时先擦它, 这次删除同样被拦 ⇒ **开跑 1 秒即退出**。
  - 复用已存在的 basetemp ⇒ pytest 开跑前 `rm_rf` 会拉起回收站助手进程, 被记成越界 `POPEN`。
  - 写法: `COVERAGE_FILE=H:/Temp/aqb.coverage uv run pytest tests -q --basetemp=H:/Temp/<全新目录>`(须在 `tempfile.gettempdir()` 之下)。
- **「Windows 全绿 / Linux 全红」: 本机跑通不等于 CI 跑通**(Linux CI 一次红 4 项, 真根因三个): ①**POSIX 的 `shutil.rmtree` 走 fd 版实现**(删目录内条目时传**纯文件名 + `dir_fd`**, 而 Windows 不支持 dir_fd 走拼接绝对路径的另一支)⇒ 记账器只记 `path`, 同一份临时目录清理在 Linux 记成 `'state.json'`、realpath 落到 CWD ⇒ 判越界。修法: 记账前用 `_with_dir_fd()` 把 `dir_fd` 补成绝对路径(Linux 读 `/proc/self/fd/<fd>`, macOS 用 `fcntl.F_GETPATH`)。②**`utils.atomic_write("")` 不是"什么都不写"** —— `abspath("")` 是 CWD, `dirname` 再取一级就成了**CWD 的父目录** ⇒ 往仓库外丢 `.tmp`(本机长期误判成"IDE 临时文件"的越界项就是它); 修法是对空路径直接 `raise ValueError`。③**平台专属模块导入 / 真实 socket 连接** —— `PlatformChannel("win32")` 内的 `import winreg` 在 Linux 抛 `ModuleNotFoundError`(调用方只 catch `OSError`)⇒ 用例改为 `monkeypatch.setitem(sys.modules,"winreg",替身)`; patch `qbmanager.Client` 无效(`connect()` 走的是 `qbclient._new_client`)⇒ patch 真正被调用的名字, 与网络解耦。
  - **判别法: 凡是"记账器判越界 / 平台专属模块导入 / 真实 socket 连接"这三类, 本机绿不算绿。** 平台相关测试必须以 `monkeypatch` 固定平台(测试主体是"平台逻辑"而非"当前真实平台"); 纯 Windows 行为(长路径 `\\?\` 前缀)直接断言在 Linux CI 上必失败。
  - **本机复现 CI 的平台差异(比推上去等 CI 快得多)**: WSL 里 `wsl -- bash -c '...'` 复制一份仓库(排除 `.venv`/`.git`)、`uv sync`、`uv run pytest tests -q` 即可(加 `-p 3.12`/`-p 3.13` 还能对上 CI 矩阵版本)。
- **速度**: 空载全量约 **32 秒**(带 `--cov-branch`)/ **25 秒**(`--no-cov`)⇒ 直接跑全量即可, 不必挑子集(并发污染下测出的"某文件 300 秒"是假数字)。**别用 `| tail -N` 接 pytest** —— 会缓冲到进程结束才出任何输出, 容易误判成卡死。

### 断言有效性

- **写"修复前必失败"的用例必须做红验**(把修复临时还原, 确认用例失败)。并发 / 时序类尤其容易写成**安慰剂**(有锁绿、无锁也绿 —— 因为无锁时最后发布者胜出, 四份数组仍自洽)。修法: 改成**确定性**断言(让重建卡在 builder 里不放行, "能否返回"只取决于有没有锁)。红验优先用运行时 monkeypatch 还原旧实现(不碰工作区), `lru_cache` 记得先 `cache_clear()`。
- **两种"摆设断言"**: ①**恒真断言**(`epRows >= 0`)—— 整页空白照样 PASS; 判据一律写 `> 0` 或等值比较; ②**某种模式下恒红**(error 模式下回执瞬间返回 ⇒ 乐观窗口在采样前就关了)—— 该模式实际没人跑。**"恒红"和"恒真"一样让断言失去意义**, 新增断言时两条都查。
- **A/B 结束后读到的基线是"改动后"的值**(A/B 函数收尾会把开关还原)⇒ 断言退化成自比。修法: 在同一段 `page.evaluate` 里**来回切开关各读一次**并等两帧。
- **冒烟断言别用"固定睡 N 毫秒再采样"** —— 两种假象方向相反: 动作规模大时补丁还没贴完 ⇒ 假失败; 补丁贴在 POST 之前、失败要等回执才回滚 ⇒ 假阳性。改成 `waitForFunction` **等条件成立**(成功等目标 class 出现, 失败等 pendingOps 归零再断言"不留假状态")。
- **桩是瞬时的 ⇒ 顺序型 / 延迟型缺陷本地永远测不出来**: "某段代码必须在某次 IO 之前/之后发生"的约束, 断言必须**人为造慢**才有意义(`page.route` 注入 800ms, 再断言点击 → `.is-pending` < 400ms)。两坑: Playwright 新版路由谓词收到的是 **URL 对象**(先 `String(u)`); 点击时刻取**菜单项的 click 事件**(捕获阶段)—— `h.click()` 含鼠标开销, 实测虚高 ~250ms。
- **只读调用点就断言"机制不生效" ⇒ 先看 computed 依赖链**: 组行状态色取自 `decoratedGroups.status.primary`(是 `_aggStatus` 的 computed), 上游成员的 `kind` 一变它就会变 —— "机制没工作"与"没绑 class"在源码里长得一样。先问: ①值是不是 computed 派生 ②模板有没有绑这个 class ③真跑一次看 DOM(hang 桩 + 150ms 即可)。
- **"实测 + 缓存"读不到时不要缓存兜底值**: 量不到就返回 `null` 并**不缓存**, 由调用方本轮退回全量渲染。曾把种子页间距永久缓存成兜底 0px(占位按 0 算 ⇒ 总高少算 ~14855px)。泛化: 任何"读一次就缓存"的实测值, 都要先分清"值真的是这个"与"现在读不到"。

### 浏览器冒烟(Windows 上可做, 长期能力)

- 能力: `scripts/ui_harness.py`(真 `create_app` + 真 `QbManager` + `FakeClient` + 合成种子 + 命令泵)+ `scripts/ui_smoke.cjs`(Playwright, 两套 UI 各若干项断言 + 内置 A/B)。前端渲染逻辑**无法靠 pytest 覆盖**, 改前端必做冒烟。
- **Playwright 与浏览器**: 缓存里的 chromium 版本常与 playwright 期望的不一致 ⇒ 用 `chromium.launch({ channel: "msedge" })`(系统 Edge 永远可用), 或 `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm i playwright-core@<对齐版本>`。**ESM 的 `import` 不认 `NODE_PATH`** ⇒ 冒烟脚本必须写成 **CJS**(`require`)。
- **页面 hidden 态(VS Code 内置页 / 未 bringToFront)**: `document.hidden === true` 时 **rAF 完全不触发** ⇒ ①`new Promise(r => requestAnimationFrame(...))` 永不 resolve(工具报 deferred); ②Playwright `click()` 因拿不到两帧稳定盒模型全部超时; ③Vue `<Transition>` 停在 `enter-from`(元素在 DOM 里但 opacity:0)。对策: 先 `page.bringToFront()`, 等待用 Playwright 侧 `waitForTimeout`, 交互一律 `dispatchEvent`; 截图前注入中和过渡类。读数也可能停在旧布局。
- **企业策略强装扩展(Dark Reader)会污染 headless**: 即使 `--disable-extensions` + 全新 profile 照样注入并改写 CSSOM ⇒ **颜色断言必须读 `:root` 的自定义属性**而非元素 computed 背景; 控制台错误过滤 `chrome-extension` 来源。CDP 取自定义属性返回**原始书写值(hex)**不是 rgb(), 对比度计算要先解析 hex。
- **`CSSStyleRule.cssRules` 在 Chromium 恒存在**(空 CSSRuleList, 真值)⇒ 递归遍历样式表必须按 `rule.type` 判定(MEDIA=4 / SUPPORTS=12)。
- 其它环境坑: `--window-size` 在 Windows 被最小窗口宽度**钳制**(要验真窄屏就外层包 iframe); `file://...#anchor` 截中间区块得到空白图(注入 `display:none` 把目标顶到首屏); 整页截图 + PIL 自动裁剪在有平铺底纹 / 渐变的页面上失效; `--dump-dom` 里顶层 DOM 是整整一行(按行 grep 全落空); `--headless=new` 在本环境曾挂起(回落 legacy); **注入路由必须插到 `app.router.routes` 最前**(否则被 `StaticFiles` 挂载遮蔽返回 404); 注入脚本必须放 `<head>`(在 app.js 读 localStorage 之前)。
- **Edge 同 user-data-dir 会单例移交**(新进程立即退出, `/json/list` 拿到旧实例的旧页面)⇒ 每轮独立 profile; **残留页面的轮询会在新服务起来后自动重连并继续执行"幽灵操作"**(实测把新环境里同名组删了)⇒ 起服务前按命令行过滤清 smoke edge(`CommandLine -match "edge-smoke"`, **不能全杀 msedge**), 并确认端口无监听(kill 后端口释放有延迟, 立即重启必 10048)。收尾用 **PowerShell** 关端口(`Get-NetTCPConnection -LocalPort N -State Listen` → `Stop-Process`): `uv run python` 是父子进程, 按 netstat 的 PID 杀经常杀不掉父进程 ⇒ 新桩服务 bind 失败而旧服务继续应答 ⇒ **你以为换了参数, 实际还在用旧服务**。
- **Vue 3.5.13 取根实例**: `#app.__vue_app__._instance` 恒为 `null` ⇒ 用 `document.querySelector('#app')._vnode.component.proxy`。无头页里 Vue 实例不在 window 上(模块作用域), 只能操作 DOM。
- 页面每 2s 整表重渲染会让 Playwright 动作失败("another element intercepts pointer events")⇒ `force: true` 或断言优先取值; `programmatic btn.click()` **不触发 form submit**(要 `dispatchEvent(new Event("submit"))`); 断言即时色值可能取到 transition 中间值 ⇒ 用语义断言。
- **整页白屏 = 包级失败**(`#app` 带 `v-cloak`, Vue 不 mount 就永远隐藏, 只剩背景): 定位无需 node —— 起静态服务 + 在 `page.addInitScript` 里挂 `window.addEventListener('error', ...)` 拿 `filename:lineno`。**骨架在但某块区域空 = 模板表达式错误**, 只能真机看页面。静态扫描守阵 `test_frontend_static_bundle_health`(冲突标记 / JS 注释孤儿续行 / 模板引用的静态资源)。

### 桩与仿真保真度

- **测试替身的"成功路径"往往顺手把状态补全**: `FakeClient.torrents_add` 无条件登记种子 ⇒ 想测"add 成功但确认不到", 不能靠"不预置", 必须在**替身动作之后**动手脚(子类化 + `super()` 后 `pop`)。
- **桩对象与真对象"长得像"不等于"够用"**: `FakeTorrent` 缺 `to_dict()` ⇒ 详情端点恒 500, **依赖详情的整条链路(详情抽屉 / 限速 / 分享率 / 移动 / 重命名 / 复制磁力)从未被冒烟覆盖**, 且前端 catch 后只弹 toast, 断言看不到 ⇒ 加一条"无 console.error"断言, 并至少 GET 一次该链路。
- **`FakeQbServer` 的出口必须可 JSON 序列化**: 返回 `SimpleNamespace` ⇒ handler 内 `json.dumps` TypeError ⇒ 连接被**无响应关闭** ⇒ 客户端报 `APIConnectionError` 被主循环当断连静默吞掉(表现为"辅种分组永远为空")。新增替身端点照此处理。另: 桩服务的命令队列是 **2 元组** `(cmd, body)`, `cmd_id` 在 body 里。
- **桩服务"真的改状态"后必须自愈**(长驻服务跨轮累积会让第二轮所有行都是 paused), 且**回弹必须是"真值被 `/api/state` 取走之后"再等 N ms, 不能是盲定时**(定时回弹会跑到前端观测之前把真值改回去)。判"已被取走"用 `_web_pending_ver` 被清空; 回弹记**最初**值(不是上次命令后的值)。
- **仿真端"自以为在测"的测假陷阱**(写 `scripts/sim_qb.py` / `sim_run.py` 时实测, 通用): ①状态名必须合法(见上); ②辅种组内成员必须共享**完全相同**的文件相对路径(只共享 save_path 不够 ⇒ 根本没归成组); ③未配置站点的种子**不归组** ⇒ 破坏性场景的"组内成员"必须以 **auto-qb 实际归组结果**为准; ④**首轮与稳态的 tick 间隔必须分开统计**(混算每次假红, 反而掩盖真正的稳态劣化)。
- **判据要能区分"没碰"和"没测到"**: 加一条 `*_seeded`(`>= 1`)确认样本真的存在, 否则主判据在样本为空时静默通过。固化阈值时场景候选集要**分级**(稳态池只喂漂移阈值; 灌入期 / 带 WEB 负载记 BASELINE 不判红), 且阈值**不要硬编码在调用处**(否则固化值永远用不上)。
- **Windows 上硬 kill 拿不到 `state.json`**: `terminate()` = TerminateProcess, `finally` 不跑; `CTRL_BREAK_EVENT` 也只得到 0xC000013A ⇒ 用 `scripts/sim_autoqb.py` 启动包装(子进程装 `SIGBREAK → KeyboardInterrupt`), 并加 `graceful_exit` 硬判据。
- **反向对照必做**: 撤掉守卫 / 还原旧实现跑一次, 确认它**会报** —— 否则可能只是装了个永远不触发的空壳(如把 `torrents_removed` 抹回 `[]`, `snapshot_drop` 由 20 掉到 0 才能证明该判据有效)。
- **已知未修缺陷(供后续任务)**: qB 短暂断连后 auto-qb **无法自愈** —— 重连只在 `except APIConnectionError` 分支里做, 而该分支第一步 `self.client = None`; client 为 None 后 `sync_maindata()` 抛的是 **AttributeError** ⇒ 落进 `except Exception`(只打日志不重连)⇒ 死循环。**通用教训: 凡是"异常处理器里改了状态、而这个状态又决定下次抛什么异常"的结构, 都要警惕异常类型漂移导致分支永久失效** —— 单测要断言"断连 N 秒后能自愈", 而不是只断言"断连期间不崩"。
- **仿真配置格式**: 规则块必须落在 `config:` 之内且键名以 `_rules` 结尾(顶层 `xxx_rules:` 是旧格式, 照抄会报"根节点: 未知键"); 规则内没有 `log_level` 键。配置校验是 fail-fast 且聚合报错的, 一次列全。
- **顺带实测到的真实开销**: `qbittorrent-api` 每次写请求前都要再查一次 `app/webapiVersion`(库内无缓存)⇒ **写请求量翻倍**; 叠加"逐种子打标签" ⇒ 批量提交可降一到两个数量级。
- **全量 pytest 报 `PermissionError: ... pytest-current` 是临时目录被污染, 不是测试红**(2026-09-21 实测): 删除拦截层让 pytest 的
  `garbage-*` 目录**删不掉、越堆越多**(实测 283 个), 下次运行时 `cleanup_numbered_dir → cleanup_dead_symlinks` 去 `resolve()`
  那个已成死链的 `pytest-of-<user>/pytest-current` ⇒ `PermissionError [WinError 5]`, **连汇总行都不打印**(极易误判成"测试全崩")。
  **不要去删那些目录**(同样会被拦), 给 pytest 指一个全新临时根即可:
  `mkdir -p H:/Temp/pfresh && TMP=H:/Temp/pfresh TEMP=H:/Temp/pfresh uv run pytest tests -q`。
- **`test_run_loop_throttles_without_stop_event` 偶发翻红**(同一份代码全量跑两次: 一次 `1097 passed + 1 failed`, 一次 `1098 passed`):
  它是**墙钟时序**断言(主循环节流间隔), 在覆盖率开启 + 全量负载下偶发超时; 单跑 `tests/test_qbmanager.py` **43 passed** 恒绿。
  ⇒ 全量跑出 1 条红时**先换全新临时根重跑一次再判回归**, 别急着改代码 —— 真回归会**稳定**复现。

### 真机语料抓取 / 脱敏 (2026-09-21, `scripts/qb_capture.py` 实施时实测)

- **工具 shell 里 `HTTP_PROXY` 会让 `requests` 连不上本机 qB, 且报的是 404 不是连接错**: 本会话环境设了
  `HTTP_PROXY/HTTPS_PROXY=http://127.0.0.1:6943` ⇒ `requests` 默认把 `http://127.0.0.1:16585` 也送进代理,
  代理对 localhost 返回 **404 Not Found**(连 `app/version` 都是 404, 极易误判成"路径写错 / qB 没起")。
  `curl` 不受影响(它自带 localhost 例外), 所以"curl 通、python 不通"是这个坑的典型症状。
  **判别法**: `curl` 通而 `requests` 404 ⇒ 先查 `os.environ` 里的 `*_proxy`。
  **处置**: `Session.trust_env = False`(本机 qB 不需要代理)或把 `127.0.0.1,localhost` 加进 `NO_PROXY`。
- **`sync/maindata` 的 rid 序列是"每 session 一份", 不是全局**: 真机 3 轮验证 —— 另一 session 打 `rid=0`
  **不会**把正在增量消费的 session 打回全量(它的 rid 继续单调、响应仍无 `full_update`)。**同一个 session 内**
  用一个"过时的 rid"才会退化成全量。⇒ 录制 + 周期全量校验可以用两个独立 session 并存, 不必担心互相干扰。
- **`last_activity` 是 1 秒分辨率的时钟, 会让"逐字段全等"的闭合判据永远假红**: 真机 87 个种子里有 **48 个**
  会在任意 1 秒边界上 `+1`, 而"最后一条增量 → 抓全量"的窗口必然跨过某个秒边界。
  ⇒ 闭合 / 对齐判据必须把**结构字段**(state / name / save_path / category / tags / size / added_on …)
  与**采样量**(速度 / 计数 / 时间戳 / 会话累计)分开: 前者判 PASS/FAIL, 后者只统计上报。
  写成"全字段严格相等"的判据不是更严格, 而是**丧失信号**(恒红 ⇒ 没人看)。
  同理: 抓全量前必须先补一次增量把流"追平到现在", 否则窗口是 `interval_ms` 而不是毫秒。
- **形态守恒伪名化在短串上必然撞车, 而"撞了就中止"会让抓取在真机上跑不起来**: 真实标签集里
  `zE7` / `zE8` 同形, 纯按字符类别替换会双双落到同一伪名。计划的硬约束是"碰撞即中止, 不许加序号后缀"
  —— 但中止 = 真机抓取永远失败, 加后缀 = 破坏等长性。**第三条路: 递增 nonce 重派生**(同一 HMAC 换条流),
  长度 / 字符类别 / 确定性 / 单射四条全部保持。⇒ 撞车不再是致命错误, 只记进 `meta.collisions` 可观测。
- **"比 key" 的等价类判据是空壳, 必须比成员集合**: 归组 key 会被脱敏整体改写(盘符 → `<FSROOT>/dN/`),
  所以"脱敏前 key 集合 == 脱敏后 key 集合"**永远不等**; 反过来若只比"分组个数"又会放过并组/拆组。
  正确比法是 `{成员: 同组全体}` 的**分区结构**。
- **红验要挑对"能被看见的样本"**: "改掉一个成员路径的一个字符 ⇒ 判据必须红"——若改的是**单成员组**,
  分区结构不变 ⇒ 判据照样绿, 于是红验自己成了假证据。必须改**多成员组**里的成员。
  (这两条是同一个教训: **判据第一次写出来是空壳, 是红验把它抓出来的** —— 见"反向对照必做"。)
- **`--probe-fs` 这类 `on/off` 字符串参数不能直接 `if args.x`**: `"off"` 是**真值** ⇒ 默认档会静默打开磁盘探测。
- **脱敏要连"藏在 .gz 里的第二层 key"一起做**: `disk.json` 的外层 hash 换了、**内层相对路径还是真实文件名**
  ⇒ 真机资源名原样漏进语料, 而"凭据串扫描"与"hash 一致性自检"**都发现不了**(一个扫明文、一个只看 hash)。
  判别法: 凡是"以文件名/路径为 key"的旁产物, 都要单独问一句"它的 key 过映射了吗"。
  ⇒ 并加一条结构性自检: **旁产物里的每个 rel 都必须能在主产物里找到同名条目**(语料 W3 已加)。
- **窗口合并必须按序推进, 不能做集合净额**: 先增后删与先删后加结果完全不同。
  `torrents` 要"逐 hash 后写覆盖 + 删除即刻生效"; `torrents_removed` 只在"删了且末态确实不在"时报
  (先删后加不得报, 否则客户端会误删); `tags`/`categories` 同理按**最后一次事件**为准。
  写成 `adds - removes` 那种集合运算, 会把"窗口内加了又删"的标签既不算 add 也不算 removed ⇒ 该删的没删掉。
- **`getattr(args, "x", 默认值)` 的默认值只在属性缺失时生效**: argparse 给了 `default=""` 时属性**存在且为空串**,
  `getattr` 直接返回 `""`, 那个"默认值"永远不会用上。⇒ 用 `args.x or 默认值` 显式兜底。
- **❗回放 config 的 tracker 段"只信权威映射"会让头号判据 `CORPUS.group_exact` 假绿**(2026-09-21 实测):
  根因是 `qbmanager.py:685-690` —— **未匹配 tracker 配置的种子会 `continue` 跳过, 连带不参与归组**。
  而"权威映射"是按用户 config 的 `domains:` 字面量算伪域名, 但 auto-qb 的站点匹配是**后缀**匹配、
  两者不总相等 ⇒ 该映射漏掉了语料里**最大的站点**(35 个种子) ⇒ 真值 63 组只分出 29 组(group_exact 0 → 34)。
  ⇒ 判据变成 **"权威优先 + 统计兜底 + 只输出语料里真出现过的域名"**, 两者都不单独可信。
- **❗"集合里存的是脱敏后的值" ⇒ 拿原始字面量去 `in` 判断永远为假**: 想判断"真机上有没有 `MISSING` 这个标签",
  不能拿 `"MISSING" in 标签集合` —— 集合里的都是伪名。必须用**反查表**(伪名 → 原文)还原后再比。
  同类坑在"要拿原始值做判断的任何一处"都会出现(标签 / 域名 / hash / 路径)。
- **❗Markdown 表格会被"自动格式化器"改坏**(2026-09-21 实测 `docs/sim-client-test-howto.md`):
  有个格式化器在提交后又跑了, 把表格做了列对齐 + 加硬换行(尾随双空格), 顺带**改坏两处**:
  ①单元格里的 `<br>` 被换成真换行 ⇒ **表格行被劈成两行**(markdown 表格不允许单元格内换行);
  ②`` `recorded`\|`p50` `` 这类**转义竖线被还原成 `|`** ⇒ 平白多出几列。
  ⇒ 判别法: 改文档后若 `git diff` 比预期**大一个量级**(这次 32860 vs 25027 字节, 但 `git diff -w` 只剩 19/9),
  先怀疑格式化器; **用 `git diff -w` 分辨"有没有真的动到文字"**, 再决定是留还是还原。
  表格里要换行只能用 `<br>`, 要写竖线必须 `\|`。
- **Bash heredoc 往 Python 里写"反斜杠转义"会被路径归一化层改成正斜杠**(本工具环境实测):
  写 `\n` 进文件, 落盘可能变成 `/n` 或 `//n`, 生成物里就出现字面量 `\n`。
  **规避: 多行内容用三引号 + 真实换行**(`f"""..."""`), 完全不用转义序列; 或用编辑工具逐行改, 别走 heredoc。

## ⚠️ Git / 提交推送纪律

- **❗「非快进合并 + 工作区脏」会删掉整个 `.git` 对象库**(重大事故): git 2.55 在**非快进合并**时**无条件**调 `git stash create`, 工作区脏就要真写 stash 对象, 而工具环境的删除拦截层会顺着这次写入把 `.git/objects/**` **批量删进回收站**(git 原生 unlink 绝不会走回收站)。实测矩阵: 非快进 + 干净 = 安全; 非快进 + 脏 = **必炸**(关沙箱 / 换 git / `merge.autoStash=false` 都无效); 快进 + 脏 = 安全。
  - **唯一可靠规避: 合并前先把工作区弄干净**(先提交, 或把改动移出仓库); 高风险 git 操作前 `cp -a .git <备份>`。**记不住细节就记这句: 非快进 + 脏 = 必炸。**
- **❗❗ `git rebase` 在本工具 shell 里同样会毁 `.git`, 而且「干净工作区」也照毁**(2026-09-21 实测, 连续两次):
  - **根因**: 本机 git config 里有 **`rebase.autosquash=true`** ⇒ 每次 rebase 都被当成**交互式** rebase 起
    sequencer, 而 `core.editor` 指向 `code --wait` ⇒ 第一次报 `error: could not mark as interactive:
    No such file or directory`, 事后 `.git/refs/heads/` 整个目录 + `.git/logs/` 被删、当前提交对象也没了;
    第二次加了 `GIT_SEQUENCE_EDITOR=:` + `GIT_EDITOR=:` + `-c rebase.autosquash=false` 仍以 **SIGTERM** 收场,
    `.git` 只剩 `COMMIT_EDITMSG` 与 `FETCH_HEAD`。
  - **判别法**: 只要 rebase 报 `could not mark as interactive`, **立刻停手, 别重试**。
  - **本 shell 的可用替代(线性历史, 不碰 merge / rebase 机制)**: ① 先 `cp -a .git <备份>`;
    ② `git reset --mixed <远端 tip>`(HEAD 落到远端、索引随远端, 工作区不动);
    ③ `git checkout -- <远端那次提交新增或改过、而本地工作区还是旧版的文件>` —— **不做这步会把别人的新增
    当成"删除"提交进去**; ④ 手工把双方对同一文件的编辑合并; ⑤ `git commit`(父即远端 tip)⇒ 可快进推送。
    ⚠ `reset --soft` **不能用**: 索引会保持"我的整棵树", 相对新 base 会把别人新增的文件算成删除。
  - **通用教训**: 与上一条是同一个模式 —— 本工具 shell 里**任何会走 git 内部临时目录 / stash 机制的
    历史整合操作(merge / rebase / stash)都可能被删除拦截层顺手清掉 `.git`**。
    `fetch` / `add` / `commit` / `reset` / `push` 实测安全; 涉及历史整合的优先让用户在自己终端做。
  - **事故恢复**: 恢复成本取决于有没有 `cp -a .git` 备份。本次两次都靠 rebase 前的备份 30 秒复原
    (`HEAD` 与全部 10 个文件对象逐一 `cat-file -s` 校验通过)。**所以"高风险 git 操作前先备份 .git"这条不是形式主义。**
  - 事故后补救: ①被删对象基本都在**回收站**(`$I` 偏移 16-24 是 FILETIME **UTC**, 偏移 28 起是 UTF-16LE 原始路径; 内容在同名 `$R`); ②**还原后必须先删掉被一起还原的陈旧 `*.lock`**(`index.lock`/`HEAD.lock`/`AUTO_MERGE.lock`/`packed-refs.lock`/`objects/maintenance.lock`), 否则任何 git 命令都报 `Unable to create '.git/index.lock'`; ③工作区文件成片消失但 HEAD 里还在 ⇒ `git checkout -- <file>`; ④收尾 `git fsck --no-progress` 确认 0 broken link。
- **提交后必查 ref 三处: `HEAD` == `refs/heads/<branch>` == packed-refs**(用 `my-commit-flow/scripts/verify_ref.py`)。只看 commit 输出会被骗。
  - **「分支 ref 被回退」判别法**: 提交后 `git status` 突然冒出成百上千 staged ⇒ **先别急着 stage/commit**, 用 `git write-tree` 对比 `git rev-parse <刚才的提交>^{tree}` —— 一致说明工作区 / 索引完好, 只是分支指针被回退了, **改动一个字都没丢**。处置: `git format-patch -1 <sha> --stdout > 备份.patch` + `git update-ref refs/heads/tmp-xxx <sha>` 建锚点防 GC, 再 `git reset --soft <sha>`。**不要**用 `git add -A` 去"解决"那批 staged。
  - **packed-refs 陈旧会导致核 ref 假红**: 被 pack 过的分支更新时只写 **loose ref**(优先级更高), packed-refs 保留旧值直到下次 pack。判别: 先看 `HEAD` 与 `refs/heads/<branch>` 是否一致 —— 一致即落稳。修法: 备份 `.git` 后 `git pack-refs --all`(不要靠 `update-ref`, 它只写 loose)。
- **工具 shell 里 `git rebase --continue` / `commit --amend` / `merge` 一律带 `GIT_EDITOR=true`**: 本机 `core.editor` 是 `code --wait`, 无可交互窗口 ⇒ 永久等待(实测挂 6 分钟)。
- **在工具 shell 里不要用 `git stash`**(同上事故同源)。要"改动前 vs 改动后"对照又不改工作区, 用 `git archive` + `PYTHONPATH`:
  ```bash
  git archive HEAD src | tar -x -C .workbuddy-ai/tmp/aqb_old
  PYTHONPATH=".../aqb_old/src" uv run python -c "import auto_qb.qbmanager as m; print(m.__file__)"   # 先确认加载的是旧代码
  ```
  **必须先验证 `PYTHONPATH` 真的覆盖了 editable install**, 否则是拿新代码比新代码。
- **`git status -sb` 的 ahead/behind 是上次 fetch 时的快照**, 不会自己刷新 ⇒ **push 前先 `git fetch`**(多 clone / 多 session 并行时几分钟内就可能落后)。**分支落后主线时先 fetch 再动手**, 否则会把别人已修好的问题重做一遍; 真有重叠: ①`stash push -u` 留档 ②rebase 到主线 ③只把**主线没有的增量**重做 ④被取代的计划文档**必须加存档声明**。协作主线是 Gitee 的 `develop`, **不要用 GitHub 镜像判断进度**。
- **同步上游(未提交改动 + 行尾导致快进合并被拒)的安全流程**: ①`git diff > 备份.patch` + 原文件另存 ②只对被改的跟踪文件 `git restore --source=HEAD -- <文件>` ③`git merge --ff-only origin/develop` ④`git apply --3way --ignore-whitespace 备份.patch` ⑤`.md` 的冲突基本是"两边各追加一段", **取并集**(`tasks/_index.md` 是生成物, 直接重跑 `scripts/gen_tasks_index.py`)⑥`git add` 标记已解决后 `git reset` 变回未暂存。卡点: `git diff --stat` 为空但 `git status` 仍显示 ` M` 且工作区文件比 blob 大 ⇒ **是行尾不是内容**, 把文件强制成纯 LF 即可(别急着 stash)。
- **Gitee 主线会间歇性 `Recv failure`**(同一 URL 上一个通一个不通 = 链路层, 不是远端名 / 凭据配错; 实测连测 5 次只成功 2 次, 失败与成功交替)。处置: 主线**可重试一次**(GitHub 镜像仍"尝试一次, 失败只报一次")。⚠ **命令报失败 ≠ 没推上** ⇒ **判定"推没推上"的唯一依据是 `git ls-remote <远端> <分支>`**(它自己也会瞬时失败, 重试 2~3 次再下结论); `git push --dry-run` **不能**用来判断(只做 ref 协商, 不发包, 永远"成功")。
- **提交信息里的反引号会被 bash 当命令替换**(双引号内也替换 ⇒ 那一段变成空, 同时报 `command not found`)⇒ 用**单引号**包整条 `-m` 或干脆不用反引号; 提交后 `git log -1 --format=%B` 复核。已推送的提交不要 amend + 强推。
- **`git commit -F - <<'MSG' … MSG && git push` 会让 push 静默不执行**(结束符没被识别, 命令体读到 EOF, push 被当成 heredoc 内容)⇒ commit 与 push 写**两条独立命令**, 结束符单独占一行; 提交后看 `git status -sb` 的 `[ahead N]`。
- **rebase 冲突落在"已被你迁走"的方法上: 取上游的**意图**, 不是它的**位置** —— 先 `git diff <我方基线> <上游> -- <冲突文件>` 看上游到底加了几行(冲突块 100 行可能只有 5 行是真改动, 其余是"你迁走后上游又把原方法带回来")。上游的改动不能丢(丢了等于静默回退)。`git add` 之后、`rebase --continue` **之前**先跑一次全量测试。另: rebase 下 `-X theirs` = 正在重放的"我的提交"(与 merge 相反)。
- **合并冲突处理不要把 UTF-8 当 GBK 写入**(文档乱码且**不可逆**, 曾藏 3 天; 特征是私用区字符与 U+FFFD)。检测: 统计 GBK 误解码高频字密度。**恢复从 git 取原文**(逐父 `git show <parent>:<file>` 比对取唯一来源那一侧), 不要反解; 写回保持 CRLF 否则整文件 diff 炸开; 顺手做一次全文件链接存在性扫描。**验证编码一律用 Python 显式 UTF-8 读**(`open(p,"rb").read().decode("utf-8")` 不抛错且 `"\ufffd" not in text`)—— Git Bash 的 `sed/cut` 管道对**完好的** UTF-8 也会打印乱码, 不能据此下结论。
- **用 Python 文本模式改文件会把整份 CRLF 悄悄改成 LF**(2026-09-20 实测): 本仓库行尾**不统一**(index.html 等是 CRLF, style.css / views.css 是 LF), `io.open(p).read()` 走通用换行把 
 读成 
, 再 `write(newline="")` 落盘就只剩 LF —— `git diff` 仍只显示你改的那几行(索引存 LF, 归一化后看不出来), 但字节层面整份文件的行尾都被改了。修法: 改 html/css/md 一律**按字节读写**(`open(p,"rb")` + `bytes.replace`), 或写回时补 `.replace(b"
", b"
")`; 复核用 `b.count(b"
")` —— git bash 里 `grep -c $'
' file` 会给假结果(实测计数等于总行数), 别信。
- **`core.autocrlf=true` 下编辑会归一整文件行尾**(单文件 diff 从 23 行变 1431 行): 不是损坏, 但提交信息要写明"行尾归一"。
- **多行文本替换在"多处同型块"上会错位吞行**(工具仍返回成功, 产出 `</p>note warn">` 这类语法垃圾): oldString 扩到含前后**不重复**的上下文; 改完做**标签配对计数**; 已损坏就 `git checkout -- <file>` 回滚重做, 不要就地缝补。
- **双 UI 镜像首选"以一方模板为基线重建"再回填专有部分**(实测 86% 同构), 重建后做静态 class 覆盖检查。`keep/*` 孤儿标签是**留档**不是待合并分支; 判这类线要不要合: `git merge-base --is-ancestor <关键重构提交> <旧线>` —— 不含关键重构就应**重放**; 重放提交时必须**逐文件核验**, 判定"跳过"的要写明理由并登记缺口(整文件跳过会造成"CSS 已入库但模板没切"的两不管缺口)。
- **GitHub Actions: `astral-sh/setup-uv` 没有浮动大版本标签**(`@v10` 解析不了, 该 action 从 v8 起只发固定标签)⇒ 固定到 commit SHA 并加版本注释。给第三方 action 升大版本前先查 `refs/tags` 里目标 ref 真的存在 —— "上一个大版本有浮动标签"不代表下一个也有。
- **同一文件在一条消息里多次 Edit 会互相覆盖**(工具逐个报成功, 实际只有一部分落盘)⇒ 改同一文件时**逐条改、改完 grep 复核**。删 junction 用 Python `os.rmdir()`(别用 `cmd /c rmdir`, 本会话 Git Bash 里 `cmd //c` 会被路径转换坑掉且可能静默不执行)。
- **提交消息里的规模数字要在提交那一刻实测**(`git show HEAD^:<file> | wc -l`), 别沿用会话中途量的 —— 上游合入会让基线行数变掉。

## ⚠️ 知识库与协作纪律

- **把「问答」当「执行任务」是红线**(用户指定): 开工先判这一轮是**问答 / 只读**还是**执行任务**。用户只是问("能不能 X""是什么""怎么看""有没有")⇒ **只在回复里作答**; 想延伸排查(跑测试 / 冒烟 / 探针 / 实验)**先问**。❗**"继续 / continue / 接着做 / 你看着办"不构成授权** —— 只表示"把你手上这一步做完"。四类动作必须**逐项**显式确认: ①新建文件(计划文档 / 任务档案 / 报告)②入池 issue ③认领 issue ④commit / push。
- **纪律"反复强调但从不执行"时按顺序查四条**(缺任一都会衰减): ①**载体**(skill / instruction 文件真的在吗)②**规则暴露点是否落在决策点**(写在只对 `memory-bank/**` 生效的 instruction 里, 而"该不该立档"的决策发生在编辑 `src/` 的时刻 ⇒ 规则不在上下文里)③**阈值是否可判定**("大任务要立档"无阈值 ⇒ 默认不立档)④**有没有机械后果**(现由 `tests/test_memory_bank.py` 双向校验索引 ↔ 文件 / 命名 / 状态分区 / 必备章节)。
- **任务档案的 `**Status:**` 只能取 4 个英文单词**(`In Progress` / `Pending` / `Completed` / `Abandoned`); 写成 `✅ 完成` 会让两条守阵同时红(容易误判成"索引坏了")。正确写法 `Completed (…中文说明…)`, 改完**必须重跑** `python scripts/gen_tasks_index.py`。**立档前先按 slug 查重**(并行分支各自立档会造成重复档案 + 重复索引条目, 而 `_indexed_sections()` 是 dict, 同 ID 重复登记会静默覆盖)。
- **改文件名 / 移动文档后必须查全仓引用**(三步缺一不可): ①改之前全仓 grep 旧文件名统计引用数(含 `.html` / `.md` / `.py` / `.yml`, **HTML 的 `href=` 与正文里的裸路径也算**)②用 **Python 显式 UTF-8** 批量替换 ③替换后再 grep 确认为 0。**坏链不会让任何测试失败**, 只能靠人工扫。已知守卫缺口(建议未做): 加一个相对链接存在性扫描测试。
- **推送之后回扫一遍"未提交 / 尚未提交"**, 把自己这一轮的改成**「已入库 `<sha>`」**(带提交号可核验)。⚠ **只改自己这一轮的** —— 并发会话的条目同样会失效, 但按 scope-guard 不要顺手替别人改(rebase 必然撞车)。基线数字同理: 改了测试就两侧都重测再落。
- **埋点 / 验收口径必须有人消费**(见上"性能与刷新节奏"条目); 同理适用于计划里的每条验收标准。
- **skill 里的脚本路径要写 `<skill-dir>/scripts/...`**, 别写相对路径 —— AI 会在仓库根的 `scripts/` 里找。脚本内部找仓库根用 `find_root()` 向上找 `.git`, **不要按 skill 安装深度反推 `parents[n]`**。
- **项目级 skills 挂在 `<workspace>/.codebuddy/skills`**(内置 CLI 只扫这一处; 产品文档里的 `.workbuddy-ai/skills` **它根本不读**)。装载器**递归最深 5 层**收集每一个 `SKILL.md` ⇒ 把整棵技能树挂上去会注入数百条、严重挤占上下文。现状: `scripts/sync_agent_skills.py` 只挂顶层 skill(排除设计预设包), 幂等; **在源目录增删 skill 后必须重跑该脚本**, 否则新 skill 不出现。技能没出现先查两件事: 链接是否在 `.codebuddy/skills` 下、是否重启了会话(技能列表启动时加载一次)。
- **生成型脚本往 markdown / html 里写路径**: `Path.relative_to()` **不会生成 `..` 回跳**(非前缀直接抛 `ValueError`, 捕获后返回空串 ⇒ 链接静默消失)⇒ 用 `os.path.relpath()`; 进链接前必须 `.as_posix()`(Windows 的 `str(Path)` 带 `\`)。落盘前统一转换并在真仓库里 `head` 一眼, 别只看退出码 0。
- **预检 / 检查表型脚本的 STOP 级别要按阶段区分**: 一刀切 STOP 会挡住安全动作(如 commit 阶段"落后主线"只应 WARN, push 阶段才 STOP), 逼执行者 `--skip-preflight` 绕过 ⇒ 护栏形同虚设。判据: 每条检查都问一句"这条在当前阶段真的一票否决吗"。
- **解析固定列宽输出时不要对整段 `strip()`**: `git status --porcelain` 首行的**首列空格**被吃掉 ⇒ `' M x'` 变 `'M  x'` 被判成已暂存, 且 `line[3:]` 连带把路径首字符切掉 ⇒ **红线检查静默放行**。只用 `rstrip("\n")`, 解析处再兜底 `line[:2].ljust(2)`。

## 📝 文档与代码的一致性

- **🚧 标注的语义**: "未实现 **或** 已实现但未严格测试(实盘验证)"。规则系统一节的 🚧(trigger / execute_once / cooldown、size / trackers / state / hr / date_time / seedtime / upload_* / freespace 条件、checking / move_to / reannounce 动作、stop_following_rules_if)属于**后者** —— 代码已有单测但作者认定未经实盘验证, **必须保留, 勿因"已实现"而移除**(曾误删, 已按作者要求恢复)。
- **冲突裁决顺序**: 代码 > `memory-bank/` > 根 `README.md` > `想法.md`; 漂移以代码为准并回写。想法.md 是设计草稿, 不随实现同步。
- 已落地的历史记录(不必再查): 单实例锁与 fail-fast 全量配置校验(2026-09-05)、三个种子事件触发时机(2026-09-12)、HR 判定单点化与 tags/category/trackers 的 `:ignore_case`(2026-09-12)、集数标签模板(2026-09-05)。仍留的 TODO: `config/loaders.py` 的 `# TODO: optimize`; `CheckAction.execute` 闸门 0 上方"未完成且暂停的种子 recheck 后仍未完成会再次校验"(有 3 次 / 日冷却兜底, 未彻底处理)。

