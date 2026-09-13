# 08 陷阱、风险点与文档漂移 (改代码前必读)

## 🔴 生产文件, 禁止改动/提交

- **`config.yml`**: 用户真实生产配置 — 含真实 PT 站点域名、tracker 规则、qB 凭据引用。不是示例! 改示例用 `minimal.yml`/`test_yamls/`。
- **`auto-qb-data/state.json`** (2026-09-09 改: 运行时文件集中到 auto-qb-data/ 数据目录): 运行中程序的状态文件, 程序退出时覆写。改它毫无意义且可能破坏运行。锁文件 `<state_file 去扩展名>.lock` (`auto-qb-data/state.lock`) 与伴生 `.meta.json` 也在同目录; 日志在 `auto-qb-data/logs/auto-qb.log`, 跳检备份在 `auto-qb-data/skip-check-backup/`, 均落在此数据目录下。
- 两者均已 gitignore, 但在工作区可见 — 不要"顺手"格式化/重排它们。

## ⚠️ 高风险业务操作 (代码中已有防护, 改动时不得削弱)

1. **跳检 (skip-checking)**: 删除种子→重加, 丢失统计 (下载量/上传量/做种时长/分享率); 内容错误会传垃圾数据 (PT 站严令禁止)。防护 (2026-09-05 审计加固后): ①部分下载 (0<progress<1) 拒绝跳检 (预分配零块会被标记有效上传, fail 提示改 full-checking) ②同规则同日去重 + **跨规则**同日去重 (`skip_check_day`, 统计只丢一次) ③强制 filelist 前置检查 ④重加前轮询确认种子已从客户端消失 (qB 删除异步, ≤5s; 未消失放弃, 种子还在无损失) ⑤重加属性**直传** (0/负值有语义, 不得 `or None` 吞掉) + contentLayout 由 content_path/save_path/文件列表推断 (布局错位不自愈) ⑥无参考 warning ⑦重加失败 .torrent 落盘备份且**元数据立即落盘**。跳检过程中种子会从 store 消失 (`remove_torrent`) — 该种子同 tick 内的后续动作必须容错 (历史 bug: commit e5ea9e7, 测试 test_checking.py 覆盖)。
2. **reannounce 动作**: 已加运行时保护 (2026-09-05): 同种子最小间隔 10M(state `reannounce_ts`) + 暂停种子跳过 + 加载期未配去重 WARNING —— 但高频汇报本质上仍是高风险操作, 规则应配 execute_once。
3. **qB 版本兼容**: `_refresh_torrents` 首次拉到种子信息时校验 `REQUIRED_TORRENT_FIELDS`(24 个 = 快照 18 + 跳检重加 6, 见 torrents.py `_SNAPSHOT_FIELDS`/`RE_ADD_FIELDS`), 缺失抛 `QbCompatError(AutoQbError)` → CLI 干净退出 —— 快照字段缺失会**静默零值**(规则基于假数据决策), 比崩溃更危险 (qB 5.0 preferences 键漂移前科)。
4. **`or 默认值` 掩盖数值字段** (2026-09-06 清理): `progress or 0.0`/`ratio or 0` 类写法把上游 bug 静默转为合法语义且方向可能朝危险侧 (progress=None → 视为全新辅种 → 放行跳检)。已清理: 闸门 0/_skip_gates/HR 判定 4 处。**保留的合法 `or`**: 空串/空容器归一化 (category/tags/API 边界) 与除零防护 (`total_size or 1`)。判别标准见 ai/06。
5. **死防御清理** (2026-09-06): 同型问题扩展至 `is None`/`getattr` 默认 —— 已删: client setter 的 store/api 守卫、`_execute_full_checking` 的 task_queue None 退化分支、`getattr(task, "resume_index", None)`/`getattr(prev, "is_uploading", False)` 冗余默认(含 2026-09-06 二次复查补删的 grouping 上传转暂停判定)、`_valid_for_representative` 中恒真的 MOVING 显式排除(MOVING 本就不在 is_complete/is_uploading 集合)、QbApi 的 `store=None` 可选形态与 15 处 `if self.store is not None` 守卫 (store 改必传, 见 06 可测试性原则)。**合法 None 保留**: 惰性缓存、运行时状态 (种子被删/外部入口)、功能开关。判别标准: 守卫的条件在正确上游流程下**不可能发生** → 删; 是真实可选语义 → 留。
6. **自有动作污染状态观测** (2026-09-06): 自家整组停种 (大小一致性/下载冲突) 经 QbApi 快照同步**当场改写 `by_hash` 的 state**, `_handle_state_transitions` 若在自有动作之后运行, 会把自家停种误判为外部"上传转暂停" → 多余的缺文件扫描 (曾靠代表种 is_uploading 过滤掩盖, 代表种放宽为 is_complete 后暴露)。修复: refresh 中状态转移观测移到新增归组等自有动作**之前** (轮次开始的干净观测点), 顺序约束见 ai/02。
7. **删除种子** (`QbApi.torrents_delete`, qbapi.py): 仅跳检流程使用, `delete_files=False` 固定。
8. **限速不覆盖手动值**: 奇数 KiB 视为用户手动设置则跳过 — 判定统一走 `utils.is_manual_speed_limit`, 三个调用点 (`mixins/tracker.py` 单种限速 / `rules/actions/transfer.py` 限速动作 / `mixins/speed_curve.py` 全局曲线) 逻辑必须保持一致。

