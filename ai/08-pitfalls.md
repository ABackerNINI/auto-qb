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
- **Windows 长路径**: 磁盘文件检查过 `add_long_path_prefix_for_win` (`\\?\` 前缀), 新文件访问要走同一工具。
- **`yaml.BaseLoader`**: 配置全是字符串; 写解析时不要假设 YAML 已给原生类型; 空 `trackers:` 段会解析成 None/str, 已有 `isinstance` 防御, 新增类似段同样要防。

## ⚠️ 行为细节 (易误判为 bug)

- **奇数限速保护**: `(current_limit / 1024) % 2 == 1` → 跳过。这是特性不是 bug; 相关测试断言"奇数不覆盖"。
- **interval 归一化**: `Task.interval <= 0` → 1s (每 tick 级别); 规则 interval 为 0 表示每轮执行。
- **`handled` 返回值**: `Rule.process` 返回 `not result.is_skipped` — 最后一个动作 skip 时 handled=False, 但**执行历史已记录** (只要前面动作成功过)。设计如此, 勿"修复"。
- **上传增量下限 0**: `upload_delta = max(0, uploaded - baseline)` — 种子重加/客户端重启后 uploaded 归零不会产生负增量。
- **缺文件扫描/参考种子的代表种**: 只从 `is_complete 且非 checking/errored` 成员选 (`_valid_for_representative`: 暂停/停止做种的完成成员也算, 校验中完整性存疑才排除) — 不是漏检, 是有意保守。
- **tracker 匹配是"第一个命中"且已统一为 hostname 精确匹配**: `_match_tracker_conf` 复用 `utils.match_tracker_confs` (精确/子域名匹配, 与规则绑定同语义), 取第一个匹配配置, **命中多个配置时打 ERROR 日志**(仍用第一个, 不跳过种子); 导出模板 `find_missing_domains` 仍用包含关系匹配 (有意宽松, 用于找未配置域名)。
- **`RuleContext.torrent` 的 snapshot 回退是合法语义, 非死防御**: `ctx.torrent` 实时 `store.get(hash)` 优先, 种子已从客户端删除 (`on_torrent_deleted`, store 已移除) 时回退 `RuleContext.snapshot` 删除前快照副本。这是真实可选语义 (种子被删的合法现场), 与 死防御清理 (点5) 中"条件在正确上游流程下不可能发生 → 删"的判别不冲突。供 `print_torrent_details` 只读留档用; 需活种子的动作在 config 白名单阶段已被 `on_torrent_deleted` 拒绝。
- **每个动作的 dry-run 返回 success** — dry-run 日志里看到的都是"成功", 别据此判断真实执行结果。
- **`state_file` 仅退出时落盘**: 运行中 kill -9 会丢执行历史 → 去重可能重放, 已知取舍 (想法.md 明文)。

## 📝 文档与代码的一致性 (2026-09-05 已同步)

README.md 曾有的客观漂移已于 2026-09-05 修正: 任务队列描述 (双队列→单队列)、集数标签格式 (`E1-5`→`zE1-5`)、mixins 组合列表补 SpeedCurveMixin、目录树补 qbapi/curves/speed_curve、checking.py 职责描述。

**🚧 标注的语义 (作者澄清, 重要)**: 🚧 = "未实现 **或** 已实现但未严格测试(实盘验证)"。规则系统一节的 🚧 (trigger/execute_once/cooldown、size/trackers/state/hr/date_time/seedtime/upload_*/freespace 条件、checking/move_to/reannounce 动作、stop_following_rules_if) 属于后者 — 代码已有单测, 但作者认定未经严格验证, **必须保留, 勿因"已实现"而移除** (2026-09-05 曾误删, 已按作者要求恢复)。

其余 🚧 属未实现: `on_torrent_added` / `on_torrent_deleted` / `on_torrent_state_enum_changed` 三个事件触发时机 (README 功能矩阵同样标 🚧 规划中)。**2026-09-12 全部落地** (trigger 解析/白名单/`print_torrent_details` 动作/事件分派引擎/测试), 已从 🚧 转正式特性。单实例锁 (`locking.py`) 与 fail-fast 全量配置校验 (`config.validate_config` 聚合校验, 见 05-config-reference) 均已于 2026-09-05 实现, README 中列为正式特性 (无 🚧 标注)。

> 想法.md 是设计草稿, 不随实现同步; 改 README 时以代码为准, 但 🚧 标注的取舍听作者。

## ⚠️ 代码内 TODO (改动相关区域时顺带了解)

- ~~`qbmanager.py` `_get_torrent` 兼容方法标记"TODO: 删除"~~ — 已删除, 代码统一用 `self.store.get(hash)`。
- HR 判定单点化(原 `rules/base.py` "移动到 actions.py" TODO): `check_hr_condition`/`check_hr_satisfied` 已迁到 `TorrentRecord` (torrents.py), hr 条件 (conditions.py) 已复用; 但 `mixins/tags.py` 的 `_add_hr_tag_or_category` 仍**内联重复** HR 条件/satisfied 判定 (dlratio/dlsize、做种时长/分享率) — 改 HR 判定语义仍要两处同步。
- `rules/conditions.py` tags/category/trackers 三个条件不支持 `:ignore_case` (代码内 `# TODO: 支持:ignore_case`, utils 已支持)。
- ~~`actions/checking.py` "recheck 后仍未完成防重复校验"~~ — 已处理 (2026-09-05): 连续失败 3 次当日冷却(`recheck_fails` state 键, 次日重置, 成功清零); 但 `CheckAction.execute` 闸门 0 上方仍留一条 TODO: "未完成且暂停的种子 recheck 后仍未完成, 下一轮会再次校验"(冷却兜底, 未彻底处理)。
- ~~`episodes.py` 集数标签格式不可自定义~~ — 已实现 (2026-09-05): `add_episode_tags` 段支持 `add_tag_single`/`add_tag_multi` 模板, `${episode_first}`/`${episode_last}` 占位; 仅集数连续时生成。
- `config/loaders.py` `load_global_hr`/`load_tracker_hr` 上方仍留 `# TODO: optimize`。

## ⚠️ 并发/状态机约束回顾 (违反即引入难以复现的 bug)

1. 主循环线程是唯一修改队列/state_file/store 分组索引的线程 — 不要在校验回调、信号处理器、新线程里改这些。
2. 校验登记与 recheck 的顺序 (`actions/full_checking.py`): **先 `add_task(轮询子任务)` 登记在途(已在途则 skip), 再发 `torrents_recheck`** — 发送失败返回 `fail`(不返回 pending, 规则任务不留断点); 成功才返回 pending(规则断点, origin 的恢复完全由轮询子任务负责, 队列对"暂停/恢复"无感知)。
3. 断点续跑语义 (taskqueue.py `add_task`): `keep_progress=True` 保留 `resume_index`(校验成功后续跑后续动作), 默认(重置)清空 `resume_index` 重走完整决策链 — 二者不可混用。
4. 种子删除**没有**队列级清理入口: 轮询/等待子任务靠 handler 首行 `store.get(hash) is None` 删除守卫判死(FINISHED 前 `add_task(origin)` 默认重置, origin 由 `_handle_rule`/`_handle_event_rule` 的删除守卫判死); store 侧清理走 `TorrentStore.remove_torrent`(快照/分组索引)。任何在途任务都必须自带删除守卫。**事件规则的 rule-event 任务**作 origin 被轮询子任务重新入队续跑后, 下 tick `_handle_event_rule` 首行同样用 `store.get(hash) is None` 判死 (删除时 FINISHED 消亡); 但 `print_torrent_details` 只读动作经 `ctx.torrent` 回退删除前快照副本 (`RuleContext.snapshot`) 仍可打印留档, 其余需活种子的动作则在 config 白名单阶段已被拒绝。
5. QbApi 写方法必须同步 store (`update_torrent_fields`/`invalidate_*`), 否则同 tick 读旧值 (test_snapshot_sync.py 防回归)。
