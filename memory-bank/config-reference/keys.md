# 全部配置键与语法速查

> 摘要: 顶层键、trackers 站点段、限速曲线段、流量图采样段、规则集段、变量与匹配语法、运行时文件、测试样例。
> 触发: 配置键, 配置项, trackers, 限速曲线, qb_traffic, 流量图, 流量采样, 规则集段, 变量替换, 匹配语法, 运行时文件, hr_check, HR 在线核实

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
| `schema_version` | `4` | 配置文件格式版本标记(升级链, 计划 26-09-26-0506): **文件格式标记, 非行为配置** —— 不进 `Config` dataclass; 当前版本单点 `infra/versioning.py` `CURRENT_VERSIONS["config"]=4`, WebUI 保存经 `config/writer.py` 盖章; 加载时缺失=v1, 落后则沿链迁移(内存); 磁盘由 `run()` 开头的启动物化单点改写到当前版本(版本号备份 `<名>.v<m>.bak` 后原子写, 计划 26-09-27-2252), WebUI 保存不做迁移 —— 提交树版本低于当前直接 400 指路刷新, 高于程序支持报 ConfigError; WebUI 保存/`--export-yaml` 自动盖章, 用户手编无需写。v4 = 站点级「显式空 = 覆盖为空」三态(report 26-10-03-0504 方案 B 阶段 1): 升级时 9 键作用域内的存量 `''` 由迁移移除并逐键打 WARNING |
| `log` | | `{file, level, max_bytes, format}`; `file` 未配置时默认 `<data_dir>/logs/auto-qb.log` 落盘 (显式配置优先; 留空/空串=未配置=默认落盘, 无法用空串表达仅控制台); RotatingFileHandler 5 备份 |
| `remove_similar_tags` | false | 全局默认, 站点可覆盖 |
| `maintenance_tag_mode` | `"interval"` | **维护 tags 节奏** (计划 26-09-27-1438): 站点 tags 维护(`_add_tags`/`_remove_tags`/`_remove_similar_tags`)的执行时机。`interval` = 每个内置任务间隔执行(默认 = 迁移前行为); `on_change` = 种子添加时执行一次, 之后仅当该种子 tags 被**程序之外**改动时重检(登记消费一次; 热重载 L2 后首轮全量收敛), 无变化轮跳过 —— 每轮每种子省一次 qB 读写往返。HR 标签/分类部分**不受影响**, 恒按周期执行(达标状态随时间演化, tags 变化捕捉不到)。取值限 `interval\|on_change` |
| `add_episode_tags` | `{enabled: false, add_tag_single: "zE${episode_first}", add_tag_multi: "zE${episode_first}-${episode_last}"}` | 种子添加时加集数标签; `enabled` 总开关; `add_tag_single`/`add_tag_multi` 模板, 含 `${episode_first}`/`${episode_last}` 占位, 多集仅在集数连续时生成 |
| `web` | 默认关闭 | `{enabled: bool, host: "127.0.0.1", port: 8080, token: "", skip_local_verify: false, skip_check_menu: false}`; WEB UI(辅种管理): 分组视图/组控制/**图形化配置编辑(每项可增删改 + 只读 YAML 预览)**; token 留空 = 首启随机生成持久化到 data_dir/web.token; host 默认仅本机(对外暴露需自行评估安全); `skip_local_verify=true` 时本机(loopback)访问 /api/* 免密钥鉴权直接进入, 对外暴露仍强制; `skip_check_menu=true` 时种子右键菜单(单选与多选)显示跳检项且 web 端点放行, 默认关闭 = 菜单不显示且端点拒绝(fail-closed), 规则源跳检不受影响(计划 26-10-02-1955 W1) |
| `notify` | 默认关闭 | `{enabled: bool, min_level: "ERROR", quiet_hours: "", max_per_hour: 20, dedup_window: "10M", channels: [platform]}`; 主动通知(ERROR 及以上日志 -> 平台原生通知, 零依赖; 26-09-27 等级整改后默认只推真正危险, WARNING 仅排障, 想看排障消息手动调低); quiet_hours "HH:MM-HH:MM" 支持跨午夜, 时段内跳过发送(含 ERROR); channels v1 仅 platform(缺省即启用); 节流为内存态不进 state_file |
| `grouping` | | `{enabled: bool, check_missing_files: bool, missing_tag: "MISSING", cross_group_conflict_check: false}`; `cross_group_conflict_check` = 跨组文件交叉检查(默认关, 开启后检测不同辅种组的文件指向同一磁盘物理文件, 警告并暂停涉事下载方) |
| `fs` | | 容器部署路径映射: `{path_map: [{from, to}]}`; 留空 = 现状, 改后需重启 |
| `delete_tags` | [] | 彻底删除的标签格式 (支持 `regex:`, `:ignore_case`, `@tracker_tags` 引用) |
| `delete_tags_if_has_no_torrents` | [] | 仅无种子使用时删除 |
| `hr` | | 全局 HR 输出设置 (`add_tag`/`add_category`/`overwrite_category`/`add_tag_for_satisfied`/`add_category_for_satisfied`/`overwrite_category_for_satisfied`) + 排除表 `exclude_tags`/`exclude_categories`: 命中种子不纳入 HR 体系(不打标/不核实/规则按未触发, 压过 mode=all 等一切管束), 判定时现算, 不回撤存量, 与站点段并集(26-09-28-1805); 默认分类格式 `!!HR${required_seeding_time}!!` / `--HR${required_seeding_time}--`。站点覆盖链: 站点 `hr` 段对应键优先, 未配置回退本段; v4 起站点段 4 个 str 键(`add_tag`/`add_category`/`add_tag_for_satisfied`/`add_category_for_satisfied`)显式空串 = 「覆盖为空」(如本站不打标), 整键删除 = 跟随全局; **本段(全局)同名键的空串语义仍是「使用默认值」**(加载时剥掉) |
| `skip_checking_tag` | `"zSkipChecked"` | 跳检成功标签全局名; 带此标签的种子未经哈希校验, `_find_reference` 一律排除 (防"未验证"经参考链传播)。全局统一, **checking 动作 spec 不可配置同名键** (校验报未知键), 动作运行时经 ctx 读取; YAML 留空/空串被 `_strip_none` 视为未配置走默认 (与 log.file 同约定) |
| `hr_check` | 默认关闭 | **HR 在线核实** (v3 波次模型, 计划 26-09-28-1932 §6.1 + 26-09-30-0240 三参数解耦, 全局 7 键): `{enabled(false), min_interval("90S"; 相邻请求最小间隔, 页面+.torrent 统一, 抖动只向上 +0~25%), max_requests_per_day(240; 站点级日额保险, 全部请求合计, 零点重置), max_pages_per_wave(30; 单波页数上限安全阀, 到顶该档截断), allow_window(""), shared_dir(""), reuse_window("2H"; 数据复用窗 —— 波后窗内直接复用不取数, 生效=min(本值, 拉取间隔)), channel{enabled, port(8788), token, extension_id(""), request_timeout("180S")}, sites{...}}`。判定语义硬编码(四行判定表: 命中考察中→管束 / 终态档 B·C·D 与移出未列出→放行(永续) / 无证据→本地兜底: 达标放行·未达标管束), **无撤退路径配置**。❗`allow_window` 与 `notify.quiet_hours` **语义相反**(那个是「该时段不发」, 本项是「仅该时段取数」)。旧 v2 键 26 个(min_torrent_interval/max_torrents_per_hour/failure_*/unknown_policy/verified_ttl/quota_model 双桶六键/poll_interval 等)已随 **config v2→v3 迁移**删除或常量化; `shared_dir` 与 `channel` 是仅有的两个 L1 字段(需重挂端点/重建服务), 其余全 L0。**取数通道**: 端点仅听 `127.0.0.1`, 无 token ⇒ 401 **且不写任何状态**; 同机多实例 `channel.port` 必须错开(被占 = 启动即报错)。人工对账戳: `--hr-confirm-empty <站点>`(清单为 0 的一次性确认, 非零行自动失效)。设置页「HR 在线核实」分组 |
| `global_speed_limit_curve` | 无=不启用 | 见下 |
| `qb_traffic` | 默认关闭 | 见下 |
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
| `hr` | | `{required_seeding_time(必填), required_share_ratio(0), extra_seeding_time("0H"), condition("80%"或"10MiB")}` + 覆盖全局的输出字段 + 排除表 `exclude_tags`/`exclude_categories`(与全局并集, 26-09-28-1805)。**v4 起输出字段 4 个 str 键(`add_tag`/`add_category`/`add_tag_for_satisfied`/`add_category_for_satisfied`)显式空串 = 「覆盖为空」**(如全局配了 `add_tag`, 本站写空串 = 本站不打标; 升级时存量的 `''` 由 v3→v4 迁移移除并打 WARNING, 需要该语义须重新显式配置), 整键删除 = 跟随全局; bool/list 键不在此列(`overwrite_*` 显式 false 本可表达覆盖, `exclude_*` 保持并集) |
| `hr_check` | | **旧键(已废除, 26-09-27-1930 起)**: 站点级在线核实的唯一入口是 `hr_check.sites.<档案 id>`。本键不再被任何代码接受 —— config v1→v2 迁移曾把它改写到新位置; **v3(config v2→v3)起出现即直接删除**(不再提供旧位置兼容)。站点接入键集见下节 |
| `rules` | | `["@规则集", "@规则集.规则"]`。**留空 = 该站点不执行任何规则**(无任何隐式回退; `_rules_for_torrent` 直接返回空列表) |
| `groups` | | 站点分组列表 (可多个, 自由命名无需预定义); 配置层声明不写种子; 供规则 `tracker_group` 条件按分组筛选 (2026-09-15) |
| `remove_similar_tags` | | 覆盖全局(站点显式 `false` = 本站关闭; 空串视为未配置走全局) |

