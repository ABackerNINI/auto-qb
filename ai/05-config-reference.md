# 05 配置参考与运行时文件

## 配置加载机制 (config.py `load_config`)

- YAML 用 **`yaml.BaseLoader`** 加载 → **所有标量都是字符串** (包括数字/布尔), 随后经 `utils.parse_*` 转换 (`parse_time`/`parse_fsize`/`parse_speed`/`parse_bool`/`int()`)。因此:
  - `parse_bool` 接受 true/1/yes/on (大小写不敏感), 非法值抛 ValueError (fail-fast)。
  - exporter 导出时用 `convert_bool_in_dict` 把字符串布尔转回真布尔以保留可读性。
- **fail-fast**: 非法格式/未知键在加载时抛 ValueError, 程序不启动。给新配置键写解析时必须校验并给出可读错误 (参考 `load_global_speed_limit_curve` 的逐键 unknown-key 检查风格)。
- 站点配置覆盖全局: `load_tracker_hr(spec, global_hr)` 站点字段优先全局兜底; `remove_similar_tags` 同理。合并发生在加载时, 运行期只用合并后的值。

## fail-fast 全量校验 (2026-09-05 新增, config.validate_config)

`load_config` 在解析前做全量校验, **聚合全部错误一次性抛 `ConfigError`**(ValueError 子类, 统一承载文件读取失败/YAML 解析失败/校验失败/启动期规则 spec 错误), 每条带配置路径, 形如:

```
配置校验失败(config.yml), 共 2 处:
  [1] config.qbittorrent: 未知键 ['hos'], 可用键: ['host', 'password', 'port', 'username']
  [2] config.trackers.T1: 缺少必填键 domains(站点域名列表)
```

校验范围:
- **未知键**: 根节点(仅允许 config)/config 顶层/各段(log/qbittorrent/grouping/hr)/tracker 段/站点 hr 段/规则 spec 一律拒绝; `single_instance_lock` 为规划中预留键(接受但不生效)
- **必填项**: tracker 的 `domains`(非空字符串列表)、站点 hr 的 `required_seeding_time`; 其余键有默认值
- **值格式**: 复用 utils.parse_*(时间/大小/速度/布尔)与 parse_hr_condition; `main_tick` 须 >0; `port` 1-65535; 日志等级须合法; `regex:` 模式须可编译(delete_tags/tracker.remove_tags/tags/category/trackers 条件/remove_tags 动作, 经 `_PLUGIN_SPEC_VALIDATORS` 分发)
- **规则集 spec**: 已知键/`execute_once`(never/once/daily/hourly)/`stop_following_rules_if` 六值/`trigger` 四值(interval/on_torrent_added/on_torrent_deleted/on_torrent_state_enum_changed, 取值非法即抛)/conditions-actions 须单键字典且名称已注册(经 registry 延迟导入, 避免循环依赖); **触发时机×动作兼容白名单** (`_validate_trigger_action_compat`): `on_torrent_deleted` 仅允许 `print_torrent_details`(删除后种子无活现场, 需活种子的动作直接拒绝, 见 04), 其余 trigger 不设限; 条件/动作 spec 值的深度校验在 Rule 构造时进行(报错带规则名上下文)
- **tracker.rules 引用**: 必须 `@` 开头且引用的规则集/规则存在(否则运行时会静默不执行)

**留空语义**: `yaml.BaseLoader` 把 `key:` 留空解析为空串 `''`(不是 None); `_strip_none` 将 None/空串统一视为"未配置", 走默认值(默认值本为空串的键如 hr.add_tag 行为不变)。因此"有默认值的配置允许为空, 没有的必须有"。

**默认值单一来源 (2026-09-05)**: 全部默认值只定义在 `models.py` 的 dataclass 字段上 (解析后空间, 与字段类型注解一致, `Config()` 即全默认实例)。`loaders.py` 统一用 `_get(spec, key, d.field, parse)` 取值: 键存在 → parse(原始串); 键缺失 → 字段默认(不再 parse)。models 顶部仅存 2 个**非字段默认**常量: `DEFAULT_CONFIG_FILE`(cli argparse 缺省) 与 `UNLIMITED_SPEED`(exporter 生成模板的原始串占位)。

**先验证再解析**: 全部正确性检查集中在 `validate_config`(含 `_validate_global_speed_limit_curve` 与 `_PLUGIN_SPEC_VALIDATORS` 插件 spec 深度校验); 通过后各 `load_*` 函数仅做转换、不含任何检查。**config 之后的全部代码同样假定配置正确**: registry 工厂直接按名索引(未知名 = KeyError, 由校验兜底)、`config.global_speed_limit_curve`/`rules_config`/`tracker.rules` 等属性直接访问(无 getattr 兜底)、exporter 重读原始文件时复用 `_strip_none`。注意区分: 功能开关(`grouping.enabled`/`check_missing_files`/`hr` 等)是语义判断不是正确性检查, 正常保留。

