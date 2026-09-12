<div align="center">

# auto-qb

**基于 qBittorrent WebUI API 的 PT 种子自动化管理工具**

[![Python](https://img.shields.io/badge/python-3.12+-blue?logo=python&logoColor=white)](https://www.python.org/) [![License](https://img.shields.io/badge/license-Apache%202.0-green)](https://www.apache.org/licenses/LICENSE-2.0)
[![Status](https://img.shields.io/badge/status-alpha%20%F0%9F%9A%A7-orange)]() [![CI](https://img.shields.io/github/actions/workflow/status/ABackerNINI/auto-qb/ci.yml?branch=develop&label=CI)](https://github.com/ABackerNINI/auto-qb/actions/workflows/ci.yml)

标签 / 分类 / HR 管理 · 辅种分组与缺文件保护 · 自定义规则引擎 · 多级限速 · 校验 / 跳检 · 主动通知 · 托盘常驻

</div>

---

auto-qb 是一个常驻后台运行的 Python 程序，每 2 秒一个 tick，通过 qBittorrent WebUI API 自动帮你打理 PT 种子：

- **省心保种** — 自动打站点标签、跟踪 HR（Hit & Run）触发与达标状态，做种时长满足要求后自动标记
- **辅种安全** — 把指向相同文件的种子自动归组，缺文件 / 大小不一致 / 下载冲突时**整组暂停**，防止误传垃圾数据被站点封号
- **灵活自动化** — 15 种筛选条件 × 11 种动作自由组合成规则，触发时机、去重冷却、错误处理一应俱全
- **智能限速** — tracker 级单种限速 + 规则动作限速 + 读取流量统计的全局限速曲线，到量自动降速
- **安全第一** — 高风险动作（跳检、强制汇报、移动）默认关闭；提供 `--dry-run` 试运行；启动时全量校验配置

> 🚧 **施工中**：项目功能已实现并带有完整测试（621 个用例），但尚未经过大规模实机验证。标记 🚧 的功能尤其请先用 `--dry-run` 观察，谨慎在生产环境使用。

## 目录

- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [命令行参数](#命令行参数)
- [配置说明](#配置说明)
- [全局限速曲线](#全局限速曲线)
- [规则系统](#规则系统)
- [架构与设计原则](#架构与设计原则)
- [开发测试](#开发测试)
- [免责声明与许可证](#免责声明与许可证)

## 功能特性

### 🏷️ 标签 / 分类管理

- 按 tracker 自动添加 / 删除站点标签，自动清理相似标签（单词相同、大小写不同）
- 彻底删除标签 `delete_tags`，或仅在无种子使用时删除 `delete_tags_if_has_no_torrents`（均支持正则与 `@tracker_tags` 引用）
- 新种子自动打**集数标签**：从文件列表解析集数，如 `EP01.mkv`～`EP05.mkv` → `zE1-5`；多集不连续则视为不可靠、放弃打标

### ⏱️ HR 管理

- 满足 HR 触发条件（下载比例 / 下载量）时自动加 HR 标签或分类，如 `!!HR3D!!`
- 做种时长达到「要求时间 + 额外时间」后自动加达标标签 / 分类，如 `--HR3D--`
- 标签格式支持变量，站点配置可覆盖全局配置

### 👯 辅种管理（种子分组）

- 将指向**相同文件列表**的种子（辅种）自动归为一组，并检查组内文件大小一致性（不一致 → 警告 + 整组暂停）
- **缺文件检查**：组内种子被删除、由上传转暂停、重新校验发现文件缺失（种子进入错误状态）、或保存路径变化时立即触发磁盘扫描；文件丢失 → 整组暂停 + `MISSING` 标签
- 组内多个种子同时下载、或已完成与下载中并存 → 警告 + 整组暂停 🚧（已带 `MISSING` 标签的完成成员不计入"已完成"——已知缺文件的组允许重新下载补救；多个种子同时下载仍拦截）

### 🐢 限速

- tracker 配置内置单种限速字段，种子添加即生效
- 规则动作支持单种上传 / 下载限速
- **全局限速曲线**：根据每天 / 每N天 / 每月的上传下载总量自动调整总限速（见 [全局限速曲线](#全局限速曲线)）
- 限速不覆盖奇数 KiB/s 值——手动设置且不希望被覆盖的限速可设为单数（如 `2001 KiB/s`）

### 🧩 自定义规则引擎 🚧

- 触发时机 + 筛选条件 + 动作，动作顺序执行，支持去重、冷却与错误处理（见 [规则系统](#规则系统)）
- **15 种条件 × 11 种动作**，全部可自由组合

### 🛡️ 运行时保障

- 主循环 2s tick、单任务队列驱动，各任务互不干扰、各自带独立 interval
- 状态持久化到数据目录（规则历史 / 上传量快照 / 自动分类 / 限速状态 / 跳检备份元数据），重启续跑
- 启动时 **fail-fast** 全量校验配置（未知键、非法格式、非法 HR 规则一次性聚合报错）
- 单实例锁，防止同一配置多开互相竞争
- **主动通知**：程序出错 / 危险情况（缺文件、下载冲突、跳检失败等）时推送**平台原生通知**（Windows 原生 toast / Linux / macOS，零第三方依赖）；免打扰时段 + 频率节流防打扰，全屏等繁忙场景由系统专注助手自动静默
- **托盘常驻**（`--tray`）：系统托盘图标运行，深色状态窗口（种子数 / 运行时长 / 最近日志）；运行时**暂停 / 恢复自动管理**、**通知热切换**、**开机自启**开关；重复启动自动唤起已运行实例的窗口；跨平台（Windows / Linux / macOS）
- 从已有种子的 tracker 一键导出 YAML 配置模板

## 快速开始

### 环境要求

- Python 3.12+
- qBittorrent（已开启 Web UI；已在 qB 5.2.3 测试，其他版本待测）

### 1. 安装

```bash
# 下载 / 克隆源码后，进入项目目录
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# 安装运行依赖
pip install pyyaml qbittorrent-api filelock
```

### 2. 配置

编辑 `minimal.yml`，填入 qBittorrent 连接信息（见 [配置说明](#配置说明)）。

也可以连接 qBittorrent，根据**已有种子的 tracker 自动导出配置模板**（先在 `minimal.yml` 填好连接信息）：

```bash
# 读 minimal.yml 的连接信息, 把生成的模板写入 config.yml
# ⚠️ 注意: 该命令会写入(覆盖)指定的输出文件
python src/auto-qb.py minimal.yml --export-yaml config.yml
```

加 `--only-missing` 只导出尚未配置的 tracker，生成最小骨架，方便随时增补新站点（同样会覆盖输出文件）：

```bash
python src/auto-qb.py minimal.yml --export-yaml config.yml --only-missing
```

### 3. 运行

```bash
# 强烈建议第一次先试运行: 只打印将执行的动作，不实际改动客户端
python src/auto-qb.py --dry-run

# 确认无误后正式运行(默认读 config.yml)
python src/auto-qb.py

# 指定配置文件
python src/auto-qb.py my-config.yml
```

## 命令行参数

| 参数                         | 说明                                                   |
|------------------------------|--------------------------------------------------------|
| `config`                     | 配置文件路径，位置参数，默认 `config.yml`                |
| `--export-yaml`, `-e OUTPUT` | 导出 YAML 配置模板到 OUTPUT 后退出（不进入主循环）       |
| `--only-missing`             | 仅导出未配置的 tracker 站点（配合 `--export-yaml` 使用） |
| `--dry-run`, `-n`            | 试运行：打印将执行的动作，不实际调用客户端               |
| `--tray`                     | 托盘常驻模式：系统托盘图标 + 状态窗口；再次启动唤起已有实例窗口 |

## 配置说明

### 约定与注意事项

- 启动时 fail-fast 全量校验配置（未知键 / 必填项 / 格式 / 规则引用），全部错误聚合一次性报告；显式留空的键视为未配置、走默认值
- 标签 / 分类 / 路径匹配支持正则（`regex:` 前缀）与忽略大小写（`:ignore_case` 后缀）
- Windows 路径请用 `/` 作分隔符（`\` 在正则中是转义符）；路径匹配默认区分大小写
- 速度单位：`B/s` 或 `[KMG]iB/s`；文件大小单位：`B` 或 `[KMGT]iB`；时间单位：`S` 秒 / `M` 分 / `H` 时 / `D` 天（均不区分大小写）
- 以横杠"-"开头的配置可以同时有多个
- **运行时数据目录** `data_dir`（默认 `auto-qb-data/`）：状态文件、单实例锁、日志、跳检备份默认都存放在其下，多实例运行请为每个实例指定不同目录

### 配置示例

```yaml
---
config:
    # qBittorrent 客户端
    qbittorrent:
        host: 127.0.0.1
        port: 8080
        username: <USERNAME>
        password: <PASSWORD>

    # 运行时数据主目录: 状态/单实例锁/日志/跳检备份默认均存其下; 默认 auto-qb-data, 多实例请用不同路径
    data_dir: "auto-qb-data"

    # 主循环时间间隔
    main_tick: 2S
    # 每个循环最大执行任务数, 种子数多可适当增加
    max_tasks_per_tick: 50

    # 内置任务检查间隔(从上一轮处理结束开始计时，不叠加)
    interval: 60S

    # 日志设置(留空则默认落盘到 <data_dir>/logs/auto-qb.log)
    log:
        file: ""                 # 日志文件路径，默认 <data_dir>/logs/auto-qb.log
        level: INFO              # 日志等级
        max_bytes: 10MiB         # 日志轮转大小
        format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s" # 日志格式

    # 删除种子类似(单词相同大小写不同)的标签
    remove_similar_tags: true

    # 自动添加集数标签，仅种子添加时触发; 模板含 ${episode_first}/${episode_last} 占位,
    # 单集/多集分别配置，多集仅在集数连续时生成，不连续视为不可靠放弃添加
    add_episode_tags:
        enabled: true                                       # 启用自动添加集数标签
        add_tag_single: "zE${episode_first}"                # 单集标签格式
        add_tag_multi: "zE${episode_first}-${episode_last}" # 多集标签格式

    # 种子分组管理(辅种管理)
    grouping:
        enabled: true             # 启用种子分组
        check_missing_files: true # 启用缺文件检查
        missing_tag: MISSING      # 文件丢失时整组添加的标签

    # 主动通知: WARNING 及以上日志推送平台原生通知(默认关闭)
    notify:
        enabled: true             # 启用主动通知
        min_level: WARNING        # 通知最低日志级别: INFO / WARNING / ERROR
        quiet_hours: "23:00-08:00" # 免打扰时段(支持跨午夜)，时段内跳过发送；留空不启用
        max_per_hour: 20          # 每小时通知上限，超出丢弃(防风暴)
        dedup_window: 10M         # 相同通知的去重窗口，0 表示不去重

    # 全局自动彻底删除标签
    delete_tags:                        # 彻底删除的标签格式，支持正则
        - "M-Team - TP:ignore_case"
        - "regex:^BTSCHOOL$"
    delete_tags_if_has_no_torrents:     # 无种子使用时才删除
        - "@tracker_tags:ignore_case"   # 引用全部 tracker 配置的标签， 并忽略大小写
        - "regex:^zE.*$"                # 删除所有集数标签
        - "MISSING"                     # 删除缺失文件标签

    # 全局 HR 设置(可在 tracker 中单独配置 hr 覆盖全局设置)
    hr:
        add_tag: ''                                                     # 满足 HR 触发条件时添加的标签格式，支持变量: ${required_seeding_time} - 要求做种时长
        add_category: '!!HR${required_seeding_time}!!'                  # 满足 HR 触发条件时添加的分类格式，支持变量
        overwrite_category: false                                       # HR 触发条件时是否覆盖分类 (qb中一个种子只能有一个分类)
        add_tag_for_satisfied: ''                                       # 做种时长满足要求时添加的标签格式
        add_category_for_satisfied: '--HR${required_seeding_time}--'    # 做种时长满足要求时添加的分类格式
        overwrite_category_for_satisfied: false                         # 做种时长满足要求时是否覆盖分类

    # 跳检成功标签(全局统一, checking 动作不可按规则覆盖)
    # 带此标签的种子未经哈希校验, 查找参考种子时一律排除(防"未验证"经辅种参考链传播); 默认 zSkipChecked
    skip_checking_tag: zSkipChecked

    # 全局限速曲线配置 (需配置数据来源, 完整示例见[#全局限速曲线])
    # global_speed_limit_curve:

    # 自定义规则集 (名称以 "_rules" 结尾): 完整示例见[#规则系统])
    # example_rules:
    #     rule1: ...

    # tracker 站点配置 (建议先用 `--export-yaml missing.yml --only-missing` 导出后再改)
    trackers:
        tracker1:                                  # 自定义 tracker 站点名称
            domains:                               # 站点域名，可以有多个
                - domain1
                - domain2
            tags:                                  # 自动添加站点标签
                - tag1
                - tag2
            remove_tags:                           # 自动删除站点标签，支持正则
                - tag3
                - tag4
            upload_speed_limit: 1000KiB/s          # 单种上传限速，0 指无限制
            download_speed_limit: 10MiB/s          # 单种下载限速，0 指无限制
            hr:                                    # HR 规则(可覆盖全局设置)
                required_seeding_time: 3D          # 要求做种时间
                required_share_ratio: 2.0          # 要求分享率
                extra_seeding_time: 12H            # 额外做种时间防止意外
                condition: 80%                     # 触发 HR 的下载比例；也可用绝对值，如 10MiB
            # rules:                               # tracker 引用规则(完整示例见[#规则系统])
            #     - "@example_rules"               # 引用整个规则集
            #     - "@example_rules.rule1"         # 引用具体规则
        tracker2:
            # ...
```

## 全局限速曲线

> 目前本软件不支持监控设备全局流量，所以需配置外部流量数据来源。

根据流量数据来源记录的每日流量，按日 / N天 / 月等周期聚合，上传或下载量达到阈值后自动收紧 qB 全局限速；同一方向命中多条曲线时取**最严**限速。

```yaml
---
config:
    global_speed_limit_curve:
        interval: 10M
        traffic_source:
            - traffic_monitor: # Traffic Monitor: 流量监控软件，可记录每天使用流量
                dat_path: "D:/Programs/TrafficMonitor/history_traffic.dat" # 路径若需使用\，则请使用\\
            # 后续可能支持接入其它软件来源
        curves: # 每条 period 曲线为 curve 单项映射; 重复 period 拒绝
            - curve:
                period: DAY    # 周期，支持 DAY(当天)、MONTH(当月)、ND(最近N天)
                upload_curve:  # 由上传量阈值和对应速度组成，限制上传速度(阈值须严格递增)
                    - 10GiB:   # 上传量小于 10GiB 时，限制上传速度为 6MiB/s
                        upload_speed_limit: 6MiB/s
                    - 20GiB:   # 上传量大于等于 10GiB 且小于 20GiB 时，限制上传速度为 5MiB/s
                        upload_speed_limit: 5MiB/s
                    - 50GiB:   # ...
                        upload_speed_limit: 2MiB/s
                    - 100GiB:
                        upload_speed_limit: 1MiB/s
                download_curve: # 由下载量阈值和对应速度组成，限制下载速度(可省略 = 不管理该方向)
                    - 100GiB:   # 同理
                        download_speed_limit: 5MiB/s
                    - 200GiB:
                        download_speed_limit: 2MiB/s
            - curve: # 多条曲线同方向取最严限速(各 period 口径都需满足)
                period: 7D
                upload_curve:
                    - 50GiB:
                        upload_speed_limit: 4MiB/s
            # ... 可继续添加 MONTH / ND 等周期的 curve
```

### 流量数据来源：Traffic Monitor

[Traffic Monitor](https://github.com/zhongyang219/TrafficMonitor)（[Gitee 镜像](https://gitee.com/zhongyang219/TrafficMonitor)）是一款显示当前网速、CPU / 内存利用率的桌面悬浮窗软件。可以记录每天的上传 / 下载流量，建议开启开机自启，以便持续记录流量。

> **如何找到数据文件路径？** 常规设置 → 配置和数据文件 → 打开配置文件所在目录。其中 `history_traffic.dat` 记录了每天的上传 / 下载流量历史，格式如下：

```text
lines: "30"
2026/09/04 64033621/104743685
2026/09/03 23295975/37857445
2026/09/02 23243979/53483350
...
```

> 希望接入其它流量监控软件可提Issue。

## 规则系统

规则集名称以 `_rules` 结尾，挂在 `config` 段下；tracker 通过 `rules` 引用（`@规则集` 引用整组，`@规则集.规则名` 引用单条）。

```yaml
---
config:
    example_rules: # 🚧
        rule1:
            enabled: true
            trigger: interval                      # 触发时机: 固定时间间隔循环 🚧
            interval: 60S                          # 执行间隔
            execute_once: never                    # 去重: never/once/daily/hourly 🚧
            cooldown: 0S                           # 距上次执行成功不足该时长则跳过 🚧
            conditions:                            # 筛选条件必须全部满足
                - path: /path/to/file              # 路径，支持正则
                - size: ">=100MiB"                 # 文件大小
                - tags:                            # 标签(不同标签组之间为或)
                    - tag1,tag2
                - category:                        # 分类
                    - category
                - trackers:                        # tracker 自定义名称(不同组之间为或) 🚧
                    - tracker1
                - state:                           # 语义化状态(不同组之间为或) 🚧
                    - is_complete&is_uploading     # 已完成且正在上传(& 连接)
                - hr: condition-met                # condition-met/condition-not-met/satisfied 🚧
                - date_time:                       # 当前时间 🚧
                    day_of_month: 1-31
                    day_of_week: 1-7
                    time: 10:00-23:00
                - seedtime: "<24H"                 # 做种时长 🚧
                - upload_ratio: ">1.5"             # 上传比率 🚧
                - upload_size: ">10GiB"            # 总上传大小 🚧
                - upload_size_today: ">10GiB"      # 今日上传大小 🚧
                - upload_size_this_week: ">10GiB"  # 本周上传大小 🚧
                - upload_size_this_month: ">10GiB" # 本月上传大小 🚧
                - freespace:                       # 剩余空间 🚧
                    path: "R:/"
                    amount: "<100GiB"
            actions:                               # 动作顺序执行，默认一个出错后续不执行
                - checking:                        # ⚠️ 校验/跳检(见下方 checking 动作说明) 🚧
                    basic_check: filelist          # filelist/piecehashes/custom
                    with_reference:                # 有参考种子(已完成的同组种子)
                        enabled: true              # 启用
                        mode: skip-checking        # skip-checking 跳检(风险可控)/full-checking 全量校验
                        auto_start: true           # 校验成功后自动开始
                    without_reference:             # 无参考种子
                        enabled: true              # 启用
                        mode: full-checking        # full-checking 安全；skip-checking 高风险
                        auto_start: true           # 校验成功后自动开始
                - start: true                      # 开始
                - stop: true                       # 暂停
                - ignore_next_action_error: true   # 忽略下一个动作的错误继续执行 🚧
                - add_tags:                        # 添加标签，支持变量
                    - tag-format1
                - remove_tags:                     # 删除标签，支持正则和变量
                    - tag-format3
                - add_category:                    # 添加分类
                    format: category-format
                    overwrite: true                # 强制覆盖已有分类
                - remove_category: true            # 自动删除站点分类
                - move_to:                         # ⚠️ 移动保存路径 🚧
                    path: /path/to/move/to
                    overwrite: true
                - reannounce: true                 # ⚠️ 强制汇报 tracker(有风险) 🚧
                - upload_speed_limit: 1000KiB/s    # 上传速度，不覆盖单数值
                - download_speed_limit: 1000KiB/s  # 下载速度，不覆盖单数值
            # 可选: conditions-met / conditions-not-met / action-failed /
            #       all-actions-succeed / always / never
            stop_following_rules_if: conditions-met # 🚧
    trackers:
        tracker1:
            domains:
                - domain1
            rules:                                 # tracker 引用规则
                - "@example_rules"                 # 引用整个规则集
                - "@example_rules.rule1"           # 引用具体规则
```

### 触发时机

| 触发时机                                  | 状态      | 说明                   |
|-------------------------------------------|-----------|------------------------|
| `interval`                                | ✅ 已实现  | 固定时间间隔循环一次   |
| `on_torrent_state_changed`                | 🚧 规划中 | 种子状态发生变化时触发 |
| `on_torrent_added` / `on_torrent_deleted` | 🚧 规划中 | 种子添加 / 删除时触发  |

### 筛选条件（15 种）

| 条件                     | 说明                                                                                      |
|--------------------------|-------------------------------------------------------------------------------------------|
| `path`                   | 保存路径，支持正则，使用 `/` 分隔符                                                         |
| `size`                   | 文件大小限制，支持比较符 `> < >= <=`                                                       |
| `tags`                   | 标签，不同标签组之间为或关系，支持正则和 `${required_seeding_time}` 变量                    |
| `category`               | 分类，支持正则和变量                                                                       |
| `trackers`               | tracker 自定义名称，不同组之间为或关系，支持正则                                            |
| `state`                  | 语义化状态（见[状态映射表](#状态映射表)），支持 `&` 连接多个状态                             |
| `hr`                     | HR 筛选：`condition-met`（满足触发）/ `condition-not-met` / `satisfied`（满足要求 + 额外时长） |
| `date_time`              | 日期时间：`day_of_month` / `day_of_week` / `time`                                          |
| `seedtime`               | 做种时长                                                                                  |
| `upload_ratio`           | 上传比率                                                                                  |
| `upload_size`            | 总上传大小                                                                                |
| `upload_size_today`      | 今日上传大小：基于状态文件按自然日增量统计，同一天多次运行有效                              |
| `upload_size_this_week`  | 本周上传大小                                                                              |
| `upload_size_this_month` | 本月上传大小                                                                              |
| `freespace`              | 指定路径剩余空间                                                                          |

### 动作（11 种）

| 动作                                          | 说明                                                                                       |
|-----------------------------------------------|--------------------------------------------------------------------------------------------|
| `checking`                                    | 校验 / 跳检：skip-checking (⚠️ __<font color="red">有风险!</font>__) 或 full-checking（安全） |
| `start` / `stop`                              | 开始 / 暂停种子                                                                            |
| `add_tags` / `remove_tags`                    | 添加 / 删除标签，支持正则和变量                                                             |
| `add_category` / `remove_category`            | 设置 / 清空分类，支持强制覆盖                                                               |
| `move_to`                                     | 移动保存路径                                                                               |
| `reannounce`                                  | 强制汇报 tracker (⚠️ __<font color="red">有风险!</font>__)                                 |
| `upload_speed_limit` / `download_speed_limit` | 单种上传 / 下载限速 （⚠️ 注意上传限速过低有风险）                                            |
| `ignore_next_action_error`                    | 忽略下一个动作的错误继续执行（仅对下一个动作起效）                                           |

### 去重与一次执行

- 规则默认 `execute_once: never`，只适合幂等动作（加 / 删标签、设分类）
- 非幂等动作（校验、开始、强制汇报、限速）**必须**配置 `execute_once` 或 `cooldown`，否则会在条件成立期间反复触发
- `execute_once` 取值：`never` / `once`（每种子仅一次）/ `daily`（每种子每天最多一次）/ `hourly`（每种子每小时最多一次）
- `cooldown` 可覆盖 `execute_once` 粒度，如 `execute_once: never` + `cooldown: 10M`
- 执行历史记录在状态文件，键为 `规则名 + 种子 hash + 时间窗口(日/小时)`；`daily` 按自然日切换，与 `upload_size_today` 口径一致
- 跳检另有独立兜底：跨规则同日去重（同一种子当日只跳检一次）+ full-checking 连续失败 3 次当日冷却（防损坏文件 recheck 死循环，次日重置）+ reannounce 运行时最小间隔 10M（不依赖规则去重）

### 动作结果与错误处理

- 每个动作返回统一结果：`success` / `failed` / `skipped`
- `failed`：qB API 返回非 200 或抛异常；`skipped`：条件不满足（如标签已存在、分类已设置），**不算失败**
- `stop_following_rules_if: action-failed` 只对 `failed` 生效，`skipped` 不影响
- `ignore_next_action_error` 只对下一个动作生效，忽略 `failed` 继续执行

### 状态映射表

规则条件里的 `state` 是语义化状态，直接用 qB `TorrentState` 枚举属性判定（`is_checking` / `is_downloading` / `is_complete` / `is_uploading` / `is_errored` / `is_stopped`），与 qB 官方语义一致：

| 状态             | 覆盖的 qB state                                                                                   | 说明                         |
|------------------|---------------------------------------------------------------------------------------------------|------------------------------|
| `is_checking`    | checkingDL, checkingUP, checkingResumeData                                                        | 正在校验                     |
| `is_downloading` | downloading, forcedDL, metaDL, forcedMetaDL, checkingDL, queuedDL, stalledDL, pausedDL, stoppedDL | 下载中（含暂停 / 排队 / 校验） |
| `is_complete`    | uploading, stalledUP, pausedUP, forcedUP, queuedUP, stoppedUP, checkingUP                         | 已完成下载                   |
| `is_uploading`   | uploading, forcedUP, stalledUP, queuedUP, checkingUP                                              | 上传做种中                   |
| `is_errored`     | missingFiles, error                                                                               | 出错                         |
| `is_stopped`     | pausedDL, pausedUP, stoppedDL, stoppedUP                                                          | 已暂停 / 停止                |

`is_complete&is_uploading` 即"正在做种中"（含 queuedUP/checkingUP）。
注意 `downloading` 含 pausedDL/stoppedDL 等暂停下载状态；条件不支持 `!` 取反，需排除暂停下载时用 `is_stopped` 另行判断。

### `checking` 动作说明

- `basic_check` 决定如何从同组「已完成」的成员中确定**参考种子**：
  - `filelist`：分组已保证文件列表与大小一致，候选直接作为参考（最宽松）
  - `piecehashes`：额外调用 qB `torrents_piece_hashes` API 对比双方每个块的 hash 列表完全相同（不读取实际文件）；直接转种有效，重新制作且块大小不同的种子无效（较严格）
  - `custom`：运行外部程序判定（参数 `<候选hash> <保存路径>`，返回码 0 即视为参考，需配 `custom_basic_check_program_path`）
  - 此外，历史上 full-checking 通过的种子会记入内存参考集，同样可作参考（程序重启后重新积累）
- 确定参考后按段执行（`with_reference` / `without_reference` 两段均可独立 `enabled: false` 关闭）：
  - **有参考种子**：`full-checking` 为 qB 自带全量哈希校验 __<font color="green">安全</font>__；`skip-checking` 跳检 __<font color="orange">风险相对可控</font>__
  - **无参考种子**：`full-checking` __<font color="green">安全</font>__；`skip-checking` 为⚠️ __<font color="red">高风险</font>__（仅做基础文件存在与大小对比、不做哈希校验直接开始，文件内容错误会上传垃圾数据，被大部分 PT 站点严令禁止）

**配置组合风险对照表**

| 参考种子              | 模式            | 风险等级                                     | 说明                                                                                |
|-----------------------|-----------------|----------------------------------------------|-------------------------------------------------------------------------------------|
| 有(with_reference)    | `full-checking` | __<font color="green">安全</font>__          | qB 全量哈希校验，且同组已有完整种子佐证数据                                          |
| 有(with_reference)    | `skip-checking` | __<font color="orange">风险相对可控</font>__ | 文件内容有同组完整种子参照，跳过哈希但数据相对可信                                   |
| 无(without_reference) | `full-checking` | __<font color="green">安全</font>__          | qB 全量哈希校验，本身不依赖参考种子                                                  |
| 无(without_reference) | `skip-checking` | __<font color="red">高风险</font>__          | 仅文件存在与大小对比、无任何哈希校验，内容错误即上传垃圾数据，被大部分 PT 站点严令禁止 |

> 「有参考」是否可靠取决于 `basic_check` 的严格度：`piecehashes`（块 hash 列表完全相同）严于 `filelist`（仅文件列表与大小一致）。判定越严格，「有参考 + skip-checking」的 <font color="orange">风险相对可控</font> 才越站得住脚；不确定时优先用 `full-checking`。

- **skip-checking 的机制与代价**：通过「导出种子 → **删除种子** → 重新导入时跳过哈希校验」四阶段实现，它可**保留**标签、分类、上传 / 下载限速、保存路径，但**丢失**下载量、上传量、做种时长、上传比率等**本地统计数据**（删除种子会清空 qB 本地统计，属固有代价），请务必谨慎使用。
  - 注意: 万一跳检时种子重加失败，会把种子备份到数据目录 `skip-check-backup/`，请自行手动恢复。
- 校验通过后的种子可成为同组其他种子的**参考种子**，让后续辅种走上面「有参考种子」的路径。
- **跳检打标与参考排除**（`skip_checking_tag`，默认 `zSkipChecked`）：跳检成功后自动给该种子打上标签，标记它**未经哈希校验**；此后查找参考种子时，凡带此标签的种子一律排除（即使它在内存参考集中）。这样可避免「未验证」的种子被当作可信参考、经辅种参考链把潜在的数据错误扩散到整组。标签名是全局配置 `config.skip_checking_tag`，对所有 checking 动作统一生效，不可按规则覆盖。
  - ⚠️ **修改标签名的风险**：标签打在种子上持久保存，而参考排除只认**当前配置**的标签名。更改全局标签名后：
    - 此前按旧标签打标的种子将**不再被排除**出参考种子——「未验证」的旧跳检种子会重新成为可信参考，数据错误可能经参考链扩散到整组；
    - 旧标签**不会自动移除**，仍残留在种子上；若日后改回旧名，这些种子又会重新被排除。
  - 建议：确需更换标签名时，先在 qB 中手动替换所有种子上的旧标签，再修改配置；并保持标签名长期稳定，避免频繁变更。

#### `checking` 安全保障

为防止误传垃圾数据被站点处罚，checking 动作在真正执行前会按顺序经过多道闸门，任一不满足即跳过或等待（均无副作用）：

**① 状态与分组门槛**

- 仅处理「暂停中且未完成」的种子（`is_stopped` 且 `progress < 1`）；已完成（`progress = 1`）或活跃中（下载 / 做种中）的种子直接跳过，避免已完成种子被反复校验
- 组内有种子正在下载 → 整组视为未完成，**不进行任何校验**（包括跳检）

**② 组内校验协同**

- 组内其它成员正在 full-checking → **让位等待**（组内共享同一物理文件，并行全量校验只是重复磁盘 I/O），待其完成后重走决策链；等待上限 2 小时，防止异常卡死
- 组内其它成员当日校验失败、且文件大小与本种子一致（即同一份物理数据）→ 校验结果必然相同，**直接跳过**（失败推断）

**③ 执行前文件复查**

- 分段确定后、真正校验前，再次确认文件全部存在且大小一致（分组虽已保证，仍强制复查一遍），不通过则跳过

**④ 跳检专属红线**（仅 skip-checking）

- **部分下载的种子禁止跳检**：`0 < progress < 1` 时 qB 预分配使文件尺寸等于完整尺寸，尺寸检查发现不了尚未下载的零块，跳检会把零块标记为有效并上传垃圾数据；**只有 `progress = 0`（全新辅种、数据完整）的种子才能跳检**，部分下载请改用 full-checking
- **跨规则同日去重**：同一种子当日最多跳检一次（跳检必然清空本地统计，重复跳检只有损失没有收益）

**⑤ full-checking 失败冷却**

- 同一种子当日连续校验失败 3 次后不再重试（防止损坏文件触发 recheck 死循环），次日自动重置

## 架构与设计原则

### 设计原则

- **幂等性**：所有动作重复执行不应产生副作用或重复操作；需要"每天一次"等窗口语义的动作必须依赖状态文件去重，而非循环频率
- **保守默认**：高风险动作（跳检、强制汇报、删除种子、覆盖限速）默认关闭，或只对显式允许的范围生效
- **状态持久化**：跨轮次状态（规则历史、上传量快照、脚本设置过的限速等）统一存入数据目录，程序重启后续跑
- **fail-fast**：启动时全量校验配置，尽早报错，不运行到一半才发现问题

### 架构要点

- **单任务队列**：所有功能都是带内置 interval 的任务，统一进时间优先堆（含校验结果轮询）。
- **插件框架**：条件 / 动作通过 `@register_condition` / `@register_action` 装饰器注册、按名称实例化，易于扩展
- **mixin 组合**：`QbManager(RuleEngineMixin, TagsMixin, CheckingMixin, GroupingMixin, TrackerMixin, SpeedCurveMixin)`，职责清晰
- **数据层**：`TorrentStore` 每 tick 全量快照 + 惰性缓存；`QbApi` Facade 封装客户端调用并在写操作后同步快照

```
src/auto_qb/
├── cli.py             # 命令行入口(argparse)
├── config/            # 配置包: models(数据模型)/validation(全量校验)/loaders(解析加载)
├── curves.py          # 全局限速曲线纯逻辑: dat 解析/period 聚合/档位计算
├── episodes.py        # 集数标签解析
├── exporter.py        # YAML 配置模板导出
├── locking.py         # 单实例锁(filelock)
├── logging.py         # 日志配置
├── qbmanager.py       # QbManager 主类: 主循环 2s tick，协调任务队列/规则/内置功能
├── qbapi.py           # qB API Facade: 封装客户端调用 + 写后同步 store 快照
├── taskqueue.py       # 单任务队列: 时间优先堆，所有任务统一调度
├── torrents.py        # 种子信息数据层: 全量快照+惰性缓存+分组索引
├── utils.py           # 通用工具(速度/时间/大小解析，标签/路径匹配)
├── mixins/            # QbManager 组合 mixins
│   ├── checking.py    # 文件存在与大小检查(checking 动作前置)
│   ├── grouping.py    # 种子分组管理(辅种管理)
│   ├── rule_engine.py # 规则加载/状态持久化/种子级规则任务
│   ├── speed_curve.py # 全局限速曲线: Traffic Monitor 流量 -> qB 全局限速
│   ├── tags.py        # 标签/分类/HR 辅助
│   └── tracker.py     # tracker 配置匹配(hostname 精确匹配)/单种限速
└── rules/             # 规则插件框架(装饰器注册)
    ├── actions/       # 11 种动作插件: basic/transfer/checking/full_checking/skip_checking
    ├── base.py        # Rule/BaseCondition/BaseAction/ActionResult
    ├── conditions.py  # 15 种条件插件
    └── registry.py    # 条件/动作插件注册表
```

## 开发测试

```bash
# 安装开发依赖
pip install pytest pytest-cov

# 运行全部测试(无需真实 qBittorrent，全部 Fake)
pytest tests -q

# 输出覆盖率
pytest --cov=src --cov-report=term-missing tests -q

# 生成 HTML 覆盖率报告
pytest --cov=src --cov-report=html tests/
```

- 测试基础设施见 `tests/helpers.py`（`FakeClient` / `FakeTorrent` / `FakeConfig`，无需真实 qBittorrent）
- 当前共 612 个测试用例

## 免责声明与许可证

本项目采用 [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)。

本项目仅供个人学习与交流使用。使用本工具产生的一切后果由使用者自行承担，请务必：

- 遵守各 PT 站点的规则，谨慎使用跳检、强制汇报等高风险功能
- 上线前先用 `--dry-run` 试运行确认行为符合预期
- 作者不对因使用本工具导致的账号处罚、数据损失等负责