## hr_check.sites 站点接入(26-09-27-1318 REV2 上收; v3 收敛 + 26-10-05-0555 增稳态降频键)

站点启用与微调的唯一配置源; 键 = 内置站点档案 id(单点: `src/auto_qb/config/site_presets.py`, 首发两档):

| 档案 id | adapter | web 域(仅派生 HR 页) | announce 域(默认映射查表键) | HR 页 | 种子下载 | 翻页参数 |
|---|---|---|---|---|---|---|
| `btschool` | `nexusphp` | `pt.btschool.club` | `pt.btschool.club` | `/myhr.php` | `/download.php?id={id}` | `page` |
| `carpt` | `carpt` | `carpt.net` | `tracker.carpt.net` | `/myhr.php` | `/download.php?id={id}` | `page` |

条目键集(v3, 计划 26-09-28-1932 §6.1 + 26-09-30-0240 改名 + 26-10-05-0555 S1 增稳态降频): `enabled(false; 启用即管, 无 mode 分叉)` + 显式映射 `tracker(留空=默认映射; 非空=按 trackers 条目名直取)` + `refresh_interval("12H"; 拉取间隔 —— 自上次健康波起每隔多久重新拉取, 失败档随下一轮自然重试; 点「立即拉取」可越过本闸, 频控仍生效)` + `idle_refresh_interval("24H"; 稳态拉取间隔 —— 本地无义务对象(对账对象集为空)时改用的对账节奏, 对象集一翻非空自动回退拉取间隔并下一轮立即拉取; 须 >= 拉取间隔, 相等 = 等效关闭降频; 校验期交叉校验拦 idle < refresh)`。页面事实(adapter/页面路径/下载路径/翻页参数/清单形态 listing)由内置站点档案填充, **任何配置位置都不再接受**; v2 的九个微调键(mode/hr_page_scopes/max_pages_per_refresh/completed_age_limit/accept_empty_listing/auto_age_limit/seeding_exempt_ratio/quota_model/page_rate_per_hour 等)已随 config v2→v3 迁移删除 —— partial/all 差异归档案 `listing` 字段(站点事实), 超额豁免以常量 SEED_EXEMPT_RATIO=3(做种 ≥ 3×要求+extra 免对账, 被动命中考察中仍管束), 空清单走 `--hr-confirm-empty` 人工对账戳。

