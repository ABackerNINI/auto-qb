# 09 路线图与项目状态

> 来源: `想法.md` (设计草稿, 权威) + `README.md` 功能状态标注 + 源码 TODO + git log (截至 2026-09-09, commit 884702d)。回答"XX 做了吗/计划怎么做"以此为准。

## 已实现 (✅, 有单测覆盖)

> 注意区分: 下表部分功能作者在 README 中标注 🚧 = "已实现但未严格测试(实盘验证)", 如规则引擎的条件/动作/checking/去重语义等 — 有单测但作者尚不认为经过严格验证; 此类 🚧 ≠ 未实现, 勿移除 (语义详见 08-pitfalls)。

- 标签/分类管理: 站点标签加/删、相似标签清理、`delete_tags`/`delete_tags_if_has_no_torrents` 全局清理、集数标签
- HR 管理: 触发标签/分类 + satisfied 标签/分类, 站点覆盖全局
- 辅种分组: 增量归组、大小一致性、缺文件事件驱动扫描 (删除/上传转暂停/路径变化)、下载冲突检查
- 规则引擎: interval 触发 + 15 条件 + 11 动作 + execute_once/cooldown 去重 + 断点续跑 + stop_following_rules_if
- checking 动作: filelist/piecehashes/custom 三种参考判定 + full-checking (异步轮询) + skip-checking (导出→删除→重加, 同日去重+备份)
- tracker 单种限速 (奇数保护)
- 全局限速曲线: Traffic Monitor 数据源, DAY/MONTH/ND 聚合, 全程分档覆盖, 取最严 (2026-09 最近的大功能, commit ee88bc8..20481f3)
- 任务队列: 单 heapq 队列 + `add_task(keep_progress=...)` 断点语义 + check 轮询在途去重 (12f3b46 重构完成)
- 数据层: TorrentStore 快照+惰性缓存+分组索引; QbApi Facade写后同步
- YAML 导出 (`--export-yaml`, `--only-missing`), qB 5.0 API 适配
- fail-fast 全量配置校验 (2026-09-05): `config.validate_config` 聚合校验未知键/必填项/值格式/规则 spec/引用存在性; 留空(空串/None)走默认值; Rule 构造报错带规则名上下文; `load_*` 解析函数已剥离全部检查(先验证再解析, 解析假定配置正确)
- 单实例锁 (2026-09-05): 基于第三方 `filelock`, 锁文件 `<state_file 去扩展名>.lock` + 伴生 `.meta.json`; 仅正常 `run()` 模式持锁, `--export-yaml` 等只读模式通过 `no_lock=True` 跳过; 失败抛 `SingleInstanceLockError(AutoQbError)`, CLI 单点捕获 AutoQbError 体系干净退出 (退出码 1, stderr 无堆栈); 陈旧锁不接管 (OS 句柄随进程退出自动释放, 必要时手动删除)
- 测试: 621 passed, 分支覆盖 94% (2026-09-09)

## 规划中 (🚧, 尚未实现)

### 规则系统
- 触发时机: `on_torrent_state_changed` / `on_torrent_added` / `on_torrent_deleted` (想法.md; 架构上需要把"新种子检测"泛化为事件源, 任务队列已具备 pending 让出 + `add_task` 恢复基础)
- 条件取反 (`!` / 非 logic)、tags/category/trackers 条件的 `:ignore_case` 支持
- tracker 分组 (规则按组筛选)
- HR 判定单点化收尾: `check_hr_condition`/`check_hr_satisfied` 已在 `TorrentRecord` (torrents.py), hr 条件已复用; 但 `mixins/tags.py` `_add_hr_tag_or_category` 仍内联重复 HR 判定 (详见 08-pitfalls TODO 段)

### 其它功能
- 插件系统: 直接支持自定义 Python plugin
- 根据流量接入更多数据源 (traffic_source 当前仅 traffic_monitor 单源, 代码已按列表预留)
- 与 PTD-cli 合作: 自动分析 HR 标签 / 暂停低分享率非免费种子 (想法.md 标注"需可行性验证")

## 已知 BUG (来自 想法.md)