## ⚠️ 平台/API 兼容陷阱

- **锁文件残留随平台不同** (2026-09-10): `locking.py` 的 `release()` 只无条件删除伴生 `meta.json`, 锁文件 `state.lock` 的删除交给 `filelock` 底层 — Windows(msvcrt) 释放时删, POSIX(flock) **不删**(flock 标准语义, 删锁文件反而不安全)。因此 Linux CI 上 `release()` 后锁文件残留是正常行为, 测试按 `os.name == "nt"` 分平台断言, 不是代码 bug。
- **qB 5.0+ 全局限速**: 必须走 `transfer_upload_limit`/`transfer_set_upload_limit` 端点 (bytes/s, 0=不限)。旧 `app.preferences` 的 `upload_limit/download_limit` 键**已静默失效** (历史 bug, commit f402eaf)。qbittorrent-api 新版 `app.preferences` 是 property 不是方法 (commit be0911b)。
- **qB 状态枚举**: 用 `qbittorrentapi.TorrentState` 枚举属性 (`is_stopped` 等) 判定, 不要比较 state 字符串 (pausedUP vs stoppedUP 跨版本差异)。
- **`/api/v2/sync/maindata` 是增量接口, 响应不是全量** (2026-09-13): rid 与上次一致时只回**变化种子的变化字段**(qB 端 `processMap` 逐字段 diff), **未变化种子完全不出现在响应中**; 删除的种子列在 `torrents_removed`(哈希列表); 新增种子(基线缺失)回全量字段; rid 不匹配/为 0 时 `full_update=true`(自愈信号, 漏 tick/qB 重启都只退化成一次全量)。**因此绝不能把单次响应当成种子全集** —— 必须像 `TorrentSync` 一样维护本地 baseline 逐字段合并。
- **sync 与 `torrents/info` 字段齐平**(同一 C++ 序列化器 `serialize/serialize_torrent.{h,cpp}`, sync 仅额外移除 `"id"` 键): 所以 `REQUIRED_TORRENT_FIELDS` 可直接用于 sync 响应; 但**只能在全量轮校验** —— 增量响应只含变化字段, 做字段存在性校验必误报缺失(已由 `TorrentSync.need_validate` 闸门隔离)。
- **sync 端点不可降级为“少几个字段”**: 旧版 qB 无该端点时抛 `NotFound404Error`(qbittorrent-api 对未知 API 方法), 测试替身缺方法时抛 `AttributeError` —— `TorrentSync.fetch` 只捕获这两类并降级 `torrents_info()`(一次性 WARNING), **其它异常(网络等)rid 归零后原样上抛**, 否则会掩盖断连/鉴权失败。
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
- **分组视图"惰性组装"的脏标记必须精确, 否则惰性名存实亡** (2026-09-13): `_refresh_torrents` 曾**无条件** `_group_view_dirty = True`, 导致只要网页开着就每 2s 全量重建 group view + 全量 JSON 序列化 + 前端整表重渲染(种子库静止时也一样)。现改为 `store.view_changed` 仅在 `_VIEW_FIELDS`(name/save_path/state/dlspeed/upspeed/uploaded/size/progress/seeding_time/ratio)或组成员变化时置真, 由 `_tick` 消费判定。
- **`seeding_time` 必须按分钟量化, 否则惰性重建对做种库形同虚设** (2026-09-13): 该字段每秒递增, 而 PT 库里绝大多数种子都在做种 → 不量化时几乎每轮都置脏。现由 `torrents._VIEW_QUANTUM = {"seeding_time": 60}` + `view_field_value()` 统一向下取整(**重建判定与 `_build_group_view` 展示值共用**, 不能只改一处 —— 只改判定不改展示会让 UI 显示的秒数停留在上次重建时刻; 只改展示不改判定则永远重建)。前端 `fmtDuration` 同步去掉 <1h 的秒位。剩余每轮置脏的情形是**真在上传**的种子(uploaded/upspeed 增长), 这是真实数据变化, 属于预期行为。
- **WEB `/api/state?rid=` 的版本门控** (2026-09-13): `_group_view_ver` 每次重建自增, `ensure_group_state(rid)` 在 rid 一致时**不回传 groups**(只回 status)。前端靠 `updated` 字段决定是否整表替换 —— 若以后把其他会变的数据也塞进 groups 之外的字段, 要记得它们不受版本门控(status 是故意恒回传的 4 个标量)。前端适配: 换密钥/重新鉴权时须把 `lastRid` 置 null, 否则可能因版本碰巧一致而拿不到 groups 导致列表残留。
- **每个动作的 dry-run 返回 success** — dry-run 日志里看到的都是"成功", 别据此判断真实执行结果。
- **配置热重载分级的两处"看着像 bug"的现状** (2026-09-13, 补 `test_impact.py` 时发现, 未改动):
  1. `impact.py` 注释说 L0 段"字段级 diff, 仅变更字段计入", 但 `_diff_flat` 的分支条件是**两侧值都是纯 dict** —— 真实 `Config` 的 L0 段(`grouping`/`add_episode_tags`)是 dataclass 实例, 故实际产出**整段单条 L0** 变更(path 只到段名)。级别判定仍正确(热重载行为没问题), 差异仅在变更条目粒度与"变更 N 项"日志计数。已有测试固化该现状。
  2. `max_level` / `restart_required_paths` 是模块公共工具但**当前无生产调用**(`web.py` 与 `qbmanager.py` 各自内联 `[c.path for c in changes if c.level == "R"]`)。属清理候选, 未擅自删除(测试已覆盖其契约)。