- **绑定 = 映射(26-09-27-1930)**: web 域与 announce 域是两个命名空间, **永不互相比对**。每个 mode != off 的条目按「显式直取 > 默认查表」解析: 条目 `tracker` 非空 -> 按 trackers 条目名直取; 为空 -> 档案已知 announce 域(`tracker_domain`)在同命名空间(用户 `domains`)查表, 双向子域容错(`t == d or t.endswith("." + d) or d.endswith("." + t)`, 单点 `site_presets.match_trackers`), 恰好 1 个命中即自动绑定(**用户零配置**, CarPT 只配 announce 域也能绑)。HR 页地址恒为 `https://{档案 web_domain}{page_path}`, 与用户 domains 写法无关。派生结果写入 `TrackerConfig.hr_check`(绑定结果视图, `tracker` 字段回填解析出的条目名), 下游 service/channel/parse 零感知。
- **配置期 fail-fast**: 未登记档案 id(报错+已支持清单) / 默认映射零命中(附档案 announce 域与两条出路) / 默认映射 >=2 命中歧义 / 显式 `tracker` 键不存在 / 同一 tracker 被两个条目绑定 / 绑定站点缺 `hr` 段。

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

## qb_traffic 段 (qB 口径流量采样)

| 键 | 类型/默认 | 校验边界 | 说明 |
|----|-----------|----------|------|
| `enabled` | bool / `false` | — | 功能总开关; false(缺省) = 不建采样任务不建目录零文件(保守默认) |
| `sample_interval` | time / `30S` | >= `main_tick`, 上限 10M | 采样间隔(v3 计划 26-10-04-1957 §06.1: 下限硬校验 = `main_tick`, 从同一份 config 现取 —— 采样任务由主循环节拍驱动, 低于它加载期直接拒); 也是 raw 段视图(1m-24h)的曲线颗粒, 越小曲线越细但存储体量线性增长。非 `main_tick` 整数倍只是精度损耗(运行期告警), 校验不拒 |
| `flush_interval` | time / `10M` | 60S~1H, 整数秒 | 缓冲批量落盘周期(v3 新键, 计划 26-10-04-1957 §06.1): 采样点先入内存缓冲, 每过一个周期单次批量追加写盘; 越大写盘越少但崩溃丢失窗口越大(默认 10 分钟) |
| `raw_window` | time / `24H` | 1H~90D | 高分辨率保留窗: 逐点采样行(速率+累计)的保留时长, raw 段视图(1m-24h)从它取数, 超窗随小时封口裁剪 |
| `rollup_window` | time / `30D` | 7D~无上限 | 小时均值保留窗: 小时封口行(均值/峰值)的保留时长, hour 段视图(3d/7d/30d)从它取数; 也是已删种子文件的淘汰龄 |