- ~~新加的种子无法触发 skip-checking~~ (2026-09-06 已修复): 生产日志实锤 —— 跳检删除→重加同 hash 种子后, `store.remove_torrent` 保留 `_known_hashes` 导致重加种子**不进 added 列表**, 下轮 refresh 重建记录 `tracker_conf=None` 永久未匹配; `log_repr → tracker_name` 回退 `self.tor.client`(真实 TorrentDictionary 无此属性) AttributeError。修复: ①跳检重加成功后恢复删除前快照记录(tracker_conf/惰性缓存保留) ②tracker_name 无 conf 返回 "Unknown"(与 FakeTorrent 对齐, 不再回退 tor.client)
- 复杂限速规则 (tracker+时段组合等)
- 性能: 主循环拆分平滑占用、全面优化 (想法.md 标注)

### 代码内待办 (TODO 清单, 2026-09-09 核对; 位置用函数/方法名锚定, 行号易漂移)
| 位置 | 内容 |
|------|------|
| ~~qbmanager.py `_get_torrent`~~ | 兼容方法已删除, 统一用 `store.get(hash)` |
| ~~rules/base.py 多 tracker 匹配~~ | 已处理 2026-09-05: `_match_tracker_conf` 命中多个打 ERROR 用第一个 |
| ~~rules/base.py HR 判定迁移~~ | 已迁移 2026-09-05: check_hr_* 移至 TorrentRecord, replace_vars 移至 utils |
| rules/conditions.py (tags/category/trackers 三处 `# TODO: 支持:ignore_case`) | 条件支持 `:ignore_case` |
| ~~recheck 失败冷却~~ | 已实现 2026-09-05: 连续失败3次当日冷却, recheck_fails |
| rules/actions/checking.py `CheckAction.execute` 闸门 0 上方 | 未完成且暂停的种子 recheck 后仍未完成, 下一轮会再次校验 (3 次失败冷却兜底, TODO 未销) |
| rules/actions/checking.py `_find_reference` 上方 | 优化为 `has_reference() -> bool` 提前返回 |
| rules/actions/checking.py 分段执行处 | 重新设计自定义 (custom) 校验流程 |
| mixins/tags.py `_add_hr_tag_or_category` | HR 条件/satisfied 判定内联重复, 未复用 `TorrentRecord.check_hr_*` |
| config/loaders.py `load_global_hr` / `load_tracker_hr` | 函数上方 `# TODO: optimize` |
| ~~reannounce 限频~~ | 已实现 2026-09-05: 运行时最小间隔10M + 加载告警 |
| ~~episodes.py 集数标签格式~~ | 已实现 2026-09-05: add_episode_tags 段 add_tag_single/add_tag_multi 模板 |

## 近期演进脉络 (git log 提炼, 有助于理解"为什么现在是这样")

1. 任务队列驱动重构 (12f3b46, 528 passed) — 双队列合并为单 heapq 队列, `add_task` 断点语义 (keep_progress 续跑/默认重置) 建立
2. 全局限速曲线落地 (ee88bc8 → 20481f3) — SpeedCurveMixin + curves 纯逻辑模块 + qB5.0 transfer 端点适配 (f402eaf)
3. 跳检稳健性 (5ab17c5, e5ea9e7) — 修复删除种子后访问属性/后续任务报错
4. 覆盖率补齐 (6f60a5a) — config/qbapi/qbmanager/logging/cli/tracker/speed_curve 缺口

## 给 AI 的实现建议 (基于现有架构的延伸方向)

- **新触发时机** (`on_torrent_added`): `_refresh_torrents` 的 added 循环已经是事件点; Rule 需要支持非周期任务 (一次性触发后消亡或转为 interval)。复用 `_create_torrent_tasks` 的 tracker 匹配 + `_dedup_allowed`。
- **状态变化触发**: `store.state_snapshot` 已保存上一轮枚举状态, `_handle_state_transitions` 是现成的"状态转移检测"参考实现 (grouping 内部用)。
- **新流量源**: `curves.py` 保持无项目内依赖; 数据源解析独立成函数返回 `List[HistoryRow]` 即可复用 aggregate/curve_speed 全链路。