**单实例锁 (2026-09-05)**: 仅正常 `run()` 模式持锁, 锁文件 `<state_file 去扩展名>.lock` 与伴生 `.meta.json` (PID/启动时间/配置路径); 锁失败抛 `SingleInstanceLockError(AutoQbError)`, 走 CLI 退出码 1 + stderr 无堆栈; `--export-yaml` / `--export-torrents_info` 通过 `QbManager(no_lock=True)` 跳过锁 (可与正常实例并发); 基于第三方 `filelock` (跨平台 fcntl/msvcrt); 陈旧锁不接管, OS 句柄随进程退出自动释放, 必要时手动删除锁文件。

**CLI 错误输出**: `cli.main` 单点捕获 **`AutoQbError` 体系** —— `ConfigError` 加 `配置错误: ` 前缀输出; `SingleInstanceLockError`(锁竞争)/`QbCompatError`(qB 字段不兼容)等消息自身已含完整上下文, 直接输出。均无堆栈/exec_info, 退出码 1。非 AutoQbError 异常(ValueError/OSError 等)属程序 bug, 照常抛出保留堆栈。入口(auto-qb.py / __main__.py)用 `sys.exit(main())` 使退出码生效。

## 全部配置键 (顶层 `config:` 段)

| 键 | 类型/默认 | 说明 |
|----|-----------|------|
| `qbittorrent` | 必填 | `{host, port, username, password}` → `http://host:port` |
| `main_tick` | `"2s"` | 主循环间隔 |
| `max_tasks_per_tick` | 20 | 每 tick 最多弹出的任务数 |
| `interval` | `"60s"` | 默认任务间隔 (maintenance/全局任务), 从上一轮结束起算 |
| `data_dir` | `"auto-qb-data"` | 运行时数据主目录; state/锁/日志/跳检备份默认均派生其下 (显式配 `state_file`/`log.file` 优先; 留空走默认) |
| `state_file` | `<data_dir>/state.json` | 状态文件; 未显式配置时由 data_dir 派生 (显式配置优先), 须可写 |
| `log` | | `{file, level, max_bytes, format}`; `file` 未配置时默认 `<data_dir>/logs/auto-qb.log` 落盘 (显式配置优先; 留空/空串=未配置=默认落盘, 无法用空串表达仅控制台); RotatingFileHandler 5 备份 |
| `remove_similar_tags` | false | 全局默认, 站点可覆盖 |
| `add_episode_tags` | `{enabled: false, add_tag_single: "zE${episode_first}", add_tag_multi: "zE${episode_first}-${episode_last}"}` | 种子添加时加集数标签; `enabled` 总开关; `add_tag_single`/`add_tag_multi` 模板, 含 `${episode_first}`/`${episode_last}` 占位, 多集仅在集数连续时生成 |
| `notify` | 默认关闭 | `{enabled: bool, min_level: "WARNING", quiet_hours: "", max_per_hour: 20, dedup_window: "10M", channels: [platform]}`; 主动通知(WARNING 及以上日志 -> 平台原生通知, 零依赖); quiet_hours "HH:MM-HH:MM" 支持跨午夜, 时段内跳过发送(含 ERROR); channels v1 仅 platform(缺省即启用); 节流为内存态不进 state_file |
| `grouping` | | `{enabled: bool, check_missing_files: bool, missing_tag: "MISSING"}` |
| `delete_tags` | [] | 彻底删除的标签格式 (支持 `regex:`, `:ignore_case`, `@tracker_tags` 引用) |
| `delete_tags_if_has_no_torrents` | [] | 仅无种子使用时删除 |
| `hr` | | 全局 HR 输出设置 (add_tag/add_category/overwrite_category/add_tag_for_satisfied/add_category_for_satisfied/overwrite_category_for_satisfied); 默认分类格式 `!!HR${required_seeding_time}!!` / `--HR${required_seeding_time}--` |
| `skip_checking_tag` | `"zSkipChecked"` | 跳检成功标签全局名; 带此标签的种子未经哈希校验, `_find_reference` 一律排除 (防"未验证"经参考链传播)。全局统一, **checking 动作 spec 不可配置同名键** (校验报未知键), 动作运行时经 ctx 读取; YAML 留空/空串被 `_strip_none` 视为未配置走默认 (与 log.file 同约定) |
| `global_speed_limit_curve` | 无=不启用 | 见下 |
| `trackers` | {} | 站点配置, 见下 |
| `<任意>_rules` | {} | 规则集 (键名以 `_rules` 结尾), 见 04 |

时间单位: `S/M/H/D` (不区分大小写, 支持小数如 `1.5D`); 大小单位: `B/KiB/MiB/GiB/TiB/PiB` (仅二进制单位); 速度单位: `B/s ~ GiB/s`。空串 parse_time/parse_speed → 0。

## trackers 站点段