整段缺省 = 未启用。启用后按 `sample_interval` 周期读内存快照采样(零新增 qB 请求): 全局系列恒采(qB 速度/累计), 单种系列仅采活跃种子(`dlspeed>0 or upspeed>0`; 空闲期不产 raw 点, 已有数据文件者记零值行程行(z 行, plan 26-10-04-0721 v2), 从未传输者无文件)。数据供 WEB UI 流量图(1m/5m/30m/3h/6h/12h/24h 对齐 qB 速度图 + 3d/7d/30d 共十视图, 2026-10-04)消费; 空闲在图上表现为 0 平线, 停机/断连/计数器重置表现为断线(null), 不补 0 不回填。

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
| `auto-qb-data/config.yml.bak` | 配置保存前的自动备份(路径由 `webui/server/routes/config.py` 传入 `write_tree`, 单点在 `webui/server/common.py` `config_backup_path`, 落在 data_dir 下, **不再**在项目根目录生成; 父目录不存在时自动创建) |
| `torrents.txt` | `--export-torrents_info` 的调试输出 |

## 测试配置样例

`test_yamls/` 下有运行用测试配置 (`test_up_dl_limit_tracker.yml`, `test_actions/` 目录等); `test.yml`/`minimal.yml` 是手工/最小样例。调试入口见 `.vscode/launch.json` (4 个配置: 正常运行/dry-run/导出/测试限速配置)。
