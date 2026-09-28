# 全部配置键与语法速查

> 摘要: 顶层键、trackers 站点段、限速曲线段、规则集段、变量与匹配语法、运行时文件、测试样例。
> 触发: 配置键, 配置项, trackers, 限速曲线, 规则集段, 变量替换, 匹配语法, 运行时文件, hr_check, HR 在线核实

## 全部配置键 (顶层 `config:` 段)

| 键 | 类型/默认 | 说明 |
|----|-----------|------|
| `qbittorrent` | 必填 | `{host, port, username, password}` → `http://host:port` |
| `main_tick` | `"2s"` | **任务线**间隔: 到期任务 + tracker 错误原因预取 + 搜索索引推进(见下方"分层节拍") |
| `sync_interval` | `"1.5s"` | **同步线**间隔: 只拉 qB 增量刷新快照/事件/分组, **不跑任务**。默认 1.5s 与 qB 自带 WebUI(1500ms)同量级 —— 比 qB 自身数据粒度更快没有意义。大于 `main_tick` 时按 `main_tick` 生效(两条线谁先到就先跑谁)。L0 热重载, 主循环每轮重读 |
| `state_save_interval` | `"120s"` | 状态周期落盘间隔: 非优雅终止(taskkill/断电/崩溃)时的状态丢失窗口, 优雅退出仍立即落盘; `0` = 关闭(仅优雅退出落盘, 旧行为); 配置端下限 30s 防误配置写放大。L0 热重载 |
| `max_tasks_per_tick` | 20 | 每 tick 最多弹出的任务数 |
| `interval` | `"60s"` | 默认任务间隔 (maintenance/全局任务), 从上一轮结束起算 |
| `data_dir` | `"auto-qb-data"` | 运行时数据主目录; state/锁/日志/跳检备份默认均派生其下 (显式配 `state_file`/`log.file` 优先; 留空走默认) |
| `state_file` | `<data_dir>/state.json` | 状态文件; 未显式配置时由 data_dir 派生 (显式配置优先), 须可写 |
| `schema_version` | `2` | 配置文件格式版本标记(升级链, 计划 26-09-26-0506): **文件格式标记, 非行为配置** —— 不进 `Config` dataclass; 加载时缺失=v1, 落后则沿链迁移(内存); 磁盘由 `run()` 开头的启动物化单点改写到当前版本(版本号备份 `<名>.v<m>.bak` 后原子写, 计划 26-09-27-2252), WebUI 保存不做迁移 —— 提交树版本低于当前直接 400 指路刷新, 高于程序支持报 ConfigError; WebUI 保存/`--export-yaml` 自动盖章, 用户手编无需写 |
| `log` | | `{file, level, max_bytes, format}`; `file` 未配置时默认 `<data_dir>/logs/auto-qb.log` 落盘 (显式配置优先; 留空/空串=未配置=默认落盘, 无法用空串表达仅控制台); RotatingFileHandler 5 备份 |
| `remove_similar_tags` | false | 全局默认, 站点可覆盖 |
| `maintenance_tag_mode` | `"interval"` | **维护 tags 节奏** (计划 26-09-27-1438): 站点 tags 维护(`_add_tags`/`_remove_tags`/`_remove_similar_tags`)的执行时机。`interval` = 每个内置任务间隔执行(默认 = 迁移前行为); `on_change` = 种子添加时执行一次, 之后仅当该种子 tags 被**程序之外**改动时重检(登记消费一次; 热重载 L2 后首轮全量收敛), 无变化轮跳过 —— 每轮每种子省一次 qB 读写往返。HR 标签/分类部分**不受影响**, 恒按周期执行(达标状态随时间演化, tags 变化捕捉不到)。取值限 `interval\|on_change`; 未列入 SECTION_LEVELS → L2 保守重建 |
| `add_episode_tags` | `{enabled: false, add_tag_single: "zE${episode_first}", add_tag_multi: "zE${episode_first}-${episode_last}"}` | 种子添加时加集数标签; `enabled` 总开关; `add_tag_single`/`add_tag_multi` 模板, 含 `${episode_first}`/`${episode_last}` 占位, 多集仅在集数连续时生成 |
| `web` | 默认关闭 | `{enabled: bool, host: "127.0.0.1", port: 8080, token: "", skip_local_verify: false}`; WEB UI(辅种管理): 分组视图/组控制/**图形化配置编辑(每项可增删改 + 只读 YAML 预览)**; token 留空 = 首启随机生成持久化到 data_dir/web.token; host 默认仅本机(对外暴露需自行评估安全); `skip_local_verify=true` 时本机(loopback)访问 /api/* 免密钥鉴权直接进入, 对外暴露仍强制 |
| `notify` | 默认关闭 | `{enabled: bool, min_level: "ERROR", quiet_hours: "", max_per_hour: 20, dedup_window: "10M", channels: [platform]}`; 主动通知(ERROR 及以上日志 -> 平台原生通知, 零依赖; 26-09-27 等级整改后默认只推真正危险, WARNING 仅排障, 想看排障消息手动调低); quiet_hours "HH:MM-HH:MM" 支持跨午夜, 时段内跳过发送(含 ERROR); channels v1 仅 platform(缺省即启用); 节流为内存态不进 state_file |
| `grouping` | | `{enabled: bool, check_missing_files: bool, missing_tag: "MISSING"}` |
| `delete_tags` | [] | 彻底删除的标签格式 (支持 `regex:`, `:ignore_case`, `@tracker_tags` 引用) |
| `delete_tags_if_has_no_torrents` | [] | 仅无种子使用时删除 |
| `hr` | | 全局 HR 输出设置 (add_tag/add_category/overwrite_category/add_tag_for_satisfied/add_category_for_satisfied/overwrite_category_for_satisfied) + 排除表 exclude_tags/exclude_categories: 命中种子不纳入 HR 体系(不打标/不核实/规则按未触发, 压过 mode=all 等一切管束), 判定时现算, 不回撤存量, 与站点段并集(26-09-28-1805); 默认分类格式 `!!HR${required_seeding_time}!!` / `--HR${required_seeding_time}--` |
| `skip_checking_tag` | `"zSkipChecked"` | 跳检成功标签全局名; 带此标签的种子未经哈希校验, `_find_reference` 一律排除 (防"未验证"经参考链传播)。全局统一, **checking 动作 spec 不可配置同名键** (校验报未知键), 动作运行时经 ctx 读取; YAML 留空/空串被 `_strip_none` 视为未配置走默认 (与 log.file 同约定) |
| `hr_check` | 默认关闭 | **HR 在线核实** (部分种子 HR 站点): `{enabled(false), min_torrent_interval("90S"; split 站点改义为「仅 .torrent 下载间隔」), max_torrents_per_hour(12; split 站点不使用), max_torrents_per_day(留空=按模型取默认: legacy 60 / split 200; split 下改义为「仅下载天顶」), page_rate_per_hour(40, 仅 split), page_burst(10, 仅 split), torrent_rate_per_hour(20, 仅 split), torrent_burst(5, 仅 split), max_pages_per_day(400, 仅 split), min_page_interval("90S", 仅 split), max_pages_per_round(9, 单轮页面总量, 0=不限), failure_threshold(3), failure_cooldown("12H"), allow_window(""), unknown_policy(hr|not-hr), verified_ttl(留空=跟随站点 refresh_interval), index_retention("30D"), max_download_retries(3), channel_silence_warn("6H"), shared_dir(""), lock_timeout("0S"), poll_interval("1M"), parse_missing_rate_max(0.5), channel{enabled, port(8788), token, extension_id(""), request_timeout("180S")}}`。❗`allow_window` 与 `notify.quiet_hours` **语义相反**(那个是「该时段不发」, 本项是「仅该时段取数」); `unknown_policy`/`verified_ttl` 调松等于自愿放大漏管窗口。**取数通道(M2 已落地)**: 端点仅听 `127.0.0.1`, 无 token ⇒ 401 **且不写任何状态**; 同机多实例 `channel.port` 必须错开(被占 = 启动即报错); `shared_dir` 与 `channel` 是 hr_check 里**仅有的两个 L1 字段**(需重挂端点/重建服务), 其余全 L0(站点接入 `sites` 也是 L0)。**站点接入(26-09-27-1318 收敛; 绑定改映射制见 26-09-27-1930)**: `sites` 子段是站点启用与微调的唯一配置源, 见下方「hr_check.sites」节; 旧键 `trackers.<站点>.hr_check` 已随 config schema v2 废除(迁移链一次性改写, 无常驻兼容层)。设置页「HR 在线核实」分组 |
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
| `hr` | | `{required_seeding_time(必填), required_share_ratio(0), extra_seeding_time("0H"), condition("80%"或"10MiB")}` + 覆盖全局的输出字段 + 排除表 `exclude_tags`/`exclude_categories`(与全局并集, 26-09-28-1805) |
| `hr_check` | | **旧键(已废除, 26-09-27-1930)**: 站点级在线核实的唯一入口是 `hr_check.sites.<档案 id>`。本键不再被任何代码接受 —— 加载时由 schema 迁移链 **config v1→v2**(单点 `config/migrations.py`)一次性改写: mode=off/非字典直接删除; mode != off 时按 `hr_page_url` 的 host(web 命名空间)定位档案, mode 与微调项搬入新位置(页面事实四键 adapter/hr_page_url/download_path/page_param 丢弃, 值一律以档案为准), 旧键删除; host 定位不到档案则旧键原地保留, 校验报废除错。迁移语义与 `hr_check.sites` 键集见下节 |
| `rules` | | `["@规则集", "@规则集.规则"]`。**留空 = 该站点不执行任何规则**(无任何隐式回退; `_rules_for_torrent` 直接返回空列表) |
| `groups` | | 站点分组列表 (可多个, 自由命名无需预定义); 配置层声明不写种子; 供规则 `tracker_group` 条件按分组筛选 (2026-09-15) |
| `remove_similar_tags` | | 覆盖全局 |

## hr_check.sites 站点接入(26-09-27-1318 REV2)

站点启用与微调的唯一配置源; 键 = 内置站点档案 id(单点: `src/auto_qb/config/site_presets.py`, 首发两档):

| 档案 id | adapter | web 域(仅派生 HR 页) | announce 域(默认映射查表键) | HR 页 | 种子下载 | 翻页参数 |
|---|---|---|---|---|---|---|
| `btschool` | `nexusphp` | `pt.btschool.club` | `pt.btschool.club` | `/myhr.php` | `/download.php?id={id}` | `page` |
| `carpt` | `carpt` | `carpt.net` | `tracker.carpt.net` | `/myhr.php` | `/download.php?id={id}` | `page` |

条目键集: `mode(off|partial|all)` + 显式映射 `tracker(留空=默认映射; 非空=按 trackers 条目名直取)` + 微调项 `hr_page_scopes([A,B,C]) / refresh_interval("12H") / max_pages_per_refresh(5) / completed_age_limit(0=关闭; 开启时 1D~3650D) / accept_empty_listing(false; 人工确认口子——清单连续 3 轮为 0 且结构完好时的空清单接受开关) / auto_age_limit(false; 豁免 A——用反算考核期 P 作豁免线, P 一致性机检不过即禁用) / seeding_exempt_ratio(0=关闭; 豁免 B——本地做种时长 ≥ 要求时长 × 倍数即豁免, 建议 5) / quota_model(legacy|split; 激活门——split 才启用页面/下载双令牌桶) / page_rate_per_hour(留空=回退全局) / torrent_rate_per_hour(留空=回退全局, 再回落 max_torrents_per_hour) / max_torrents_per_hour(留空=回退全局)`。超龄豁免语义不变(见上一节 `hr_check` 旧键行内的说明)。

- **绑定 = 映射(26-09-27-1930)**: web 域与 announce 域是两个命名空间, **永不互相比对**。每个 mode != off 的条目按「显式直取 > 默认查表」解析: 条目 `tracker` 非空 -> 按 trackers 条目名直取; 为空 -> 档案已知 announce 域(`tracker_domain`)在同命名空间(用户 `domains`)查表, 双向子域容错(`t == d or t.endswith("." + d) or d.endswith("." + t)`, 单点 `site_presets.match_trackers`), 恰好 1 个命中即自动绑定(**用户零配置**, CarPT 只配 announce 域也能绑)。HR 页地址恒为 `https://{档案 web_domain}{page_path}`, 与用户 domains 写法无关。派生结果写入 `TrackerConfig.hr_check`(绑定结果视图, `tracker` 字段回填解析出的条目名), 下游 service/channel/parse 零感知。
- **配置期 fail-fast**: 未登记档案 id(报错+已支持清单) / 默认映射零命中(附档案 announce 域与两条出路) / 默认映射 >=2 命中歧义 / 显式 `tracker` 键不存在 / 同一 tracker 被两个条目绑定 / 绑定站点缺 `hr` 段 / `hr_page_scopes` 不含 A+B+C。

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

见 [rule-system.md](../rule-system.md)。规则级键: `enabled`/`interval`/`trigger`/`watch_fields`/`execute_once`/`cooldown`/`conditions`/`actions`/`stop_following_rules_if`。`trigger` 默认 `interval` (周期轮询), 事件 trigger 见 04 触发时机表与 09 规划。

**`trigger: on_torrent_field_changed` (第五种触发时机, 计划 26-09-27-1438)**: 指定字段变化时才检查该规则, 替代"interval 轮询 + 条件判断"。配套键 `watch_fields`(必填, 仅该 trigger 下允许, 校验期 fail-fast): 非空列表, v1 取值限 `tags`/`category`(state 有专属 trigger, `amount_left` 高频噪音)。语义: 外部(人工/其它工具)改动种子 tags/category → 下一轮 sync 内触发且仅触发一次(与持久化基线对比出净变化, tags 排序后比较消除 qB 顺序噪声); 程序自身 add_tags/remove_tags/set_category **不自触发**(self-caused 抑制, 单点在 store.update_torrent_fields: 上报值与自写期望一致才按自写处理); 首见种子只落基线不触发; 重启后停机期变化首轮补捕(受 cooldown 约束); `cooldown`/`execute_once` 复用 exec_history 机制。跨轮基线持久化于 state 顶层 `field_snapshots`(state v2→v3, 仅存被监听字段; 无监听规则时零写入)。已知取舍: 同轮内外部变化与自写叠加值不可区分时按值判定; 自写后值被覆盖的场景按外部变化放行。

## 变量与匹配语法速查

- `regex:` 前缀 = 正则 (match_tag/match_path 用 re.search; conditions 的 tags/category/trackers 也用 search)
- `:ignore_case` 后缀 = 忽略大小写 (全项目统一支持: utils 的 tag/path 匹配与 conditions 的 tags/category/trackers/path 条件均生效; 语法解析唯一入口 utils.MatchPattern)
- `${required_seeding_time}` 变量 (标签/分类格式)
- `@tracker_tags` (delete_tags 中) = 展开为所有 tracker tags 并集
- Windows 路径用 `/` (`\` 是正则转义); 程序内部 `path_normalize` 统一为 `/`, 保留首尾斜杠

## 运行时文件

| 文件 | 性质 |
|------|------|
| `auto-qb-data/state.json` | ★ 生产状态 (gitignore, 位于数据目录 auto-qb-data/)。实测结构: 顶层 `schema_version`(升级链版本章, 当前 v3; 缺失=v1 存量口径由迁移链升级, 计划 26-09-26-0506); `exec_history = {"{rule}:{hash}": {ts, date, hour}}`; `auto_categories = {hash: category}`; `speed_limit_curve = {"YYYY-MM-DD": {upload_kib, download_kib, dry_run}}`; `skip_check_backup = {hash: {path, save_path, category, tags, ts}}` (跳检删除前备份的元数据, 重加成功后移除); `reannounce_ts = {hash: 上次reannounce时间戳}`; `recheck_fails = {hash: {date, count}}`(当日连续校验失败); `skip_check_day = {hash: "YYYY-MM-DD"}`(跨规则同日跳检去重); `field_snapshots = {hash: {tags: [排序后], category}}`(字段变化触发的跨轮基线, 计划 26-09-27-1438, 仅存被监听字段; 无监听规则时恒空表零写入)。历史键 `upload_snapshots` 已在 v2 迁移清除(计划 26-09-27-1232), v2→v3 补空 `field_snapshots` |
| `auto-qb-data/state.lock` / `state.lock.meta.json` | 单实例锁及伴生 meta (由 state_file 派生: 去扩展名 + `.lock`, meta 再加 `.meta.json`) |
| `auto-qb-data/logs/auto-qb.log` | RotatingFileHandler, maxBytes 按 `log.max_bytes`, 5 备份 (log.file 未配置时默认落盘此路径, 显式配 `log.file` 优先; setup_logging 自动建 logs/ 子目录) |
| `auto-qb-data/skip-check-backup/` | 跳检**删除前**落盘的 .torrent 备份 (由 dirname(state_file) 派生, 与状态同目录); 重加确认成功后由 `_clear_backup` 删除, 只有重加失败 / 缝隙内崩溃才会留下 |
| `auto-qb-data/config.yml.bak` | 配置保存前的自动备份(路径由 `web.py` 传入 `write_tree`, 落在 data_dir 下, **不再**在项目根目录生成; 父目录不存在时自动创建) |
| `torrents.txt` | `--export-torrents_info` 的调试输出 |

## 测试配置样例

`test_yamls/` 下有运行用测试配置 (`test_up_dl_limit_tracker.yml`, `test_actions/` 目录等); `test.yml`/`minimal.yml` 是手工/最小样例。调试入口见 `.vscode/launch.json` (4 个配置: 正常运行/dry-run/导出/测试限速配置)。