| 键 | 必填 | 说明 |
|----|------|------|
| `domains` | ✅ | 域名列表。匹配逻辑 (2026-09-05 起统一): `_match_tracker_conf` 复用 `utils.match_tracker_confs`, 按 hostname 精确匹配(含子域名), 取第一个命中配置; 命中多个配置时打 ERROR 日志 |
| `tags` | | 站点标签 (maintenance 加) |
| `remove_tags` | | 删除标签格式 (正则) |
| `upload_speed_limit` / `download_speed_limit` | `"0KiB/s"` | 单种限速, 0=不限; 种子添加时应用; 奇数保护 |
| `hr` | | `{required_seeding_time(必填), required_share_ratio(0), extra_seeding_time("0S"), condition("80%"或"10MiB")}` + 覆盖全局的输出字段 |
| `rules` | | `["@规则集", "@规则集.规则"]` |
| `remove_similar_tags` | | 覆盖全局 |

## global_speed_limit_curve 段

```yaml
global_speed_limit_curve:
    interval: 10M                    # 可选, 缺省回退主 interval
    traffic_source:
        - traffic_monitor:
            dat_path: ".../history_traffic.dat"   # 当前仅支持单一 traffic_monitor 源
    curves:                          # 重复 period 拒绝; 每条为单项映射 curve:
        - curve:
            period: DAY              # DAY/1D/D | MONTH | ND (如 7D 滚动窗口)
            upload_curve:            # 阈值严格递增; 每档 {upload_speed_limit: 速度}
                - 10GiB: {upload_speed_limit: 6MiB/s}
            download_curve: [...]    # 可省略 (省略=不管理该方向)
```

计算: 读 dat (行 `YYYY/MM/DD 上传KB/下载KB`, KB=1024B) → 按 period 聚合 (day=当天行; month=当月求和; Nd=最近 N 天求和; 缺失日=0 自动回落) → `curve_speed` 全程分档覆盖 (累计 < 阈值₁ 用档₁速度; 超末档用末档; 速度 0=不限) → 同方向多曲线取**最小非零** (最严) → bytes→KiB (半值向上取整) → 奇数保护/幂等比较 → `set_global_speed_limits` (qB5.0 transfer 端点)。

## 规则集段 (`*_rules`)

见 [04-rule-system.md](04-rule-system.md)。规则级键: `enabled`/`interval`/`trigger`/`execute_once`/`cooldown`/`conditions`/`actions`/`stop_following_rules_if`。`trigger` 默认 `interval` (周期轮询), 事件 trigger 见 04 触发时机表与 09 规划。

## 变量与匹配语法速查

- `regex:` 前缀 = 正则 (match_tag/match_path 用 re.search; conditions 的 tags/category/trackers 也用 search)
- `:ignore_case` 后缀 = 忽略大小写 (全项目统一支持: utils 的 tag/path 匹配与 conditions 的 tags/category/trackers/path 条件均生效; 语法解析唯一入口 utils.MatchPattern)
- `${required_seeding_time}` 变量 (标签/分类格式)
- `@tracker_tags` (delete_tags 中) = 展开为所有 tracker tags 并集
- Windows 路径用 `/` (`\` 是正则转义); 程序内部 `path_normalize` 统一为 `/`, 保留首尾斜杠

## 运行时文件

| 文件 | 性质 |
|------|------|
| `auto-qb-data/state.json` | ★ 生产状态 (gitignore, 位于数据目录 auto-qb-data/)。实测结构: `upload_snapshots.{daily,weekly,monthly} = {key, baseline{hash: uploaded}}`; `exec_history = {"{rule}:{hash}": {ts, date, hour}}`; `auto_categories = {hash: category}`; `speed_limit_curve = {"YYYY-MM-DD": {upload_kib, download_kib, dry_run}}`; `skip_check_backup = {hash: {path, save_path, category, tags, ts}}`; `reannounce_ts = {hash: 上次reannounce时间戳}`; `recheck_fails = {hash: {date, count}}`(当日连续校验失败); `skip_check_day = {hash: "YYYY-MM-DD"}`(跨规则同日跳检去重) |
| `auto-qb-data/state.lock` / `state.lock.meta.json` | 单实例锁及伴生 meta (由 state_file 派生: 去扩展名 + `.lock`, meta 再加 `.meta.json`) |
| `auto-qb-data/logs/auto-qb.log` | RotatingFileHandler, maxBytes 按 `log.max_bytes`, 5 备份 (log.file 未配置时默认落盘此路径, 显式配 `log.file` 优先; setup_logging 自动建 logs/ 子目录) |
| `auto-qb-data/skip-check-backup/` | 跳检重加失败时的 .torrent 备份 (由 dirname(state_file) 派生, 与状态同目录) |
| `torrents.txt` | `--export-torrents_info` 的调试输出 |

## 测试配置样例

`test_yamls/` 下有运行用测试配置 (`test_up_dl_limit_tracker.yml`, `test_actions/` 目录等); `test.yml`/`minimal.yml` 是手工/最小样例。调试入口见 `.vscode/launch.json` (4 个配置: 正常运行/dry-run/导出/测试限速配置)。