- **`state_file` 仅退出时落盘**: 运行中 kill -9 会丢执行历史 → 去重可能重放, 已知取舍 (想法.md 明文)。
- **qB 断连期间错误日志静默**: tick 内 `APIConnectionError` 经 `_last_conn_ok` 状态机节流 (2026-09-12) — 仅"连接态→断开"转换时记一次 ERROR, 恢复时记一次 INFO("已重新连接 qBittorrent", `connect()` 内), 断开期间每 tick 重试失败不打日志。是有意节流 (防 qB 宕机刷屏), 不是丢日志; 非 `APIConnectionError` 异常照常记 "主循环异常"(exc_info=True)。

## 📝 文档与代码的一致性 (2026-09-05 已同步)

README.md 曾有的客观漂移已于 2026-09-05 修正: 任务队列描述 (双队列→单队列)、集数标签格式 (`E1-5`→`zE1-5`)、mixins 组合列表补 SpeedCurveMixin、目录树补 qbapi/curves/speed_curve、checking.py 职责描述。

**🚧 标注的语义 (作者澄清, 重要)**: 🚧 = "未实现 **或** 已实现但未严格测试(实盘验证)"。规则系统一节的 🚧 (trigger/execute_once/cooldown、size/trackers/state/hr/date_time/seedtime/upload_*/freespace 条件、checking/move_to/reannounce 动作、stop_following_rules_if) 属于后者 — 代码已有单测, 但作者认定未经严格验证, **必须保留, 勿因"已实现"而移除** (2026-09-05 曾误删, 已按作者要求恢复)。

其余 🚧 属未实现: `on_torrent_added` / `on_torrent_deleted` / `on_torrent_state_enum_changed` 三个事件触发时机 (README 功能矩阵同样标 🚧 规划中)。**2026-09-12 全部落地** (trigger 解析/白名单/`print_torrent_details` 动作/事件分派引擎/测试), 已从 🚧 转正式特性。单实例锁 (`locking.py`) 与 fail-fast 全量配置校验 (`config.validate_config` 聚合校验, 见 05-config-reference) 均已于 2026-09-05 实现, README 中列为正式特性 (无 🚧 标注)。

> 想法.md 是设计草稿, 不随实现同步; 改 README 时以代码为准, 但 🚧 标注的取舍听作者。

