# auto-qb (🚧施工中)

> PT Seed Auto Manager for qBittorrent — 基于 [qbittorrent-api](https://pypi.org/project/qbittorrent-api/) 的 PT 种子自动化管理工具

<table>
<tr>
<td>语言</td><td>Python 3.12+</td>
<td>依赖</td><td>qbittorrent-api / PyYAML</td>
</tr>
</table>

自动管理 qBittorrent 的 PT 种子: 标签/分类与 HR 管理、辅种分组与缺文件检查、自定义规则引擎(筛选条件 + 动作)、tracker 级限速与校验/跳检。所有功能均可配置，高风险动作默认关闭，只对显式允许的范围生效。

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
- 自动添加集数标签(种子添加时触发): 从文件列表解析，如 `01.mkv~05.mkv` → `E1-5`

### HR 管理

- 满足 HR 触发条件(下载比例/下载量)时自动添加 HR 标签或分类，如 `!!HR3D!!`，格式可自定义
- 做种时间满足「要求时间 + 额外时间」后自动添加完成标签或分类，如 `--HR3D--`，格式可自定义
- 站点配置可覆盖全局配置

### 辅种管理(种子分组)

- 将指向相同文件列表的种子自动归为一组，组内文件大小一致性检查(不一致 → 警告 + 整组暂停)
- 缺文件检查: 组内种子被删除、或由上传转暂停、或保存路径变化时立即触发磁盘扫描(仅验证文件存在性与大小)；文件丢失 → 整组暂停 + `MISSING` 标签
- 组内多个种子同时下载、或已完成与下载中并存 → 警告 + 整组暂停

### 自定义规则 🚧

- 触发时机 + 筛选条件 + 动作，动作顺序执行，支持去重与错误处理(详见[规则系统](#规则系统))
- 条件 15 种、动作 11 种，全部可组合

### 限速

- 规则动作支持单种上传/下载限速(`upload_speed_limit` / `download_speed_limit`)
- tracker 配置内置限速字段，种子添加时自动触发限速
- 限速不覆盖单数值，手动设置且不希望被覆盖的可以设置为单数比如: 2001 KiB/s

### 其他

- 主循环 2s tick，任务队列驱动，任务互不干扰，各自带内置 interval
- 根据已有种子 tracker 导出 YAML 配置模板(`--export-yaml --only-missing`，只追加不重写)
- 状态持久化到 `state_file`(规则执行历史/上传量快照/脚本限速记录)，重启继续有效
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
pip install pyyaml qbittorrent-api

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

- 标签/分类/路径匹配支持正则(`regex:` 前缀)与忽略大小写(`:ignore_case` 后缀)
- Windows 路径请使用 `/` 作为分隔符(`\` 在正则中用于转义)；路径匹配默认区分大小写
- 下载速度单位: `B/s` 或 `[KMG]iB/s`；文件大小单位: `B` 或 `[KMGT]iB`，不区分大小写
- 时间单位: `S` 秒、`M` 分、`H` 时、`D` 天，不区分大小写

### 完整示例

```yaml
---
config:
    main_tick: 2S          # 主循环时间间隔
    max_tasks_per_tick: 20 # 每个循环最大执行任务数

    interval: 60S          # 内置任务检查间隔(从上一轮处理结束开始计时，不叠加)

    state_file: "auto-qb-state.json" # 状态持久化文件，必须可写
    single_instance_lock: true       # 单实例锁 🚧

    log:
        file: "logs/auto-qb.log" # 日志文件路径， 留空仅输出控制台； 24/7运行建议落盘
        level: INFO         # 日志等级
        max_bytes: 10MiB    # 日志轮转大小
        format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s" # 日志格式

    remove_similar_tags: true # 删除种子类似(单词相同大小写不同)的标签
    add_episode_tags: true    # 自动添加集数标签(仅种子添加时触发)

    # 种子分组管理(辅种管理)
    grouping:
        enabled: true        # 启用种子分组
        missing_tag: MISSING # 文件丢失时整组添加的标签

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

    # qBittorrent 客户端
    qbittorrent:
        host: 127.0.0.1
        port: 8080
        username: <USERNAME>
        password: <PASSWORD>

    # 自定义规则集(名称以 "_rules" 结尾)
    example_rules: # 🚧
        rule1:
            enabled: true
            trigger: interval                     # 触发时机: 固定时间间隔循环
            interval: 60S                         # 执行间隔
            execute_once: never                   # 去重: never/once/daily/hourly
            cooldown: 0S                          # 距上次执行成功不足该时长则跳过
            conditions:                           # 筛选条件必须全部满足
                - path: /path/to/file             # 路径，支持正则
                - size: ">=100MiB"                # 文件大小
                - tags:                           # 标签(不同标签组之间为或)
                    - tag1,tag2
                - category:                       # 分类
                    - category
                - trackers:                       # tracker 自定义名称(不同组之间为或)
                    - tracker1
                - state:                          # 语义化状态(不同组之间为或)
                    - complete&uploading          # 已完成且正在上传(& 连接)
                - hr: condition-met               # condition-met/condition-not-met/satisfied
                - date_time:
                    day_of_month: 1-31
                    day_of_week: 1-7
                    time: 10:00-23:00
                - seedtime: "<24H"                # 做种时长
                - upload_ratio: ">1.5"            # 上传比率
                - upload_size: ">10GiB"           # 总上传大小
                - upload_size_today: ">10GiB"     # 今日上传大小(按自然日增量统计)
                - upload_size_this_week: ">10GiB"
                - upload_size_this_month: ">10GiB"
                - freespace:                      # 剩余空间
                    path: "R:/"
                    amount: "<100GiB"
            actions:                              # 动作顺序执行，默认一个出错后续不执行
                - checking:                       # ⚠️ 校验/跳检(见下方说明)
                    basic_check: filelist         # filelist/piecehashes/custom
                    with_reference:               # 有参考种子(已完成同组种子)
                        mode: skip-checking       # skip-checking 跳检(风险可控)/full-checking 全量校验
                        auto_start: true          # 校验成功后自动开始
                    without_reference:            # 无参考种子
                        mode: full-checking       # full-checking 安全；skip-checking 高风险
                        auto_start: true          # 校验成功后自动开始
                - start: true                     # 开始
                - stop: true                      # 暂停
                - ignore_next_action_error: true  # 忽略下一个动作的错误继续执行
                - add_tags:                       # 添加标签，支持变量
                    - tag-format1
                - remove_tags:                    # 删除标签，支持正则和变量
                    - tag-format3
                - add_category:                   # 添加分类
                    format: category-format
                    overwrite: true               # 强制覆盖已有分类
                - remove_category: true           # 自动删除站点分类
                - move_to:                        # ⚠️ 移动保存路径
                    path: /path/to/move/to
                    overwrite: true
                - reannounce: true                # ⚠️ 强制汇报 tracker(有风险)
                - upload_speed_limit: 1000KiB/s     # 上传速度，不覆盖单数值
                - download_speed_limit: 1000KiB/s   # 上传速度，不覆盖单数值
            stop_following_rules_if: conditions-met
            # 可选: conditions-met / conditions-not-met / action-failed /
            #       all-actions-succeed / always / never

    # tracker 站点配置 (建议直接使用`python src/auto-qb.py --export-yaml missing.yml --only-missing`直接导出后修改)
    trackers:
        tracker1:                           # 自定义 tracker 站点名称
            domains:                        # 站点域名，可以有多个
                - domain1
                - domain2
            tags:                           # 自动添加站点标签
                - tag1
            remove_tags:                    # 自动删除站点标签，支持正则
                - tag3
            upload_speed_limit: 1000KiB/s   # 单种上传限速，0 指无限制 🚧
            download_speed_limit: 10MiB/s   # 单种下载限速，0 指无限制 🚧
            hr:                             # HR 规则(可覆盖全局设置)
                required_seeding_time: 3D   # 要求做种时间
                required_share_ratio: 2.0   # 要求分享率
                extra_seeding_time: 12H     # 额外做种时间防止意外
                condition: 80%              # 触发 HR 的下载比例；也可用绝对值，如 10MiB
            rules:                          # tracker 引用规则
                - "@example_rules"          # 引用整个规则集
                - "@example_rules.rule1"    # 引用具体规则
```

### `checking` 动作说明

- `basic_check` 用于确定参考种子: `filelist` 对比两个种子的文件列表和文件大小(宽松)；`piecehashes` 额外对比两个种子每个块的 hash，不读取实际文件(对直接转种的种子有效，重新制作且块大小不同的种子无效)；`custom` 自定义程序
- **有参考种子**(组内有已完成、正在上传的同组种子): `full-checking` qb自带全量校验 __<font color="green">安全</font>__， `skip-checking` 跳检 __<font color="orange">风险相对可控</font>__
- **无参考种子**: `full-checking` __<font color="green">安全</font>__；`skip-checking` 为 __<font color="red">高风险</font>__ (仅做基础文件存在与大小对比，不做哈希校验直接开始，文件内容错误时会传垃圾数据，被大部分PT站点严令禁止)!
- 组内有种子正在下载 → 整组未完成，不进行任何校验(包括跳检)
- 校验通过后种子可成为同组种子的参考

## 规则系统

### 触发时机

| 触发时机                                  | 状态      | 说明                   |
|-------------------------------------------|-----------|------------------------|
| `interval`                                | ✅ 已实现  | 固定时间间隔循环一次   |
| `on_torrent_state_changed`                | 🚧 规划中 | 种子状态发生变化时触发 |
| `on_torrent_added` / `on_torrent_deleted` | 🚧 规划中 | 种子添加/删除时触发    |

### 筛选条件(15 种)

| 条件                     | 说明                                                                                    |
|--------------------------|-----------------------------------------------------------------------------------------|
| `path`                   | 保存路径，支持正则，使用 `/` 分隔符                                                       |
| `size`                   | 文件大小限制，支持比较符 `> < >= <=`                                                     |
| `tags`                   | 标签，不同标签组之间为或关系，支持正则和 `${required_seeding_time}` 变量                  |
| `category`               | 分类，支持正则和变量                                                                     |
| `trackers`               | tracker 自定义名称，不同组之间为或关系，支持正则                                          |
| `state`                  | 语义化状态(见状态映射表)，支持 `&` 连接多个状态                                          |
| `hr`                     | HR 筛选: `condition-met`(满足触发)/ `condition-not-met` / `satisfied`(满足要求+额外时长) |
| `date_time`              | 日期时间: `day_of_month` / `day_of_week` / `time`                                        |
| `seedtime`               | 做种时长                                                                                |
| `upload_ratio`           | 上传比率                                                                                |
| `upload_size`            | 总上传大小                                                                              |
| `upload_size_today`      | 今日上传大小: 基于 state_file 按自然日增量统计，同一天多次运行有效                        |
| `upload_size_this_week`  | 本周上传大小                                                                            |
| `upload_size_this_month` | 本月上传大小                                                                            |
| `freespace`              | 指定路径剩余空间                                                                        |

### 动作(11 种)

| 动作                                          | 说明                                                                                                         |
|-----------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| `checking`                                    | 校验/跳检: 确定参考种子后执行 skip-checking (__<font color="red">有风险!</font>__) 或 full-checking(异步校验) |
| `start` / `stop`                              | 开始 / 暂停种子                                                                                              |
| `add_tags` / `remove_tags`                    | 添加 / 删除标签，支持正则和变量                                                                               |
| `add_category` / `remove_category`            | 设置 / 清空分类，支持强制覆盖                                                                                 |
| `move_to`                                     | 移动保存路径                                                                                                 |
| `reannounce`                                  | 强制汇报 tracker(__<font color="red">有风险!</font>__)                                                       |
| `upload_speed_limit` / `download_speed_limit` | 单种上传 / 下载限速                                                                                          |
| `ignore_next_action_error`                    | 忽略下一个动作的错误继续执行(仅对下一个动作起效)                                                             |

### 去重与一次执行

- 规则默认 `execute_once: never`，只适合幂等动作(加/删标签、设分类)
- 非幂等动作(校验、开始、强制汇报、限速)必须配置 `execute_once` 或 `cooldown`，否则循环会在条件成立期间反复触发
- `execute_once` 可选: `never` / `once`(每种子只执行一次)/ `daily`(每种子每天最多一次)/ `hourly`(每种子每小时最多一次)
- `cooldown` 覆盖 `execute_once` 的粒度，如 `execute_once: never` + `cooldown: 10M`
- 执行历史记录在 `state_file`，键为 `规则名 + 种子 hash + 时间窗口(日/小时)`；`daily` 窗口按自然日切换，与 `upload_size_today` 统计口径一致

### 动作结果与错误处理

- 每个动作返回统一结果: `success` / `failed` / `skipped`
- `failed`: qB API 返回非 200 或抛出异常；`skipped`:条件不满足(如标签已存在、分类已设置)，不算失败
- `stop_following_rules_if: action-failed` 只对 `failed` 生效，`skipped` 不影响
- `ignore_next_action_error` 只对下一个动作生效，忽略 `failed` 继续执行

### 状态映射表

规则条件里的 `state` 是语义化状态，由 qB 原始 state 字符串映射而来:

| 语义状态      | 覆盖的 qB state                                               | 说明         |
|---------------|---------------------------------------------------------------|--------------|
| `checking`    | checking， checkingResumeData， checkingDL， checkingUP          | 正在校验     |
| `downloading` | downloading， forcedDL， metaDL， forcedMetaDL                   | 正在下载     |
| `complete`    | uploading， stalledUP， pausedUP， forcedUP， queuedUP， stoppedUP | 已完成下载   |
| `uploading`   | uploading， forcedUP， stalledUP                                | 正在上传做种 |
| `errored`     | missingFiles， error， unknown                                  | 出错         |
| `stopped`     | pausedDL， pausedUP， stoppedDL， stoppedUP                      | 已暂停/停止  |

`complete&uploading` = `is_complete 且 is_uploading`，即"正在做种中"。

## 目录结构

```
src/auto_qb/
├── cli.py             # 命令行入口(argparse)
├── config.py          # 配置数据类与加载(Config/TrackerConfig/HRRule)，fail-fast 校验
├── episodes.py        # 集数标签解析
├── exporter.py        # YAML 配置模板导出
├── logging.py         # 日志配置
├── qbmanager.py       # QbManager 主类: 主循环 2s tick，协调任务队列/规则/内置功能
├── taskqueue.py       # 双任务队列: 快速队列(时间优先堆)+ 慢速队列(异步校验轮询)
├── torrents.py        # 种子信息缓存, 避免频繁访问 qB API, 每main_tick刷新
├── utils.py           # 通用工具(速度/时间/大小解析，标签/路径匹配)
├── mixins/            # QbManager 组合 mixins
│   ├── checking.py    # 校验完成判定/异步校验轮询回调
│   ├── grouping.py    # 种子分组管理(辅种管理)
│   ├── rule_engine.py # 规则加载/状态持久化/种子级规则任务
│   ├── tags.py        # 标签/分类/HR 辅助
│   └── tracker.py     # tracker 配置匹配(hostname 精确匹配)
└── rules/             # 规则插件框架(装饰器注册)
    ├── actions.py     # 11 种动作插件
    ├── base.py        # Rule/BaseCondition/BaseAction/ActionResult
    ├── conditions.py  # 15 种条件插件
    └── registry.py    # 条件/动作插件注册表
```

### 设计要点

- **双任务队列**: 所有功能都是带内置 interval 的任务。快速队列为时间优先堆；慢速队列承载异步校验——工作线程仅发送校验请求，结果通过线程安全队列回传主循环轮询，不触碰队列结构、不写 state_file
- **插件框架**: 条件/动作通过 `@register_condition` / `@register_action` 装饰器注册，按名称创建实例，易于扩展
- **mixins 组合**: `QbManager(RuleEngineMixin， TagsMixin， CheckingMixin， GroupingMixin， TrackerMixin)`，职责清晰
- **状态持久化**: 规则执行历史、上传量快照、脚本限速记录统一存 `state_file`，程序退出时落盘；主循环线程是唯一修改队列结构与 state_file 的线程

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
pytest --cov=auto_qb --cov-report=term-missing tests -q

# 生成 HTML 覆盖率报告
pytest --cov=src --cov-report=html tests/
```

- 测试基础设施见 `tests/helpers.py`(FakeClient / FakeTorrent / FakeConfig，无需真实 qBittorrent)
- 每个测试文件头部 docstring 维护"## 测试计划"清单，新增测试须同步更新

## 许可证

LICENSE: [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)

本项目仅供个人学习与使用。请遵守各 PT 站点规则，谨慎使用高风险功能(跳检、强制汇报等)。
