# 09 路线图与项目状态

> 来源: `想法.md` (设计草稿, 权威) + `README.md` 功能状态标注 + 源码 TODO + git log (截至 2026-09-05, commit 51374bd)。回答"XX 做了吗/计划怎么做"以此为准。

## 已实现 (✅, 有单测覆盖)

> 注意区分: 下表部分功能作者在 README 中标注 🚧 = "已实现但未严格测试(实盘验证)", 如规则引擎的条件/动作/checking/去重语义等 — 有单测但作者尚不认为经过严格验证; 此类 🚧 ≠ 未实现, 勿移除 (语义详见 08-pitfalls)。

- 标签/分类管理: 站点标签加/删、相似标签清理、`delete_tags`/`delete_tags_if_has_no_torrents` 全局清理、集数标签
- HR 管理: 触发标签/分类 + satisfied 标签/分类, 站点覆盖全局
- 辅种分组: 增量归组、大小一致性、缺文件事件驱动扫描 (删除/上传转暂停/路径变化)、下载冲突检查
- 规则引擎: interval 触发 + 15 条件 + 11 动作 + execute_once/cooldown 去重 + 断点续跑 + stop_following_rules_if
- checking 动作: filelist/piecehashes/custom 三种参考判定 + full-checking (异步轮询) + skip-checking (导出→删除→重加, 同日去重+备份)
- tracker 单种限速 (奇数保护)
- 全局限速曲线: Traffic Monitor 数据源, DAY/MONTH/ND 聚合, 全程分档覆盖, 取最严 (2026-09 最近的大功能, commit ee88bc8..20481f3)
- 任务队列: 单队列 + defer/resume + check 轮询去重 (12f3b46 重构完成)
- 数据层: TorrentStore 快照+惰性缓存+分组索引; QbApi 门面写后同步
- YAML 导出 (`--export-yaml`, `--only-missing`), qB 5.0 API 适配
- fail-fast 全量配置校验 (2026-09-05): `config.validate_config` 聚合校验未知键/必填项/值格式/规则 spec/引用存在性; 留空(空串/None)走默认值; Rule 构造报错带规则名上下文; `load_*` 解析函数已剥离全部检查(先验证再解析, 解析假定配置正确)
- 测试: 598 passed, 分支覆盖 95%

## 规划中 (🚧, 尚未实现)

### 规则系统
- 触发时机: `on_torrent_state_changed` / `on_torrent_added` / `on_torrent_deleted` (想法.md; 架构上需要把"新种子检测"泛化为事件源, 任务队列已具备让位/恢复基础)
- 条件取反 (`!` / 非 logic)、tags/category/trackers 条件的 `:ignore_case` 支持
- tracker 分组 (规则按组筛选)
- `hr` 条件/状态与 `RuleContext.check_hr_*` 的位置整理 (TODO: 移到 actions.py)

### 其它功能
- 单实例锁 (`single_instance_lock` 配置已占位, 校验接受该键但不生效)
- 插件系统: 直接支持自定义 Python plugin
- 根据流量接入更多数据源 (traffic_source 当前仅 traffic_monitor 单源, 代码已按列表预留)
- 与 PTD-cli 合作: 自动分析 HR 标签 / 暂停低分享率非免费种子 (想法.md 标注"需可行性验证")
- 集数标签自定义格式 (`zE` 前缀等)
- 复杂限速规则 (tracker+时段组合等)
- 性能: 主循环拆分平滑占用、全面优化 (想法.md 标注)

### 代码内待办 (TODO 清单, 2026-09-05)
| 位置 | 内容 |
|------|------|
| qbmanager.py:190 | 删除 `_get_torrent` 兼容方法 |
| rules/base.py:116 | 多 tracker 匹配时 warning+跳过 (2026-09-05: `_match_tracker_conf` 已改为命中多个时打 ERROR 日志并用第一个, 是否跳过仍待作者决定) |
| rules/base.py:134,150 | HR 判定从 RuleContext 移到 actions.py |
| rules/conditions.py:79,108,134 | 条件支持 `:ignore_case` |
| rules/actions.py:220 | recheck 后仍未完成的种子防重复校验 |
| rules/actions.py:254 | `_find_reference` 优化为提前返回 |
| rules/actions.py:292 | 重新设计 custom 校验流程 |
| rules/actions.py:546 | reannounce 添加频率限制 |
| episodes.py:112 | 集数标签格式自定义 |

## 近期演进脉络 (git log 提炼, 有助于理解"为什么现在是这样")

1. 任务队列驱动重构 (12f3b46, 528 passed) — 双队列合并为单队列, defer/resume 语义建立
2. 全局限速曲线落地 (ee88bc8 → 20481f3) — SpeedCurveMixin + curves 纯逻辑模块 + qB5.0 transfer 端点适配 (f402eaf)
3. 跳检稳健性 (5ab17c5, e5ea9e7) — 修复删除种子后访问属性/后续任务报错
4. 覆盖率补齐 (6f60a5a) — config/qbapi/qbmanager/logging/cli/tracker/speed_curve 缺口

## 给 AI 的实现建议 (基于现有架构的延伸方向)

- **新触发时机** (`on_torrent_added`): `_refresh_torrents` 的 added 循环已经是事件点; Rule 需要支持非周期任务 (一次性触发后消亡或转为 interval)。复用 `_create_torrent_tasks` 的 tracker 匹配 + `_dedup_allowed`。
- **状态变化触发**: `store.state_snapshot` 已保存上一轮枚举状态, `_handle_state_transitions` 是现成的"状态转移检测"参考实现 (grouping 内部用)。
- **fail-fast 全量校验**: 参照 `load_global_speed_limit_curve` / `CheckAction._validate` 的 unknown-key + 取值域校验风格, 逐段补齐 (规则 spec 校验可放 `Rule.__init__`)。
- **新流量源**: `curves.py` 保持无项目内依赖; 数据源解析独立成函数返回 `List[HistoryRow]` 即可复用 aggregate/curve_speed 全链路。
