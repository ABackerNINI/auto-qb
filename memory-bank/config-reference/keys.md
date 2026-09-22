# 全部配置键与语法速查

> 摘要: 顶层键、trackers 站点段、限速曲线段、规则集段、变量与匹配语法、运行时文件、测试样例。
> 触发: 配置键, 配置项, trackers, 限速曲线, 规则集段, 变量替换, 匹配语法, 运行时文件

## 全部配置键 (顶层 `config:` 段)

| 键 | 类型/默认 | 说明 |
|----|-----------|------|
| `qbittorrent` | 必填 | `{host, port, username, password}` → `http://host:port` |
| `main_tick` | `"2s"` | **任务线**间隔: 到期任务 + tracker 错误原因预取 + 搜索索引推进(见下方"分层节拍") |
| `sync_interval` | `"1.5s"` | **同步线**间隔: 只拉 qB 增量刷新快照/事件/分组, **不跑任务**。默认 1.5s 与 qB 自带 WebUI(1500ms)同量级 —— 比 qB 自身数据粒度更快没有意义。大于 `main_tick` 时按 `main_tick` 生效(两条线谁先到就先跑谁)。L0 热重载, 主循环每轮重读 |
| `max_tasks_per_tick` | 20 | 每 tick 最多弹出的任务数 |
| `interval` | `"60s"` | 默认任务间隔 (maintenance/全局任务), 从上一轮结束起算 |
| `data_dir` | `"auto-qb-data"` | 运行时数据主目录; state/锁/日志/跳检备份默认均派生其下 (显式配 `state_file`/`log.file` 优先; 留空走默认) |
| `state_file` | `<data_dir>/state.json` | 状态文件; 未显式配置时由 data_dir 派生 (显式配置优先), 须可写 |
| `log` | | `{file, level, max_bytes, format}`; `file` 未配置时默认 `<data_dir>/logs/auto-qb.log` 落盘 (显式配置优先; 留空/空串=未配置=默认落盘, 无法用空串表达仅控制台); RotatingFileHandler 5 备份 |
| `remove_similar_tags` | false | 全局默认, 站点可覆盖 |
| `add_episode_tags` | `{enabled: false, add_tag_single: "zE${episode_first}", add_tag_multi: "zE${episode_first}-${episode_last}"}` | 种子添加时加集数标签; `enabled` 总开关; `add_tag_single`/`add_tag_multi` 模板, 含 `${episode_first}`/`${episode_last}` 占位, 多集仅在集数连续时生成 |
| `web` | 默认关闭 | `{enabled: bool, host: "127.0.0.1", port: 8080, token: "", skip_local_verify: false}`; WEB UI(辅种管理): 分组视图/组控制/**图形化配置编辑(每项可增删改 + 只读 YAML 预览)**; token 留空 = 首启随机生成持久化到 data_dir/web.token; host 默认仅本机(对外暴露需自行评估安全); `skip_local_verify=true` 时本机(loopback)访问 /api/* 免密钥鉴权直接进入, 对外暴露仍强制 |
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
| `hr` | | `{required_seeding_time(必填), required_share_ratio(0), extra_seeding_time("0H"), condition("80%"或"10MiB")}` + 覆盖全局的输出字段 |
| `rules` | | `["@规则集", "@规则集.规则"]`。**留空 = 该站点不执行任何规则**(无任何隐式回退; `_rules_for_torrent` 直接返回空列表) |
| `groups` | | 站点分组列表 (可多个, 自由命名无需预定义); 配置层声明不写种子; 供规则 `tracker_group` 条件按分组筛选 (2026-09-15) |
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

见 [rule-system.md](rule-system.md)。规则级键: `enabled`/`interval`/`trigger`/`execute_once`/`cooldown`/`conditions`/`actions`/`stop_following_rules_if`。`trigger` 默认 `interval` (周期轮询), 事件 trigger 见 04 触发时机表与 09 规划。

## 变量与匹配语法速查

- `regex:` 前缀 = 正则 (match_tag/match_path 用 re.search; conditions 的 tags/category/trackers 也用 search)
- `:ignore_case` 后缀 = 忽略大小写 (全项目统一支持: utils 的 tag/path 匹配与 conditions 的 tags/category/trackers/path 条件均生效; 语法解析唯一入口 utils.MatchPattern)
- `${required_seeding_time}` 变量 (标签/分类格式)
- `@tracker_tags` (delete_tags 中) = 展开为所有 tracker tags 并集
- Windows 路径用 `/` (`\` 是正则转义); 程序内部 `path_normalize` 统一为 `/`, 保留首尾斜杠

## 运行时文件

| 文件 | 性质 |
|------|------|
| `auto-qb-data/state.json` | ★ 生产状态 (gitignore, 位于数据目录 auto-qb-data/)。实测结构: `upload_snapshots.{daily,weekly,monthly} = {key, baseline{hash: uploaded}}`; `exec_history = {"{rule}:{hash}": {ts, date, hour}}`; `auto_categories = {hash: category}`; `speed_limit_curve = {"YYYY-MM-DD": {upload_kib, download_kib, dry_run}}`; `skip_check_backup = {hash: {path, save_path, category, tags, ts}}` (跳检删除前备份的元数据, 重加成功后移除); `reannounce_ts = {hash: 上次reannounce时间戳}`; `recheck_fails = {hash: {date, count}}`(当日连续校验失败); `skip_check_day = {hash: "YYYY-MM-DD"}`(跨规则同日跳检去重) |
| `auto-qb-data/state.lock` / `state.lock.meta.json` | 单实例锁及伴生 meta (由 state_file 派生: 去扩展名 + `.lock`, meta 再加 `.meta.json`) |
| `auto-qb-data/logs/auto-qb.log` | RotatingFileHandler, maxBytes 按 `log.max_bytes`, 5 备份 (log.file 未配置时默认落盘此路径, 显式配 `log.file` 优先; setup_logging 自动建 logs/ 子目录) |
| `auto-qb-data/skip-check-backup/` | 跳检**删除前**落盘的 .torrent 备份 (由 dirname(state_file) 派生, 与状态同目录); 重加确认成功后由 `_clear_backup` 删除, 只有重加失败 / 缝隙内崩溃才会留下 |
| `auto-qb-data/config.yml.bak` | 配置保存前的自动备份(路径由 `web.py` 传入 `write_tree`, 落在 data_dir 下, **不再**在项目根目录生成; 父目录不存在时自动创建) |
| `torrents.txt` | `--export-torrents_info` 的调试输出 |

## 测试配置样例

`test_yamls/` 下有运行用测试配置 (`test_up_dl_limit_tracker.yml`, `test_actions/` 目录等); `test.yml`/`minimal.yml` 是手工/最小样例。调试入口见 `.vscode/launch.json` (4 个配置: 正常运行/dry-run/导出/测试限速配置)。
