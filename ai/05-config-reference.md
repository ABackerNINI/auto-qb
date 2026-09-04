# 05 配置参考与运行时文件

## 配置加载机制 (config.py `load_config`)

- YAML 用 **`yaml.BaseLoader`** 加载 → **所有标量都是字符串** (包括数字/布尔), 随后经 `utils.parse_*` 转换 (`parse_time`/`parse_fsize`/`parse_speed`/`parse_bool`/`int()`)。因此:
  - `parse_bool` 接受 true/1/yes/on (大小写不敏感), 非法值抛 ValueError (fail-fast)。
  - exporter 导出时用 `convert_bool_in_dict` 把字符串布尔转回真布尔以保留可读性。
- **fail-fast**: 非法格式/未知键在加载时抛 ValueError, 程序不启动。给新配置键写解析时必须校验并给出可读错误 (参考 `load_global_speed_limit_curve` 的逐键 unknown-key 检查风格)。
- 站点配置覆盖全局: `load_tracker_hr(spec, global_hr)` 站点字段优先全局兜底; `remove_similar_tags` 同理。合并发生在加载时, 运行期只用合并后的值。

## 全部配置键 (顶层 `config:` 段)

| 键 | 类型/默认 | 说明 |
|----|-----------|------|
| `qbittorrent` | 必填 | `{host, port, username, password}` → `http://host:port` |
| `main_tick` | `"2s"` | 主循环间隔 |
| `max_tasks_per_tick` | 20 | 每 tick 最多弹出的任务数 |
| `interval` | `"60s"` | 默认任务间隔 (maintenance/全局任务), 从上一轮结束起算 |
| `state_file` | `"auto-qb-state.json"` | 状态文件, 必须可写 |
| `log` | | `{file, level, max_bytes, format}`; file 空=仅控制台; RotatingFileHandler 5 备份 |
| `remove_similar_tags` | false | 全局默认, 站点可覆盖 |
| `add_episode_tags` | false | 种子添加时加集数标签 (仅添加时触发一次) |
| `grouping` | | `{enabled: bool, check_missing_files: bool, missing_tag: "MISSING"}` |
| `delete_tags` | [] | 彻底删除的标签格式 (支持 `regex:`, `:ignore_case`, `@tracker_tags` 引用) |
| `delete_tags_if_has_no_torrents` | [] | 仅无种子使用时删除 |
| `hr` | | 全局 HR 输出设置 (add_tag/add_category/overwrite_category/add_tag_for_satisfied/add_category_for_satisfied/overwrite_category_for_satisfied); 默认分类格式 `!!HR${required_seeding_time}!!` / `--HR${required_seeding_time}--` |
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
            bat_path: ".../history_traffic.dat"   # 当前仅支持单一 traffic_monitor 源
    curves:                          # 重复 period 拒绝; 每条为单项映射 curve:
        - curve:
            period: DAY              # DAY/1D/D | MONTH | ND (如 7D 滚动窗口)
            upload_curve:            # 阈值严格递增; 每档 {upload_speed_limit: 速度}
                - 10GiB: {upload_speed_limit: 6MiB/s}
            download_curve: [...]    # 可省略 (省略=不管理该方向)
```

计算: 读 dat (行 `YYYY/MM/DD 上传KB/下载KB`, KB=1024B) → 按 period 聚合 (day=当天行; month=当月求和; Nd=最近 N 天求和; 缺失日=0 自动回落) → `curve_speed` 全程分档覆盖 (累计 < 阈值₁ 用档₁速度; 超末档用末档; 速度 0=不限) → 同方向多曲线取**最小非零** (最严) → bytes→KiB (半值向上取整) → 奇数保护/幂等比较 → `set_global_speed_limits` (qB5.0 transfer 端点)。

## 规则集段 (`*_rules`)

见 [04-rule-system.md](04-rule-system.md)。规则级键: `enabled`/`interval`/`execute_once`/`cooldown`/`conditions`/`actions`/`stop_following_rules_if`。

## 变量与匹配语法速查

- `regex:` 前缀 = 正则 (match_tag/match_path 用 re.search; conditions 的 tags/category/trackers 也用 search)
- `:ignore_case` 后缀 = 忽略大小写 (utils 的 tag/path 匹配支持; conditions 内部暂不支持)
- `${required_seeding_time}` 变量 (标签/分类格式)
- `@tracker_tags` (delete_tags 中) = 展开为所有 tracker tags 并集
- Windows 路径用 `/` (`\` 是正则转义); 程序内部 `path_normalize` 统一为 `/`, 保留首尾斜杠

## 运行时文件

| 文件 | 性质 |
|------|------|
| `auto-qb-state.json` | ★ 生产状态 (gitignore)。实测结构: `upload_snapshots.{daily,weekly,monthly} = {key, baseline{hash: uploaded}}`; `exec_history = {"{rule}:{hash}": {ts, date, hour}}`; `auto_categories = {hash: category}`; `speed_limit_curve = {"YYYY-MM-DD": {upload_kib, download_kib, dry_run}}`; `skip_check_backup = {hash: {path, save_path, category, tags, ts}}` |
| `logs/auto-qb.log` | RotatingFileHandler, maxBytes 按 `log.max_bytes`, 5 备份 |
| `skip-check-backup/` | 跳检重加失败时的 .torrent 备份 (state_file 同目录) |
| `torrents.txt` | `--export-torrents_info` 的调试输出 |

## 测试配置样例

`test_yamls/` 下有运行用测试配置 (`test_up_dl_limit_tracker.yml`, `test_actions/` 目录等); `test.yml`/`minimal.yml` 是手工/最小样例。调试入口见 `.vscode/launch.json` (4 个配置: 正常运行/dry-run/导出/测试限速配置)。
