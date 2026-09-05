# auto-qb (🚧施工中)

> PT Seed Auto Manager for qBittorrent — 基于 [qbittorrent-api](https://pypi.org/project/qbittorrent-api/) 的 PT 种子自动化管理工具

<table>
<tr>
<td>语言</td><td>Python 3.12+</td>
<td>依赖</td><td>qbittorrent-api / PyYAML</td>
</tr>
</table>

自动管理 qBittorrent 的 PT 种子: 标签/分类与 HR 管理、辅种分组与缺文件检查、自定义规则引擎(筛选条件 + 动作)、tracker 级限速与校验/跳检、全局限速曲线。所有功能均可配置，高风险动作默认关闭，只对显式允许的范围生效。

## 目录

- [功能特性](#功能特性)
- [设计原则](#设计原则)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [规则系统](#规则系统)
- [目录结构](#目录结构)
- [开发测试](#开发测试)
- [许可证](#许可证)

## 功能特性

### 标签 / 分类管理

- 按 tracker 自动添加/删除站点标签，自动清理相似(单词相同大小写不同)标签
- 彻底删除标签(`delete_tags`)，仅在无种子使用时删除(`delete_tags_if_has_no_torrents`)
- 种子添加时自动添加集数标签: 从文件列表解析，如 `01.mkv~05.mkv` → `E1-5`

### HR 管理

- 满足 HR 触发条件(下载比例/下载量)时自动添加 HR 标签或分类，如 `!!HR3D!!`，格式可自定义
- 做种时间满足「要求时间 + 额外时间」后自动添加完成标签或分类，如 `--HR3D--`，格式可自定义
- 站点配置可覆盖全局配置

### 辅种管理(种子分组)

- 将指向相同文件列表的种子自动归为一组，组内文件大小一致性检查(不一致 → 警告 + 整组暂停)
- 缺文件检查: 组内种子被删除、或由上传转暂停、或保存路径变化时立即触发磁盘扫描(仅验证文件存在性与大小)；文件丢失 → 整组暂停 + `MISSING` 标签
- 组内多个种子同时下载、或已完成与下载中并存 → 警告 + 整组暂停

### 限速

- tracker 配置内置限速字段，种子添加时自动触发限速
- 规则动作支持单种上传/下载限速(`upload_speed_limit` / `download_speed_limit`)
- 可自定义全局限速曲线, 根据每天上传下载总量设置总限速(详见[全局限速曲线配置](#全局限速曲线配置))
- 限速不覆盖单数值，手动设置且不希望被覆盖的可以设置为单数比如: 2001 KiB/s

### 自定义规则 🚧

- 触发时机 + 筛选条件 + 动作，动作顺序执行，支持去重与错误处理(详见[规则系统](#规则系统))
- 条件 15 种、动作 11 种，全部可组合

### 其他

- 主循环 2s tick，任务队列驱动，任务互不干扰，各自带内置 interval
- 根据已有种子 tracker 导出 YAML 配置模板(`--export-yaml --only-missing`，只追加不重写)
- 状态持久化到 `state_file`(规则执行历史/上传量快照/自动分类记录/限速曲线状态/跳检备份元数据)，重启继续有效
- 启动时 fail-fast 全量校验配置(未知键、非法格式、非法 HR 规则) 🚧
- 单实例锁，防止 cron + 手动同时运行互相竞争 🚧

## 快速开始

### 环境要求

- Python 3.12+
- qBittorrent (Web UI 已开启， 已测试qb5.2.3， 其它版本待测试)

### 安装运行依赖

```bash
# 创建虚拟环境 (可跳过)
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# 安装依赖
pip install pyyaml qbittorrent-api filelock

# 开发依赖(可选)
pip install pytest pytest-cov
```

### 安装auto_qb

下载源码解压即可

### 配置

1. 编辑 `minimal.yml`，填入 qBittorrent 连接信息与规则(见[配置说明](#配置说明))。

2. 从现有种子导出模板:

```bash
python src/auto-qb.py minimal.yml --export-yaml config.yml
```

`--export-yaml` 会连接 qBittorrent，按已有种子的 tracker 生成配置模板(尽量保留已有配置不含注释)；加 `--only-missing` 只导出未配置的 tracker，生成最小骨架，方便随时添加新的 tracker。

### 运行

__python src/auto-qb.py [CONFIG] [--export-yaml， -e OUTPUT] [--only-missing] [--dry-run， -n]__

```bash
python src/auto-qb.py                # 使用默认 config.yml
python src/auto-qb.py my-config.yml  # 指定配置文件
python src/auto-qb.py -n             # dry-run: 只打印将执行的动作，不实际调用客户端
```

### 命令行参数

| 参数                       | 说明                                                |
|----------------------------|-----------------------------------------------------|
| `config`                   | 配置文件路径，默认 `config.yml`                      |
| `--export-yaml， -e OUTPUT` | 导出 YAML 配置模板到 OUTPUT 并退出                  |
| `--only-missing`           | 只导出未配置的 tracker 站点(需配合 `--export-yaml`) |
| `--dry-run， -n`            | 试运行，不实际修改客户端                             |

## 配置说明

### 注意事项

- 启动时 fail-fast 全量校验配置(未知键/必填项/格式/规则引用)，全部错误聚合一次性报告；显式留空的键视为未配置，使用默认值
- 标签/分类/路径匹配支持正则(`regex:` 前缀)与忽略大小写(`:ignore_case` 后缀)
- Windows 路径请使用 `/` 作为分隔符(`\` 在正则中用于转义)；路径匹配默认区分大小写
- 下载速度单位: `B/s` 或 `[KMG]iB/s`；文件大小单位: `B` 或 `[KMGT]iB`，不区分大小写
- 时间单位: `S` 秒、`M` 分、`H` 时、`D` 天，不区分大小写

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

    # 主循环时间间隔
    main_tick: 2S
    # 每个循环最大执行任务数
    max_tasks_per_tick: 20

    # 内置任务检查间隔(从上一轮处理结束开始计时，不叠加)
    interval: 60S

    # 状态持久化文件，必须可写, 注意多实例运行时请使用不同路径!
    state_file: "logs/auto-qb-state.json"

    # 日志设置
    log:
        file: "logs/auto-qb.log" # 日志文件路径， 留空仅输出控制台； 24/7运行建议落盘
        level: INFO              # 日志等级
        max_bytes: 10MiB         # 日志轮转大小
        format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s" # 日志格式

    # 删除种子类似(单词相同大小写不同)的标签
    remove_similar_tags: true

    # 自动添加集数标签(仅种子添加时触发; enabled=false 关闭, 模板含 ${episode_first}/${episode_last} 占位,
    # 单集/多集分别渲染, 多集仅在集数连续时生成, 不连续视为不可靠放弃添加)
    add_episode_tags:
        enabled: true
        add_tag_single: "zE${episode_first}"                # 单集标签格式
        add_tag_multi: "zE${episode_first}-${episode_last}" # 多集标签格式

    # 种子分组管理(辅种管理)
    grouping:
        enabled: true             # 启用种子分组
        check_missing_files: true # 启用缺文件检查
        missing_tag: MISSING      # 文件丢失时整组添加的标签

    # 全局自动彻底删除标签
    delete_tags:                     # 彻底删除的标签格式，支持正则
        - "M-Team - TP:ignore_case"
        - "regex:^BTSCHOOL$"
    delete_tags_if_has_no_torrents:  # 无种子使用时才删除
        - "@tracker_tags:ignore_case" # 引用全部 tracker 配置的标签， 并忽略大小写

    # 全局 HR 设置(站点 hr: 段未设置时兜底)
    hr:
        add_tag: '' # 满足 HR 触发条件时添加的标签格式，支持变量
        add_category: '!!HR${required_seeding_time}!!' # 满足 HR 触发条件时添加的分类格式，支持变量
        overwrite_category: false # HR 触发条件时是否覆盖分类 (qb中一个种子只能有一个分类)
        add_tag_for_satisfied: '' # 做种时长满足要求时添加的标签格式
        add_category_for_satisfied: '--HR${required_seeding_time}--' # 做种时长满足要求时添加的分类格式
        overwrite_category_for_satisfied: false # 做种时长满足要求时是否覆盖分类

    # 全局限速曲线配置 (需配置数据来源)
    global_speed_limit_curve: # 见下方[#全局限速配置]

    # 自定义规则集(名称以 "_rules" 结尾): 完整示例见下方[#自定义规则配置示例]
    # example_rules:
    #     rule1: ...

    # tracker 站点配置 (建议直接使用`python src/auto-qb.py --export-yaml missing.yml --only-missing`直接导出后修改)
    trackers:
        tracker1:                                  # 自定义 tracker 站点名称
            domains:                               # 站点域名，可以有多个
                - domain1
                - domain2
            tags:                                  # 自动添加站点标签
                - tag1
            remove_tags:                           # 自动删除站点标签，支持正则
                - tag3
            upload_speed_limit: 1000KiB/s          # 单种上传限速，0 指无限制
            download_speed_limit: 10MiB/s          # 单种下载限速，0 指无限制
            hr:                                    # HR 规则(可覆盖全局设置)
                required_seeding_time: 3D          # 要求做种时间
                required_share_ratio: 2.0          # 要求分享率
                extra_seeding_time: 12H            # 额外做种时间防止意外
                condition: 80%                     # 触发 HR 的下载比例；也可用绝对值，如 10MiB
            # rules:                               # tracker 引用规则(定义见下方[#自定义规则配置示例])
            #     - "@example_rules"               # 引用整个规则集
            #     - "@example_rules.rule1"         # 引用具体规则
        tracker2:
            # ...
```

### 全局限速曲线配置

```yaml
---
config:
    global_speed_limit_curve:
        interval: 10M
        traffic_source:
            - traffic_monitor: # Traffic Monitor: 流量监控软件，可记录每天使用流量
                bat_path: "D:/Programs/TrafficMonitor/history_traffic.dat" # 路径若需使用\，则请使用\\
            # 后续可能支持接入其它软件来源
        curves: # 每条 period 曲线为 curve 单项映射; 重复 period 拒绝
            - curve:
                period: DAY # 周期，支持DAY(1D)，MONTH，ND(最近N天)
                upload_curve: # 上传量达到指定值后，限制上传速度(阈值须严格递增)
                    - 10GiB:
                        upload_speed_limit: 6MiB/s
                    - 20GiB:
                        upload_speed_limit: 5MiB/s
                    - 30GiB:
                        upload_speed_limit: 4MiB/s
                    - 50GiB:
                        upload_speed_limit: 2MiB/s
                    - 100GiB:
                        upload_speed_limit: 1MiB/s
                    - 1000GiB:
                        upload_speed_limit: 0.5MiB/s
                download_curve: # 下载量达到指定值后，限制下载速度(可省略，省略 = 不管理该方向)
                    - 30GiB:
                        download_speed_limit: 11MiB/s
                    - 50GiB:
                        download_speed_limit: 10MiB/s
                    - 100GiB:
                        download_speed_limit: 5MiB/s
                    - 200GiB:
                        download_speed_limit: 2MiB/s
                    - 1000GiB:
                        download_speed_limit: 1MiB/s
            - curve: # 多条曲线同方向取最严限速(各 period 口径都需满足)
                period: 7D
                upload_curve:
                    - 50GiB:
                        upload_speed_limit: 4MiB/s
            # ... 可继续添加 MONTH / ND 等周期的 curve
```

#### 流量统计数据来源: Traffic Monitor

> 后续可能支持其它流量统计数据源

Traffic Monitor: 这是一个用于显示当前网速、CPU及内存利用率的桌面悬浮窗软件，并支持任务栏显示，支持更换皮肤。

[Traffic Monitor: GITHUB](https://github.com/zhongyang219/TrafficMonitor)
[Traffic Monitor: GITEE](https://gitee.com/zhongyang219/TrafficMonitor)

需要使用Traffic Monitor统计上传/下载流量的功能，建议开启开机自启动。

> Q: Traffic Monitor如何获得配置文件路径?
> A: 常规设置 - 配置和数据文件 - 打开配置文件所在目录

`history_traffic.dat`记录了每天上传下载流量历史

样例

```text
lines: "30"
2026/09/04 64033621/104743685
2026/09/03 23295975/37857445
2026/09/02 23243979/53483350
...
```

### 自定义规则配置示例

```yaml
---
config:
    # 自定义规则集(名称以 "_rules" 结尾)
    example_rules: # 🚧
        rule1:
            enabled: true
            trigger: interval                      # 触发时机: 固定时间间隔循环 🚧
            interval: 60S                          # 执行间隔
            execute_once: never                    # 去重: never/once/daily/hourly 🚧
            cooldown: 0S                           # 距上次执行成功不足该时长则跳过 🚧
            conditions:                            # 筛选条件必须全部满足
                - path: /path/to/file              # 路径，支持正则
                - size: ">=100MiB"                 # 文件大小 🚧
                - tags:                            # 标签(不同标签组之间为或)
                    - tag1,tag2
                - category:                        # 分类
                    - category
                - trackers:                        # tracker 自定义名称(不同组之间为或) 🚧
                    - tracker1
                - state:                           # 语义化状态(不同组之间为或) 🚧
                    - is_complete&is_uploading     # 已完成且正在上传(& 连接)
                - hr: condition-met                # condition-met/condition-not-met/satisfied 🚧
                - date_time:                       # 🚧
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
                - checking:                        # ⚠️ 校验/跳检(见下方[# `checking` 动作说明]) 🚧
                    basic_check: filelist          # filelist/piecehashes/custom
                    with_reference:                # 有参考种子(已完成同组种子)
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
                - download_speed_limit: 1000KiB/s  # 上传速度，不覆盖单数值
            # 可选: conditions-met / conditions-not-met / action-failed /
            #       all-actions-succeed / always / never
            stop_following_rules_if: conditions-met # 🚧
    trackers:
        tracker1:                                  # 自定义 tracker 站点名称
            domains:                               # 站点域名，可以有多个
                - domain1
            rules:                                 # tracker 引用规则
                - "@example_rules"                 # 引用整个规则集
                - "@example_rules.rule1"           # 引用具体规则
```

## 规则系统

### 触发时机

| 触发时机                                  | 状态      | 说明                   |
|-------------------------------------------|-----------|------------------------|
| `interval`                                | ✅ 已实现  | 固定时间间隔循环一次   |
| `on_torrent_state_changed`                | 🚧 规划中 | 种子状态发生变化时触发 |
| `on_torrent_added` / `on_torrent_deleted` | 🚧 规划中 | 种子添加/删除时触发    |

### 筛选条件(15 种)

| 条件                     | 说明                                                                                     |
|--------------------------|------------------------------------------------------------------------------------------|
| `path`                   | 保存路径，支持正则，使用 `/` 分隔符                                                        |
| `size`                   | 文件大小限制，支持比较符 `> < >= <=`                                                      |
| `tags`                   | 标签，不同标签组之间为或关系，支持正则和 `${required_seeding_time}` 变量                   |
| `category`               | 分类，支持正则和变量                                                                      |
| `trackers`               | tracker 自定义名称，不同组之间为或关系，支持正则                                           |
| `state`                  | 语义化状态(见状态映射表)，支持 `&` 连接多个状态                                           |
| `hr`                     | HR 筛选: `condition-met`(满足触发)/ `condition-not-met` / `satisfied`(满足要求+额外时长) |
| `date_time`              | 日期时间: `day_of_month` / `day_of_week` / `time`                                        |
| `seedtime`               | 做种时长                                                                                 |
| `upload_ratio`           | 上传比率                                                                                 |
| `upload_size`            | 总上传大小                                                                               |
| `upload_size_today`      | 今日上传大小: 基于 state_file 按自然日增量统计，同一天多次运行有效                        |
| `upload_size_this_week`  | 本周上传大小                                                                             |
| `upload_size_this_month` | 本月上传大小                                                                             |
| `freespace`              | 指定路径剩余空间                                                                         |

### 动作(11 种)

| 动作                                          | 说明                                                                                                          |
|-----------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| `checking`                                    | 校验/跳检: 确定参考种子后执行 skip-checking (__<font color="red">有风险!</font>__) 或 full-checking(异步校验) |
| `start` / `stop`                              | 开始 / 暂停种子                                                                                               |
| `add_tags` / `remove_tags`                    | 添加 / 删除标签，支持正则和变量                                                                                |
| `add_category` / `remove_category`            | 设置 / 清空分类，支持强制覆盖                                                                                  |
| `move_to`                                     | 移动保存路径                                                                                                  |
| `reannounce`                                  | 强制汇报 tracker(__<font color="red">有风险!</font>__)                                                        |
| `upload_speed_limit` / `download_speed_limit` | 单种上传 / 下载限速                                                                                           |
| `ignore_next_action_error`                    | 忽略下一个动作的错误继续执行(仅对下一个动作起效)                                                              |

### 去重与一次执行

- 规则默认 `execute_once: never`，只适合幂等动作(加/删标签、设分类)
- 非幂等动作(校验、开始、强制汇报、限速)必须配置 `execute_once` 或 `cooldown`，否则循环会在条件成立期间反复触发
- `execute_once` 可选: `never` / `once`(每种子只执行一次)/ `daily`(每种子每天最多一次)/ `hourly`(每种子每小时最多一次)
- `cooldown` 覆盖 `execute_once` 的粒度，如 `execute_once: never` + `cooldown: 10M`
- 执行历史记录在 `state_file`，键为 `规则名 + 种子 hash + 时间窗口(日/小时)`；`daily` 窗口按自然日切换，与 `upload_size_today` 统计口径一致
- 跳检另有独立兜底: 跨规则同日去重(同一种子当日只跳检一次) + full-checking 连续失败 3 次当日冷却(防损坏文件 recheck 死循环, 次日重置) + reannounce 运行时最小间隔 10M(不依赖规则去重)

### 动作结果与错误处理

- 每个动作返回统一结果: `success` / `failed` / `skipped`
- `failed`: qB API 返回非 200 或抛出异常；`skipped`:条件不满足(如标签已存在、分类已设置)，不算失败
- `stop_following_rules_if: action-failed` 只对 `failed` 生效，`skipped` 不影响
- `ignore_next_action_error` 只对下一个动作生效，忽略 `failed` 继续执行

### 状态映射表

规则条件里的 `state` 是语义化状态，直接用 qB `TorrentState` 枚举属性判定(`is_checking` /
`is_downloading` / `is_complete` / `is_uploading` / `is_errored` / `is_stopped`)，与 qB 官方语义一致:

| 状态             | 覆盖的 qB state                                                                                   | 说明                     |
|------------------|---------------------------------------------------------------------------------------------------|--------------------------|
| `is_checking`    | checkingDL， checkingUP， checkingResumeData                                                        | 正在校验                 |
| `is_downloading` | downloading， forcedDL， metaDL， forcedMetaDL， checkingDL， queuedDL， stalledDL， pausedDL， stoppedDL | 下载中(含暂停/排队/校验) |
| `is_complete`    | uploading， stalledUP， pausedUP， forcedUP， queuedUP， stoppedUP， checkingUP                         | 已完成下载               |
| `is_uploading`   | uploading， forcedUP， stalledUP， queuedUP， checkingUP                                              | 上传做种中               |
| `is_errored`     | missingFiles， error                                                                               | 出错                     |
| `is_stopped`     | pausedDL， pausedUP， stoppedDL， stoppedUP                                                          | 已暂停/停止              |

`is_complete&is_uploading` = "正在做种中"(含 queuedUP/checkingUP)。
注意 `downloading` 含 pausedDL/stoppedDL 等暂停下载状态；条件不支持 `!` 取反，需排除暂停下载时
用 `stopped` 条件另行判断。

### `checking` 动作说明

- `basic_check` 用于确定参考种子: `filelist` 对比两个种子的文件列表和文件大小(宽松)；`piecehashes` 额外对比两个种子每个块的 hash，不读取实际文件(对直接转种的种子有效，重新制作且块大小不同的种子无效)；`custom` 自定义程序
- **有参考种子**(组内有已完成、正在上传的同组种子): `full-checking` qb自带全量校验 __<font color="green">安全</font>__， `skip-checking` 跳检 __<font color="orange">风险相对可控</font>__
- **无参考种子**: `full-checking` __<font color="green">安全</font>__；`skip-checking` 为 __<font color="red">高风险</font>__ (仅做基础文件存在与大小对比，不做哈希校验直接开始，文件内容错误时会传垃圾数据，被大部分PT站点严令禁止)!
- 组内有种子正在下载 → 整组未完成，不进行任何校验(包括跳检)
- **只校验暂停中未完成的种子**(`is_paused` 且 `progress < 1`，如跨种添加后的 `pausedDL`)；已完成(`progress=1`)或活跃中(下载/做种中)的种子直接跳过，避免已完成种子被反复校验
- **部分下载的种子禁止跳检**: `progress` 在 0~1 之间时(如暂停的下载任务)，预分配使文件尺寸=完整尺寸，尺寸检查无法发现未下载的零块；skip-checking 会把全部块标记有效导致上传垃圾数据 —— 此时请改用 full-checking
- **跳检**: `skip-checking` 跳检是通过 "导出原种子 → 删除原种子 → 重新导入种子时选择跳过哈希校验" 的方法实现的，该方法可以保留种子的标签、分类、下载限速、上传限速、保存路径，但无法保留种子的下载量、上传量、做种时长、上传比率等统计数据，请务必谨慎使用!
- 校验通过后种子可成为同组种子的参考

## 目录结构

```
src/auto_qb/
├── cli.py             # 命令行入口(argparse)
├── config/            # 配置包: models(数据模型)/validation(全量校验)/loaders(解析加载)
├── curves.py          # 全局限速曲线纯逻辑: dat 解析/period 聚合/档位计算(无项目内依赖)
├── episodes.py        # 集数标签解析
├── exporter.py        # YAML 配置模板导出
├── logging.py         # 日志配置
├── qbmanager.py       # QbManager 主类: 主循环 2s tick，协调任务队列/规则/内置功能
├── qbapi.py           # qB API Facade: 封装客户端调用 + 写操作后同步 store 快照
├── taskqueue.py       # 单任务队列: 时间优先堆，所有任务(含校验结果轮询)统一调度
├── torrents.py        # 种子信息数据层: 全量快照+惰性缓存+分组索引，每main_tick刷新
├── utils.py           # 通用工具(速度/时间/大小解析，标签/路径匹配)
├── mixins/            # QbManager 组合 mixins
│   ├── checking.py    # 文件存在与大小检查(checking 动作前置检查)
│   ├── grouping.py    # 种子分组管理(辅种管理)
│   ├── rule_engine.py # 规则加载/状态持久化/种子级规则任务
│   ├── speed_curve.py # 全局限速曲线: Traffic Monitor 流量 -> qB 全局限速
│   ├── tags.py        # 标签/分类/HR 辅助
│   └── tracker.py     # tracker 配置匹配(hostname 精确匹配)/单种限速
└── rules/             # 规则插件框架(装饰器注册)
    ├── actions.py     # 11 种动作插件
    ├── base.py        # Rule/BaseCondition/BaseAction/ActionResult
    ├── conditions.py  # 15 种条件插件
    └── registry.py    # 条件/动作插件注册表
```

### 设计要点

- **单任务队列**: 所有功能都是带内置 interval 的任务，统一进时间优先堆(含校验结果轮询)。full-checking 发起后规则任务让位(defer)，轮询任务完成后 resume(校验成功，续跑后续动作)或 reschedule(失败，重走决策链)；主循环线程是唯一修改队列结构与 state_file 的线程，无需加锁
- **插件框架**: 条件/动作通过 `@register_condition` / `@register_action` 装饰器注册，按名称创建实例，易于扩展
- **mixins 组合**: `QbManager(RuleEngineMixin， TagsMixin， CheckingMixin， GroupingMixin， TrackerMixin， SpeedCurveMixin)`，职责清晰
- **状态持久化**: 规则执行历史、上传量快照、自动分类记录、限速曲线状态、跳检备份元数据统一存 `state_file`，程序退出时落盘

## 设计原则

- **幂等性**: 所有动作重复执行不应产生副作用或重复操作；需要"每天一次"等窗口语义的动作必须依赖状态文件去重，不能依赖循环频率
- **保守默认**: 高风险动作(跳检、强制汇报、删除种子、覆盖限速)默认关闭或只对显式允许的范围生效
- **状态持久化**: 跨轮次状态(规则执行历史、上传量快照、脚本设置过的限速等)统一存到 `state_file`，程序重启后继续有效
- **fail-fast**: 启动时全量校验配置(未知键、非法格式、非法 HR 规则)，尽早报错，不运行到一半才发现

## 开发测试

```bash
# 安装开发依赖
pip install pytest pytest-cov

# 运行全部测试
pytest tests -q

# 运行测试并输出覆盖率
pytest --cov=src --cov-report=term-missing tests -q

# 生成 HTML 覆盖率报告
pytest --cov=src --cov-report=html tests/
```

- 测试基础设施见 `tests/helpers.py`(FakeClient / FakeTorrent / FakeConfig，无需真实 qBittorrent)
- 每个测试文件头部 docstring 维护"## 测试计划"清单，新增测试须同步更新

## 许可证

LICENSE: [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)

本项目仅供个人学习与使用。请遵守各 PT 站点规则，谨慎使用高风险功能(跳检、强制汇报等)。