## ⚠️ 代码内 TODO (改动相关区域时顺带了解)

- ~~`qbmanager.py` `_get_torrent` 兼容方法标记"TODO: 删除"~~ — 已删除, 代码统一用 `self.store.get(hash)`。
- ~~HR 判定单点化(原 `rules/base.py` "移动到 actions.py" TODO)~~ — 已完成 (2026-09-12, commit d987015): `check_hr_condition`/`check_hr_satisfied` 单点判定在 `TorrentRecord` (torrents.py), hr 条件 (conditions.py) 与 `mixins/tags.py` 的 `_add_hr_tag_or_category` 均已委托复用 (移除 tracker_conf 参数), 改 HR 判定语义只动 torrents.py 一处。**2026-09-12 语义变更**: 触发条件增加"完全下载即触发"边界 (`is_fully_downloaded`: `progress>=1.0` 或 `amount_left==0` 且 `total_size>0`) — 小于触发量/比例的种子下载完成也视为触发(修复想法.md 已知问题), 生产 `torrents.py` 与测试 `helpers.py` 两处已同步实现(注意 FakeTorrent `amount_left` 默认按 `total_size-downloaded` 推导, 显式传值优先)。
- ~~`rules/conditions.py` tags/category/trackers 三个条件不支持 `:ignore_case`~~ — 已完成 (2026-09-12): 三条件统一改走 `utils.match_value`(语法解析唯一入口 `utils.MatchPattern`), `:ignore_case` 对精确与 regex: 均生效; 同时 config 阶段对这些条件与 remove_tags 动作补 `regex:` 可编译 fail-fast 校验, 运行时的静默跳过仅为兜底。
- ~~`actions/checking.py` "recheck 后仍未完成防重复校验"~~ — 已处理 (2026-09-05): 连续失败 3 次当日冷却(`recheck_fails` state 键, 次日重置, 成功清零); 但 `CheckAction.execute` 闸门 0 上方仍留一条 TODO: "未完成且暂停的种子 recheck 后仍未完成, 下一轮会再次校验"(冷却兜底, 未彻底处理)。
- ~~`episodes.py` 集数标签格式不可自定义~~ — 已实现 (2026-09-05): `add_episode_tags` 段支持 `add_tag_single`/`add_tag_multi` 模板, `${episode_first}`/`${episode_last}` 占位; 仅集数连续时生成。
- `config/loaders.py` `load_global_hr`/`load_tracker_hr` 上方仍留 `# TODO: optimize`。

## ⚠️ 并发/状态机约束回顾 (违反即引入难以复现的 bug)

1. 主循环线程是唯一修改队列/state_file/store 分组索引的线程 — 不要在校验回调、信号处理器、新线程里改这些。
2. 校验登记与 recheck 的顺序 (`actions/full_checking.py`): **先 `add_task(轮询子任务)` 登记在途(已在途则 skip), 再发 `torrents_recheck`** — 发送失败返回 `fail`(不返回 pending, 规则任务不留断点); 成功才返回 pending(规则断点, origin 的恢复完全由轮询子任务负责, 队列对"暂停/恢复"无感知)。
3. 断点续跑语义 (taskqueue.py `add_task`): `keep_progress=True` 保留 `resume_index`(校验成功后续跑后续动作), 默认(重置)清空 `resume_index` 重走完整决策链 — 二者不可混用。
4. 种子删除**没有**队列级清理入口: 轮询/等待子任务靠 handler 首行 `store.get(hash) is None` 删除守卫判死(FINISHED 前 `add_task(origin)` 默认重置, origin 由 `_handle_rule`/`_handle_event_rule` 的删除守卫判死); store 侧清理走 `TorrentStore.remove_torrent`(快照/分组索引)。任何在途任务都必须自带删除守卫。**事件规则的 rule-event 任务**作 origin 被轮询子任务重新入队续跑后, 下 tick `_handle_event_rule` 首行同样用 `store.get(hash) is None` 判死 (删除时 FINISHED 消亡); 但 `print_torrent_details` 只读动作经 `ctx.torrent` 回退删除前快照副本 (`RuleContext.snapshot`) 仍可打印留档, 其余需活种子的动作则在 config 白名单阶段已被拒绝。
5. QbApi 写方法必须同步 store (`update_torrent_fields`/`invalidate_*`), 否则同 tick 读旧值 (test_snapshot_sync.py 防回归)。
