# 08 陷阱、风险点与文档漂移 (改代码前必读)

## 🔴 生产文件, 禁止改动/提交

- **`config.yml`**: 用户真实生产配置 — 含真实 PT 站点域名、tracker 规则、qB 凭据引用。不是示例! 改示例用 `minimal.yml`/`test_yamls/`。
- **`auto-qb-state.json`**: 运行中程序的状态文件, 程序退出时覆写。改它毫无意义且可能破坏运行。
- 两者均已 gitignore, 但在工作区可见 — 不要"顺手"格式化/重排它们。

## ⚠️ 高风险业务操作 (代码中已有防护, 改动时不得削弱)

1. **跳检 (skip-checking)**: 删除种子→重加, 丢失统计 (下载量/上传量/做种时长/分享率); 内容错误会传垃圾数据 (PT 站严令禁止)。防护: 同日去重 / 强制 filelist 前置检查 / 无参考 warning / 重加失败落盘备份。跳检过程中种子会从 store 消失 (`remove_torrent`) — 该种子同 tick 内的后续动作必须容错 (历史 bug: commit e5ea9e7, 测试 test_checking.py 覆盖)。
2. **reannounce 动作**: 目前**无任何频率限制** (TODO in code), 只能靠规则 execute_once 控制。
3. **删除种子** (`torrents_delete`): 仅跳检流程使用, `delete_files=False` 固定。
4. **全局限速覆盖**: 奇数 KiB 视为用户手动设置则跳过 — 三处实现 (tracker.py/actions.py/speed_curve.py) 逻辑必须保持一致。

## ⚠️ 平台/API 兼容陷阱

- **qB 5.0+ 全局限速**: 必须走 `transfer_upload_limit`/`transfer_set_upload_limit` 端点 (bytes/s, 0=不限)。旧 `app.preferences` 的 `upload_limit/download_limit` 键**已静默失效** (历史 bug, commit f402eaf)。qbittorrent-api 新版 `app.preferences` 是 property 不是方法 (commit be0911b)。
- **qB 状态枚举**: 用 `qbittorrentapi.TorrentState` 枚举属性 (`is_stopped` 等) 判定, 不要比较 state 字符串 (pausedUP vs stoppedUP 跨版本差异)。
- **Windows 长路径**: 磁盘文件检查过 `add_long_path_prefix_for_win` (`\\?\` 前缀), 新文件访问要走同一工具。
- **`yaml.BaseLoader`**: 配置全是字符串; 写解析时不要假设 YAML 已给原生类型; 空 `trackers:` 段会解析成 None/str, 已有 `isinstance` 防御, 新增类似段同样要防。

## ⚠️ 行为细节 (易误判为 bug)

- **奇数限速保护**: `(current_limit / 1024) % 2 == 1` → 跳过。这是特性不是 bug; 相关测试断言"奇数不覆盖"。
- **interval 归一化**: `Task.interval <= 0` → 1s (每 tick 级别); 规则 interval 为 0 表示每轮执行。
- **`handled` 返回值**: `Rule.process` 返回 `not result.is_skipped` — 最后一个动作 skip 时 handled=False, 但**执行历史已记录** (只要前面动作成功过)。设计如此, 勿"修复"。
- **上传增量下限 0**: `upload_delta = max(0, uploaded - baseline)` — 种子重加/客户端重启后 uploaded 归零不会产生负增量。
- **缺文件扫描的代表种**: 只从"已完成+做种中"成员选, 无代表则整组不扫 — 不是漏检, 是有意保守。
- **tracker 匹配是"第一个命中"且已统一为 hostname 精确匹配**: `_match_tracker_conf` 复用 `utils.match_tracker_confs` (精确/子域名匹配, 与规则绑定同语义), 取第一个匹配配置, **命中多个配置时打 ERROR 日志**(仍用第一个, 不跳过种子); 导出模板 `find_missing_domains` 仍用包含关系匹配 (有意宽松, 用于找未配置域名)。
- **每个动作的 dry-run 返回 success** — dry-run 日志里看到的都是"成功", 别据此判断真实执行结果。
- **`state_file` 仅退出时落盘**: 运行中 kill -9 会丢执行历史 → 去重可能重放, 已知取舍 (想法.md 明文)。

## 📝 文档与代码的一致性 (2026-09-05 已同步)

README.md 曾有的客观漂移已于 2026-09-05 修正: 任务队列描述 (双队列→单队列)、集数标签格式 (`E1-5`→`zE1-5`)、mixins 组合列表补 SpeedCurveMixin、目录树补 qbapi/curves/speed_curve、checking.py 职责描述。

**🚧 标注的语义 (作者澄清, 重要)**: 🚧 = "未实现 **或** 已实现但未严格测试(实盘验证)"。规则系统一节的 🚧 (trigger/execute_once/cooldown、size/trackers/state/hr/date_time/seedtime/upload_*/freespace 条件、checking/move_to/reannounce 动作、stop_following_rules_if) 属于后者 — 代码已有单测, 但作者认定未经严格验证, **必须保留, 勿因"已实现"而移除** (2026-09-05 曾误删, 已按作者要求恢复)。

其余 🚧 属未实现: 单实例锁 / 启动 fail-fast 全量校验 (config 校验只覆盖部分: 曲线/checking 段严格, 其它宽松) / `on_torrent_state_changed` / `on_torrent_added` / `on_torrent_deleted` 触发时机。

> 想法.md 是设计草稿, 不随实现同步; 改 README 时以代码为准, 但 🚧 标注的取舍听作者。

## ⚠️ 代码内 TODO (改动相关区域时顺带了解)

- `qbmanager.py:190` `_get_torrent` 标记"TODO: 删除" — 新代码直接用 `self.store.get(hash)`。
- `rules/base.py:134,150` HR 判定函数标记"移动到 actions.py" — RuleContext 上的 `check_hr_*` 与 TagsMixin `_add_hr_tag_or_category` 逻辑重复, 改 HR 语义要两处同步。
- `conditions.py` tags/category/trackers 三个条件不支持 `:ignore_case` (utils 支持)。
- `actions.py:220` "未完成且暂停的种子若 recheck 后仍未完成, 下一轮会再次校验" — 已知待处理。
- `episodes.py:112` 集数标签格式不可自定义。
- `config.py:357,373` HR 加载标记 TODO optimize。

## ⚠️ 并发/状态机约束回顾 (违反即引入难以复现的 bug)

1. 主循环线程是唯一修改队列/state_file/store 分组索引的线程 — 不要在校验回调、信号处理器、新线程里改这些。
2. defer 与 recheck 的顺序: **先 `add_check_task` 登记, 再 `defer(origin)`, 再发 recheck** — 任何调整都要保持"发送失败绝不 defer"。
3. `resume` 保留 `resume_index` (续跑), `reschedule` 清空 (重走决策链) — 二者语义不可混用。
4. `remove_torrent(hash)` 是清理唯一入口 (队列任务+让位+在途校验) — 种子删除路径必须经过它。
5. QbApi 写方法必须同步 store (`update_torrent_fields`/`invalidate_*`), 否则同 tick 读旧值 (test_snapshot_sync.py 防回归)。
